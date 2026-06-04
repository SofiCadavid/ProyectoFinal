# Punto de entrada de la aplicacion Vitalis

import sys

from PyQt5.QtWidgets import QApplication, QMessageBox

import config
from controllers.app_controller import AppController


def main(): # Arranca la aplicacion y muestra la primera ventana
    config.ensure_dirs()

    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)

    try:
        controlador = AppController()
        controlador.iniciar()
    except Exception as e:
        QMessageBox.critical(
            None,
            "Error al iniciar Vitalis",
            f"Ocurrio un error al iniciar la aplicacion:\n\n{e}",
        )
        return 1

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
