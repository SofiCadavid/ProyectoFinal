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
        self.volumen_3d = None
        self.metadatos  = {}
        self.datasets   = []
        self.recorte    = None

    def cargar_serie(self, carpeta):
        """Carga y ordena slices DICOM, construye volumen 3D y extrae metadatos."""
        dcms = [pydicom.dcmread(os.path.join(carpeta, f))
                for f in os.listdir(carpeta) if f.lower().endswith(".dcm")]
        if not dcms:
            return False, "No se hallaron archivos .dcm."
        dcms.sort(key=lambda d: float(getattr(d, "ImagePositionPatient", [0,0,0])[2]))
        self.datasets   = dcms
        self.volumen_3d = np.stack([d.pixel_array for d in dcms], 0).astype(np.float64)
        if str(dcms[0].get("Modality","")).upper() == "CT":
            slope     = float(dcms[0].get("RescaleSlope", 1))
            intercept = float(dcms[0].get("RescaleIntercept", 0))
            self.volumen_3d = self.volumen_3d * slope + intercept
        self._extraer_metadatos(dcms[0])
        return True, "Serie cargada correctamente."

    def _extraer_metadatos(self, ds):
        """Parsea tags DICOM relevantes y calcula duración del estudio."""
        def fmt_fecha(s):
            try: return datetime.strptime(s, "%Y%m%d").strftime("%d/%m/%Y")
            except: return s
        def fmt_hora(s):
            try: return datetime.strptime(s[:6], "%H%M%S").strftime("%H:%M:%S")
            except: return s
        def duracion(h1, h2):
            try:
                d = datetime.strptime(h2[:6],"%H%M%S") - datetime.strptime(h1[:6],"%H%M%S")
                m = int(d.total_seconds()//60)
                return f"{m} min {int(d.total_seconds()%60)} s"
            except: return "N/D"
        ti, ts = str(ds.get("StudyTime","")), str(ds.get("SeriesTime",""))
        self.metadatos = {
            "Paciente":        str(ds.get("PatientName","N/D")),
            "ID Paciente":     str(ds.get("PatientID","N/D")),
            "Fecha Estudio":   fmt_fecha(str(ds.get("StudyDate",""))),
            "Hora Estudio":    fmt_hora(ti),
            "Hora Serie":      fmt_hora(ts),
            "Duración":        duracion(ti, ts),
            "Modalidad":       str(ds.get("Modality","N/D")),
            "Fabricante":      str(ds.get("Manufacturer","N/D")),
            "Descripción":     str(ds.get("StudyDescription","N/D")),
            "Cortes":          str(len(self.datasets)),
        }

    def guardar_csv(self, ruta="metadatos.csv"):
        """Exporta metadatos a CSV con Pandas."""
        pd.DataFrame(list(self.metadatos.items()), columns=["Campo","Valor"]).to_csv(ruta, index=False)
        return ruta

    def metadatos_lista(self):
        """Retorna lista de tuplas para poblar QTableWidget."""
        return list(self.metadatos.items())

    def convertir_nifti(self, ruta="volumen.nii.gz"):
        """Convierte el volumen 3D a NIfTI usando PixelSpacing y SliceThickness."""
        if self.volumen_3d is None: return False, "Sin datos."
        ds = self.datasets[0]
        ps = getattr(ds, "PixelSpacing", [1.0, 1.0])
        st = float(getattr(ds, "SliceThickness", 1.0))
        nib.save(nib.Nifti1Image(self.volumen_3d, np.diag([float(ps[1]), float(ps[0]), st, 1.0])), ruta)
        return True, f"Guardado: {ruta}"

    def obtener_corte(self, plano, idx):
        """Devuelve corte 2D normalizado a uint8 según plano ('axial','sagital','coronal')."""
        if self.volumen_3d is None: return None
        corte = {"axial": self.volumen_3d[idx,:,:],
                 "sagital": self.volumen_3d[:,:,idx],
                 "coronal": self.volumen_3d[:,idx,:]}.get(plano)
        if corte is None: return None
        mn, mx = corte.min(), corte.max()
        return ((corte-mn)/(mx-mn+1e-9)*255).astype(np.uint8)

    def dimensiones(self):
        """Retorna (max_axial, max_coronal, max_sagital) para los sliders."""
        if self.volumen_3d is None: return (0,0,0)
        z,y,x = self.volumen_3d.shape
        return (z-1, y-1, x-1)

    def zoom_recorte(self, plano, idx, x1, y1, x2, y2, escala=2.0):
        """Recorta ROI, redimensiona y dibuja rectángulo con dimensiones en mm."""
        corte = self.obtener_corte(plano, idx)
        if corte is None: return None, None, ""
        bgr    = cv2.cvtColor(corte, cv2.COLOR_GRAY2BGR)
        roi    = bgr[y1:y2, x1:x2]
        if roi.size == 0: return bgr, bgr, "ROI inválida"
        amplia = cv2.resize(roi, (int(roi.shape[1]*escala), int(roi.shape[0]*escala)))
        try:
            ps  = self.datasets[0].PixelSpacing
            txt = f"{(x2-x1)*float(ps[1]):.1f} x {(y2-y1)*float(ps[0]):.1f} mm"
        except: txt = f"{x2-x1} x {y2-y1} px"
        marc = bgr.copy()
        cv2.rectangle(marc, (x1,y1),(x2,y2),(0,0,255),2)
        cv2.putText(marc, txt,(x1, max(y1-8,12)), cv2.FONT_HERSHEY_SIMPLEX, 0.45,(0,255,0),1)
        self.recorte = amplia
        return marc, amplia, txt

    def guardar_recorte(self, nombre):
        """Guarda el último recorte en disco."""
        if self.recorte is None: return False, "Sin recorte."
        os.makedirs("recortes", exist_ok=True)
        ruta = os.path.join("recortes", nombre)
        cv2.imwrite(ruta, self.recorte)
        return True, f"Guardado: {ruta}"

    def binarizar(self, img_gray, umbral, tipo_cv2):
        """Aplica umbralización OpenCV."""
        _, result = cv2.threshold(img_gray, umbral, 255, tipo_cv2)
        return result

    def morfologia(self, img_bin, op_cv2, tam_kernel):
        """Aplica operación morfológica con kernel rectangular."""
        k = cv2.getStructuringElement(cv2.MORPH_RECT, (tam_kernel, tam_kernel))
        return cv2.morphologyEx(img_bin, op_cv2, k)
