import sys
import os
from pathlib import Path
from typing import Optional, List

def get_base_dir() -> Path:
    if is_frozen():
        # Rodando como executável 
        return Path(sys.executable).parent
    
    # Rodando como script Python
    # Este arquivo está em utils/, subir 1 nível
    return Path(__file__).parent.parent

def get_meipass() -> Optional[Path]:
    meipass = getattr(sys, '_MEIPASS', None)
    return Path(meipass) if meipass else None

def is_frozen() -> bool:
    return getattr(sys, 'frozen', False) # Se é um executável

def setup_encoding() -> None:
    if sys.platform != 'win32':
        return
    
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')  # type: ignore
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')  # type: ignore
    except Exception:
        pass


def setup_directories(base_dir: Optional[Path] = None) -> List[Path]:
    if base_dir is None:
        base_dir = get_base_dir()
    
    dirs_to_create = [
        base_dir / "data",
        base_dir / "config",
        base_dir / "reports",
    ]
    
    for dir_path in dirs_to_create:
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
    
    return dirs_to_create

def get_environment_info(base_dir: Optional[Path] = None) -> dict:
    if base_dir is None:
        base_dir = get_base_dir()
    
    info = {
        "python_version": sys.version,
        "executable": sys.executable,
        "frozen": is_frozen(),
        "platform": sys.platform,
        "current_dir": os.getcwd(),
        "base_dir": str(base_dir),
    }
    
    meipass = get_meipass()
    if meipass:
        info["meipass"] = str(meipass)
    
    return info


def setup_environment(base_dir: Optional[Path] = None) -> Path:
    if base_dir is None:
        base_dir = get_base_dir()
    
    setup_encoding()
    setup_directories(base_dir)
    
    return base_dir

def platform_is_windows() -> bool:
    return sys.platform.startswith('win')

def platform_is_linux() -> bool:
    return sys.platform.startswith('linux')

def platform_is_mac() -> bool:
    return sys.platform.startswith('darwin')