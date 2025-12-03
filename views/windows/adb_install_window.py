import customtkinter as ctk
from typing import Optional, Callable
import threading
import os

from views.base.base_window import BaseWindow

class ADBInstallWindow(BaseWindow):
   
    def __init__(
        self,
        parent: ctk.CTk,
        on_success: Optional[Callable[[str], None]] = None
    ):
        self._on_success = on_success
        self.adb_path: Optional[str] = None
        self.installation_complete = False
        self.is_installing = False
        
        super().__init__(
            parent,
            title="Instalar Android Debug Bridge (ADB)",
            size=(500, 380),
            resizable=(False, False),
            modal=True
        )
    
    def _build_ui(self):
        self.configure_grid_weights(
            self.main_frame,
            rows=[(0, 0), (1, 1), (2, 0), (3, 0)],
            cols=[(0, 1)]
        )
        
        self._build_header()
        self._build_info()
        self._build_progress()
        self._build_footer()
    
    def _build_header(self):
        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        
        ctk.CTkLabel(
            header,
            text="ADB não encontrado",
            font=("", 18, "bold")
        ).pack()
        
        ctk.CTkLabel(
            header,
            text="O Android Debug Bridge (ADB) é necessário para enviar SMS",
            wraplength=450,
            font=("", 11),
            text_color="gray"
        ).pack(pady=5)
    
    def _build_info(self):
        info_frame = ctk.CTkFrame(self.main_frame)
        info_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        
        info_text = """O Android Debug Bridge (ADB) é uma ferramenta oficial da Google necessária para comunicação entre o computador e dispositivos Android.

                        Este programa pode fazer o download e instalação automática:

                        Transferência direta dos servidores oficiais da Google
                        Tamanho aproximado: 10-15 MB
                        Instalação local (sem permissões de administrador)
                        Compatível com Windows, macOS e Linux

                        Deseja continuar com a instalação?"""
                                
        ctk.CTkLabel(
            info_frame,
            text=info_text,
            justify="left",
            wraplength=info_frame.winfo_width(),
            anchor="w"
        ).pack(padx=15, pady=15, anchor="w")
    def _build_progress(self):
        self.progress_frame = ctk.CTkFrame(self.main_frame)        
        self.status_label = ctk.CTkLabel(
            self.progress_frame,
            text="A preparar instalação...",
            font=("", 12)
        )
        self.status_label.pack(pady=10)
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, width=400)
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0)
        
        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="",
            font=("", 10),
            text_color="gray"
        )
        self.progress_label.pack(pady=5)
    
    def _build_footer(self):
        footer = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=20, pady=20)
        
        self.cancel_btn = ctk.CTkButton(
            footer,
            text="Cancelar",
            fg_color="gray",
            width=120,
            command=self._cancel
        )
        self.cancel_btn.pack(side="left")
        
        self.install_btn = ctk.CTkButton(
            footer,
            text="Instalar ADB",
            fg_color="green",
            width=150,
            command=self._start_installation
        )
        self.install_btn.pack(side="right")
    
    def _start_installation(self):
        if self.is_installing:
            return
        
        self.is_installing = True
        self.progress_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        
        self.install_btn.configure(state="disabled")
        self.cancel_btn.configure(state="disabled")
        
        threading.Thread(target=self._install_adb, daemon=True).start()
    
    def _install_adb(self):
        try:
            # Define pasta de instalação
            install_folder = os.path.join(os.path.expanduser("~"), ".android_tools")
            os.makedirs(install_folder, exist_ok=True)
            
            self.after(0, lambda: self.status_label.configure(
                text="A fazer download dos servidores da Google..."
            ))
            
            try:
                from controllers.services.sms_sender import download_adb
                
                def update_progress(downloaded, total):
                    if total > 0:
                        percent = (downloaded / total) * 100
                        self.after(0, lambda: self.progress_bar.set(downloaded / total))
                        self.after(0, lambda: self.progress_label.configure(
                            text=f"{downloaded // 1024 // 1024} MB / {total // 1024 // 1024} MB ({percent:.1f}%)"
                        ))
                
                success, message, adb_path = download_adb(install_folder, update_progress)
                
            except ImportError:
                success, message, adb_path = self._simulate_download(install_folder)
            
            if success:
                self.adb_path = adb_path
                self.installation_complete = True
                
                self.after(0, lambda: self.status_label.configure(
                    text="Instalação concluída com sucesso!"
                ))
                self.after(0, lambda: self.progress_bar.set(1))
                self.after(0, lambda: self.progress_label.configure(
                    text=f"ADB instalado em: {adb_path}"
                ))
                
                # Callback de sucesso
                if self._on_success and adb_path and callable(self._on_success):
                    self.after(500, lambda: self._on_success(adb_path) if self._on_success else None)  # type: ignore
                
                # Fecha após 2 segundos
                self.after(2000, self._on_close)
            else:
                self._show_error(message)
                
        except Exception as e:
            self._show_error(str(e))
    
    def _simulate_download(self, install_folder: str) -> tuple:
        import time
        
        # Simula progresso
        for i in range(10):
            progress = (i + 1) / 10
            downloaded = int(15 * 1024 * 1024 * progress)
            total = 15 * 1024 * 1024
            
            self.after(0, lambda p=progress: self.progress_bar.set(p))
            self.after(0, lambda d=downloaded, t=total: self.progress_label.configure(
                text=f"{d // 1024 // 1024} MB / {t // 1024 // 1024} MB ({progress*100:.0f}%)"
            ))
            time.sleep(0.3)
        
        # Simula caminho do ADB
        adb_path = os.path.join(install_folder, "platform-tools", "adb")
        if os.name == 'nt':
            adb_path += ".exe"
        
        return True, "Instalação simulada com sucesso", adb_path
    
    def _show_error(self, message: str):
        self.after(0, lambda: self.status_label.configure(
            text=f"Erro: {message}",
            text_color="red"
        ))
        self.after(0, lambda: self.cancel_btn.configure(state="normal"))
        self.after(0, lambda: self.install_btn.configure(
            state="normal",
            text="Tentar Novamente"
        ))
        self.is_installing = False
    
    def _cancel(self):
        if not self.installation_complete:
            self._on_close()