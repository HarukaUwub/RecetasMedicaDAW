import os, sys

def resource_path(relative_path: str) -> str:
    """
    Obtiene la ruta absoluta al recurso, compatible con PyInstaller.
    - En desarrollo: usa el path normal.
    - En exe empaquetado: busca en _MEIPASS.
    """
    try:
        # PyInstaller crea una carpeta temporal con los recursos empaquetados
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
