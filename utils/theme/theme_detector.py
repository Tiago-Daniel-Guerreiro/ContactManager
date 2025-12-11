import sys
from pathlib import Path
from typing import Literal, Optional, Callable
from utils.environment import get_base_dir, is_frozen
from utils.logger import get_logger

ThemeType = Literal["light", "dark"]

def get_windows_theme() -> ThemeType:
    if sys.platform != 'win32':
        return "dark"  # Default para outras plataformas
    
    try:
        import winreg
        
        # Registros do Windows que indicam o tema
        registry_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        registry_key = "AppsUseLightTheme"
        
        try:
            # Abre a chave do registro
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                registry_path,
                0,
                winreg.KEY_READ
            )
            
            # Lê o valor (0 = dark theme, 1 = light theme)
            value, _ = winreg.QueryValueEx(key, registry_key)
            winreg.CloseKey(key)
            
            # Retorna o tema apropriado
            return "light" if value == 1 else "dark"
            
        except FileNotFoundError:
            # Chave não existe, assume tema claro
            return "light"
        except Exception as e:
            get_logger().error(f"Erro ao ler registro do tema", error=e)
            return "light"
            
    except ImportError:
        # winreg não disponível
        return "light"

def get_icon_path(base_dir: Path | None = None) -> Path:
    # Detecta base_dir se não fornecido
    if base_dir is None:
        base_dir = get_base_dir()

    # Seleciona o ícone apropriado
    if sys.platform == 'win32':
        icon_name = "icon.ico"
    else:
        icon_name = "icon.png"

    icon_path = base_dir / icon_name

    return icon_path
