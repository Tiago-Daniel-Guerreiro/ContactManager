import sys
import os
from pathlib import Path
from typing import Optional, TYPE_CHECKING

import tkinter as tk
from tkinter import messagebox

from utils.environment import (
    get_base_dir,
    setup_environment,
    get_environment_info,
    is_frozen,
    get_meipass
)
from utils.windows import is_windows, allocate_console, set_app_user_model_id

if TYPE_CHECKING:
    from utils.logger import Logger

class DebugManager:
    _instance: Optional['DebugManager'] = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, debug_mode: Optional[bool] = None):
        # Se já foi inicializado, não inicializa novamente
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._initialized = True
        if debug_mode is not None:
            self._debug_mode = debug_mode 
        else:
            self._debug_mode = self._detect_debug_from_args()
        self._console_allocated = False
        self._logger: Optional['Logger'] = None
        self._root_dir = get_base_dir()

    @staticmethod
    def _detect_debug_from_args() -> bool:
        # Tenta detectar --debug de 2 formas:
        # Via sys.argv (quando roda script Python)
        is_debug_argv = "--debug" in sys.argv
        
        # Via variável de ambiente (quando roda exe ou script)
        is_debug_env = os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes")
        
        return is_debug_argv or is_debug_env
    
    @property
    def debug_mode(self) -> bool:
        return self._debug_mode
    
    @debug_mode.setter
    def debug_mode(self, value: bool):
        self._debug_mode = value
    
    @property
    def root_dir(self) -> Path:
        return self._root_dir

    def get_meipass(self) -> Optional[str]:
        meipass = get_meipass()
        return str(meipass) if meipass else None
    
    def setup_debug_environment(self) -> None:
        # Configura ambiente (encoding, diretórios, env vars)
        setup_environment(self._root_dir)
        
        # Se debug está ativo, mostra no console e message box
        if self._debug_mode:
            print(f"[INICIALIZAÇÃO] Modo DEBUG ativado!", flush=True)
            # Message box visível
            try:
                root = tk.Tk()
                root.withdraw()  # Esconde a janela principal
                messagebox.showinfo("Debug Mode", "Modo DEBUG ativado!")
                root.destroy()
            except Exception as e:
                print(f"[INICIALIZAÇÃO] Erro ao mostrar message box: {e}", flush=True)
        
        # Aloca console se necessário (Windows .exe em modo debug)
        if self._debug_mode and is_windows() and is_frozen():
            self._console_allocated = allocate_console()
        
        # AppUserModelID para Windows
        if is_windows():
            set_app_user_model_id()
    
    def get_environment_info(self) -> dict:
        info = get_environment_info(self._root_dir)
        info["debug_mode"] = self._debug_mode
        return info
    
    def log_environment_info(self, source: str = "Main") -> None:
        if not self._debug_mode:
            return
        
        from utils.logger import get_logger
        
        info = self.get_environment_info()
        get_logger().debug("Modo debug ativado", source)
        get_logger().debug(f"Python: {info['python_version']}", source)
        get_logger().debug(f"Executável: {info['executable']}", source)
        get_logger().debug(f"Frozen: {info['frozen']}", source)
        if info.get('meipass'): # Meipass = 
            get_logger().debug(f"_MEIPASS: {info['meipass']}", source)
        get_logger().debug(f"Diretório atual: {info['current_dir']}", source)
        get_logger().debug(f"ROOT_DIR: {info['base_dir']}", source)

# Instância global
_debug_manager: Optional[DebugManager] = None

def get_debug_manager() -> DebugManager:
    global _debug_manager
    if _debug_manager is None:
        _debug_manager = DebugManager()
    return _debug_manager


def initialize_debug(debug_mode: Optional[bool] = None) -> DebugManager:
    global _debug_manager
    if _debug_manager is not None:
        _debug_manager._initialized = False
    _debug_manager = DebugManager(debug_mode=debug_mode)
    return _debug_manager

def is_debug_mode() -> bool:
    return get_debug_manager().debug_mode

def set_debug_mode(enabled: bool) -> None:
    get_debug_manager().debug_mode = enabled