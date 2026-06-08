import cv2
import os
from datetime import datetime

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