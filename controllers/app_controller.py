# Controlador principal que maneja toda la app

from views.bienvenida_view import BienvenidaView
from views.login_view import LoginView
from views.verificacion_view import VerificacionView
from views.dashboard_view import DashboardView

from models.user_model import UserModel
from models.session_model import SessionModel
from models.camera_model import CameraModel

from controllers.auth_controller import AuthController
from controllers.verification_controller import VerificationController
from controllers.user_controller import UserController


class AppController:
    def __init__(self):
        self.bienvenida = BienvenidaView()
        self.login = LoginView()
        self.verificacion = VerificacionView()
        self.dashboard = DashboardView()

        self.user_model = UserModel()
        self.session_model = SessionModel()
        self.camera_model = CameraModel()

        self.usuario_actual = None

        self.auth = AuthController(
            self.login, self.user_model, on_login_ok=self._on_login_ok
        )
        self.verification = VerificationController(
            self.verificacion,
            self.camera_model,
            self.session_model,
            on_verificado=self._on_verificado,
        )
        self.users = UserController(self.dashboard, self.user_model)

        self._conectar_navegacion()

    def _conectar_navegacion(self): # Conecta los botones de navegacion con sus paginas
        self.bienvenida.btnEntrar.clicked.connect(self.ir_a_login)

        self.dashboard.btnNavInicio.clicked.connect(
            lambda: self.dashboard.mostrar_pagina(self.dashboard.pageInicio)
        )
        self.dashboard.btnNavDicom.clicked.connect(
            lambda: self.dashboard.mostrar_pagina(self.dashboard.pageDicom)
        )
        self.dashboard.btnNavSenales.clicked.connect(
            lambda: self.dashboard.mostrar_pagina(self.dashboard.pageSenales)
        )
        self.dashboard.btnNavDatos.clicked.connect(
            lambda: self.dashboard.mostrar_pagina(self.dashboard.pageDatos)
        )
        self.dashboard.btnNavUsuarios.clicked.connect(self.ir_a_usuarios)

        self.dashboard.btnCerrarSesion.clicked.connect(self.cerrar_sesion)

    def iniciar(self): # Arranca mostrando la ventana de bienvenida
        self.bienvenida.show()

    def ir_a_login(self): # Pasa de la bienvenida al login
        self.bienvenida.close()
        self.login.limpiar()
        self.login.show()

    def _on_login_ok(self, usuario): # Tras un login correcto, abre la verificacion
        self.usuario_actual = usuario
        self.login.close()
        self.verification.iniciar(usuario)

    def _on_verificado(self, usuario): # Tras verificar, muestra el dashboard
        self.dashboard.set_usuario(usuario.nombre, usuario.rol)
        self.dashboard.mostrar_pagina(self.dashboard.pageInicio)
        self.dashboard.show()

    def ir_a_usuarios(self): # Abre la pagina de usuarios y carga la lista
        self.dashboard.mostrar_pagina(self.dashboard.pageUsuarios)
        self.users.cargar_usuarios()

    def cerrar_sesion(self): # Cierra el dashboard y vuelve al login
        self.verification.detener()
        self.usuario_actual = None
        self.dashboard.close()
        self.login.limpiar()
        self.login.show()
