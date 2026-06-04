# Configuracion global del proyecto (lee los datos desde el .env)

import os

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(BASE_DIR, ".env"))

UI_DIR = os.path.join(BASE_DIR, "views", "ui")

CAPTURES_DIR = os.path.join(BASE_DIR, "assets", "captures")

ASSETS_DIR = os.path.join(BASE_DIR, "assets")

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT")),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}

APP_NAME = os.getenv("APP_NAME")
APP_SLOGAN = os.getenv("APP_SLOGAN")


def ensure_dirs(): # Crea las carpetas necesarias si no existen
    os.makedirs(CAPTURES_DIR, exist_ok=True)
    os.makedirs(ASSETS_DIR, exist_ok=True)
