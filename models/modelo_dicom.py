"""Procesamiento de imágenes médicas DICOM/NIfTI — Modelo MVC."""
import os
import numpy as np
import pandas as pd
import cv2
import pydicom
import nibabel as nib
from datetime import datetime


class ModeloDicom:
    def __init__(self):
        self.volumen_3d  = None   
        self.metadatos   = {}
        self.datasets    = []
        self.recorte_actual = None  

    def cargar_serie(self, carpeta):
        """Carga y ordena slices DICOM, construye volumen 3D y extrae metadatos."""
        try:
            dcms = [pydicom.dcmread(os.path.join(carpeta, f))
                    for f in os.listdir(carpeta) if f.lower().endswith(".dcm")]
        except Exception as e:
            return False, str(e)

        if not dcms:
            return False, "No se hallaron archivos .dcm en la carpeta."

        try:
            dcms.sort(key=lambda d: float(getattr(d, "ImagePositionPatient", [0, 0, 0])[2]))
        except Exception:
            try:
                dcms.sort(key=lambda d: int(d.InstanceNumber))
            except Exception:
                pass

        self.datasets    = dcms
        self.volumen_3d  = np.stack([d.pixel_array for d in dcms], 0).astype(np.float64)

        if str(dcms[0].get("Modality", "")).upper() == "CT":
            slope     = float(dcms[0].get("RescaleSlope", 1))
            intercept = float(dcms[0].get("RescaleIntercept", 0))
            self.volumen_3d = self.volumen_3d * slope + intercept

        self._extraer_metadatos(dcms[0])
        return True, f"Serie cargada: {len(dcms)} cortes."

    def _extraer_metadatos(self, ds):
        """Parsea tags DICOM relevantes y calcula duración del estudio."""
        def fmt_fecha(s):
            try:    return datetime.strptime(s, "%Y%m%d").strftime("%d/%m/%Y")
            except: return s or "N/D"

        def fmt_hora(s):
            try:    return datetime.strptime(s[:6], "%H%M%S").strftime("%H:%M:%S")
            except: return s or "N/D"

        def duracion(h1, h2):
            try:
                d = datetime.strptime(h2[:6], "%H%M%S") - datetime.strptime(h1[:6], "%H%M%S")
                m = int(d.total_seconds() // 60)
                return f"{m} min {int(d.total_seconds() % 60)} s"
            except:
                return "N/D"

        ti = str(ds.get("StudyTime",  "") or "")
        ts = str(ds.get("SeriesTime", "") or "")

        self.metadatos = {
            "Paciente":      str(ds.get("PatientName",       "N/D")),
            "ID Paciente":   str(ds.get("PatientID",         "N/D")),
            "Fecha Estudio": fmt_fecha(str(ds.get("StudyDate",      "") or "")),
            "Hora Estudio":  fmt_hora(ti),
            "Hora Serie":    fmt_hora(ts),
            "Duración":      duracion(ti, ts),
            "Modalidad":     str(ds.get("Modality",          "N/D")),
            "Fabricante":    str(ds.get("Manufacturer",      "N/D")),
            "Descripción":   str(ds.get("StudyDescription",  "N/D")),
            "Cortes":        str(len(self.datasets)),
        }

    def guardar_csv(self, ruta="metadatos_dicom.csv"):
        """Exporta metadatos a CSV con Pandas."""
        pd.DataFrame(list(self.metadatos.items()),
                     columns=["Campo", "Valor"]).to_csv(ruta, index=False)
        return ruta

    def metadatos_lista(self):
        """Retorna lista de tuplas (campo, valor) para QTableWidget."""
        return list(self.metadatos.items())

    def dimensiones(self):
        """Retorna (max_axial, max_coronal, max_sagital) para los sliders."""
        if self.volumen_3d is None:
            return (0, 0, 0)
        z, y, x = self.volumen_3d.shape
        return (z - 1, y - 1, x - 1)

    def obtener_corte(self, plano, idx, aplicar_aspecto=True):
        """Devuelve corte 2D normalizado a uint8 aplicando la escala física real."""
        if self.volumen_3d is None:
            return None
        
        v = self.volumen_3d
        
        # 1. Validación de seguridad para los índices de los sliders (Evita el IndexError)
        if plano == "axial":
            idx = max(0, min(idx, v.shape[0] - 1))
            corte = v[idx, :, :]
        elif plano == "coronal":
            idx = max(0, min(idx, v.shape[1] - 1))
            corte = v[:, idx, :]
        elif plano == "sagital":
            idx = max(0, min(idx, v.shape[2] - 1))
            corte = v[:, :, idx]
        else:
            return None

        # 2. Normalización a 0-255 (uint8)
        mn, mx = corte.min(), corte.max()
        img_uint8 = ((corte - mn) / (mx - mn + 1e-9) * 255).astype(np.uint8)
        
        # 3. Corrección de proporciones isométricas reales usando mm
        if aplicar_aspecto and plano != "axial":
            ds = self.datasets[0]
            
            # Obtenemos los tamaños reales de los píxeles en milímetros
            slice_thickness = float(getattr(ds, "SliceThickness", 1.0))
            pixel_size = float(getattr(ds, "PixelSpacing", [1.0, 1.0])[0])
            
            # Dimensiones actuales en píxeles de la matriz reconstruida (Alto es Z con tamaño 22)
            alto_matriz, ancho_matriz = img_uint8.shape
            
            # Calculamos el tamaño físico real que debería tener la imagen en milímetros
            ancho_mm = ancho_matriz * pixel_size
            alto_mm = alto_matriz * slice_thickness
            
            # Seteamos el nuevo alto mapeándolo proporcionalmente al ancho de la matriz original
            nuevo_ancho = ancho_matriz
            nuevo_alto = int(ancho_matriz * (alto_mm / ancho_mm))
            
            # Redimensionamos la imagen final usando interpolación lineal
            if nuevo_alto > 0 and nuevo_ancho > 0:
                img_uint8 = cv2.resize(img_uint8, (nuevo_ancho, nuevo_alto), 
                                       interpolation=cv2.INTER_LINEAR)
        
        return img_uint8

    def convertir_nifti(self, ruta="volumen.nii.gz"):
        """Convierte el volumen 3D a NIfTI."""
        if self.volumen_3d is None:
            return False, "Sin datos DICOM cargados."
        ds  = self.datasets[0]
        ps  = getattr(ds, "PixelSpacing", [1.0, 1.0])
        st  = float(getattr(ds, "SliceThickness", 1.0))
        aff = np.diag([float(ps[1]), float(ps[0]), st, 1.0])
        nib.save(nib.Nifti1Image(self.volumen_3d, aff), ruta)
        return True, f"NIfTI guardado en: {ruta}"

    def zoom_recorte(self, plano, idx, x1, y1, x2, y2, escala=2.0):
        """Recorta ROI, redimensiona con OpenCV y dibuja rectángulo con mm."""
        corte = self.obtener_corte(plano, idx)
        if corte is None:
            return None, None, ""

        bgr  = cv2.cvtColor(corte, cv2.COLOR_GRAY2BGR)
        roi  = bgr[y1:y2, x1:x2]
        if roi.size == 0:
            return bgr, bgr, "ROI inválida"

        amplia = cv2.resize(roi,
                            (int(roi.shape[1] * escala), int(roi.shape[0] * escala)),
                            interpolation=cv2.INTER_LINEAR)

        try:
            ps  = self.datasets[0].PixelSpacing
            txt = f"{(x2-x1)*float(ps[1]):.1f} x {(y2-y1)*float(ps[0]):.1f} mm"
        except Exception:
            txt = f"{x2-x1} x {y2-y1} px"

        marc = bgr.copy()
        cv2.rectangle(marc, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.putText(marc, txt, (x1, max(y1 - 8, 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

        self.recorte_actual = amplia 
        return marc, amplia, txt

    def guardar_recorte(self, nombre):
        """Guarda el último recorte en disco."""
        if self.recorte_actual is None:
            return False, "Sin recorte generado."
        os.makedirs("recortes", exist_ok=True)
        ruta = os.path.join("recortes", nombre)
        cv2.imwrite(ruta, self.recorte_actual)
        return True, f"Guardado en: {ruta}"

    def binarizar(self, img_gray, umbral, tipo_cv2):
        """Aplica umbralización OpenCV."""
        _, result = cv2.threshold(img_gray, umbral, 255, tipo_cv2)
        return result

    def morfologia(self, img_bin, op_cv2, tam_kernel):
        """Aplica operación morfológica con kernel rectangular."""
        k = cv2.getStructuringElement(cv2.MORPH_RECT, (tam_kernel, tam_kernel))
        return cv2.morphologyEx(img_bin, op_cv2, k)