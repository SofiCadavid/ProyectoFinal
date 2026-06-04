# Controlador de usuarios, sirve para listar y crear usuarios desde el dashboard

from PyQt5.QtWidgets import QMessageBox

class UserController:
    def __init__(self, view, user_model):
        self.view = view
        self.user_model = user_model

        self.view.btnCrearUsuario.clicked.connect(self.crear_usuario)
        self.view.btnRefrescarUsuarios.clicked.connect(self.cargar_usuarios)

    def cargar_usuarios(self): # Trae la lista de usuarios y la muestra en la tabla
        try:
            usuarios = self.user_model.listar_usuarios()
        except ConnectionError as e:
            QMessageBox.critical(self.view, "Error de base de datos", str(e))
            return
        self.view.cargar_usuarios(usuarios)

    def crear_usuario(self): # Crea un usuario nuevo con los datos del formulario
        nombre, password, rol = self.view.obtener_datos_nuevo_usuario()

        if not nombre or not password:
            self.view.mensaje_usuarios("Escribe nombre y contrasena.", error=True)
            return

        try:
            exito, mensaje = self.user_model.crear_usuario(nombre, password, rol)
        except ConnectionError as e:
            QMessageBox.critical(self.view, "Error de base de datos", str(e))
            return

        self.view.mensaje_usuarios(mensaje, error=not exito)
        if exito:
            self.view.limpiar_form_usuario()
            self.cargar_usuarios()
