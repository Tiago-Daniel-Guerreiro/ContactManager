import sys
from pathlib import Path
from typing import Optional

def get_base_dir() -> Path:
    if getattr(sys, 'frozen', False):
        # Rodando como executável PyInstaller
        return Path(sys.executable).parent
    else:
        # Rodando como script Python normal
        # Este arquivo está em utils/theme/, então precisamos subir 2 níveis
        return Path(__file__).parent.parent.parent


def get_resource_path(relative_path: str) -> Path:
    if getattr(sys, 'frozen', False):
        # Executável PyInstaller - arquivos estão em _MEIPASS
        base_path = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
    else:
        # Script Python normal
        base_path = Path(__file__).parent.parent.parent
    
    return base_path / relative_path


def get_icon_path() -> Optional[str]:
    print("Iniciando busca por ícone...")
    print(f"sys.frozen = {getattr(sys, 'frozen', False)}")
    
    try:
        from utils.theme.theme_detector import get_icon_path as get_themed_icon, get_windows_theme
        
        # Detecta o tema atual do Windows
        current_theme = get_windows_theme()
        print(f"Tema do Windows detectado: {current_theme}")
        
        # Se estiver empacotado, usa _MEIPASS para recursos
        if getattr(sys, 'frozen', False):
            base = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
            print(f"Modo frozen, base = {base}")
        else:
            base = get_base_dir()
            print(f"Modo script, base = {base}")
        
        # Passa o tema detectado para o get_themed_icon
        icon_path_str = str(get_themed_icon(base, current_theme))
        print(f"Ícone selecionado para tema '{current_theme}': {icon_path_str}")

        # Verifica se existe
        if Path(icon_path_str).exists():
            print(f"Ícone encontrado via detector de tema")
            return icon_path_str
        else:
            print(f"Ícone do tema não existe: {icon_path_str}")
            
    except (ImportError, Exception) as e:
        print(f"Erro ao detectar tema: {e}")
        import traceback
        traceback.print_exc()
    
    # Fallback: tenta localizar ícone manualmente
    print("Iniciando busca manual...")
    
    # Prioridade: .ico > .png
    icon_names = [
        "icon_light.ico",
        "icon_dark.ico", 
        "icon_light.png",
        "icon_dark.png"
    ]
    
    # Se for executável, procura em _MEIPASS primeiro
    if getattr(sys, 'frozen', False):
        try:
            meipass = Path(getattr(sys, '_MEIPASS'))
            print(f"Procurando em _MEIPASS: {meipass}")
            for icon_name in icon_names:
                icon_path = meipass / icon_name
                print(f"Tentando: {icon_path} - existe: {icon_path.exists()}")
                if icon_path.exists():
                    print(f"Encontrado em _MEIPASS: {icon_name}")
                    return str(icon_path)
        except Exception as e:
            print(f"Erro ao procurar em _MEIPASS: {e}")
    
    # Procura no diretório base (pasta do .exe ou pasta do projeto)
    base = get_base_dir()
    print(f"Procurando em base_dir: {base}")
    for icon_name in icon_names:
        icon_path = base / icon_name
        print(f"Tentando: {icon_path} - existe: {icon_path.exists()}")
        if icon_path.exists():
            print(f"Encontrado em base_dir: {icon_name}")
            return str(icon_path)
    
    print(f"Nenhum ícone encontrado!")
    print(f"Procurado em: {base}")
    if getattr(sys, 'frozen', False):
        print(f"E em: {getattr(sys, '_MEIPASS', 'N/A')}")
    
    return None
