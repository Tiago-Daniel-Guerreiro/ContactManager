from pathlib import Path
from typing import Optional
from utils.logger import get_logger
from utils.environment import get_base_dir, get_meipass, is_frozen
from utils.theme.theme_detector import get_icon_path as get_themed_icon, get_windows_theme

def get_resource_path(relative_path: str) -> Path:
    meipass = get_meipass()
    if meipass:
        # Executável PyInstaller - arquivos estão em _MEIPASS
        return meipass / relative_path
    
    # Script Python normal
    return get_base_dir() / relative_path

def get_icon_path(ext_preference: Optional[str] = None) -> Optional[str]:
    logger = get_logger()
    logger.debug("Iniciando busca por ícone...")
    logger.debug(f"is_frozen = {is_frozen()}")

    if ext_preference == "png":
        icon_names = ["icon.png", "icon.ico"]
    else: # O icon é o padrão
        icon_names = ["icon.ico", "icon.png"]

    meipass = get_meipass()
    search_paths = []
    if meipass:
        search_paths.append(meipass)
    search_paths.append(get_base_dir())

    for base in search_paths:
        logger.debug(f"Procurando ícone em: {base}")
        for icon_name in icon_names:
            icon_path = base / icon_name
            logger.debug(f"A tentar: {icon_path} - existe: {icon_path.exists()}")
            if icon_path.exists():
                logger.debug(f"Encontrado: {icon_path}")
                return str(icon_path)

    logger.debug("Nenhum ícone encontrado!")
    return None
