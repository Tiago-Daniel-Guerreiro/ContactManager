import sys
from pathlib import Path
from typing import Literal

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
            print(f"Erro ao ler registro: {e}")
            return "light"
            
    except ImportError:
        # winreg não disponível
        return "light"

def get_icon_path(base_dir: Path | None = None, theme: ThemeType | None = None) -> Path:
    # Detecta base_dir se não fornecido
    if base_dir is None:
        if getattr(sys, 'frozen', False):
            # Rodando como executável PyInstaller
            base_dir = Path(sys.executable).parent
        else:
            # Rodando como script Python normal
            # Este arquivo está em utils/theme/, então precisamos subir 2 níveis
            base_dir = Path(__file__).parent.parent.parent
    
    # Detecta tema se não fornecido
    if theme is None:
        theme = get_windows_theme()
    
    # Seleciona o ícone apropriado
    if sys.platform == 'win32':
        # No Windows, usa ICO
        if theme == "dark":
            icon_name = "icon_dark.ico"
        else:
            icon_name = "icon_light.ico"
    else:
        # Em outras plataformas, usa PNG
        if theme == "dark":
            icon_name = "icon_dark.png"
        else:
            icon_name = "icon_light.png"
    
    icon_path = base_dir / icon_name
    
    # Fallback para ícone padrão se o específico não existir
    if not icon_path.exists():
        fallback_ext = ".ico" if sys.platform == 'win32' else ".png"
        fallback_path = base_dir / f"icon{fallback_ext}"
        
        if fallback_path.exists():
            return fallback_path
    
    return icon_path