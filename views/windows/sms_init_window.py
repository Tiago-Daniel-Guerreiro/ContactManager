import customtkinter as ctk
from typing import Optional, Callable
import threading
import time

from views.base.base_window import BaseWindow
from views.windows.adb_install_window import ADBInstallWindow

class SMSInitializationWindow(BaseWindow):    
    def __init__(
        self,
        parent: ctk.CTk,
        sms_sender,  # SMS_Sender instance
        on_success: Optional[Callable] = None
    ):
        self.sms_sender = sms_sender
        self._on_success = on_success
        
        # Estado
        self.is_monitoring = False
        self.device_detected = False
        self.adb_authorized = False
        self.initialization_complete = False
        self.adb_checked = False
        
        super().__init__(
            parent,
            title="Configurar Envio de SMS",
            size=(700, 700),
            resizable=(False, False),
            modal=True
        )
        
        # Verifica ADB antes de iniciar monitoramento
        self.after(100, self._check_adb)
    
    def _build_ui(self):
        # Configurar grid
        self.configure_grid_weights(
            self.main_frame,
            rows=[(0, 0), (1, 1), (2, 0)],
            cols=[(0, 1)]
        )
        
        self._build_header()
        self._build_content()
        self._build_footer()
    
    def _build_header(self):
        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        
        ctk.CTkLabel(
            header,
            text="Configuração de Envio SMS via Android",
            font=("", 18, "bold")
        ).pack()
        
        ctk.CTkLabel(
            header,
            text="Conecte o seu dispositivo Android via USB",
            text_color="gray"
        ).pack(pady=5)
    
    def _build_content(self):
        content = ctk.CTkFrame(self.main_frame)
        content.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        content.grid_columnconfigure(0, weight=1)
        
        self.step1_frame = self._create_step_frame(
            content,
            row=0,
            icon="⏳",
            title="Passo 1: Conectar Telemóvel",
            description="Aguardando conexão USB..."
        )
        
        self.step2_frame = self._create_step_frame(
            content,
            row=1,
            icon="⏸️",
            title="Passo 2: Ativar Depuração USB",
            description="Aguardando passo 1..."
        )
        
        self.step3_frame = self._create_step_frame(
            content,
            row=2,
            icon="⚙️",
            title="Passo 3: Desativar RCS (Chat) no app de mensagens",
            description="Importante: Desative o RCS/Chat no app de mensagens para garantir o envio correto de SMS."
        )
        
        # Frame de instruções (inicialmente oculto)
        self.instructions_frame = ctk.CTkFrame(content)
        
        self._build_instructions()
    
    def _check_adb(self):
        def check_thread():
            adb_found, msg = self.sms_sender.find_adb()
            
            if not adb_found:
                # ADB não encontrado, mostra janela de instalação
                self.after(0, self._show_adb_install_window)
            else:
                # ADB encontrado, inicia monitoramento
                self.after(0, self._start_monitoring)
        
        threading.Thread(target=check_thread, daemon=True).start()
    
    def _show_adb_install_window(self):
        def on_adb_installed(adb_path: str):
            self.sms_sender.adb_path = adb_path
            self.adb_checked = True
            self.after(100, self._start_monitoring)
        
        # Mostra janela de instalação
        _ = ADBInstallWindow(
            parent=self.winfo_toplevel(),  # type: ignore
            on_success=on_adb_installed
        )
    
    def _create_step_frame(
        self,
        parent,
        row: int,
        icon: str,
        title: str,
        description: str
    ) -> dict:
        frame = ctk.CTkFrame(parent)
        frame.grid(row=row, column=0, sticky="ew", padx=10, pady=10)
        frame.grid_columnconfigure(1, weight=1)
        
        # Ícone
        icon_label = ctk.CTkLabel(frame, text=icon, font=("", 28))
        icon_label.grid(row=0, column=0, rowspan=2, padx=15, pady=10)
        
        # Título
        title_label = ctk.CTkLabel(
            frame,
            text=title,
            font=("", 14, "bold"),
            anchor="w"
        )
        title_label.grid(row=0, column=1, sticky="w", pady=(10, 0))
        
        # Descrição
        desc_label = ctk.CTkLabel(
            frame,
            text=description,
            anchor="w",
            text_color="gray"
        )
        desc_label.grid(row=1, column=1, sticky="w", pady=(0, 10))
        
        return {
            "frame": frame,
            "icon": icon_label,
            "title": title_label,
            "description": desc_label
        }
    
    def _build_instructions(self):
        scroll = ctk.CTkScrollableFrame(self.instructions_frame, height=200)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Título principal
        ctk.CTkLabel(
            scroll,
            text="Como ativar a Depuração USB no Android:",
            font=("", 14, "bold"),
            anchor="w",
            text_color="#3b82f6"
        ).pack(anchor="w", pady=(5, 15))
        
        # Instruções detalhadas
        instructions = [
            ("1. Ativar Modo de Programador:", [
                "• Abra as 'Definições' no seu telemóvel Android",
                "• Procure por 'Acerca do telefone' ou 'Sobre o dispositivo'",
                "• Encontre 'Número de compilação' ou 'Versão de compilação'",
                "• Toque 7 VEZES seguidas no 'Número de compilação'",
                "• Aparecerá uma mensagem: 'Agora é um programador!'"
            ]),
            ("", []),  # Espaço
            ("2. Ativar Depuração USB:", [
                "• Volte ao menu principal de Definições",
                "• Procure por 'Opções de programador' ou 'Opções de desenvolvedor'",
                "• Entre nesse menu",
                "• Encontre 'Depuração USB' ou 'USB debugging'",
                "• ATIVE a opção 'Depuração USB'"
            ]),
            ("", []),  # Espaço
            ("3. Autorizar o Computador:", [
                "• Quando ligar o telemóvel ao PC via USB",
                "• Aparecerá um aviso no telemóvel perguntando:",
                "  'Permitir depuração USB?'",
                "• MARQUE a caixa 'Permitir sempre deste computador'",
                "• Toque em 'PERMITIR' ou 'OK'"
            ]),
            ("", []),  # Espaço
            ("⚠️ Importante:", [
                "• Use um cabo USB de DADOS (não apenas de carregamento)",
                "• Alguns cabos só servem para carregar e não funcionam!",
                "• Se não aparecer nada no telemóvel, experimente outro cabo USB"
            ])
        ]
        
        for title, steps in instructions:
            if title:
                title_label = ctk.CTkLabel(
                    scroll,
                    text=title,
                    font=("", 12, "bold"),
                    anchor="w",
                    wraplength=620
                )
                title_label.pack(anchor="w", pady=(5, 3))
            
            for step in steps:
                step_label = ctk.CTkLabel(
                    scroll,
                    text=step,
                    anchor="w",
                    wraplength=600,
                    font=("", 11)
                )
                step_label.pack(anchor="w", padx=(10, 0), pady=1)
        
        # Nota final
        note_frame = ctk.CTkFrame(scroll, fg_color="#2d2d2d")
        note_frame.pack(fill="x", pady=(15, 5))
        
        ctk.CTkLabel(
            note_frame,
            text="Dica: Estas opções variam ligeiramente entre marcas (Samsung, Xiaomi, Huawei, etc.)\nmas o processo geral é sempre o mesmo.",
            font=("", 10),
            text_color="gray",
            justify="left"
        ).pack(padx=10, pady=10)
        
        # Botão de retry
        self.retry_btn = ctk.CTkButton(
            self.instructions_frame,
            text="Verificar Novamente",
            fg_color="#FFA500",
            command=self._retry_check
        )
        self.retry_btn.pack(pady=10)
    
    def _build_footer(self):
        footer = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=20, pady=20)
        
        self.cancel_btn = ctk.CTkButton(
            footer,
            text="Cancelar",
            fg_color="gray",
            width=100,
            command=self._cancel
        )
        self.cancel_btn.pack(side="left")
        
        self.finish_btn = ctk.CTkButton(
            footer,
            text="Concluir",
            fg_color="green",
            width=120,
            state="disabled",
            command=self._finish
        )
        self.finish_btn.pack(side="right")
    
    def _start_monitoring(self):
        self.is_monitoring = True
        threading.Thread(target=self._monitor_loop, daemon=True).start()
    
    def _monitor_loop(self):
        while self.is_monitoring and not self.initialization_complete:
            try:
                # Verifica dispositivos conectados
                if hasattr(self.sms_sender, '_get_connected_devices'):
                    devices = self.sms_sender._get_connected_devices()
                else:
                    devices = []
                
                if devices:
                    # Dispositivo detectado
                    if not self.device_detected:
                        self.device_detected = True
                        self.after(0, self._update_step1_detected)
                    
                    # Verifica autorização
                    authorized = [(d, s) for d, s in devices if s == 'device']
                    unauthorized = [(d, s) for d, s in devices if s == 'unauthorized']
                    
                    if authorized:
                        if not self.adb_authorized:
                            self.adb_authorized = True
                            device_id = authorized[0][0]
                            self.after(0, lambda d=device_id: self._update_step2_authorized(d))
                    elif unauthorized:
                        self.adb_authorized = False
                        self.after(0, self._update_step2_unauthorized)
                else:
                    # Sem dispositivo
                    if self.device_detected:
                        self.device_detected = False
                        self.adb_authorized = False
                        self.after(0, self._update_step1_waiting)
                
                time.sleep(2)
                
            except Exception as e:
                self._log_error(f"Erro no monitoramento: {e}")
                time.sleep(2)
    
    def _update_step1_detected(self):
        self.step1_frame["icon"].configure(text="✅")
        self.step1_frame["description"].configure(
            text="Dispositivo Android conectado!",
            text_color="green"
        )
        
        # Atualiza passo 2
        self.step2_frame["icon"].configure(text="⏳")
        self.step2_frame["description"].configure(
            text="Verificando depuração USB...",
            text_color="gray"
        )
        
        # Atualiza passo 3
        self.step3_frame["icon"].configure(text="⏸️")
        self.step3_frame["description"].configure(
            text="Aguardando autorização...",
            text_color="gray"
        )
    
    def _update_step1_waiting(self):
        self.step1_frame["icon"].configure(text="⏳")
        self.step1_frame["description"].configure(
            text="Aguardando conexão USB...",
            text_color="gray"
        )
        
        self.step2_frame["icon"].configure(text="⏸️")
        self.step2_frame["description"].configure(
            text="Aguardando passo 1...",
            text_color="gray"
        )
        
        # Esconde instruções
        self.instructions_frame.grid_forget()
        self.finish_btn.configure(state="disabled")
    
    def _update_step2_unauthorized(self):
        self.step2_frame["icon"].configure(text="⚠️")
        self.step2_frame["description"].configure(
            text="Depuração USB não ativada ou não autorizada - Veja as instruções abaixo",
            text_color="orange"
        )
        
        # Mostra instruções com destaque
        if not self.instructions_frame.winfo_viewable():
            self.instructions_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=10)
    
    def _update_step2_authorized(self, device_id: str):
        self.step2_frame["icon"].configure(text="✅")
        
        # Obtém info do dispositivo usando método centralizado
        if hasattr(self.sms_sender, 'get_device_info_external'):
            model, brand, full_name = self.sms_sender.get_device_info_external(device_id)
        else:
            # Fallback para compatibilidade
            model = ""
            brand = ""
            if hasattr(self.sms_sender, '_get_device_model'):
                model = self.sms_sender._get_device_model(device_id)
            if hasattr(self.sms_sender, '_get_device_brand'):
                brand = self.sms_sender._get_device_brand(device_id)
            full_name = f"{brand} {model}".strip() if brand else model
        
        self.step2_frame["description"].configure(
            text=f"Autorizado! Dispositivo: {full_name}",
            text_color="green"
        )
        
        # Atualiza passo 3
        self.step3_frame["icon"].configure(text="⚠️")
        self.step3_frame["description"].configure(
            text="Importante: Desative o RCS/Chat no app de mensagens manualmente!",
            text_color="#FFA500"
        )
        
        # Esconde instruções
        self.instructions_frame.grid_forget()
        
        # Atualiza sms_sender
        if hasattr(self.sms_sender, 'device_id'):
            self.sms_sender.device_id = device_id
        if hasattr(self.sms_sender, 'device_connected'):
            self.sms_sender.device_connected = True
        
        # Ativa botão de concluir
        self.finish_btn.configure(state="normal")
        self.initialization_complete = True
    
    def _retry_check(self):
        self.step2_frame["description"].configure(
            text="Verificando...",
            text_color="gray"
        )
    
    def _cancel(self):
        self.is_monitoring = False
        self.initialization_complete = False
        self._on_close()
    
    def _finish(self):
        self.is_monitoring = False
        
        if self._on_success:
            self._on_success()
        
        self._on_close()