import sys
import io
import numpy as np
import matplotlib
matplotlib.use("Agg")                     
import matplotlib.pyplot as plt

from PyQt5.QtWidgets import (
    QMainWindow, QMessageBox, QFileDialog
)
from PyQt5.uic import loadUi
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap

def _numpy_a_pixmap(imagen_np: np.ndarray) -> QPixmap:
    """Convierte un array numpy (uint8, escala de grises o BGR) a QPixmap."""
    if imagen_np.ndim == 2:
        alto, ancho = imagen_np.shape
        qimg = QImage(imagen_np.data, ancho, alto, ancho, QImage.Format_Grayscale8)
    else:
        alto, ancho, _ = imagen_np.shape
        rgb = imagen_np[:, :, ::-1].copy()          # BGR → RGB
        qimg = QImage(rgb.data, ancho, alto, ancho * 3, QImage.Format_RGB888)
    return QPixmap.fromImage(qimg)


def _figura_a_pixmap(fig: plt.Figure) -> QPixmap:
    """Renderiza una figura Matplotlib en memoria y la convierte a QPixmap."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=96,
                facecolor="#FAFFFC")
    buf.seek(0)
    pixmap = QPixmap()
    pixmap.loadFromData(buf.read())
    plt.close(fig)
    return pixmap


def _mostrar_en_label(label, pixmap: QPixmap):
    """Escala el QPixmap al tamaño del QLabel manteniendo proporciones."""
    label.setPixmap(
        pixmap.scaled(label.width(), label.height(), Qt.KeepAspectRatio,
                      Qt.SmoothTransformation)
    )

class VentanaBienvenida(QMainWindow):
    def __init__(self, coordinador=None):
        super().__init__()
        loadUi("views/ui/bienvenida.ui", self)
        self.__coordinador = coordinador
        self.btnEntrar.clicked.connect(self.__coordinador.abrir_login)

class VentanaLogin(QMainWindow):
    def __init__(self, coordinador=None):
        super().__init__()
        loadUi("views/ui/login.ui", self)
        self.__coordinador = coordinador
        self.btnLogin.clicked.connect(self.__intentar_ingresar)

    def __intentar_ingresar(self):
        usuario  = self.lineEditUsuario.text().strip()
        password = self.lineEditPassword.text()
        if not usuario or not password:
            QMessageBox.warning(self, "Campos vacíos",
                                "Por favor, ingrese usuario y contraseña.")
            return
        self.__coordinador.validar_credenciales(usuario, password)

class VentanaCamara(QMainWindow):
    def __init__(self, coordinador=None):
        super().__init__()
        loadUi("views/ui/verificacion.ui", self)
        self.__coordinador = coordinador
        self.__timer = QTimer()
        self.__timer.timeout.connect(self.__mostrar_frame)
        self.btnVerificar.clicked.connect(self.__tomar_foto)

    def encender_refresco(self):
        self.__timer.start(30)

    def __mostrar_frame(self):
        frame = self.__coordinador.obtener_cuadro_camara()
        if frame is not None:
            alto, ancho, canales = frame.shape
            qimg = QImage(frame.data, ancho, alto, canales * ancho,
                          QImage.Format_RGB888)
            self.labelCamara.setPixmap(
                QPixmap.fromImage(qimg).scaled(
                    self.labelCamara.width(), self.labelCamara.height(),
                    Qt.KeepAspectRatio
                )
            )

    def __tomar_foto(self):
        self.__timer.stop()
        self.__coordinador.finalizar_verificacion()


class VentanaDashboard(QMainWindow):

    def __init__(self, coordinador=None):
        super().__init__()
        loadUi("views/ui/dashboard.ui", self)
        self.__coordinador = coordinador
        self.__conectar_sidebar()
        self.__conectar_dicom()
        self.__conectar_senales()
        self.__conectar_datos()
        self.__conectar_usuarios()

    def __conectar_sidebar(self):
        indices = {
            "btnNavInicio":    0,
            "btnNavDicom":     2,
            "btnNavSenales":   3,
            "btnNavDatos":     4,
            "btnNavUsuarios":  1,
        }
        for nombre, idx in indices.items():
            btn = getattr(self, nombre)
            btn.clicked.connect(lambda _, i=idx: self.stackedContenido.setCurrentIndex(i))
        self.btnCerrarSesion.clicked.connect(self.__cerrar_sesion)

    def __cerrar_sesion(self):
        resp = QMessageBox.question(
            self, "Cerrar sesión", "¿Desea cerrar sesión?",
            QMessageBox.Yes | QMessageBox.No
        )
        if resp == QMessageBox.Yes:
            self.close()

    def set_nombre_usuario(self, nombre: str):
        """Llamado por el coordinador para personalizar el saludo."""
        self.labelBienvenidaUsuario.setText(f"Bienvenido, {nombre} 👋")

    def __conectar_dicom(self):
        self.btnCargarDicom.clicked.connect(self.__seleccionar_carpeta_dicom)
        self.btnExportarCSV.clicked.connect(self.__coordinador.exportar_metadatos_csv
                                            if self.__coordinador else lambda: None)
        self.btnNifti.clicked.connect(self.__coordinador.convertir_a_nifti
                                      if self.__coordinador else lambda: None)
        self.sliderAxial.valueChanged.connect(
            lambda v: self.__on_slider_dicom("axial", v, self.labelSliderAxialVal, "Corte axial"))
        self.sliderCoronal.valueChanged.connect(
            lambda v: self.__on_slider_dicom("coronal", v, self.labelSliderCoronalVal, "Corte coronal"))
        self.sliderSagital.valueChanged.connect(
            lambda v: self.__on_slider_dicom("sagital", v, self.labelSliderSagitalVal, "Corte sagital"))
        self.btnAplicarZoom.clicked.connect(self.__aplicar_zoom)
        self.btnGuardarRecorte.clicked.connect(self.__guardar_recorte)
        self.btnSegmentar.clicked.connect(self.__segmentar)

    def __seleccionar_carpeta_dicom(self):
        carpeta = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta DICOM")
        if carpeta and self.__coordinador:
            self.__coordinador.cargar_dicom(carpeta)

    def __on_slider_dicom(self, plano, valor, label, texto):
        label.setText(f"{texto}: {valor}")
        if self.__coordinador:
            self.__coordinador.actualizar_corte(plano, valor)

    def __aplicar_zoom(self):
        if self.__coordinador:
            idx = self.sliderAxial.value()
            self.__coordinador.aplicar_zoom_y_recorte(
                "axial", idx,
                self.spinX1.value(), self.spinY1.value(),
                self.spinX2.value(), self.spinY2.value()
            )

    def __guardar_recorte(self):
        nombre = self.lineEditNombreRecorte.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Nombre vacío", "Ingrese un nombre para el archivo.")
            return
        if self.__coordinador:
            self.__coordinador.guardar_recorte(nombre)

    def __segmentar(self):
        if self.__coordinador:
            self.__coordinador.segmentar_imagen(
                self.comboTipoUmbral.currentIndex(),
                self.spinValorUmbral.value(),
                self.spinKernel.value(),
                self.comboTipoMorfologia.currentIndex()
            )

    def actualizar_sliders_dicom(self, max_ax: int, max_cor: int, max_sag: int):
        """Ajusta rangos de los 3 sliders independientes desactivando señales temporalmente."""
        for slider, maximo in [
            (self.sliderAxial,   max_ax),
            (self.sliderCoronal, max_cor),
            (self.sliderSagital, max_sag),
        ]:
            # 1. Bloqueamos las señales para que no llamen al controlador con índices viejos
            slider.blockSignals(True)
            
            # 2. Configuramos el nuevo valor máximo y el valor intermedio seguro
            slider.setMaximum(maximo)
            slider.setValue(maximo // 2)
            
            # 3. Desbloqueamos las señales para que vuelvan a funcionar con la interacción del usuario
            slider.blockSignals(False)

    def mostrar_corte(self, plano: str, imagen_np: np.ndarray):
        """Muestra un corte (uint8 numpy) en el QLabel correspondiente."""
        mapping = {
            "axial":   self.lblCorteAxial,
            "coronal": self.lblCorteCoronal,
            "sagital": self.lblCorteSagital,
        }
        label = mapping.get(plano)
        if label is not None:
            _mostrar_en_label(label, _numpy_a_pixmap(imagen_np))

    def poblar_tabla_metadatos(self, datos: list):
        """Llena la tabla de metadatos con lista de tuplas (campo, valor)."""
        self.tablaMetadatos.setRowCount(len(datos))
        for fila, (campo, valor) in enumerate(datos):
            from PyQt5.QtWidgets import QTableWidgetItem
            self.tablaMetadatos.setItem(fila, 0, QTableWidgetItem(str(campo)))
            self.tablaMetadatos.setItem(fila, 1, QTableWidgetItem(str(valor)))
        self.tablaMetadatos.resizeColumnsToContents()

    def mostrar_zoom(self, img_orig: np.ndarray, img_recorte: np.ndarray, texto: str):
        """Muestra imagen original con recuadro y recorte ampliado en un subplot."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4),
                                        facecolor="#FAFFFC")
        ax1.imshow(img_orig[:, :, ::-1] if img_orig.ndim == 3 else img_orig,
                   cmap="gray")
        ax1.set_title("Imagen original con ROI", color="#0F766E")
        ax1.axis("off")
        ax2.imshow(img_recorte[:, :, ::-1] if img_recorte.ndim == 3 else img_recorte,
                   cmap="gray")
        ax2.set_title(f"Recorte ampliado\n{texto}", color="#0F766E")
        ax2.axis("off")
        fig.tight_layout()
        _mostrar_en_label(self.lblCorteAxial, _figura_a_pixmap(fig))

    def mostrar_segmentacion(self, binarizada: np.ndarray, morfologica: np.ndarray):
        """Muestra resultado de binarización y morfología."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4),
                                        facecolor="#FAFFFC")
        ax1.imshow(binarizada, cmap="gray")
        ax1.set_title("Binarización", color="#0F766E")
        ax1.axis("off")
        ax2.imshow(morfologica, cmap="gray")
        ax2.set_title("Transformación morfológica", color="#0F766E")
        ax2.axis("off")
        fig.tight_layout()
        _mostrar_en_label(self.lblCorteAxial, _figura_a_pixmap(fig))

    def __conectar_senales(self):
        self.btnCargarSenal.clicked.connect(self.__cargar_senal)
        self.btnGraficarCanal.clicked.connect(self.__graficar_canal)
        self.btnAgregarRuido.clicked.connect(self.__agregar_ruido)
        self.btnEstadisticas3D.clicked.connect(self.__estadisticas_3d)

    def __cargar_senal(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo .mat", "", "MAT files (*.mat)"
        )
        if ruta and self.__coordinador:
            self.__coordinador.cargar_señal(ruta)

    def __graficar_canal(self):
        if self.__coordinador:
            self.__coordinador.graficar_canal(
                self.spinCanalSenal.value(),
                self.spinInicio.value(),
                self.spinFin.value()
            )

    def __agregar_ruido(self):
        if self.__coordinador:
            self.__coordinador.mostrar_canal_ruidoso(
                self.spinCanalRuido.value(),
                self.spinDesviacion.value()
            )

    def __estadisticas_3d(self):
        if self.__coordinador:
            eje = 0
            if self.radioEje1.isChecked():
                eje = 1
            elif self.radioEje2.isChecked():
                eje = 2
            self.__coordinador.calcular_estadisticas_3d(eje)


    def mostrar_canal_senal(self, tiempo: list, canal: list, titulo: str):
        """Grafica un canal de señal biomédica."""
        fig, ax = plt.subplots(figsize=(10, 3.5), facecolor="#FAFFFC")
        ax.plot(tiempo, canal, color="#14B87A", linewidth=0.8)
        ax.set_title(titulo, color="#0F766E")
        ax.set_xlabel("Muestras")
        ax.set_ylabel("Amplitud (μV)")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        _mostrar_en_label(self.lblGraficaSenal, _figura_a_pixmap(fig))

    def mostrar_señal_vs_ruidosa(self, original, ruidosa):
        """Subplot: señal original vs. señal con ruido."""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 5),
                                        facecolor="#FAFFFC", sharex=True)
        t = np.arange(len(original))
        ax1.plot(t, original, color="#14B87A", linewidth=0.8)
        ax1.set_title("Señal original", color="#0F766E")
        ax1.set_ylabel("μV")
        ax1.grid(True, alpha=0.3)
        ax2.plot(t, ruidosa, color="#E87A14", linewidth=0.8)
        ax2.set_title("Señal con ruido gaussiano", color="#0F766E")
        ax2.set_ylabel("μV")
        ax2.set_xlabel("Muestras")
        ax2.grid(True, alpha=0.3)
        fig.tight_layout()
        _mostrar_en_label(self.lblGraficaSenal, _figura_a_pixmap(fig))

    def mostrar_estadisticas_stem(self, prom, desv, nombre: str, unidades: str):
        """Subplot: gráfico stem de promedio y desviación estándar."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4),
                                        facecolor="#FAFFFC")
        x1 = np.arange(len(prom))
        ax1.stem(x1, prom, linefmt="#14B87A", markerfmt="o", basefmt=" ")
        ax1.set_title(f"Promedio — {nombre}", color="#0F766E")
        ax1.set_ylabel(unidades)
        ax1.grid(True, alpha=0.3)
        x2 = np.arange(len(desv))
        ax2.stem(x2, desv, linefmt="#E87A14", markerfmt="o", basefmt=" ")
        ax2.set_title(f"Desviación estándar — {nombre}", color="#0F766E")
        ax2.set_ylabel(unidades)
        ax2.grid(True, alpha=0.3)
        fig.tight_layout()
        _mostrar_en_label(self.lblGraficaSenal, _figura_a_pixmap(fig))

    def mostrar_canal_ruidoso(self, original, ruidosa):
        self.mostrar_señal_vs_ruidosa(original, ruidosa)

    def __conectar_datos(self):
        self.btnCargarTabla.clicked.connect(self.__cargar_tabla)
        self.btnGraficarColumnas.clicked.connect(self.__graficar_columnas)
        self.btnGraficarScatter.clicked.connect(self.__graficar_scatter)

    def __cargar_tabla(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo",
            "", "Datos (*.csv *.xlsx *.xls)"
        )
        if ruta and self.__coordinador:
            self.__coordinador.cargar_tabla(ruta)

    def __graficar_columnas(self):
        if self.__coordinador:
            seleccionados = [item.text() for item in self.listColumnas.selectedItems()]
            if len(seleccionados) < 4:
                QMessageBox.warning(self, "Selección vacía",
                                    "Seleccione 4 columnas de la lista.")
                return
            self.__coordinador.graficar_columnas(seleccionados)

    def __graficar_scatter(self):
        if self.__coordinador:
            col_x = self.comboScatterX.currentText()
            col_y = self.comboScatterY.currentText()
            if col_x and col_y:
                self.__coordinador.graficar_scatter(col_x, col_y)


    def poblar_combos_columnas(self, columnas: list):
        """Llena la lista de columnas y los dos combos del scatter."""
        self.listColumnas.clear()
        self.listColumnas.addItems(columnas)
        for combo in (self.comboScatterX, self.comboScatterY):
            combo.clear()
            combo.addItems(columnas)
        # Compatibilidad: también poblar comboColGraficar si existiera en .ui previo
        if hasattr(self, "comboColGraficar"):
            self.comboColGraficar.clear()
            self.comboColGraficar.addItems(columnas)

    def poblar_tabla_generica(self, tabla_widget, encabezados: list, filas: list):
        """Rellena cualquier QTableWidget con encabezados y filas de strings."""
        from PyQt5.QtWidgets import QTableWidgetItem
        tabla_widget.clear()
        tabla_widget.setColumnCount(len(encabezados))
        tabla_widget.setHorizontalHeaderLabels(encabezados)
        tabla_widget.setRowCount(len(filas))
        for r, fila in enumerate(filas):
            for c, valor in enumerate(fila):
                tabla_widget.setItem(r, c, QTableWidgetItem(str(valor)))
        tabla_widget.resizeColumnsToContents()

    def mostrar_plot_columnas(self, datos: dict):
        """Grafica cada columna seleccionada en subplots individuales."""
        n = len(datos)
        cols = min(n, 2)
        rows = (n + 1) // 2
        fig, axes = plt.subplots(rows, cols,
                                  figsize=(10, 3.5 * rows),
                                  facecolor="#FAFFFC")
        if n == 1:
            axes = [axes]
        else:
            axes = list(np.array(axes).flatten())
        for ax, (nombre, serie) in zip(axes, datos.items()):
            ax.plot(serie.values, color="#14B87A", linewidth=0.8)
            ax.set_title(nombre, color="#0F766E")
            ax.grid(True, alpha=0.3)
        # Ocultar ejes sobrantes
        for ax in axes[n:]:
            ax.set_visible(False)
        fig.tight_layout()
        _mostrar_en_label(self.lblGraficaDatos, _figura_a_pixmap(fig))

    def mostrar_scatter(self, sx, sy, col_x: str, col_y: str):
        """Gráfico scatter entre dos columnas."""
        fig, ax = plt.subplots(figsize=(8, 4), facecolor="#FAFFFC")
        ax.scatter(sx, sy, alpha=0.5, color="#14B87A", edgecolors="#0F766E",
                   linewidth=0.4, s=30)
        ax.set_xlabel(col_x, color="#0F766E")
        ax.set_ylabel(col_y, color="#0F766E")
        ax.set_title(f"Scatter: {col_x} vs {col_y}", color="#0F766E")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        _mostrar_en_label(self.lblGraficaDatos, _figura_a_pixmap(fig))

    def __conectar_usuarios(self):
        self.btnCrearUsuario.clicked.connect(self.__crear_usuario)
        self.btnRefrescarUsuarios.clicked.connect(self.__refrescar_usuarios)

    def __crear_usuario(self):
        nombre   = self.lineEditNuevoNombre.text().strip()
        password = self.lineEditNuevoPassword.text()
        rol      = self.comboRol.currentText()
        if not nombre or not password:
            self.labelMensajeUsuarios.setStyleSheet("color: red;")
            self.labelMensajeUsuarios.setText("Complete todos los campos.")
            return
        if self.__coordinador:
            self.__coordinador.crear_usuario(nombre, password, rol)

    def __refrescar_usuarios(self):
        if self.__coordinador:
            self.__coordinador.cargar_usuarios()

    def poblar_tabla_usuarios(self, usuarios: list):
        """Llena la tabla de usuarios con lista de dicts {id, nombre, rol}."""
        from PyQt5.QtWidgets import QTableWidgetItem
        self.tableUsuarios.setRowCount(len(usuarios))
        for fila, u in enumerate(usuarios):
            self.tableUsuarios.setItem(fila, 0, QTableWidgetItem(str(u.get("id", u.get("_id", "")))))
            self.tableUsuarios.setItem(fila, 1, QTableWidgetItem(str(u.get("nombre", ""))))
            self.tableUsuarios.setItem(fila, 2, QTableWidgetItem(str(u.get("rol", ""))))
        self.tableUsuarios.resizeColumnsToContents()

    def mostrar_mensaje_usuario(self, mensaje: str, exito: bool = True):
        color = "#14B87A" if exito else "red"
        self.labelMensajeUsuarios.setStyleSheet(f"color: {color};")
        self.labelMensajeUsuarios.setText(mensaje)
        self.lineEditNuevoNombre.clear()
        self.lineEditNuevoPassword.clear()