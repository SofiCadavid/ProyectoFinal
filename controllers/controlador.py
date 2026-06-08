import cv2
import sys
from PyQt5.QtWidgets import QApplication, QMessageBox

# Modelos
from models.modelo_db import SistemaBaseDatos
from models.modelo_camara import ControlCamara
from models.modelo_dicom import ModeloDicom
from models.modelo_senales import ModeloSenales
from models.modelo_tablas import ModeloTablas

# Vistas
from views.Vista import VentanaBienvenida, VentanaLogin, VentanaCamara, VentanaDashboard


# Mapeos de constantes OpenCV para no exponer cv2 a la Vista
_TIPOS_UMBRAL = {
    0: cv2.THRESH_BINARY,
    1: cv2.THRESH_BINARY_INV,
    2: cv2.THRESH_TRUNC,
    3: cv2.THRESH_TOZERO,
    4: cv2.THRESH_TOZERO_INV,
}

_TIPOS_MORFOLOGIA = {
    0: cv2.MORPH_OPEN,
    1: cv2.MORPH_CLOSE,
    2: cv2.MORPH_ERODE,
    3: cv2.MORPH_DILATE,
    4: cv2.MORPH_GRADIENT,
}


class Coordinador:
    def __init__(self):
        # ── Modelos ─────────────────────────────────────────────────
        self.modelo_bd      = SistemaBaseDatos()
        self.modelo_camara  = ControlCamara()
        self.modelo_dicom   = ModeloDicom()
        self.modelo_senales = ModeloSenales()
        self.modelo_tablas  = ModeloTablas()

        # ── Vistas ──────────────────────────────────────────────────
        self.v_bienvenida = VentanaBienvenida(self)
        self.v_login      = VentanaLogin(self)
        self.v_camara     = VentanaCamara(self)
        self.v_dashboard  = VentanaDashboard(self)

        self.usuario_actual = None

    # FLUJO DE AUTENTICACIÓN (sin cambios respecto al original)
 
    def arrancar_aplicacion(self):
        self.v_bienvenida.show()

    def abrir_login(self):
        self.v_bienvenida.close()
        self.v_login.show()

    def validar_credenciales(self, usuario, password):
        resultado = self.modelo_bd.validar_usuario_en_bd(usuario, password)
        if resultado is not None:
            self.usuario_actual = resultado
            self.v_login.close()
            if self.modelo_camara.encender_camara():
                self.v_camara.show()
                self.v_camara.encender_refresco()
            else:
                QMessageBox.critical(self.v_login, "Error de Hardware", "No se pudo acceder a la cámara web.")
        else:
            QMessageBox.critical(self.v_login, "Acceso Denegado", "Usuario o contraseña incorrectos.")

    def obtener_cuadro_camara(self):
        return self.modelo_camara.leer_fotograma()

    def finalizar_verificacion(self):
        id_user = self.usuario_actual['id']
        ruta_foto = self.modelo_camara.capturar_y_guardar_disco(id_user)
        if ruta_foto:
            self.modelo_bd.guardar_sesion_foto(id_user, ruta_foto)
            self.modelo_camara.apagar_camara()
            self.v_camara.close()
            self.v_dashboard.show()
            QMessageBox.information(self.v_dashboard, "Éxito", "Bienvenido al sistema médico.")
        else:
            QMessageBox.warning(self.v_camara, "Error", "No se pudo capturar la foto. Reintente.")
            self.v_camara.encender_refresco()


    # MÓDULO DICOM
   
    def cargar_dicom(self, carpeta):
        """Carga la serie DICOM, actualiza sliders y muestra corte central."""
        exito, mensaje = self.modelo_dicom.cargar_serie_dicom(carpeta)
        if not exito:
            QMessageBox.critical(self.v_dashboard, "Error DICOM", mensaje)
            return

        # Ajustar rangos de los sliders al tamaño real del volumen
        max_ax, max_cor, max_sag = self.modelo_dicom.obtener_dimensiones_volumen()
        self.v_dashboard.actualizar_sliders_dicom(max_ax, max_cor, max_sag)

        # Mostrar corte central en los tres planos
        for plano, idx in [("axial", max_ax // 2), ("coronal", max_cor // 2), ("sagital", max_sag // 2)]:
            corte = self.modelo_dicom.obtener_corte(plano, idx)
            if corte is not None:
                self.v_dashboard.mostrar_corte(plano, corte)

        # Poblar tabla de metadatos
        datos = self.modelo_dicom.obtener_metadatos_como_lista()
        self.v_dashboard.poblar_tabla_metadatos(datos)
        QMessageBox.information(self.v_dashboard, "DICOM cargado", mensaje)

    def actualizar_corte(self, plano, indice):
        """Llamado por el slider — recupera el corte y lo pinta."""
        corte = self.modelo_dicom.obtener_corte(plano, indice)
        if corte is not None:
            self.v_dashboard.mostrar_corte(plano, corte)

    def exportar_metadatos_csv(self):
        ruta = self.modelo_dicom.guardar_metadatos_csv()
        QMessageBox.information(self.v_dashboard, "CSV exportado", f"Metadatos guardados en:\n{ruta}")

    def convertir_a_nifti(self):
        exito, mensaje = self.modelo_dicom.convertir_a_nifti()
        nivel = QMessageBox.information if exito else QMessageBox.critical
        nivel(self.v_dashboard, "Conversión NIfTI", mensaje)

    def aplicar_zoom_y_recorte(self, plano, indice, x1, y1, x2, y2):
        img_orig, img_rec, texto = self.modelo_dicom.aplicar_zoom_y_recorte(
            plano, indice, x1, y1, x2, y2
        )
        if img_orig is not None:
            self.v_dashboard.mostrar_zoom(img_orig, img_rec, texto)

    def guardar_recorte(self, nombre):
        exito, mensaje = self.modelo_dicom.guardar_recorte(nombre)
        nivel = QMessageBox.information if exito else QMessageBox.warning
        nivel(self.v_dashboard, "Guardar recorte", mensaje)

    def segmentar_imagen(self, idx_umbral, valor_umbral, tam_kernel, idx_morfologia):
        """
        Toma el último recorte disponible, lo binariza y aplica morfología.
        """
        recorte = self.modelo_dicom.recorte_actual
        if recorte is None:
            QMessageBox.warning(self.v_dashboard, "Sin imagen", "Primero genere un recorte con el zoom.")
            return

        # Convertir a escala de grises si es BGR
        if recorte.ndim == 3:
            gris = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
        else:
            gris = recorte

        tipo_thresh = _TIPOS_UMBRAL.get(idx_umbral, cv2.THRESH_BINARY)
        tipo_morf   = _TIPOS_MORFOLOGIA.get(idx_morfologia, cv2.MORPH_OPEN)

        binarizada   = self.modelo_dicom.aplicar_binarizacion(gris, valor_umbral, tipo_thresh)
        morfologica  = self.modelo_dicom.aplicar_morfologia(binarizada, tipo_morf, tam_kernel)

        self.v_dashboard.mostrar_segmentacion(binarizada, morfologica)
        
    # MÓDULO SEÑALES
  
    def cargar_señal(self, ruta):
        exito, mensaje = self.modelo_senales.cargar_mat(ruta)
        if exito:
            # Actualizar el rango máximo del SpinBox de canal en la vista
            n_canales = self.modelo_senales.obtener_num_canales()
            n_muestras = self.modelo_senales.obtener_num_muestras()
            self.v_dashboard.spinCanalSenal.setMaximum(n_canales - 1)
            self.v_dashboard.spinCanalRuido.setMaximum(n_canales - 1)
            self.v_dashboard.spinInicio.setMaximum(n_muestras - 1)
            self.v_dashboard.spinFin.setMaximum(n_muestras)
            self.v_dashboard.spinFin.setValue(n_muestras)
        QMessageBox.information(self.v_dashboard, "Archivo MAT", mensaje)

    def graficar_canal(self, indice_canal, inicio, fin):
        canal = self.modelo_senales.obtener_canal(indice_canal, inicio, fin)
        if canal is None:
            return
        tiempo = list(range(len(canal)))
        self.v_dashboard.mostrar_canal_senal(tiempo, canal, f"Canal {indice_canal} [{inicio}:{fin}]")

    def mostrar_canal_ruidoso(self, indice_canal, desviacion):
        original, ruidosa = self.modelo_senales.agregar_ruido_gaussiano(indice_canal, desviacion)
        if original is not None:
            self.v_dashboard.mostrar_señal_vs_ruidosa(original, ruidosa)

    def calcular_estadisticas_3d(self, eje):
        prom, desv, nombre, unidades = self.modelo_senales.calcular_estadisticas_3d(eje)
        if prom is not None:
            self.v_dashboard.mostrar_estadisticas_stem(prom, desv, nombre, unidades)
        else:
            QMessageBox.warning(self.v_dashboard, "Sin datos", "Primero cargue un archivo .mat.")

    # MÓDULO TABLAS
   
    def cargar_tabla(self, ruta):
        exito, mensaje = self.modelo_tablas.cargar_archivo(ruta)
        if not exito:
            QMessageBox.critical(self.v_dashboard, "Error", mensaje)
            return

        # Poblar combos y lista de columnas numéricas
        cols_num = self.modelo_tablas.obtener_columnas_numericas()
        self.v_dashboard.poblar_combos_columnas(cols_num)

        # Mostrar .describe() y .info() en las tablas de la interfaz
        enc_desc, filas_desc = self.modelo_tablas.obtener_describe_como_lista()
        self.v_dashboard.poblar_tabla_generica(self.v_dashboard.tablaDescribeDf, enc_desc, filas_desc)

        enc_info, filas_info = self.modelo_tablas.obtener_info_como_lista()
        self.v_dashboard.poblar_tabla_generica(self.v_dashboard.tablaInfoDf, enc_info, filas_info)

        QMessageBox.information(self.v_dashboard, "Tabla cargada", mensaje)

    def graficar_columnas(self, nombres_columnas):
        datos = {}
        for nombre in nombres_columnas:
            serie = self.modelo_tablas.obtener_serie(nombre)
            if serie is not None:
                datos[nombre] = serie
        if datos:
            self.v_dashboard.mostrar_plot_columnas(datos)

    def graficar_scatter(self, col_x, col_y):
        sx, sy = self.modelo_tablas.obtener_dos_series_para_scatter(col_x, col_y)
        if sx is not None:
            self.v_dashboard.mostrar_scatter(sx, sy, col_x, col_y)
        else:
            QMessageBox.warning(self.v_dashboard, "Sin datos", "Seleccione columnas válidas.")
    

# PUNTO DE ENTRADA

if __name__ == "__main__":
    app = QApplication(sys.argv)
    coordinador = Coordinador()
    coordinador.arrancar_aplicacion()
    sys.exit(app.exec_())
