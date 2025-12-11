import sys
from typing import Optional
from utils.environment import is_frozen

# Constantes da aplicação
APP_USER_MODEL_ID = 'TiagoGuerreiro.ContactManager.8.1.3'

def is_windows() -> bool:
    return sys.platform == 'win32'

def allocate_console() -> bool:
    if not is_windows():
        return False
    
    # Só faz sentido se for executável (frozen)
    if not is_frozen():
        return False
    
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        
        if kernel32.AllocConsole():
            # Redireciona stdout e stderr para o novo console
            sys.stdout = open('CONOUT$', 'w', encoding='utf-8')
            sys.stderr = open('CONOUT$', 'w', encoding='utf-8')
            
            print("\n Consola de Debug\nFeche esta janela para encerrar a aplicação\n\n")
            
            return True
    except Exception as e:
        # Usamos print pois o console pode não estar pronto para logger
        print(f"Erro ao alocar console: {e}")
    
    return False

def set_app_user_model_id(app_id: Optional[str] = None) -> bool:
    if not is_windows():
        return False
    
    if app_id is None:
        app_id = APP_USER_MODEL_ID
    
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        return True
    except Exception:
        return False


def setup_windows(allocate_debug_console: bool = False) -> dict:
    results = {
        "is_windows": is_windows(),
        "console_allocated": False,
        "app_id_set": False,
    }
    
    if not is_windows():
        return results
    
    # Aloca console se solicitado
    if allocate_debug_console:
        results["console_allocated"] = allocate_console()
    
    # Define AppUserModelID
    results["app_id_set"] = set_app_user_model_id()
    
    return results
