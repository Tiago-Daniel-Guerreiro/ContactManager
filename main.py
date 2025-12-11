import sys
import time
from utils.debug import get_debug_manager

def main():
    # Inicializa DebugManager (detecta --debug automaticamente)
    debug_mgr = get_debug_manager()
    
    # Configura todo o ambiente (encoding, diretórios, console, AppUserModelID)
    debug_mgr.setup_debug_environment()
    
    # Adiciona diretório raiz ao path para imports
    sys.path.insert(0, str(debug_mgr.root_dir))
    
    # Loga informações do ambiente (apenas se debug_mode ativo)
    debug_mgr.log_environment_info("Main")
    
    # Import após configuração do ambiente
    from views.windows.main_window import MainWindow
    from views.windows.disclaimer_window import show_disclaimer_blocking
    from controllers.services.config_service import ConfigService
    from config.settings import ThemeManager
    from utils.logger import get_logger, set_log_callback
    
    logger = get_logger()
    
    # Inicializa tema global
    ThemeManager()
    
    # Cria e executa aplicação
    try:
        config_path = debug_mgr.root_dir / "config" / "user_config.json"
        config_service = ConfigService(config_path)
        
        if not config_service.get("disclaimer_accepted", False):
            # Cria app visível (não withdraw)
            app = MainWindow()
            
            # Configura callback do logger ANTES de mostrar disclaimer
            set_log_callback(app._log)
            
            # Mostra disclaimer (parent=app para poder minimizar)
            accepted = show_disclaimer_blocking(parent=app)
            
            if not accepted:
                logger.info("Aplicação encerrada: disclaimer não aceito", "Main")
                sys.exit(0)
            
            # Salva aceitação
            config_service.set("disclaimer_accepted", True)
            
            # Traz app para primeiro plano se necessário
            app.after(100, lambda: app.lift())
            app.after(150, lambda: app.focus_force())
        else:
            # Disclaimer já aceito, mostra app normalmente
            app = MainWindow()
            
            # Configura callback do logger
            set_log_callback(app._log)
        
        app.mainloop()
    except KeyboardInterrupt:
        logger.info("Aplicação encerrada pelo utilizador", "Main")
    except Exception as e:
        logger.error(f"Erro fatal: {e}", "Main", error=e)
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
    if "--profile" in sys.argv:
        run_with_profiling()
        exit(0)

    main()
