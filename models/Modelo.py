from pymongo import MongoClient
import cv2
import os
from datetime import datetime

#Logica de la base de datos
class SistemaBaseDatos:
    def __init__(self):
        # Conexión al cluster en la nube
        ruta_internet_atlas = "mongodb+srv://gsanin:yvfugtRkB4iRruKO@cluster0.2re9zvu.mongodb.net/?appName=Cluster0"
        self.client = MongoClient(ruta_internet_atlas)
        self.db = self.client["vitalis_db"] # Conexion a la database especifica
        # Colecciones para usuarios y sesiones
        self.coleccion_usuarios = self.db["usuarios"]
        self.coleccion_sesiones = self.db["sesiones"]

    def validar_usuario_en_bd(self, login_usuario, password_usuario):
        # Busca a través de internet en tu cluster remoto
        usuario_encontrado = self.coleccion_usuarios.find_one({
            "$or": [{"nombre": login_usuario}, {"id": login_usuario}],
            "password": password_usuario
        })
        return usuario_encontrado 

    def guardar_sesion_foto(self, id_usuario, ruta_archivo_foto):
        # Sube a internet el registro del historial de la sesión
        registro_sesion = {
            "id_usuario": id_usuario,
            "ruta_foto": ruta_archivo_foto,
            "fecha_sesion": datetime.now()
        }
        self.coleccion_sesiones.insert_one(registro_sesion)

# Camara web y procesamiento de video
class ControlCamara:
    def __init__(self):
        self.dispositivo_captura = None

    def encender_camara(self):
        self.dispositivo_captura = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        return self.dispositivo_captura.isOpened()

    def leer_fotograma(self):
        if self.dispositivo_captura and self.dispositivo_captura.isOpened():
            exito, frame = self.dispositivo_captura.read()
            if exito:
                return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return None

    def capturar_y_guardar_disco(self, id_usuario):
        if self.dispositivo_captura and self.dispositivo_captura.isOpened():
            exito, frame = self.dispositivo_captura.read()
            if exito:
                os.makedirs("capturas", exist_ok=True)
                ruta_final = f"capturas/usuario_{id_usuario}.jpg"
                cv2.imwrite(ruta_final, frame)
                return ruta_final
        return None

    def apagar_camara(self):
        if self.dispositivo_captura:
            self.dispositivo_captura.release()
            self.dispositivo_captura = None