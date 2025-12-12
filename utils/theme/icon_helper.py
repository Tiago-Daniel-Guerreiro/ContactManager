from pathlib import Path
from typing import Union, Callable, Any
import customtkinter as ctk
import tkinter as tk
from utils.logger import get_logger
from utils.theme.get_icon import get_icon_path
from utils.environment import platform_is_windows

# Tenta importar Pillow para melhor qualidade
try:
    from PIL import Image, ImageTk
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


def set_window_icon_unified(
    window: Union[ctk.CTk, ctk.CTkToplevel], 
    window_name: str = "Window"
) -> bool:
    logger = get_logger()

    try:
        is_main_window = isinstance(window, ctk.CTk)
        icon_aplicado = False

        if platform_is_windows: # .ico
            icon_aplicado = _apply_ico_icon(window, window_name, is_main_window, logger)

        if not icon_aplicado: # .png
            icon_aplicado = _apply_png_icon(window, window_name, is_main_window, logger)

        if not icon_aplicado: # Se nenhum ícone foi aplicado
            logger.warning(f"[{window_name}] Nenhum ícone foi aplicado!")

        return icon_aplicado
        
    except Exception as e:
        logger.error(f"[{window_name}] Erro ao aplicar ícone", error=e)
        return False

def _apply_ico_icon(
    window: Union[ctk.CTk, ctk.CTkToplevel],
    window_name: str,
    is_main_window: bool,
    logger
) -> bool:
    icon_path = get_icon_path("ico")
    
    if not icon_path or not Path(icon_path).exists():
        logger.debug(f"[{window_name}] Arquivo .ico não encontrado")
        return False

    try:
        if is_main_window:
            window.iconbitmap(str(icon_path))
            logger.debug(f"[{window_name}] Ícone .ico aplicado (janela principal)")
            return True
        else:
            # Para CTkToplevel, precisa de delay
            _apply_with_retry(
                window=window,
                apply_func=lambda: window.iconbitmap(str(icon_path)),
                window_name=window_name,
                icon_type="ico",
                logger=logger
            )
            return True
    except Exception as e:
        logger.error(f"[{window_name}] Erro ao aplicar .ico",error=e)
        return False


def _apply_png_icon(
    window: Union[ctk.CTk, ctk.CTkToplevel],
    window_name: str,
    is_main_window: bool,
    logger
) -> bool:
    icon_path = get_icon_path(ext_preference="png")
    
    if not icon_path or not Path(icon_path).exists():
        logger.debug(f"[{window_name}] Arquivo .png não encontrado")
        return False

    try:
        # Tenta usar Pillow para melhor qualidade
        if HAS_PILLOW:
            icon = _load_png_with_pillow(icon_path)
            logger.debug(f"[{window_name}] PNG carregado via Pillow")
        else:
            icon = tk.PhotoImage(file=str(icon_path))
            logger.debug(f"[{window_name}] PNG carregado via tk.PhotoImage")

        # Mantém referência para evitar garbage collection
        setattr(window, '_icon_reference', icon)

        if is_main_window:
            window.iconphoto(True, icon)  # True = aplicar a todas as janelas
            logger.debug(f"[{window_name}] Ícone .png aplicado (janela principal)")
            return True
        else:
            _apply_with_retry(
                window=window,
                apply_func=lambda: window.iconphoto(False, icon),
                window_name=window_name,
                icon_type="png",
                logger=logger
            )
            return True
            
    except Exception as e:
        logger.error(f"[{window_name}] Erro ao aplicar .png",error=e)
        return False


def _load_png_with_pillow(icon_path: str) -> Any:
    img = Image.open(icon_path)
    
    # Redimensiona para tamanho adequado mantendo qualidade
    # Windows usa 32x32 para a barra de título
    sizes = [(256, 256), (48, 48), (32, 32), (16, 16)]
    
    # Usa o tamanho original se for adequado, senão redimensiona
    if img.size[0] > 64:
        img = img.resize((64, 64), Image.Resampling.LANCZOS)
    
    return ImageTk.PhotoImage(img)


def _apply_with_retry(
    window: Union[ctk.CTk, ctk.CTkToplevel],
    apply_func: Callable[[], None],
    window_name: str,
    icon_type: str,
    logger,
    max_attempts: int = 30,
    initial_delay: int = 100,
    retry_delay: int = 50
) -> None:    
    def attempt(count: int = 0) -> None:
        try:
            if window.winfo_exists():
                apply_func()
                logger.debug(f"[{window_name}] Ícone .{icon_type} aplicado após {count + 1} tentativa(s)")
                return
        except tk.TclError:
            pass  # Janela ainda não está pronta
        except Exception as e:
            if count + 1 >= max_attempts:
                logger.error(f"[{window_name}] Falha ao aplicar .{icon_type} após {max_attempts} tentativas",error=e)
                return
        
        if count < max_attempts:
            window.after(retry_delay, lambda: attempt(count + 1))
    
    # Delay inicial maior para garantir que a janela está criada
    window.after(initial_delay, attempt)