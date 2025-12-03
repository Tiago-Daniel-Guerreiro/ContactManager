import sys
import os
from pathlib import Path

# Adiciona diretório raiz ao path para imports
ROOT_DIR = Path(__file__).parent
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
    ]
    
    for dir_path in dirs_to_create:
        dir_path.mkdir(exist_ok=True)
    
    # Configura variáveis de ambiente para CustomTkinter
    os.environ["CTK_SILENCE_DEPRECATION_WARNINGS"] = "1"


def check_dependencies():
    required = ['customtkinter', 'tkinter']
    missing = []
    
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"Dependências em falta: {', '.join(missing)}")
        print("   Instale com: pip install customtkinter")
        sys.exit(1)


def main():
    # Verificações iniciais
    check_dependencies()
    setup_environment()
    
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
    # Verifica se deve executar com profiling
    if "--profile" in sys.argv:
        run_with_profiling()
    else:
        main()
