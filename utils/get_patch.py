import sys
from pathlib import Path


def get_base_dir() -> Path:
    if getattr(sys, 'frozen', False):
        # Rodando como executável PyInstaller
        # Usa o diretório do executável, não o temp _MEIPASS
        return Path(sys.executable).parent
    else:
        # Rodando como script Python normal
        # Este arquivo está em utils/, então precisamos subir 1 nível
        return Path(__file__).parent.parent
