import customtkinter as ctk
from typing import Optional, Callable
import sys
import tkinter as tk
from pathlib import Path

# Importação condicional para evitar erros
try:
    from config.settings import ThemeManager
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from config.settings import ThemeManager


def set_window_icon_unified(window, window_name="Window"):
    """
    Aplica ícone a qualquer tipo de janela (CTk ou CTkToplevel).
    Usa o ícone apropriado para o tema atual do sistema.
    """
    try:
        from utils.theme.theme_detector import get_icon_path, get_windows_theme
        
        # Detecta tema e obtém ícone apropriado
        theme = get_windows_theme()
        icon_path = get_icon_path(theme=theme)
        
        if icon_path.exists():
            window.iconbitmap(str(icon_path))
            return True
        else:
            print(f"Ícone não encontrado: {icon_path}")
            return False
    except Exception as e:
        print(f"Erro ao aplicar ícone em {window_name}: {e}")
        return False


class BaseWindow(ctk.CTkToplevel):
    def __init__(
        self,
        parent: ctk.CTk,
        title: str = "Janela",
        size: tuple = (600, 400),
        resizable: tuple = (True, True),
        modal: bool = True,
        center: bool = True
    ):
        # Inicialização silenciosa - esconde antes de construir
        super().__init__(parent)
        self.withdraw()  # Esconde imediatamente
        
        # Referências
        self.parent = parent
        self.theme = ThemeManager()
        
        # Configuração básica
        self.title(title)
        self.geometry(f"{size[0]}x{size[1]}")
        self.resizable(resizable[0], resizable[1])
        
        # Aplica cores do tema
        self.configure(fg_color=self.theme.get_background())
        
        # Configurar grid elástico na raiz
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Container principal com grid e cores do tema
        self.main_frame = ctk.CTkFrame(
            self,
            fg_color=self.theme.get_background(),
            border_color=self.theme.get_border(),
            border_width=0
        )
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Callbacks
        self._on_close_callback: Optional[Callable] = None
        
        # Bind de eventos
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Configure>", self._on_configure) # Redimensionamento
        self.bind("<Escape>", lambda e: self._on_close())
        
        # Construir UI (implementado nas subclasses)
        self._build_ui()
        
        # Modal e transient
        if modal:
            self.transient(parent)
            # Aplica ícone também em janelas secundárias
            set_window_icon_unified(self, title)
            self.grab_set()
        else:
            # Também aplica em janelas não-modais
            set_window_icon_unified(self, title)
        
        # Centralizar e mostrar
        if center:
            self._center_on_parent()
        
        # Mostra a janela já construída (sem flickering)
        self.deiconify()
        self.lift()
        self.focus_force()
    
    def _build_ui(self):
        pass
    
    def _center_on_parent(self):
        self.update_idletasks()

        # Dimensões da janela e do pai
        w = self.winfo_width()
        h = self.winfo_height()
        pw = self.parent.winfo_width()
        ph = self.parent.winfo_height()
        px = self.parent.winfo_x()
        py = self.parent.winfo_y()

        # Dimensões da tela
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        # Calcula posição central relativa ao pai
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2

        # Ajusta para não sair da tela
        x = max(0, min(x, sw - w))
        y = max(0, min(y, sh - h))

        self.geometry(f"+{x}+{y}")

    def _on_configure(self, event):
        pass
    
    # Removido _set_window_icon - janelas secundárias herdam ícone do pai via transient()
    
    def _on_close(self):
        if self._on_close_callback:
            self._on_close_callback()
        self.grab_release()
        self.destroy()
    
    def set_on_close(self, callback: Callable):
        self._on_close_callback = callback
    
    def configure_grid_weights(
        self,
        frame: ctk.CTkFrame,
        rows: list[tuple[int, int]],
        cols: list[tuple[int, int]]
    ):
        for row_idx, weight in rows:
            frame.grid_rowconfigure(row_idx, weight=weight)
        for col_idx, weight in cols:
            frame.grid_columnconfigure(col_idx, weight=weight)
    
    def apply_theme_to_widget(self, widget, widget_type: str = "default"):
        """
        Aplica cores do tema a um widget específico.
        
        Args:
            widget: O widget CTk a ser estilizado
            widget_type: Tipo do widget ('frame', 'button', 'label', 'entry', 'default')
        """
        if widget_type == "frame":
            widget.configure(
                fg_color=self.theme.get_surface(),
                border_color=self.theme.get_border()
            )
        elif widget_type == "button":
            widget.configure(
                fg_color=self.theme.get_primary(),
                hover_color=self.theme.get_primary(),
                text_color=self.theme.get_text(),
                border_color=self.theme.get_border()
            )
        elif widget_type == "label":
            widget.configure(
                text_color=self.theme.get_text(),
                fg_color="transparent"
            )
        elif widget_type == "entry":
            widget.configure(
                fg_color=self.theme.get_surface(),
                text_color=self.theme.get_text(),
                border_color=self.theme.get_border()
            )
        elif widget_type == "text":
            widget.configure(
                fg_color=self.theme.get_surface(),
                text_color=self.theme.get_text(),
                border_color=self.theme.get_border()
            )
        # Adicione mais tipos conforme necessário


class BaseMainWindow(ctk.CTk):   
    def __init__(
        self,
        title: str = "Aplicação",
        size: tuple = (1000, 750),
        min_size: tuple = (800, 600)
    ):
        super().__init__()
        
        # Esconde durante construção
        self.withdraw()
        
        # Theme
        self.theme = ThemeManager()
        
        # Configuração
        self.title(title)
        self.geometry(f"{size[0]}x{size[1]}")
        self.minsize(min_size[0], min_size[1])
        
        # Aplica cores do tema
        self.configure(fg_color=self.theme.get_background())
        
        # Grid elástico
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Define ícone da janela principal (usa tema do sistema)
        self._set_window_icon()
        
        # Construir UI
        self._build_ui()
        
        # Mostrar após construção
        self.after(50, self._show_window)
    
    def _set_window_icon(self):
        """Define o ícone baseado no tema do sistema"""
        from utils.theme.theme_detector import get_icon_path
        try:
            icon_path = get_icon_path(theme=self.theme.current_theme)
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except Exception as e:
            print(f"Erro ao definir ícone: {e}")
    
    def _show_window(self):
        self.deiconify()
        self.lift()
    
    def _build_ui(self):
        pass # Implementado nas subclasses
    
    def apply_theme_to_widget(self, widget, widget_type: str = "default"):
        """
        Aplica cores do tema a um widget específico.
        
        Args:
            widget: O widget CTk a ser estilizado
            widget_type: Tipo do widget ('frame', 'button', 'label', 'entry', 'default')
        """
        if widget_type == "frame":
            widget.configure(
                fg_color=self.theme.get_surface(),
                border_color=self.theme.get_border()
            )
        elif widget_type == "button":
            widget.configure(
                fg_color=self.theme.get_primary(),
                hover_color=self.theme.get_primary(),
                text_color=self.theme.get_text(),
                border_color=self.theme.get_border()
            )
        elif widget_type == "label":
            widget.configure(
                text_color=self.theme.get_text(),
                fg_color="transparent"
            )
        elif widget_type == "entry":
            widget.configure(
                fg_color=self.theme.get_surface(),
                text_color=self.theme.get_text(),
                border_color=self.theme.get_border()
            )
        elif widget_type == "text":
            widget.configure(
                fg_color=self.theme.get_surface(),
                text_color=self.theme.get_text(),
                border_color=self.theme.get_border()
            )