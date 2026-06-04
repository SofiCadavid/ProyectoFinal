# Modelo de base de datos, sirve para conectar con MySQL

import mysql.connector
from mysql.connector import Error

from config import DB_CONFIG


class Database:
    def __init__(self, config=None):
        self.config = config or DB_CONFIG
        self.connection = None

    def connect(self): # Abre la conexion con MySQL
        try:
            self.connection = mysql.connector.connect(use_pure=True, **self.config)
            if self.connection.is_connected():
                return self.connection
        except Error as e:
            raise ConnectionError(
                "No se pudo conectar a la base de datos MySQL.\n\n"
                "Verifica que el servidor MySQL este encendido (por ejemplo en XAMPP) "
                "y que los datos en config.py sean correctos.\n\n"
                f"Detalle tecnico: {e}"
            )
        return None

    def fetch_one(self, query, params=None): # Devuelve una sola fila de un SELECT
        conn = self.connect()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params or ())
            return cursor.fetchone()
        finally:
            cursor.close()
            self.close()

    def fetch_all(self, query, params=None): # Devuelve todas las filas de un SELECT
        conn = self.connect()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params or ())
            return cursor.fetchall()
        finally:
            cursor.close()
            self.close()

    def execute(self, query, params=None): # Ejecuta INSERT/UPDATE/DELETE
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params or ())
            conn.commit()
            return cursor.lastrowid
        finally:
            cursor.close()
            self.close()

    def close(self): # Cierra la conexion si esta abierta
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.connection = None
