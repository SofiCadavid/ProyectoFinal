import sys
from PyQt5.QtWidgets import QMainWindow, QMessageBox
from PyQt5.uic import loadUi
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap

# Ventana de Bienvenida
class VentanaBienvenida(QMainWindow):
    def __init__(self, coordinador=None):
        super().__init__()
        # Carga del archivo
        loadUi("views/ui/bienvenida.ui", self) 
        self.__miCoordinador = coordinador
        self.btnEntrar.clicked.connect(self.avanzar_al_login) 
    def avanzar_al_login(self):
        # Avisar al coordinador que cierre esta ventana y abra el login
        self.__miCoordinador.abrir_login()

# Ventana de login
class VentanaLogin(QMainWindow):
    def __init__(self, coordinador=None):
        super().__init__()
        loadUi("views/ui/login.ui", self)
        self.__miCoordinador = coordinador
        self.btnLogin.clicked.connect(self.intentar_ingresar)

    def intentar_ingresar(self):
        usuario = self.lineEditUsuario.text().strip() # Leemos lo que el usuario escribió en los campos de texto
        password = self.lineEditPassword.text()
        # Validación básica en la interfaz: que no estén vacíos
        if usuario == "" or password == "":
            QMessageBox.warning(self, "Campos Vacíos", "Por favor, ingrese usuario y contraseña.")
            return
        self.__miCoordinador.validar_credenciales(usuario, password)  # Si todo va bien, le pasamos los datos al coordinador para que revise la BD

# Ventana de verificación con cámara
class VentanaCamara(QMainWindow):
    def __init__(self, coordinador=None):
        super().__init__()
        loadUi("views/ui/verificacion.ui", self)
        self.__miCoordinador = coordinador
        
        # Un QTimer es un temporizador que usaremos para refrescar la cámara
        self.timer = QTimer()
        self.timer.timeout.connect(self.mostrar_video_en_pantalla)
        self.btnVerificar.clicked.connect(self.tomar_foto)

    def encender_refresco(self):
        # Hace que el temporizador se active cada 30 milisegundos para leer frames
        self.timer.start(30)

    def mostrar_video_en_pantalla(self):
        # Le pedimos el cuadro de video actual al coordinador
        frame = self.__miCoordinador.obtener_cuadro_camara()
        
        if frame is not None:
            # Convertir la matriz de OpenCV a formato PyQt
            alto, ancho, canales = frame.shape
            bytes_por_linea = canales * ancho
            imagen_qt = QImage(frame.data, ancho, alto, bytes_por_linea, QImage.Format_RGB888)
            
            # Ajustamos la imagen al tamaño del QLabel "labelCamara"
            pixmap = QPixmap.fromImage(imagen_qt)
            self.labelCamara.setPixmap(pixmap.scaled(
                self.labelCamara.width(), 
                self.labelCamara.height(), 
                Qt.KeepAspectRatio
            ))

    def tomar_foto(self):
        self.timer.stop()
        self.__miCoordinador.finalizar_verificacion() # Coordinador que procese el guardado de la foto y de la sesión


# Ventana principal
class VentanaDashboard(QMainWindow):
    def __init__(self, coordinador=None):
        super().__init__()
        loadUi("views/ui/dashboard.ui", self)
        self.__miCoordinador = coordinador
        
        # Más adelante, aquí conectaremos los botones laterales (btnNavDicom, etc.)