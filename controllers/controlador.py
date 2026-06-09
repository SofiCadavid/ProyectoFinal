import cv2
import sys
from PyQt5.QtWidgets import QApplication, QMessageBox

# Modelos
from models.modelo_db     import SistemaBaseDatos
from models.modelo_camara import ControlCamara
from models.modelo_dicom  import ModeloDicom
from models.modelo_senales import ModeloSenales
from models.modelo_tablas  import ModeloTablas

from views.Vista import (
    VentanaBienvenida, VentanaLogin, VentanaCamara, VentanaDashboard
)

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
        self.modelo_bd      = SistemaBaseDatos()
        self.modelo_camara  = ControlCamara()
        self.modelo_dicom   = ModeloDicom()
        self.modelo_senales = ModeloSenales()
        self.modelo_tablas  = ModeloTablas()
        self.v_bienvenida = VentanaBienvenida(self)
        self.v_login      = VentanaLogin(self)
        self.v_camara     = VentanaCamara(self)
        self.v_dashboard  = VentanaDashboard(self)

        self.usuario_actual = None

    def arrancar_aplicacion(self):
        self.v_bienvenida.show()

    def abrir_login(self):
        self.v_bienvenida.close()
        self.v_login.show()

    def validar_credenciales(self, usuario: str, password: str):
        resultado = self.modelo_bd.validar_usuario_en_bd(usuario, password)
        if resultado is not None:
            self.usuario_actual = resultado
            self.v_login.close()
            if self.modelo_camara.encender_camara():
                self.v_camara.show()
                self.v_camara.encender_refresco()
            else:
                QMessageBox.critical(self.v_login, "Error de Hardware",
                                     "No se pudo acceder a la cámara web.")
        else:
            QMessageBox.critical(self.v_login, "Acceso Denegado",
                                 "Usuario o contraseña incorrectos.")

    def obtener_cuadro_camara(self):
        return self.modelo_camara.leer_fotograma()

    def finalizar_verificacion(self):
        id_user   = self.usuario_actual["id"]
        ruta_foto = self.modelo_camara.capturar_y_guardar_disco(id_user)
        if ruta_foto:
            self.modelo_bd.guardar_sesion_foto(id_user, ruta_foto)
            self.modelo_camara.apagar_camara()
            self.v_camara.close()
            self.v_dashboard.set_nombre_usuario(
                str(self.usuario_actual.get("nombre", ""))
            )
            self.v_dashboard.show()
            QMessageBox.information(self.v_dashboard, "Éxito",
                                    "Bienvenido al sistema médico Vitalis.")
        else:
            QMessageBox.warning(self.v_camara, "Error",
                                "No se pudo capturar la foto. Reintente.")
            self.v_camara.encender_refresco()

    def crear_usuario(self, nombre: str, password: str, rol: str):
        """Crea un nuevo usuario en la BD y refresca la tabla."""
        try:
            self.modelo_bd.crear_usuario(nombre, password, rol)
            self.v_dashboard.mostrar_mensaje_usuario(
                f"Usuario '{nombre}' creado correctamente.", exito=True
            )
            self.cargar_usuarios()
        except Exception as e:
            self.v_dashboard.mostrar_mensaje_usuario(
                f"Error al crear usuario: {e}", exito=False
            )

    def cargar_usuarios(self):
        """Obtiene todos los usuarios de la BD y los muestra en la tabla."""
        try:
            usuarios = self.modelo_bd.obtener_todos_los_usuarios()
            self.v_dashboard.poblar_tabla_usuarios(usuarios)
        except Exception as e:
            QMessageBox.warning(self.v_dashboard, "Error BD",
                                f"No se pudieron cargar usuarios: {e}")

    def cargar_dicom(self, carpeta: str):
        """Carga serie DICOM, ajusta sliders y muestra cortes centrales."""
        exito, mensaje = self.modelo_dicom.cargar_serie(carpeta)
        if not exito:
            QMessageBox.critical(self.v_dashboard, "Error DICOM", mensaje)
            return

        max_ax, max_cor, max_sag = self.modelo_dicom.dimensiones()
        self.v_dashboard.actualizar_sliders_dicom(max_ax, max_cor, max_sag)

        for plano, idx in [("axial", max_ax // 2),
                           ("coronal", max_cor // 2),
                           ("sagital", max_sag // 2)]:
            corte = self.modelo_dicom.obtener_corte(plano, idx)
            if corte is not None:
                self.v_dashboard.mostrar_corte(plano, corte)

        datos = self.modelo_dicom.metadatos_lista()
        self.v_dashboard.poblar_tabla_metadatos(datos)
        QMessageBox.information(self.v_dashboard, "DICOM cargado", mensaje)

    def actualizar_corte(self, plano: str, indice: int):
        corte = self.modelo_dicom.obtener_corte(plano, indice)
        if corte is not None:
            self.v_dashboard.mostrar_corte(plano, corte)

    def exportar_metadatos_csv(self):
        ruta = self.modelo_dicom.guardar_csv()
        QMessageBox.information(self.v_dashboard, "CSV exportado",
                                f"Metadatos guardados en:\n{ruta}")

    def convertir_a_nifti(self):
        exito, mensaje = self.modelo_dicom.convertir_nifti()
        (QMessageBox.information if exito else QMessageBox.critical)(
            self.v_dashboard, "Conversión NIfTI", mensaje
        )

    def aplicar_zoom_y_recorte(self, plano: str, indice: int,
                                x1: int, y1: int, x2: int, y2: int):
        img_orig, img_rec, texto = self.modelo_dicom.zoom_recorte(
            plano, indice, x1, y1, x2, y2
        )
        if img_orig is not None:
            self.v_dashboard.mostrar_zoom(img_orig, img_rec, texto)

    def guardar_recorte(self, nombre: str):
        exito, mensaje = self.modelo_dicom.guardar_recorte(nombre)
        (QMessageBox.information if exito else QMessageBox.warning)(
            self.v_dashboard, "Guardar recorte", mensaje
        )

    def segmentar_imagen(self, idx_umbral: int, valor_umbral: int,
                         tam_kernel: int, idx_morfologia: int):
        recorte = self.modelo_dicom.recorte_actual
        if recorte is None:
            QMessageBox.warning(self.v_dashboard, "Sin imagen",
                                "Primero genere un recorte con el botón Zoom.")
            return

        import cv2 as cv
        gris = cv.cvtColor(recorte, cv.COLOR_BGR2GRAY) if recorte.ndim == 3 else recorte
        tipo_thresh = _TIPOS_UMBRAL.get(idx_umbral, cv.THRESH_BINARY)
        tipo_morf   = _TIPOS_MORFOLOGIA.get(idx_morfologia, cv.MORPH_OPEN)

        binarizada  = self.modelo_dicom.binarizar(gris, valor_umbral, tipo_thresh)
        morfologica = self.modelo_dicom.morfologia(binarizada, tipo_morf, tam_kernel)
        self.v_dashboard.mostrar_segmentacion(binarizada, morfologica)

    def cargar_señal(self, ruta: str):
        exito, mensaje = self.modelo_senales.cargar_mat(ruta)
        if exito:
            n_c = self.modelo_senales.num_canales()
            n_m = self.modelo_senales.num_muestras()
            self.v_dashboard.spinCanalSenal.setMaximum(n_c - 1)
            self.v_dashboard.spinCanalRuido.setMaximum(n_c - 1)
            self.v_dashboard.spinInicio.setMaximum(n_m - 1)
            self.v_dashboard.spinFin.setMaximum(n_m)
            self.v_dashboard.spinFin.setValue(n_m)
        QMessageBox.information(self.v_dashboard, "Archivo MAT", mensaje)

    def graficar_canal(self, indice: int, inicio: int, fin: int):
        canal = self.modelo_senales.canal(indice, inicio, fin)
        if canal is None:
            return
        self.v_dashboard.mostrar_canal_senal(
            list(range(len(canal))), list(canal),
            f"Canal {indice}  [{inicio}:{fin}]"
        )

    def mostrar_canal_ruidoso(self, indice: int, desviacion: float):
        original, ruidosa = self.modelo_senales.agregar_ruido(indice, desviacion)
        if original is not None:
            self.v_dashboard.mostrar_señal_vs_ruidosa(original, ruidosa)

    def calcular_estadisticas_3d(self, eje: int):
        prom, desv, nombre, unidades = self.modelo_senales.estadisticas_3d(eje)
        if prom is not None:
            self.v_dashboard.mostrar_estadisticas_stem(prom, desv, nombre, unidades)
        else:
            QMessageBox.warning(self.v_dashboard, "Sin datos",
                                "Primero cargue un archivo .mat.")

    def cargar_tabla(self, ruta: str):
        exito, mensaje = self.modelo_tablas.cargar(ruta)
        if not exito:
            QMessageBox.critical(self.v_dashboard, "Error", mensaje)
            return

        cols_num = self.modelo_tablas.cols_numericas()
        self.v_dashboard.poblar_combos_columnas(cols_num)

        enc_desc, filas_desc = self.modelo_tablas.describe_lista()
        self.v_dashboard.poblar_tabla_generica(
            self.v_dashboard.tablaDescribeDf, enc_desc, filas_desc
        )
        enc_info, filas_info = self.modelo_tablas.info_lista()
        self.v_dashboard.poblar_tabla_generica(
            self.v_dashboard.tablaInfoDf, enc_info, filas_info
        )
        QMessageBox.information(self.v_dashboard, "Tabla cargada", mensaje)

    def graficar_columnas(self, nombres_columnas: list):
        datos = {}
        for nombre in nombres_columnas:
            serie = self.modelo_tablas.serie(nombre)
            if serie is not None:
                datos[nombre] = serie
        if datos:
            self.v_dashboard.mostrar_plot_columnas(datos)

    def graficar_scatter(self, col_x: str, col_y: str):
        sx, sy = self.modelo_tablas.scatter_data(col_x, col_y)
        if sx is not None:
            self.v_dashboard.mostrar_scatter(sx, sy, col_x, col_y)
        else:
            QMessageBox.warning(self.v_dashboard, "Sin datos",
                                "Seleccione columnas válidas.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    coordinador = Coordinador()
    coordinador.arrancar_aplicacion()
    sys.exit(app.exec_())