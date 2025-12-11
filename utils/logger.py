from typing import Optional, Callable
from enum import Enum
from datetime import datetime
import traceback

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

class Logger:    
    def __init__(self, log_callback: Optional[Callable] = None):
        self._log_callback = log_callback
        self._console_enabled = True
    
    @property
    def debug_mode(self) -> bool:
        from utils.debug import is_debug_mode
        return is_debug_mode()
    
    def set_callback(self, callback: Callable):
        self._log_callback = callback
    
    def set_debug_mode(self, enabled: bool):
        from utils.debug import get_debug_manager
        get_debug_manager().debug_mode = enabled
    
    def set_console(self, enabled: bool):
        self._console_enabled = enabled
    
    def _format_message(self, level: LogLevel, message: str, source: str = "") -> str:
        timestamp = datetime.now().strftime("%H:%M:%S")
        source_str = f"[{source}]" if source else ""
        return f"[{timestamp}] {level.value:7s} {source_str} {message}"

    def _output(self, formatted_message: str, level: LogLevel, error: Optional[Exception] = None, source: str = ""):
        # Console: só imprime se debug_mode está ativo
        if self._console_enabled and self.debug_mode:
            print(formatted_message)
            if error is not None:
                traceback.print_exc()

        # Callback UI recebe tudo exceto DEBUG, trace e source (exceto se debug_mode)
        if self._log_callback:
            send_to_callback = True
            # Não envia DEBUG nunca
            if level == LogLevel.DEBUG:
                send_to_callback = False
            # Não envia trace de erro, exceto se debug_mode
            if error is not None and not self.debug_mode:
                send_to_callback = False
            # Não envia source, exceto se debug_mode
            if source and not self.debug_mode:
                # Remove o source da mensagem
                formatted_message = formatted_message.replace(f"[{source}] ", "")
            if send_to_callback:
                try:
                    self._log_callback(formatted_message, error if self.debug_mode else None)
                except Exception as e:
                    if self._console_enabled and self.debug_mode:
                        print(f"[LOG ERROR] Falha no callback: {e}")
    
    def debug(self, message: str, source: str = ""):
        if self.debug_mode:
            formatted = self._format_message(LogLevel.DEBUG, message, source)
            self._output(formatted, LogLevel.DEBUG, source=source)
    
    def info(self, message: str, source: str = ""):
        formatted = self._format_message(LogLevel.INFO, message, source)
        self._output(formatted, LogLevel.INFO, source=source)
    
    def warning(self, message: str, source: str = ""):
        formatted = self._format_message(LogLevel.WARNING, message, source)
        self._output(formatted, LogLevel.WARNING, source=source)
    
    def error(self, message: str, source: str = "", error: Optional[Exception] = None):
        formatted = self._format_message(LogLevel.ERROR, message, source)
        self._output(formatted, LogLevel.ERROR, error, source=source)

# Instância global do logger
_global_logger: Optional[Logger] = None

def get_logger() -> Logger:
    global _global_logger
    if _global_logger is None:
        _global_logger = Logger()
    return _global_logger

def initialize_logger(log_callback: Optional[Callable] = None):
    if log_callback is not None: 
        get_logger().set_callback(log_callback)

def set_log_callback(callback: Callable):
    get_logger().set_callback(callback)

def set_debug_mode(enabled: bool):
    get_logger().set_debug_mode(enabled)

def set_console_output(enabled: bool):
    get_logger().set_console(enabled)
