"""Procesamiento de señales biomédicas ECG/EEG desde archivos .mat — Modelo MVC."""
import numpy as np
import scipy.io as sio


class ModeloSenales:
    def __init__(self):
        self.señal_3d = None
        self.señal_2d = None  # (canales, muestras)

    def cargar_mat(self, ruta):
        """Carga archivo .mat y construye tensores 2D y 3D."""
        try:
            datos_raw = sio.loadmat(ruta)
            clave = next(k for k in datos_raw if not k.startswith("__"))
            d = datos_raw[clave].astype(np.float64)
            self.señal_3d = d
            if   d.ndim == 1: self.señal_2d = d.reshape(1,-1)
            elif d.ndim == 2: self.señal_2d = d if d.shape[0] < d.shape[1] else d.T
            elif d.ndim == 3: self.señal_2d = d.reshape(d.shape[1], -1)  # (canales, ep*muestras)
            else: self.señal_2d = d.reshape(d.shape[0],-1)
            return True, f"{self.señal_2d.shape[0]} canales, {self.señal_2d.shape[1]} muestras."
        except Exception as e:
            return False, str(e)

    def canal(self, idx, inicio=0, fin=None):
        """Devuelve segmento temporal de un canal."""
        if self.señal_2d is None: return None
        idx = max(0, min(idx, self.señal_2d.shape[0]-1))
        return self.señal_2d[idx, inicio:fin]

    def num_canales(self):
        return 0 if self.señal_2d is None else self.señal_2d.shape[0]

    def num_muestras(self):
        return 0 if self.señal_2d is None else self.señal_2d.shape[1]

    def agregar_ruido(self, idx, desv=0.05):
        """Retorna (original, ruidosa) con ruido gaussiano escalado a la amplitud."""
        c = self.canal(idx)
        if c is None: return None, None
        return c, c + np.random.normal(0, desv * np.ptp(c), c.shape)

    def estadisticas_3d(self, eje):
        """Calcula media y std del tensor 3D por eje; retorna (prom, desv, nombre, unidad)."""
        if self.señal_3d is None: return None, None, "", ""
        eje = min(eje, self.señal_3d.ndim-1)
        nombres = {0:("Eje 0 — Epochs","μV"), 1:("Eje 1 — Canales","μV"), 2:("Eje 2 — Muestras","μV")}
        nom, uni = nombres.get(eje, (f"Eje {eje}","u.a."))
        return (np.mean(self.señal_3d, eje).flatten(),
                np.std(self.señal_3d, eje).flatten(), nom, uni)
