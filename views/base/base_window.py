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
    try:
        from utils.theme.theme_detector import get_windows_theme
        from pathlib import Path
        from PIL import Image
        import tkinter as tk
        import sys
        
        # Detecta tema
        theme = get_windows_theme()
        
        # Define nome do ícone baseado no tema
        icon_name = f"icon_{'light' if theme == 'light' else 'dark'}.ico"
        
        # Procura o ícone: prioridade para _MEIPASS (executável empacotado)
        icon_path = None
        
        # 1. Tenta _MEIPASS primeiro (executável)
        if getattr(sys, 'frozen', False):
            meipass = Path(getattr(sys, '_MEIPASS', ''))
            test_path = meipass / icon_name
            if test_path.exists():
                icon_path = test_path
                print(f"Ícone encontrado em _MEIPASS: {icon_path}")
        
        # 2. Tenta diretório do script/executável
        if icon_path is None:
            if getattr(sys, 'frozen', False):
                base_dir = Path(sys.executable).parent
            else:
                base_dir = Path(__file__).parent.parent.parent
            
            test_path = base_dir / icon_name
            if test_path.exists():
                icon_path = test_path
                print(f"Ícone encontrado em base_dir: {icon_path}")
        
        if icon_path is None or not icon_path.exists():
            print(f"Ícone não encontrado: {icon_name}")
            print(f"  Procurado em _MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}")
            print(f"  Frozen: {getattr(sys, 'frozen', False)}")
            return False
        
        # Para janelas CTkToplevel (secundárias), usa iconphoto com conversão
        if isinstance(window, ctk.CTkToplevel):
            try:
                # Carrega o .ico e converte para PhotoImage
                img = Image.open(str(icon_path))
                
                # Redimensiona para 32x32 (padrão Windows)
                if img.size[0] > 32 or img.size[1] > 32:
                    try:
                        # Tenta PIL 10+ primeiro
                        img = img.resize((32, 32), Image.Resampling.LANCZOS)  # type: ignore
                    except AttributeError:
                        # Fallback para PIL 9 e anteriores
                        img = img.resize((32, 32), Image.LANCZOS)  # type: ignore
                
                # Converte para RGB se necessário
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Salva em buffer e cria PhotoImage
                import io
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                buffer.seek(0)
                
                photo = tk.PhotoImage(data=buffer.getvalue())
                window.iconphoto(True, photo)
                # Mantém referência para evitar garbage collection
                setattr(window, '_icon_reference', photo)
                
                print(f"Ícone aplicado (CTkToplevel)")
                return True
            except Exception as e:
                print(f"Erro ao aplicar ícone (CTkToplevel): {e}")
                return False
        else:
            # Para janela principal (CTk), usa iconbitmap
            try:
                window.iconbitmap(str(icon_path))
                print(f"Ícone aplicado (CTk)")
                return True
            except Exception as e:
                print(f"Erro ao aplicar ícone (CTk): {e}")
                return False
                
    except Exception as e:
        print(f"Erro geral ao aplicar ícone: {e}")
        import traceback
        traceback.print_exc()
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
        set_window_icon_unified(self, title)
        
        # Construir UI
        self._build_ui()
        
        # Mostrar após construção
        self.after(50, self._show_window)
    
    def _show_window(self):
        self.deiconify()
        self.lift()
    
    def _build_ui(self):
        pass # Implementado nas subclasses
    
    def apply_theme_to_widget(self, widget, widget_type: str = "default"):
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