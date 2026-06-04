# Controlador de login, sirve para validar las credenciales del usuario

from PyQt5.QtWidgets import QMessageBox

class AuthController:
    def __init__(self, view, user_model, on_login_ok):
        self.view = view
        self.user_model = user_model
        self.on_login_ok = on_login_ok

        self.view.btnLogin.clicked.connect(self.intentar_login)
        self.view.lineEditPassword.returnPressed.connect(self.intentar_login)

    def intentar_login(self): # Valida el usuario y avisa al coordinador si es correcto
        usuario, password = self.view.obtener_credenciales()

        if not usuario or not password:
            self.view.mostrar_mensaje("Escribe usuario y contrasena.")
            return

        try:
            resultado = self.user_model.validar_login(usuario, password)
        except ConnectionError as e:
            QMessageBox.critical(self.view, "Error de base de datos", str(e))
            return

        if resultado is None:
            self.view.mostrar_mensaje("Usuario o contraseña incorrectos.")
            return

        self.on_login_ok(resultado)
