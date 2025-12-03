import customtkinter as ctk
from typing import Optional, List, Union, TYPE_CHECKING
import threading
import json
import os
import webbrowser
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

from views.base.base_window import BaseMainWindow
from views.windows.contact_editor_window import ContactEditorWindow
from views.windows.preview_window import PreviewDashboardWindow
from views.windows.selection_window import ContactSelectionWindow
from models.contact import Contact
from config.settings import ThemeManager
from controllers.contact_controller import ContactController
from controllers.services.data_handler import DataHandler
from controllers.services.contact_service import ContactService

if TYPE_CHECKING:
    from controllers.services.whatsapp_sender import WhatsAppSender
    from controllers.services.sms_sender import SMSSender

@dataclass
class SendReport:
    contact_name: str
    contact_phone: str
    status: str  # 'sucesso', 'erro'
    message: str
    timestamp: str

class ReportGenerator:    
    @staticmethod
    def generate_html_report(reports: List[SendReport], method: str, output_file: Path) -> bool:
        try:
            successful = sum(1 for r in reports if r.status == "sucesso")
            total = len(reports)
            
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Relatório de Envios</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
        .header h1 {{ margin: 0; }}
        .summary {{ background: white; padding: 15px; margin: 20px 0; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .success {{ color: #27ae60; font-weight: bold; }}
        .error {{ color: #e74c3c; font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; background: white; }}
        th {{ background: #34495e; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #ecf0f1; }}
        tr:hover {{ background: #f8f9fa; }}
        .status-success {{ background: #d5f4e6; color: #27ae60; }}
        .status-error {{ background: #fadbd8; color: #e74c3c; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ecf0f1; color: #7f8c8d; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Relatório de Envios</h1>
        <p>Método: <strong>{method.upper()}</strong></p>
    </div>
    
    <div class="summary">
        <h2>Resumo</h2>
        <p>Total de Contactos: <strong>{total}</strong></p>
        <p class="success">Sucesso: {successful}/{total}</p>
        <p class="error">Erros: {total - successful}/{total}</p>
        <p>Taxa de Sucesso: <strong>{(successful/total*100):.1f}%</strong></p>
    </div>
    
    <h2>Detalhes</h2>
    <table>
        <thead>
            <tr>
                <th>Nome</th>
                <th>Telefone</th>
                <th>Status</th>
                <th>Mensagem</th>
                <th>Data/Hora</th>
            </tr>
        </thead>
        <tbody>
"""
            
            for report in reports:
                status_class = "status-success" if report.status == "sucesso" else "status-error"
                status_text = "SUCESSO" if report.status == "sucesso" else "ERRO"
                html_content += f"""            <tr>
                <td>{report.contact_name}</td>
                <td>{report.contact_phone}</td>
                <td class="{status_class}">{status_text}</td>
                <td>{report.message}</td>
                <td>{report.timestamp}</td>
            </tr>
"""
            html_content += """        </tbody>
    </table>
    
    <div class="footer">
        <p>Relatório gerado automaticamente pela aplicação de Mensagens Automáticas</p>
        <p>Data: """ + datetime.now().strftime("%d/%m/%Y %H:%M:%S") + """</p>
    </div>
</body>
</html>
"""
            
            # Salva arquivo HTML
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return True
        except Exception as e:
            print(f"Erro ao gerar relatório: {e}")
            return False

class MainWindow(BaseMainWindow):
    def __init__(self):
        self.theme = ThemeManager()
        
        # Controller e Data Handler
        self.controller = ContactController()
        self.data_handler = DataHandler()
        self.controller.set_data_handler(self.data_handler)
        
        # Service (lógica de negócio centralizada)
        self.service = ContactService(self.data_handler)
        
        # Estado da aplicação
        self.is_sending = False
        self.selected_contacts: List[Contact] = []
        self.sender: Optional[Union['WhatsAppSender', 'SMSSender']] = None
        
        # Configura callbacks
        self.controller.set_callbacks(
            on_contacts_changed=self._on_contacts_changed,
            on_log=self._log
        )
        
        super().__init__(
            title=self.theme.settings.app_name,
            size=self.theme.settings.main_window_size,
            min_size=self.theme.settings.min_window_size
        )

    def _build_ui(self):
        # Container principal com scroll
        self.main_container = ctk.CTkScrollableFrame(self)
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.main_container.grid_columnconfigure(0, weight=1)
        
        row = 0
        row = self._build_header(row)
        row = self._build_data_section(row)
        row = self._build_message_section(row)
        row = self._build_options_section(row)
        row = self._build_controls_section(row)
        row = self._build_log_section(row)
        self.after(100, self._load_config)
        
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _build_header(self, row: int) -> int:
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent", height=60)
        frame.grid(row=row, column=0, sticky="ew", padx=10, pady=(10, 5))
        frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            frame,
            text=self.theme.settings.app_name,
            font=("Segoe UI", 24, "bold")
        ).grid(row=0, column=0, sticky="w")
        
        ctk.CTkLabel(
            frame,
            text=f"v{self.theme.settings.version}",
            text_color="gray",
            font=("Segoe UI", 11)
        ).grid(row=0, column=1, sticky="e")
        
        return row + 1
    
    def _build_data_section(self, row: int) -> int:
        # Frame principal
        frame = ctk.CTkFrame(self.main_container)
        frame.grid(row=row, column=0, sticky="ew", padx=10, pady=5)
        frame.grid_columnconfigure(0, weight=1)
        row_inner = 0
        
        # Título
        ctk.CTkLabel(frame, text="Fonte de Dados", font=("Segoe UI", 16, "bold")).grid(
            row=row_inner, column=0, columnspan=2, sticky="w", padx=10, pady=10)
        row_inner += 1
        
        # Tabs
        tabs = ctk.CTkTabview(frame, height=120)
        tabs.grid(row=row_inner, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        
        # Tab Ficheiro JSON
        json_tab = tabs.add("Ficheiro JSON")
        json_tab.grid_columnconfigure(0, weight=1)

        # Campo de entrada + botão de carregar
        json_input_frame = ctk.CTkFrame(json_tab, fg_color="transparent")
        json_input_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        json_input_frame.grid_columnconfigure(0, weight=1)
        
        self.json_entry = ctk.CTkEntry(json_input_frame, placeholder_text="Caminho do ficheiro JSON...", font=("Segoe UI", 12), height=35)
        self.json_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ctk.CTkButton(json_input_frame, text="Carregar", width=90, height=35, font=("Segoe UI", 12), command=self._select_and_import_json).grid(row=0, column=1)
        
        # Tab Google Sheets
        excel_tab = tabs.add("Google Sheets")
        excel_tab.grid_columnconfigure(0, weight=1)
        self.excel_entry = ctk.CTkEntry(excel_tab, placeholder_text="URL do Google Sheets...", font=("Segoe UI", 12), height=35)
        self.excel_entry.grid(row=0, column=0, sticky="ew", padx=(10, 5), pady=10)
        ctk.CTkButton(excel_tab, text="Carregar", width=90, height=35, font=("Segoe UI", 12), command=self._load_excel).grid(row=0, column=1, padx=5, pady=10)
        
        row_inner += 1
        
        # Info e botões
        info_frame = ctk.CTkFrame(frame, fg_color="transparent")
        info_frame.grid(row=row_inner, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        info_frame.grid_columnconfigure(0, weight=1)
        
        self.contacts_label = ctk.CTkLabel(info_frame, text="Contactos: 0", font=("Segoe UI", 13))
        self.contacts_label.grid(row=0, column=0, sticky="w")
        
        ctk.CTkButton(info_frame, text="Editar", width=90, height=35, font=("Segoe UI", 11), command=self._open_editor).grid(row=0, column=1, padx=(5, 2))
        return row + 1
    
    def _build_message_section(self, row: int) -> int:
        frame = ctk.CTkFrame(self.main_container)
        frame.grid(row=row, column=0, sticky="ew", padx=10, pady=5)
        frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(frame, text="Mensagens", font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 5))
        
        # Boas-vindas
        ctk.CTkLabel(frame, text="Boas-vindas (primeiro envio):", font=("Segoe UI", 12, "bold")).grid(
            row=1, column=0, sticky="w", padx=10, pady=(5, 2))
        self.welcome_text = ctk.CTkTextbox(frame, height=60, font=("Segoe UI", 12))
        self.welcome_text.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        # Principal
        ctk.CTkLabel(frame, text="Mensagem Principal:", font=("Segoe UI", 12, "bold")).grid(
            row=3, column=0, sticky="w", padx=10, pady=(5, 2))
        self.message_text = ctk.CTkTextbox(frame, height=100, font=("Segoe UI", 12))
        self.message_text.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 5))
        self.message_text.insert("1.0", "Olá {nome}!")
        
        ctk.CTkLabel(frame, text="Use {nome} para personalizar", text_color="gray", font=("Segoe UI", 10)).grid(
            row=5, column=0, sticky="w", padx=10, pady=(0, 10))
        
        return row + 1
    
    def _build_options_section(self, row: int) -> int:
        frame = ctk.CTkFrame(self.main_container)
        frame.grid(row=row, column=0, sticky="ew", padx=10, pady=5)
        frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(frame, text="Opções", font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 5))
        
        opts = ctk.CTkFrame(frame, fg_color="transparent")
        opts.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        # Método
        method_frame = ctk.CTkFrame(opts, fg_color="transparent")
        method_frame.grid(row=0, column=0, sticky="w", padx=(0, 30))
        
        self.method_var = ctk.StringVar(value="whatsapp")
        ctk.CTkRadioButton(method_frame, text="WhatsApp", variable=self.method_var, value="whatsapp", font=("Segoe UI", 12)).pack(anchor="w", pady=3)
        ctk.CTkRadioButton(method_frame, text="SMS", variable=self.method_var, value="sms", font=("Segoe UI", 12)).pack(anchor="w", pady=3)
        
        # Delay
        delay_frame = ctk.CTkFrame(opts, fg_color="transparent")
        delay_frame.grid(row=0, column=1, sticky="w", padx=(0, 30))
        
        ctk.CTkLabel(delay_frame, text="Delay (seg):", font=("Segoe UI", 12, "bold")).pack()
        self.delay_slider = ctk.CTkSlider(delay_frame, from_=1, to=10, number_of_steps=9, width=150)
        self.delay_slider.set(3)
        self.delay_slider.pack()
        self.delay_label = ctk.CTkLabel(delay_frame, text="3s", font=("Segoe UI", 11))
        self.delay_label.pack()
        self.delay_slider.configure(command=lambda v: self.delay_label.configure(text=f"{int(v)}s"))
        
        # Seleção de contactos (à direita do delay, reserva espaço para botão e status)
        selection_frame = ctk.CTkFrame(opts, fg_color="transparent")
        selection_frame.grid(row=0, column=2, sticky="nw", padx=(0, 10))

        self.send_all_var = ctk.BooleanVar(value=True)
        self.send_all_toggle = ctk.CTkSwitch(
            selection_frame,
            text="Enviar para Todos",
            variable=self.send_all_var,
            command=self._toggle_send_all_mode,
            font=("Segoe UI", 11)
        )
        self.send_all_toggle.grid(row=0, column=0, sticky="w", pady=(0, 2))

        # Container para botão e status, com altura fixa
        self.selection_btn_container = ctk.CTkFrame(selection_frame, fg_color="transparent", height=54)  # 28+2+24
        self.selection_btn_container.grid(row=1, column=0, sticky="nw")
        self.selection_btn_container.grid_propagate(False)

        self.select_contacts_btn = ctk.CTkButton(
            self.selection_btn_container,
            text="Selecionar Contactos",
            width=120,
            height=28,
            command=self._open_contact_selection,
            font=("Segoe UI", 11)
        )
        self.select_contacts_btn.grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.select_contacts_btn.grid_remove()

        self.selection_status_label = ctk.CTkLabel(
            self.selection_btn_container,
            text="",
            text_color="gray",
            font=("Segoe UI", 10)
        )
        self.selection_status_label.grid(row=1, column=0, sticky="w")
        self.selection_status_label.grid_remove()

        return row + 1
    
    def _build_controls_section(self, row: int) -> int:
        frame = ctk.CTkFrame(self.main_container)
        frame.grid(row=row, column=0, sticky="ew", padx=10, pady=5)
        frame.grid_columnconfigure(0, weight=1)
        
        # Botões
        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.grid(row=0, column=0, sticky="ew", padx=10, pady=15)
        
        ctk.CTkButton(btns, text="Inicializar", width=120, height=40, font=("Segoe UI", 12), command=self._initialize).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="Preview", width=100, height=40, font=("Segoe UI", 12), command=self._show_preview).pack(side="left", padx=5)
        
        self.start_btn = ctk.CTkButton(btns, text="Enviar", width=100, height=40, font=("Segoe UI", 12), fg_color="green", command=self._start_sending)
        self.start_btn.pack(side="left", padx=5)
        
        self.stop_btn = ctk.CTkButton(btns, text="Parar", width=100, height=40, font=("Segoe UI", 12), fg_color="red", state="disabled", command=self._stop_sending)
        self.stop_btn.pack(side="left", padx=5)
        
        # Progress
        self.progress = ctk.CTkProgressBar(frame)
        self.progress.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        self.progress.set(0)
        
        self.status_label = ctk.CTkLabel(frame, text="Pronto", font=("Segoe UI", 12), text_color="gray")
        self.status_label.grid(row=2, column=0, sticky="w", padx=10, pady=(0, 5))
        
        return row + 1
    
    def _build_log_section(self, row: int) -> int:
        frame = ctk.CTkFrame(self.main_container)
        frame.grid(row=row, column=0, sticky="nsew", padx=10, pady=5)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(frame, text="Log", font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 5))
        
        self.log_text = ctk.CTkTextbox(frame, height=120, font=("Segoe UI", 11))
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        return row + 1
        
    def _toggle_send_all_mode(self):
        if self.send_all_var.get():
            self.select_contacts_btn.grid_remove()
            self.selection_status_label.grid_remove()
        else:
            # Quando muda para modo SELEÇÃO, carrega os 'selecionado' do JSON se não há seleção manual
            if not self.selected_contacts:
                self.selected_contacts = [c for c in self.service.get_active_contacts() if c.selecionado]
            
            self.select_contacts_btn.grid()
            self.selection_status_label.grid()
            self._update_selection_status()
    
    def _open_contact_selection(self):
        if not self.service.contacts:
            from tkinter import messagebox
            messagebox.showerror("Erro", "Carregue contactos primeiro")
            return
        
        available_contacts = self.service.get_active_contacts()
        if not available_contacts:
            from tkinter import messagebox
            messagebox.showwarning("Aviso", "Não há contactos disponíveis")
            return
        
        selection_window = ContactSelectionWindow(
            parent=self,
            contacts=available_contacts,
            on_confirm=self._on_contacts_selected,
            title="Selecionar Contactos para Envio"
        )
    def _on_contacts_selected(self, selected_contacts):        
        # MELHORIA: Usar 'telemovel' (original) garante unicidade, mesmo se o número for inválido
        selected_phones = {c.telemovel for c in selected_contacts}
        
        updates = 0
        # Atualiza o atributo 'selecionado' de TODOS os contactos no service
        for contact in self.service.contacts:
            # Verifica se o telemóvel deste contacto está no conjunto dos selecionados
            should_be_selected = contact.telemovel in selected_phones
            
            # Só chama o editar se o valor for realmente diferente (poupa processamento)
            if contact.selecionado != should_be_selected:
                contact.editar('selecionado', should_be_selected)
                updates += 1
                
        # Guarda lista local para uso imediato
        self.selected_contacts = selected_contacts
        
        # Atualiza a UI (Status Label)
        self._update_selection_status()
        
        # Auto-save para persistir alterações no JSON
        self.after(500, self._auto_save_contacts)

    def _update_selection_status(self):
        if not self.send_all_var.get():
            count = len(self.selected_contacts)
            if count == 0:
                self.selection_status_label.configure(
                    text="Nenhum contacto selecionado",
                    text_color="orange"
                )
            else:
                self.selection_status_label.configure(
                    text=f"{count} contacto(s) selecionado(s)",
                    text_color="gray"
                )
    
    def _on_contacts_changed(self, contacts=None):
        if contacts:
            self.service.contacts = contacts
        else:
            self.service.contacts = self.controller.contacts
        
        self._update_contacts_label()
        self.selected_contacts = []
        self._update_selection_status()
        
        self.after(500, self._auto_save_contacts)
        self.after(1000, self._save_config)
    
    def _load_json(self):
        from tkinter import filedialog
        
        filepath = filedialog.askopenfilename(
            title="Selecionar ficheiro de contactos",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filepath:
            self._log("Operação cancelada")
            return
        
        self._log(f"Carregando JSON: {filepath}")
        success, msg, warnings = self.service.load_json(filepath, merge=bool(self.service.contacts))
        
        self._log(msg)
        if warnings:
            for w in warnings[:3]:
                self._log(f"  {w}")
        
        if success:
            self.controller._contacts = self.service.contacts
            self._on_contacts_changed(self.service.contacts)
    
    def _select_and_import_json(self):
        from tkinter import filedialog, messagebox
        from pathlib import Path
        
        filepath = self.json_entry.get().strip()
        
        # Se há caminho na caixa, verifica se é válido
        if filepath:
            if Path(filepath).exists():
                # Caminho válido, importa direto
                self._import_json_file(filepath)
                return
            else:
                # Caminho inválido, pergunta se quer selecionar outro
                result = messagebox.askokcancel(
                    "Caminho Inválido",
                    f"O caminho não é válido:\n{filepath}\n\n"
                    "Deseja continuar com a seleção de um ficheiro?"
                )
                
                if not result:
                    # Utilizador clicou Cancelar, não faz nada
                    self._log("Operação cancelada")
                    return
                
                # Utilizador clicou OK, limpa o campo e abre diálogo
                self.json_entry.delete(0, "end")
        
        # Se chegou aqui, a caixa está vazia ou o utilizador aceitou fazer nova seleção
        # Abre diálogo de seleção
        filepath = filedialog.askopenfilename(
            title="Selecionar ficheiro de contactos para adicionar",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filepath:
            self._log("Operação cancelada")
            return
        
        self._import_json_file(filepath)
    
    def _import_json_file(self, filepath: str):
        from pathlib import Path
        
        if not Path(filepath).exists():
            self._log(f"Ficheiro não encontrado: {filepath}")
            return
        
        # Importa com merge automático
        self._log(f"Importando contactos de: {filepath}")
        success, msg, warnings = self.service.load_json(filepath, merge=True)
        
        self._log(msg)
        if warnings:
            for w in warnings[:3]:
                self._log(f"  {w}")
        
        if success:
            self.controller._contacts = self.service.contacts
            self._on_contacts_changed(self.service.contacts)
            # Limpa o campo após sucesso
            self.json_entry.delete(0, "end")
            self._log(f"{len(self.service.contacts)} contactos carregados")
        else:
            self._log(f"Erro ao importar: {msg}")

    def _load_excel(self):
        url = self.excel_entry.get().strip()
        if not url:
            self._log("Insira uma URL")
            return
        
        try:
            import openpyxl
        except ImportError:
            from tkinter import messagebox
            messagebox.showerror("Erro", "Instale openpyxl:\npip install openpyxl")
            return
        
        self._log(f"Carregando Google Sheets: {url}")
        success, msg, warnings = self.service.load_excel(url, merge=bool(self.service.contacts))
        
        self._log(msg)
        if warnings:
            for w in warnings[:3]:
                self._log(f"  {w}")
        
        if success:
            self.controller._contacts = self.service.contacts
            self._on_contacts_changed(self.service.contacts)
    
    def _open_editor(self):
        try:
            def on_save(contacts):
                self.service.contacts = contacts
                self.controller._contacts = contacts
                self._on_contacts_changed(contacts)
            
            self._editor_window = ContactEditorWindow(self, self.service.contacts, on_save)
        except Exception as e:
            self._log(f"Erro ao abrir editor: {e}")
    
    def _show_preview(self):
        if not self.service.contacts:
            self._log("Carregue contactos primeiro")
            return
        
        try:
            mensagem_geral = self.message_text.get("1.0", "end-1c").strip()
            mensagem_boas_vindas = self.welcome_text.get("1.0", "end-1c").strip()
            
            self._preview_window = PreviewDashboardWindow(
                self, 
                self.service.contacts, 
                mensagem_geral=mensagem_geral,
                mensagem_boas_vindas=mensagem_boas_vindas,
                read_only=True
            )
        except Exception as e:
            self._log(f"Erro ao abrir preview: {e}")
    
    def _initialize(self):
        if not self.service.contacts:
            self._log("Carregue contactos primeiro")
            return

        method = self.method_var.get()
        if method == "whatsapp":
            from controllers.services.whatsapp_sender import WhatsAppSender
            try:
                whatsapp_sender = WhatsAppSender()
                self.sender = whatsapp_sender
                self._log("Inicializando WhatsApp...")
                success, msg = whatsapp_sender.initialize(log_callback=self._log)
                if not success:
                    self._log(f"Erro: {msg}")
                    return

                self._log("Aguardando login (escaneie o QR code se necessário)...")
                # Aguardar login em thread separada para não bloquear UI
                def wait_login_thread():
                    success, msg = whatsapp_sender.wait_for_login(timeout=120, log_callback=self._log)
                    if success:
                        self._log("WhatsApp: Login confirmado")
                    else:
                        self._log(f"Erro no WhatsApp: {msg}")

                login_thread = threading.Thread(target=wait_login_thread, daemon=True)
                login_thread.start()
            except Exception as e:
                self._log(f"Erro: {str(e)}")
        elif method == "sms":
            from controllers.services.sms_sender import SMSSender
            from views.windows.sms_init_window import SMSInitializationWindow

            try:
                sms_sender = SMSSender()
                self.sender = sms_sender
                
                # Abre janela de inicialização SMS
                def on_sms_ready():
                    self._log("SMS: Dispositivo pronto para envio")
                
                self._sms_init_window = SMSInitializationWindow(
                    self, 
                    sms_sender, 
                    on_success=on_sms_ready
                )
            except Exception as e:
                self._log(f"Erro: {str(e)}")

    def _start_sending(self):
        if not self.service.contacts:
            self._log("Carregue contactos primeiro")
            return
        
        if not self.message_text.get("1.0", "end-1c").strip():
            self._log("Escreva uma mensagem")
            return
        
        method = self.method_var.get()
        
        # Verifica se o sender está inicializado
        if method == "whatsapp":
            if not hasattr(self, 'sender') or self.sender is None:
                self._log("Inicialize o WhatsApp primeiro (clique em 'Inicializar')")
                return
            # Verifica se é WhatsAppSender e está logado
            whatsapp_sender: 'WhatsAppSender' = self.sender  # type: ignore
            if not hasattr(whatsapp_sender, 'is_logged_in') or not whatsapp_sender.is_logged_in:
                self._log("Aguarde o login do WhatsApp ou inicialize novamente")
                return
        elif method == "sms":
            if not hasattr(self, 'sender') or self.sender is None:
                self._log("Inicialize o SMS primeiro (clique em 'Inicializar')")
                return
            # Verifica se é SMSSender e está conectado
            sms_sender: 'SMSSender' = self.sender  # type: ignore
            if not hasattr(sms_sender, 'device_connected') or not sms_sender.device_connected:
                self._log("Conecte um dispositivo Android e inicialize")
                return
        
        self.is_sending = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        
        message = self.message_text.get("1.0", "end-1c").strip()
        
        thread = threading.Thread(
            target=self._send_messages_thread,
            args=(method, message),
            daemon=True
        )
        thread.start()
    
    def _send_messages_thread(self, method: str, message: str):
        try:
            # Seleciona contactos baseado no toggle
            if self.send_all_var.get():
                contacts_to_send = self.service.get_sendable_contacts("all")
            else:
                # Se não há seleção manual, usa os marcados como 'selecionado' no JSON
                if not self.selected_contacts:
                    contacts_to_send = [c for c in self.service.get_active_contacts() 
                                       if c.selecionado and c.verificar_enviar_mensagem_geral()]
                else:
                    contacts_to_send = [c for c in self.selected_contacts if c.verificar_enviar_mensagem_geral()]
                            
            total = len(contacts_to_send)
            
            if total == 0:
                mode = "todos os contactos" if self.send_all_var.get() else "contactos selecionados"
                self._log(f"Nenhum contacto elegível em {mode}")
                self._stop_sending()
                return
            
            self._log(f"Enviando para {total} contactos via {method.upper()}...")
            
            if method == "whatsapp":
                self._send_whatsapp_messages(contacts_to_send, message, total)
            elif method == "sms":
                self._send_sms_messages(contacts_to_send, message, total)
        except Exception as e:
            self._log(f"Erro: {str(e)}")
        finally:
            self.is_sending = False
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
    
    def _send_whatsapp_messages(self, contacts, message: str, total: int):
        from controllers.services.whatsapp_sender import WhatsAppSender
        
        if not hasattr(self, 'sender') or self.sender is None:
            self.sender = WhatsAppSender()
            try:
                self.sender.initialize()
            except Exception as e:
                self._log(f"Erro: {str(e)}")
                return
        
        reports = []
        sent = 0
        
        for idx, contact in enumerate(contacts):
            if not self.is_sending:
                self._log("Cancelado")
                break
            
            try:
                result = self.sender.send_message(
                    phone=contact.telemovel,
                    message=message,
                    log_callback=self._log
                )
                
                if result.success:
                    sent += 1
                    contact.ultimo_envio = result.timestamp
                    self._log(f"[{idx+1}/{total}] {contact.nome}: OK")
                    reports.append(SendReport(
                        contact_name=contact.nome,
                        contact_phone=contact.telemovel_normalizado,
                        status="sucesso",
                        message="Enviado",
                        timestamp=result.timestamp
                    ))
                else:
                    reports.append(SendReport(
                        contact_name=contact.nome,
                        contact_phone=contact.telemovel_normalizado,
                        status="erro",
                        message=result.message,
                        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ))
                
                # Atualiza progress bar
                progress = (idx + 1) / total
                self.after(0, lambda p=progress: self.progress.set(p))
            except Exception as e:
                self._log(f"[{idx+1}/{total}] {contact.nome}: Erro - {str(e)}")
                reports.append(SendReport(
                    contact_name=contact.nome,
                    contact_phone=contact.telemovel_normalizado,
                    status="erro",
                    message=str(e),
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
        
        self._log(f"Concluído: {sent}/{total} mensagens enviadas")
        self._auto_save_contacts()
        
        if reports:
            self._generate_and_open_report(reports, "whatsapp")
    
    def _send_sms_messages(self, contacts, message: str, total: int):
        from controllers.services.sms_sender import SMSSender
        
        if not hasattr(self, 'sender') or self.sender is None:
            self.sender = SMSSender()
            self.sender.find_adb()
            success, msg = self.sender.check_device()
            if not success:
                self._log(f"Erro: {msg}")
                return
        
        reports = []
        sent = 0
        
        for idx, contact in enumerate(contacts):
            if not self.is_sending:
                self._log("Cancelado")
                break
            
            try:
                result = self.sender.send_message(
                    phone=contact.telemovel,
                    message=message,
                    log_callback=self._log
                )
                
                if result.success:
                    sent += 1
                    contact.ultimo_envio = result.timestamp
                    self._log(f"[{idx+1}/{total}] {contact.nome}: OK")
                    reports.append(SendReport(
                        contact_name=contact.nome,
                        contact_phone=contact.telemovel_normalizado,
                        status="sucesso",
                        message="Enviada",
                        timestamp=result.timestamp
                    ))
                else:
                    reports.append(SendReport(
                        contact_name=contact.nome,
                        contact_phone=contact.telemovel_normalizado,
                        status="erro",
                        message=result.message,
                        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ))
                
                # Atualiza progress bar
                progress = (idx + 1) / total
                self.after(0, lambda p=progress: self.progress.set(p))
            except Exception as e:
                self._log(f"[{idx+1}/{total}] {contact.nome}: Erro - {str(e)}")
                reports.append(SendReport(
                    contact_name=contact.nome,
                    contact_phone=contact.telemovel_normalizado,
                    status="erro",
                    message=str(e),
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
        
        self._log(f"Concluído: {sent}/{total} mensagens enviadas")
        self._auto_save_contacts()
        
        if reports:
            self._generate_and_open_report(reports, "sms")
    
    def _generate_and_open_report(self, reports: List[SendReport], method: str):
        try:
            reports_dir = Path(__file__).parent.parent.parent / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = reports_dir / f"relatorio_{method}_{timestamp}.html"
            
            if ReportGenerator.generate_html_report(reports, method, report_file):
                self._log(f"Relatório: {report_file.name}")
                
                try:
                    if os.name == 'nt':
                        os.startfile(str(report_file))
                    else:
                        webbrowser.open(f'file://{report_file}')
                except Exception as e:
                    self._log(f"Não foi possível abrir: {e}")
        except Exception as e:
            self._log(f"Erro ao gerar relatório: {e}")
    
    def _stop_sending(self):
        self.is_sending = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self._log("Parado")
        
    def _log(self, msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {msg}\n")
        self.log_text.see("end")
    
    def _update_contacts_label(self):
        stats = self.service.get_stats()
        self.contacts_label.configure(
            text=f"Contactos: {stats['total']}"
        )
    
    def _auto_save_contacts(self):
        try:
            default_file = Path(__file__).parent.parent.parent / "data" / "contactos.json"
            success, msg = self.service.save_json(str(default_file))
            if success:
                self._log("Auto-salvo")
        except Exception as e:
            self._log(f"Auto-save erro: {str(e)}")
    
    def _load_config(self):
        try:
            config_file = Path(__file__).parent.parent.parent / "config" / "user_config.json"
            
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                if "method" in config:
                    self.method_var.set(config["method"])
                if "delay" in config:
                    self.delay_slider.set(config["delay"])
                    self.delay_label.configure(text=f"{config['delay']}s")
                if "message" in config:
                    self.message_text.delete("1.0", "end")
                    self.message_text.insert("1.0", config["message"])
                if "welcome" in config:
                    self.welcome_text.delete("1.0", "end")
                    self.welcome_text.insert("1.0", config["welcome"])
                
                # Carregar URL do Google Sheets se existir
                if "sheets_url" in config and config["sheets_url"]:
                    self.excel_entry.delete(0, "end")
                    self.excel_entry.insert(0, config["sheets_url"])
            
            # Carregar contactos automaticamente
            self._auto_load_contacts()
            
            # Carregar Google Sheets automaticamente se URL está configurada
            self.after(500, self._auto_load_sheets)
        except Exception as e:
            self._log(f"Erro ao carregar config: {e}")
    
    def _auto_load_contacts(self):
        try:
            default_file = Path(__file__).parent.parent.parent / "data" / "contactos.json"
            
            if default_file.exists():
                success, msg, warnings = self.service.load_json(str(default_file), merge=False)
                
                if success:
                    self.controller._contacts = self.service.contacts
                    self._update_contacts_label()
                    self._log(f"Contactos carregados: {len(self.service.contacts)}")
                else:
                    self._log(f"Erro ao carregar contactos: {msg}")
            else:
                # Se não existe, oferece ao utilizador selecionar um ficheiro
                from tkinter import messagebox, filedialog
                
                if messagebox.askyesno(
                    "Ficheiro de Contactos",
                    "Ficheiro de contactos não encontrado.\n\n"
                    "Deseja procurar por um ficheiro JSON existente?"
                ):
                    filepath = filedialog.askopenfilename(
                        title="Selecionar ficheiro de contactos",
                        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
                    )
                    
                    if filepath:
                        success, msg, warnings = self.service.load_json(filepath, merge=False)
                        if success:
                            self.controller._contacts = self.service.contacts
                            self._update_contacts_label()
                            self._log(f"Contactos carregados: {len(self.service.contacts)}")
                        else:
                            self._log(f"Erro ao carregar contactos: {msg}")
                else:
                    self._log("Nenhum contacto carregado")
        except Exception as e:
            self._log(f"Erro ao carregar contactos: {e}")
    
    def _auto_load_sheets(self):
        """Carrega Google Sheets automaticamente se URL está configurada"""
        url = self.excel_entry.get().strip()
        if not url:
            return
        
        self._load_excel()
    
    def _save_config(self):
        try:
            config_file = Path(__file__).parent.parent.parent / "config" / "user_config.json"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            config = {
                "method": self.method_var.get(),
                "delay": int(self.delay_slider.get()),
                "message": self.message_text.get("1.0", "end-1c"),
                "welcome": self.welcome_text.get("1.0", "end-1c"),
                "sheets_url": self.excel_entry.get().strip()  # Salva URL do Google Sheets
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass
    
    def _on_closing(self):
        self._save_config()
        self._auto_save_contacts()
        self.quit()
