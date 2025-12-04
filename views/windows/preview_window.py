import customtkinter as ctk
from typing import List, Callable, Optional
from views.base.base_list_window import BaseListWindow
from models.contact import Contact


class PreviewDashboardWindow(BaseListWindow):
    def __init__(
        self,
        parent: ctk.CTk,
        contacts: List[Contact],
        mensagem_geral: str = "",
        mensagem_boas_vindas: str = "",
        on_send_welcome: Optional[Callable] = None,
        on_send_general: Optional[Callable] = None,
        on_send_both: Optional[Callable] = None,
        on_confirm: Optional[Callable] = None,
        read_only: bool = False,
        send_all_mode: bool = False  # Novo parâmetro
    ):
        self._on_send_welcome = on_send_welcome
        self._on_send_general = on_send_general
        self._on_send_both = on_send_both
        self._on_confirm = on_confirm
        self._read_only = read_only
        self._mensagem_geral = mensagem_geral
        self._mensagem_boas_vindas = mensagem_boas_vindas
        self._send_all_mode = send_all_mode  # Guarda o modo
        
        # Define colunas baseado no modo
        columns = [
            {"title": "Nome", "key": "nome", "weight": 1, "min_width": 200},
            {"title": "Telemóvel", "key": "telemovel_normalizado", "weight": 0, "width": 150},
        ]
        
        # Só mostra coluna "Selecionado" se NÃO estiver em modo "Enviar para Todos"
        if not send_all_mode:
            columns.append({"title": "Selecionado", "key": "selecionado", "weight": 0, "type": "icon", "width": 80})

        columns.append({"title": "Ativo", "key": "ativo", "weight": 0, "type": "icon", "width": 60})

        super().__init__(
            parent,
            title="Preview",
            size=(1000, 700),
            columns=columns,
            data=contacts,
            mode=BaseListWindow.MODE_PREVIEW
        )
        
        # Callback de seleção
        self.set_on_select(self._on_contact_selected)
        
        # Seleciona primeiro contacto automaticamente
        self.after(100, self._select_first_contact)
    
    def _build_ui(self):
        # Configurar grid com 3 áreas: header, content, preview+footer
        self.configure_grid_weights(
            self.main_frame,
            rows=[(0, 0), (1, 1), (2, 0), (3, 0)],  # header, content, preview, footer
            cols=[(0, 1)]
        )
        
        # Header e Content (da classe pai)
        self._build_header()
        self._build_content()
        
        # Preview area (fixa)
        self._build_preview_area()
        
        # Footer
        self._build_footer()
        
        # Popula dados
        self._populate_data()
        self._on_data_populated()  # Hook para subclasses
    
    def _build_preview_area(self):
        preview_container = ctk.CTkFrame(self.main_frame)
        preview_container.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        
        # Configurar grid interno
        preview_container.grid_columnconfigure(0, weight=1)
        preview_container.grid_columnconfigure(1, weight=1)
        
        # Título
        ctk.CTkLabel(
            preview_container,
            text="Preview das Mensagens",
            font=("", 14, "bold")
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))
        
        # Boas-vindas
        welcome_frame = ctk.CTkFrame(preview_container)
        welcome_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        ctk.CTkLabel(
            welcome_frame,
            text="Mensagem de Boas-Vindas:",
            font=("", 11, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.welcome_preview = ctk.CTkTextbox(welcome_frame, height=80, state="disabled")
        self.welcome_preview.pack(fill="x", padx=10, pady=(0, 10))
        
        # Geral
        general_frame = ctk.CTkFrame(preview_container)
        general_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        
        ctk.CTkLabel(
            general_frame,
            text="Mensagem Geral:",
            font=("", 11, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.general_preview = ctk.CTkTextbox(general_frame, height=80, state="disabled")
        self.general_preview.pack(fill="x", padx=10, pady=(0, 10))
    
    def _build_footer(self):
        self.footer_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.footer_frame.grid(row=3, column=0, sticky="ew", padx=5, pady=10)
        
        # Legenda
        legend_frame = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        legend_frame.pack(side="left", padx=10)
        
        legends = [
            ("Inativo", self.theme.colors.inactive),
            ("Sem envio previsto", self.theme.colors.deselected),
            ("Vai receber boas-vindas", self.theme.colors.pending),
            ("Ativo", self.theme.colors.active)
        ]
        
        for text, color in legends:
            ctk.CTkLabel(
                legend_frame,
                text=text,
                text_color=color,
                font=("", 10)
            ).pack(side="left", padx=8)
        
        # Botões
        btn_frame = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        btn_frame.pack(side="right", padx=10)
        
        if self._read_only:
            ctk.CTkButton(
                btn_frame,
                text="Concluir",
                width=120,
                command=self.destroy
            ).pack(side="right")
        else:
            ctk.CTkButton(
                btn_frame,
                text="Enviar Boas-Vindas",
                width=140,
                fg_color=self.theme.colors.warning,
                command=self._send_welcome
            ).pack(side="left", padx=5)
            
            ctk.CTkButton(
                btn_frame,
                text="Enviar Geral",
                width=120,
                command=self._send_general
            ).pack(side="left", padx=5)
            
            ctk.CTkButton(
                btn_frame,
                text="Enviar Ambas",
                width=120,
                fg_color=self.theme.colors.success,
                command=self._send_both
            ).pack(side="left", padx=5)
            
            ctk.CTkButton(
                btn_frame,
                text="Cancelar",
                width=80,
                fg_color="gray",
                command=self._on_close
            ).pack(side="left", padx=5)
    
    def _get_row_color(self, item: Contact) -> str:
        # Se estiver no modo "Enviar para Todos", ignora o campo 'selecionado'
        # e trata todos os contactos ativos como se estivessem selecionados
        is_selected = item.selecionado if not self._send_all_mode else True
        
        match (item.ativo, is_selected, item.verificar_enviar_boas_vindas()):
            case (False, _, _):  # Se inativo
                color = self.theme.colors.inactive
            case (True, False, _):  # Ativo mas não selecionado
                color = self.theme.colors.deselected
            case (True, True, True):  # Ativo, selecionado e vai receber boas-vindas
                color = self.theme.colors.pending
            case _:  # Ativo
                color = self.theme.colors.active

        return color
    
    def _select_first_contact(self):
        if self.data and len(self.data) > 0:
            self._on_contact_selected(self.data[0])
    
    def _on_contact_selected(self, contact: Contact):
        # Atualiza preview de boas-vindas - usa mensagem do parâmetro principal
        self.welcome_preview.configure(state="normal")
        self.welcome_preview.delete("1.0", "end")
        welcome_text = self._mensagem_boas_vindas if self._mensagem_boas_vindas else "(Sem mensagem de boas-vindas)"
        # Substitui {nome} pelo nome do contacto
        welcome_text = welcome_text.replace("{nome}", contact.nome)
        self.welcome_preview.insert("1.0", welcome_text)
        self.welcome_preview.configure(state="disabled")
        
        # Atualiza preview geral - usa mensagem do parâmetro principal
        self.general_preview.configure(state="normal")
        self.general_preview.delete("1.0", "end")
        general_text = self._mensagem_geral if self._mensagem_geral else "(Sem mensagem geral)"
        # Substitui {nome} pelo nome do contacto
        general_text = general_text.replace("{nome}", contact.nome)
        self.general_preview.insert("1.0", general_text)
        self.general_preview.configure(state="disabled")
    
    def _send_welcome(self):
        if self._on_send_welcome:
            eligible = [c for c in self.data if c.verificar_enviar_boas_vindas()]
            self._on_send_welcome(eligible)
    
    def _send_general(self):
        if self._on_send_general:
            eligible = [c for c in self.data if c.verificar_enviar_mensagem_geral()]
            self._on_send_general(eligible)
    
    def _send_both(self):
        if self._on_send_both:
            eligible = [c for c in self.data if c.verificar_enviar_mensagem_geral()]
            self._on_send_both(eligible)