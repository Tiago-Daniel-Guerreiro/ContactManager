
import sys
import tkinter as tk
from pathlib import Path
from typing import Union
import customtkinter as ctk
from datetime import datetime

def set_window_icon(window: Union[ctk.CTk, ctk.CTkToplevel], window_name: str = "Window") -> bool:
    try:
        # Importa função para obter caminho do ícone
        try:
            from utils.theme import get_icon_path
            icon_path_str = get_icon_path()
            
            if not icon_path_str:
                print(f"Nenhum ícone disponível")
                return False
            
            icon_path = Path(icon_path_str)
            
            # Debug detalhado
            print(f"Icon: {icon_path}")
            print(f"Existe: {icon_path.exists()}")
            print(f"Tipo janela: {type(window).__name__}")
            print(f"Frozen: {getattr(sys, 'frozen', False)}")
            if getattr(sys, 'frozen', False):
                print(f"_MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}")

        except ImportError as e:
            print(f"Erro ao importar: {e}")
            return False
        
        if not icon_path.exists():
            print(f"Ícone não encontrado: {icon_path}")
            return False
        
        # Aplica ícone baseado na plataforma
        if sys.platform == 'win32':
            if icon_path.suffix == '.ico':
                # Windows com arquivo .ico
                is_toplevel = isinstance(window, ctk.CTkToplevel)
                
                if is_toplevel:
                    # Converte .ico para PhotoImage usando PIL
                    try:
                        from PIL import Image
                        import io
                        
                        # Carrega o .ico
                        img = Image.open(str(icon_path))
                        
                        # Pega o maior ícone disponível no .ico
                        if hasattr(img, 'size'):
                            # Se for multi-size .ico, pega o maior
                            sizes = []
                            try:
                                for i in range(100):  # Tenta até 100 tamanhos
                                    img.seek(i)
                                    sizes.append((img.size, i))
                            except EOFError:
                                pass
                            
                            if sizes:
                                # Ordena por área e pega o maior
                                sizes.sort(key=lambda x: x[0][0] * x[0][1], reverse=True)
                                img.seek(sizes[0][1])
                        
                        # Converte para formato que PhotoImage aceita
                        # Redimensiona para 32x32 se necessário (padrão Windows)
                        if img.size[0] > 32 or img.size[1] > 32:
                            try:
                                img = img.resize((32, 32), Image.Resampling.LANCZOS)
                            except AttributeError:
                                img = img.resize((32, 32), Image.LANCZOS)  # type: ignore
                        
                        # Converte RGBA para RGB se necessário (PhotoImage não suporta alpha bem)
                        if img.mode == 'RGBA':
                            # Cria fundo branco
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            background.paste(img, mask=img.split()[3])  # Alpha channel como mask
                            img = background
                        elif img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        # Salva em buffer e carrega como PhotoImage
                        buffer = io.BytesIO()
                        img.save(buffer, format='PNG')
                        buffer.seek(0)
                        
                        # Cria PhotoImage
                        photo = tk.PhotoImage(data=buffer.getvalue())
                        window.iconphoto(True, photo)
                        setattr(window, '_icon_reference', photo)
                        
                        print(f"Aplicado via iconphoto() (convertido de .ico)")
                        return True
                        
                    except Exception as e:
                        print(f"Conversão PIL falhou: {e}")
                        import traceback
                        print(f"Traceback: {traceback.format_exc()}")
                
                # Para CTk (janela principal), tenta iconbitmap primeiro
                # Método 1: iconbitmap (mais compatível com CTk)
                try:
                    window.iconbitmap(str(icon_path))
                    print(f"Aplicado via iconbitmap()")
                    return True
                except Exception as e1:
                    print(f"iconbitmap() falhou: {e1}")
                
                # Método 2: wm_iconbitmap (alternativa)
                try:
                    window.wm_iconbitmap(str(icon_path))
                    print(f"Aplicado via wm_iconbitmap()")
                    return True
                except Exception as e2:
                    print(f"wm_iconbitmap() falhou: {e2}")
                
                return False
                
            elif icon_path.suffix == '.png':
                # Windows com arquivo .png
                try:
                    icon = tk.PhotoImage(file=str(icon_path))
                    window.iconphoto(True, icon)
                    # IMPORTANTE: Mantém referência para evitar garbage collection
                    setattr(window, '_icon_reference', icon)
                    print(f"Aplicado via iconphoto() (PNG)")
                    return True
                except Exception as e:
                    print(f"iconphoto() falhou: {e}")
                    return False
        else:
            # Outras plataformas (Linux, macOS) - usa PNG com iconphoto
            try:
                # Converte .ico para .png se necessário
                if icon_path.suffix == '.ico':
                    png_path = icon_path.with_suffix('.png')
                    if png_path.exists():
                        icon_path = png_path
                
                icon = tk.PhotoImage(file=str(icon_path))
                window.iconphoto(True, icon)
                setattr(window, '_icon_reference', icon)
                print(f"Aplicado (não-Windows)")
                return True
            except Exception as e:
                print(f"Erro: {e}")
                return False
        
        # Se nenhum método funcionou
        return False
                
    except Exception as e:
        print(f"Erro geral ao aplicar ícone: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False
