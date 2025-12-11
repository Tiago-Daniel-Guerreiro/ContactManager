import customtkinter as ctk
from typing import Optional, List
from pathlib import Path
from datetime import datetime
from views.windows.disclaimer_window import DisclaimerWindow
from views.base.base_window import BaseMainWindow
from views.windows.contact_editor_window import ContactEditorWindow
from views.windows.preview_window import PreviewDashboardWindow
from views.windows.selection_window import ContactSelectionWindow
from models.contact import Contact
from config.settings import ThemeManager
from controllers.contact_controller import ContactController
from controllers.services.data_handler import DataHandler
from controllers.services.contact_service import ContactService
from controllers.services.config_service import ConfigService
from controllers.services.message_service import MessageService
from utils.environment import get_base_dir

class MainWindow(BaseMainWindow):    
    def __init__(self):
        self.theme = ThemeManager()
        self.controller = ContactController()
        self.service = ContactService()
        self.data_handler = DataHandler(contact_service=self.service)
        self.controller.set_contact_service(self.service)
        self.config_service = ConfigService.create_default_config(get_base_dir())
        self.message_service = MessageService()
        self.controller.set_message_service(self.message_service)
        self.is_sending = False
        self.selected_contacts: List[Contact] = []
        self.controller.set_callbacks(
            on_contacts_changed=self._on_contacts_changed,
            on_send_progress=self._on_send_progress,
            on_send_complete=self._on_send_complete,
            on_log=self._log
        )
        super().__init__(
            title=self.theme.settings.app_name,
            size=self.theme.settings.main_window_size,
            min_size=self.theme.settings.min_window_size
        )
        self._add_context_menu_to_textboxes()

    def _add_context_menu_to_textboxes(self):
        import tkinter as tk
        def add_menu(widget):
            menu = tk.Menu(widget, tearoff=0)
            menu.add_command(label="Copiar", command=lambda: widget.event_generate('<<Copy>>'))
            menu.add_command(label="Colar", command=lambda: widget.event_generate('<<Paste>>'))
            menu.add_command(label="Cortar", command=lambda: widget.event_generate('<<Cut>>'))
            def show_menu(event):
                menu.tk_popup(event.x_root, event.y_root)
            widget.bind("<Button-3>", show_menu)
        if hasattr(self, 'message_text'):
            add_menu(self.message_text)
        if hasattr(self, 'welcome_text'):
            add_menu(self.welcome_text)

    def _build_ui(self):
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
        
        version_frame = ctk.CTkFrame(frame, fg_color="transparent")
        version_frame.grid(row=0, column=1, sticky="e")
        
        ctk.CTkLabel(
            version_frame,
            text=f"v{self.theme.settings.version}",
            text_color="gray",
            font=("Segoe UI", 11)
        ).pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(
            version_frame,
            text="Aviso Legal",
            width=100,
            height=28,
            font=("Segoe UI", 10),
            text_color=self.theme.get_text(),
            fg_color="transparent",
            border_width=2,
            border_color=self.theme.get_primary(),
            hover_color=self.theme.get_surface(),
            command=self._open_disclaimer_secondary
        ).pack(side="left")
        
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
            # Modo "Enviar para Todos" ATIVO: marca todos os contactos ativos como selecionados
            updates = 0
            for contact in self.service.get_active_contacts():
                if not contact.selecionado:
                    contact.editar('selecionado', True)
                    updates += 1
            
            if updates > 0:
                self._log(f"Modo 'Enviar para Todos': {updates} contacto(s) marcados como selecionados")
                # Auto-save para persistir as alterações
                self.after(500, self._auto_save_contacts)
            
            # Esconde opções de seleção manual
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
        
        _ = ContactSelectionWindow(
            parent=self,
            contacts=available_contacts,
            on_confirm=self._on_contacts_selected,
            title="Selecionar Contactos para Envio"
        )

    def _on_contacts_selected(self, selected_contacts):        
        # Usar 'telemovel' (original) garante unicidade, mesmo se o número for inválido
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
        
        # Se "Enviar para Todos" está ativo, marca todos como selecionados
        if self.send_all_var.get():
            for contact in self.service.get_active_contacts():
                if not contact.selecionado:
                    contact.editar('selecionado', True)
        
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
        success = self.data_handler.load_json(filepath)
        
        if success:
            self._log(f"Contactos carregados: {len(self.service.contacts)}")
            self._on_contacts_changed(self.service.contacts)
        else:
            self._log("Erro ao carregar JSON")
    
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
        success = self.data_handler.load_json(filepath)
        
        if success:
            self._on_contacts_changed(self.service.contacts)
            # Limpa o campo após sucesso
            self.json_entry.delete(0, "end")
            self._log(f"{len(self.service.contacts)} contactos carregados")
        else:
            self._log(f"Erro ao importar: {filepath}")

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
        success, msg, warnings = self.data_handler.load_excel_online(url)
        
        self._log(msg)
        if warnings:
            for w in warnings[:3]:
                self._log(f"  {w}")
        
        if success:
            self._on_contacts_changed(self.service.contacts)
    
    def _open_editor(self):
        try:
            def on_save(contacts):
                self.service.contacts = contacts
                self._on_contacts_changed(contacts)
            
            self._editor_window = ContactEditorWindow(
                self, 
                self.service.contacts, 
                on_save,
                send_all_mode=self.send_all_var.get()  # Passa o modo atual
            )
        except Exception as e:
            self._log(f"Erro ao abrir editor: {e}")
    
    def _show_preview(self):
        if not self.service.contacts:
            from tkinter import messagebox
            messagebox.showerror("Erro", "Carregue contactos primeiro")
            return
        
        try:
            mensagem_geral = self.message_text.get("1.0", "end-1c").strip()
            mensagem_boas_vindas = self.welcome_text.get("1.0", "end-1c").strip()
            
            # Converte \n literal em quebra de linha real para preview
            mensagem_geral = mensagem_geral.replace('\\n', '\n')
            mensagem_boas_vindas = mensagem_boas_vindas.replace('\\n', '\n')
            
            self._preview_window = PreviewDashboardWindow(
                self, 
                self.service.contacts, 
                mensagem_geral=mensagem_geral,
                mensagem_boas_vindas=mensagem_boas_vindas,
                read_only=True,
                send_all_mode=self.send_all_var.get()  # Passa o modo atual
            )
        except Exception as e:
            self._log(f"Erro ao abrir preview: {e}")
    
    def _initialize(self):
        if not self.service.contacts:
            from tkinter import messagebox
            messagebox.showerror("Erro", "Carregue contactos primeiro")
            return

        method = self.method_var.get()
        
        # Usa o controller para inicializar
        if method == "sms":
            # SMS precisa da janela de inicialização
            from controllers.services.sms_sender import SMS_Sender
            from views.windows.sms_init_window import SMSInitializationWindow

            try:
                # Cria sender se não existir
                if not isinstance(self.controller._sender, SMS_Sender):
                    sender = SMS_Sender()
                    self.controller.set_sender(sender)

                def on_sms_ready():
                    self._log("SMS: Dispositivo pronto para envio")
                    
                self._sms_init_window = SMSInitializationWindow(
                    self, 
                    self.controller._sender, 
                    on_success=on_sms_ready
                )
            except Exception as e:
                self._log(f"Erro ao inicializar SMS: {e}")
        else:
            # WhatsApp usa o controller (aguarda login automaticamente)
            self.controller.initialize_sender(method)

    def _start_sending(self):
        # Validações
        if not self.service.contacts:
            from tkinter import messagebox
            messagebox.showerror("Erro", "Carregue contactos primeiro")
            return
        
        message_template = self.message_text.get("1.0", "end-1c").strip()
        welcome_template = self.welcome_text.get("1.0", "end-1c").strip()
        
        method = self.method_var.get()
        delay = int(self.delay_slider.get())
        
        # Determina contactos elegíveis
        send_all_mode = self.send_all_var.get()
        contacts_to_send = self._get_contacts_to_send(send_all_mode)
        
        if not contacts_to_send:
            mode = "todos os contactos" if send_all_mode else "contactos selecionados"
            self._log(f"Nenhum contacto elegível em {mode}")
            return
        
        # Atualiza UI
        self.is_sending = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        
        # Delega tudo para o controller
        self.controller.start_sending(
            method=method,
            contacts=contacts_to_send,
            message_template=message_template,
            welcome_template=welcome_template,
            delay=delay,
            check_stop_response=(method == "whatsapp")
        )
    
    def _get_contacts_to_send(self, send_all_mode: bool) -> List[Contact]:
        if send_all_mode:
            # Modo "Enviar para Todos": ignora seleção
            return [c for c in self.service.get_active_contacts() 
                   if c.ativo and c.is_valid]
        else:
            # Modo "Seleção Manual"
            if not self.selected_contacts:
                # Usa os marcados como 'selecionado' no JSON
                return [c for c in self.service.get_active_contacts() 
                       if c.selecionado and c.verificar_enviar_mensagem_geral()]
            else:
                # Usa a lista de contactos selecionados manualmente
                return [c for c in self.selected_contacts 
                       if c.verificar_enviar_mensagem_geral()]
    
    def _stop_sending(self):
        self.controller.stop_sending()
        self.is_sending = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
    
    def _on_send_progress(self, progress: float, current: int, total: int):
        self.after(0, lambda: self.progress.set(progress))
        self.after(0, lambda: self.status_label.configure(
            text=f"Enviando: {current}/{total}"
        ))
    
    def _on_send_complete(self, sent: int, failed: int, total: int):
        self.is_sending = False
        self.after(0, lambda: self.start_btn.configure(state="normal"))
        self.after(0, lambda: self.stop_btn.configure(state="disabled"))
        self.after(0, lambda: self.status_label.configure(
            text=f"Concluído: {sent} enviados, {failed} falhados"
        ))
        
    def _log(self, msg: str, error=None):
        self.log_text.insert("end", f"{msg}\n")
        self.log_text.see("end")
    
    def _open_disclaimer_secondary(self):        
        try:
            _ = DisclaimerWindow(
                parent=self,
                on_accept=None,
                on_decline=None,
                can_close=True
            )
        except Exception as e:
            self._log(f"Erro ao abrir Aviso Legal: {e}")
    
    def _update_contacts_label(self):
        stats = self.service.get_stats()
        self.contacts_label.configure(
            text=f"Contactos: {stats['total']}"
        )
    
    def _auto_save_contacts(self):
        try:
            default_file = get_base_dir() / "data" / "contactos.json"
            default_file.parent.mkdir(parents=True, exist_ok=True)
            success = self.service.save_json(str(default_file))
            if success:
                self._log("Auto-salvo")
        except Exception as e:
            self._log(f"Auto-save erro: {str(e)}")
    
    def _load_config(self):
        try:
            config = self.config_service.load()
            
            # Aplica configurações na UI
            self.method_var.set(config.get("method", "whatsapp"))
            
            delay = config.get("delay", 3)
            self.delay_slider.set(delay)
            self.delay_label.configure(text=f"{delay}s")
            
            message = config.get("message", "Olá {nome}!")
            self.message_text.delete("1.0", "end")
            self.message_text.insert("1.0", message)
            
            welcome = config.get("welcome", "")
            self.welcome_text.delete("1.0", "end")
            self.welcome_text.insert("1.0", welcome)
            
            sheets_url = config.get("sheets_url", "")
            if sheets_url:
                self.excel_entry.delete(0, "end")
                self.excel_entry.insert(0, sheets_url)
            
            # Carregar contactos e sheets automaticamente
            self._auto_load_contacts()
            self.after(500, self._auto_load_sheets)
            
        except Exception as e:
            self._log(f"Erro ao carregar config: {e}")
    
    def _save_config(self):
        try:
            config = {
                "method": self.method_var.get(),
                "delay": int(self.delay_slider.get()),
                "message": self.message_text.get("1.0", "end-1c"),
                "welcome": self.welcome_text.get("1.0", "end-1c"),
                "sheets_url": self.excel_entry.get().strip()
            }
            
            self.config_service.save(config)
        except Exception as e:
            self._log(f"Erro ao salvar config: {e}")
    
    def _auto_load_contacts(self):
        try:
            default_file = get_base_dir() / "data" / "contactos.json"
            
            if default_file.exists():
                success = self.data_handler.load_json(str(default_file))
                
                if success:
                    self._update_contacts_label()
                    self._log(f"Contactos carregados: {len(self.service.contacts)}")
                else:
                    self._log(f"Erro ao carregar contactos")
            else:
                # Oferece ao utilizador selecionar um ficheiro
                self._log("Nenhum contacto carregado")
        except Exception as e:
            self._log(f"Erro ao carregar contactos: {e}")
    
    def _auto_load_sheets(self):
        url = self.excel_entry.get().strip()
        if url:
            self._load_excel()
    
    def _on_closing(self):
        self._save_config()
        self._auto_save_contacts()
        
        self.quit()