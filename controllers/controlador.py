import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
from models.Modelo import SistemaBaseDatos, ControlCamara
from views.Vista import VentanaBienvenida, VentanaLogin, VentanaCamara, VentanaDashboard

class Coordinador:
    def __init__(self):
        self.modelo_bd = SistemaBaseDatos()
        self.modelo_camara = ControlCamara()
        self.v_bienvenida = VentanaBienvenida(self)
        self.v_login = VentanaLogin(self)
        self.v_camara = VentanaCamara(self)
        self.v_dashboard = VentanaDashboard(self)
        self.usuario_actual = None # Variable temporal para recordar qué médico inició sesión

    def arrancar_aplicacion(self):
        # El programa inicia mostrando únicamente la ventana de bienvenida
        self.v_bienvenida.show()

    def abrir_login(self):
        # Cuando dan clic en 'btnEntrar', cerramos la bienvenida y abrimos el login
        self.v_bienvenida.close()
        self.v_login.show()

    def validar_credenciales(self, usuario, password):
        # La Vista le dio el usuario y clave. Ahora el coordinador se los pasa al Modelo
        # para que viaje por internet a MongoDB Atlas a buscarlo
        resultado = self.modelo_bd.validar_usuario_en_bd(usuario, password)
        
        if resultado is not None:
            # Guardamos los datos del médico en memoria
            self.usuario_actual = resultado
            self.v_login.close()
            
            # Intentamos encender la cámara web
            if self.modelo_camara.encender_camara():
                self.v_camara.show()
                # Le decimos a la ventana de la cámara que empiece a refrescar el video
                self.v_camara.encender_refresco()
            else:
                QMessageBox.critical(self.v_login, "Error de Hardware", "No se pudo acceder a la cámara web.")
        else:
            # Si MongoDB devolvió None, las credenciales están mal
            QMessageBox.critical(self.v_login, "Acceso Denegado", "Usuario o contraseña incorrectos.")

    def obtener_cuadro_camara(self):
        # La vista nos pide un fotograma constantemente; nosotros se lo pedimos al modelo
        return self.modelo_camara.leer_fotograma()

    def finalizar_verificacion(self):
        # Este método se ejecuta cuando el médico hunde el botón 'btnVerificar' para tomar la foto
        id_user = self.usuario_actual['id']
        
        # 1. Le decimos al modelo que capture el cuadro actual y lo guarde en el disco duro
        ruta_foto_guardada = self.modelo_camara.capturar_y_guardar_disco(id_user)
        
        if ruta_foto_guardada:
            # 2. Registramos la sesión en la nube (MongoDB Atlas) con el ID, la ruta y la fecha
            self.modelo_bd.guardar_sesion_foto(id_user, ruta_foto_guardada)
            
            # 3. Apagamos la cámara web y cerramos la ventana
            self.modelo_camara.apagar_camara()
            self.v_camara.close()
            
            # 4. Abrimos finalmente el panel médico (Dashboard) que viste en tu imagen
            self.v_dashboard.show()
            QMessageBox.information(self.v_dashboard, "Éxito", f"Bienvenido al sistema médico.")
        else:
            QMessageBox.warning(self.v_camara, "Error", "No se pudo capturar la foto. Reintente.")
            self.v_camara.encender_refresco()


