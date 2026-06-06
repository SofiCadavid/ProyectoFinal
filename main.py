import sys
from PyQt5.QtWidgets import QApplication
from controllers.controlador import Coordinador  # Importamos el coordinador

def main():
    # Se crea la aplicación gráfica de PyQt5
    app = QApplication(sys.argv)
    objeto_coordinador = Coordinador()
    objeto_coordinador.arrancar_aplicacion()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()