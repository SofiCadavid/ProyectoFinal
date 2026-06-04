# Controlador de verificacion, sirve para manejar la camara y guardar la sesión

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QTimer

class VerificationController:
    def __init__(self, view, camera_model, session_model, on_verificado):
        self.view = view
        self.camera_model = camera_model
        self.session_model = session_model
        self.on_verificado = on_verificado

        self.usuario = None
        self.timer = QTimer()
        self.timer.timeout.connect(self._actualizar_camara)

        self.view.btnVerificar.clicked.connect(self.verificar_identidad)

    def iniciar(self, usuario): # Muestra la ventana y enciende la camara
        self.usuario = usuario
        self.view.reset()
        self.view.show()

        if not self.camera_model.abrir():
            self.view.mostrar_estado(
                "No se pudo acceder a la camara. Verifica que este conectada "
                "y que ninguna otra aplicacion la este usando."
            )
            return

        self.timer.start(30)
        self.view.mostrar_estado(
            "Camara activa. Cuando estes listo, pulsa el boton para verificar."
        )

    def _actualizar_camara(self): # Refresca el video de la camara en la vista
        frame = self.camera_model.leer_frame()
        self.view.mostrar_frame(frame)

    def verificar_identidad(self): # Captura la foto, guarda la sesion y avisa al coordinador
        if not self.camera_model.esta_abierta():
            QMessageBox.information(
                self.view,
                "Camara apagada",
                "La camara no esta activa. No se pudo verificar la identidad.",
            )
            return

        ruta = self.camera_model.guardar_foto(self.usuario.id)
        if ruta is None:
            self.view.mostrar_estado("No se pudo capturar la foto. Intenta de nuevo.")
            return

        try:
            self.session_model.registrar_sesion(self.usuario.id, ruta)
        except ConnectionError as e:
            QMessageBox.critical(self.view, "Error de base de datos", str(e))
            return

        self.detener()
        self.view.close()
        self.on_verificado(self.usuario)

    def detener(self): # Apaga el temporizador y libera la camara
        if self.timer.isActive():
            self.timer.stop()
        self.camera_model.cerrar()
