import sys
import os
from pathlib import Path
from utils import get_base_dir

# Adiciona diretório raiz ao path para imports
ROOT_DIR = get_base_dir() 
sys.path.insert(0, str(ROOT_DIR))

# Configuração de encoding para Windows
if sys.platform == 'win32':
    try:
        # Reconfigure encoding para UTF-8 se disponível
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')  # type: ignore
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')  # type: ignore
    except Exception:
        pass  # Ignora erros de reconfiguração

def setup_environment():
    # Cria diretórios necessários se não existirem
    dirs_to_create = [
        ROOT_DIR / "data",
        ROOT_DIR / "config",
        ROOT_DIR / "reports",
    ]
    
    for dir_path in dirs_to_create:
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    # Configura variáveis de ambiente para CustomTkinter
    os.environ["CTK_SILENCE_DEPRECATION_WARNINGS"] = "1"

def set_app_user_model_id():
    if sys.platform == 'win32':
        try:
            import ctypes
            # Define um ID único para a aplicação
            # Isso faz o Windows reconhecer a app como diferente do Python
            myappid = 'TiagoGuerreiro.ContactManager.WhatsAppSMS.6.0.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            return True
        except Exception as e:
            print(f"Erro ao definir AppUserModelID: {e}")
            return False
    return False

def main():
    # Verificações iniciais
    setup_environment()
    
    # Modo debug: mostra console com informações detalhadas
    debug_mode = "--debug" in sys.argv
    if debug_mode:
        print("Modo debug")
        print(f"Python: {sys.version}")
        print(f"Executável: {sys.executable}")
        print(f"Frozen: {getattr(sys, 'frozen', False)}")
        if getattr(sys, 'frozen', False):
            print(f"_MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}")
        print(f"Diretório atual: {os.getcwd()}")
        print(f"ROOT_DIR: {ROOT_DIR}")
    
    # Fix para ícone na barra de tarefas do Windows
    if sys.platform == 'win32':
        try:
            result = set_app_user_model_id()
            if debug_mode:
                print(f"AppUserModelID definido: {result}")
        except Exception as e:
            if debug_mode:
                print(f"Erro ao definir AppUserModelID: {e}")
    
    # Import após verificações
    from views.windows.main_window import MainWindow
    from config.settings import ThemeManager
    
    # Inicializa tema global
    ThemeManager()
    
    # Cria e executa aplicação
    try:
        app = MainWindow()
        app.mainloop()
    except KeyboardInterrupt:
        print("\nAplicação encerrada pelo utilizador")
    except Exception as e:
        print(f"Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def run_with_profiling():
    import cProfile
    import pstats
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    main()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)

if __name__ == "__main__":
    # Verifica argumentos de linha de comando
    if "--profile" in sys.argv:
        run_with_profiling()
        exit(0)
        
    if "--debug" in sys.argv:
        # Modo debug - força console mesmo se for .exe
        if sys.platform == 'win32' and getattr(sys, 'frozen', False):
            # Se for .exe, tenta abrir um console
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                # Aloca um novo console
                if kernel32.AllocConsole():
                    # Redireciona stdout e stderr para o console
                    sys.stdout = open('CONOUT$', 'w')
                    sys.stderr = open('CONOUT$', 'w')
                    print("\nConsole de Debug")
                    print("Feche esta janela para encerrar a aplicação\n")
            except Exception as e:
                print(f"Erro ao alocar console: {e}")

    main()
