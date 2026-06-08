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
