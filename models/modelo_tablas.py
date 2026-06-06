"""Carga y análisis estadístico de datos tabulares médicos (CSV/Excel) — Modelo MVC."""
import pandas as pd


class ModeloTablas:
    def __init__(self):
        self.df = None

    def cargar(self, ruta):
        """Detecta extensión y carga CSV o Excel; retorna (bool, mensaje)."""
        try:
            ext = ruta.rsplit(".",1)[-1].lower()
            if ext == "csv":
                self.df = pd.read_csv(ruta, sep=None, engine="python")
            elif ext in ("xlsx","xls"):
                self.df = pd.read_excel(ruta)
            else:
                return False, f"Formato '{ext}' no soportado."
            return True, f"{self.df.shape[0]} filas × {self.df.shape[1]} columnas."
        except Exception as e:
            return False, str(e)

    def cols_numericas(self):
        """Lista de columnas numéricas."""
        return list(self.df.select_dtypes(include="number").columns) if self.df is not None else []

    def describe_lista(self):
        """Retorna (encabezados, filas) del df.describe() para QTableWidget."""
        if self.df is None: return [], []
        d = self.df.describe().reset_index()
        return list(d.columns), [[str(round(v,4)) if isinstance(v,float) else str(v) for v in row]
                                   for _,row in d.iterrows()]

    def info_lista(self):
        """Retorna (encabezados, filas) del df.info() resumido para QTableWidget."""
        if self.df is None: return [], []
        filas = [[c, str(self.df[c].dtype), str(self.df[c].count()), str(self.df[c].isna().sum())]
                 for c in self.df.columns]
        return ["Columna","Tipo","No Nulos","Nulos"], filas

    def serie(self, col):
        """Devuelve serie limpia de una columna."""
        return self.df[col].dropna() if self.df is not None and col in self.df.columns else None

    def scatter_data(self, cx, cy):
        """Devuelve dos series alineadas sin NaN para scatter."""
        if self.df is None: return None, None
        d = self.df[[cx,cy]].dropna()
        return d[cx], d[cy]
