from pymongo import MongoClient
from datetime import datetime


class SistemaBaseDatos:

    def __init__(self):
        uri = (
            "mongodb+srv://gsanin:yvfugtRkB4iRruKO@cluster0.2re9zvu.mongodb.net/"
            "?appName=Cluster0"
        )
        self.client = MongoClient(uri)
        self.db = self.client["vitalis_db"]
        self.col_usuarios = self.db["usuarios"]
        self.col_sesiones = self.db["sesiones"]

    def validar_usuario_en_bd(self, login: str, password: str):
        """Retorna el documento del usuario si las credenciales son correctas."""
        return self.col_usuarios.find_one({
            "$or": [{"nombre": login}, {"id": login}],
            "password": password
        })

    def crear_usuario(self, nombre: str, password: str, rol: str):
        """Inserta un nuevo usuario. Lanza excepción si el nombre ya existe."""
        if self.col_usuarios.find_one({"nombre": nombre}):
            raise ValueError(f"Ya existe un usuario con el nombre '{nombre}'.")
        nuevo = {
            "nombre":   nombre,
            "password": password,
            "rol":      rol,
            "fecha_creacion": datetime.now()
        }
        result = self.col_usuarios.insert_one(nuevo)
        nuevo["id"] = str(result.inserted_id)
        return nuevo

    def obtener_todos_los_usuarios(self) -> list:
        """Retorna lista de dicts con id, nombre y rol de todos los usuarios."""
        usuarios = []
        for u in self.col_usuarios.find({}, {"nombre": 1, "rol": 1}):
            usuarios.append({
                "id":     str(u.get("_id", "")),
                "nombre": u.get("nombre", ""),
                "rol":    u.get("rol", ""),
            })
        return usuarios

    def guardar_sesion_foto(self, id_usuario: str, ruta_foto: str):
        """Registra la sesión con la ruta de la foto y la fecha actual."""
        self.col_sesiones.insert_one({
            "id_usuario":  id_usuario,
            "ruta_foto":   ruta_foto,
            "fecha_sesion": datetime.now()
        })