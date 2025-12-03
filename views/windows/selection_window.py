import customtkinter as ctk
from typing import List, Callable, Optional
from views.base.base_list_window import BaseListWindow
from models.contact import Contact


class ContactSelectionWindow(BaseListWindow):
    def __init__(
        self,
        parent: ctk.CTk,
        contacts: List[Contact],
        on_confirm: Optional[Callable] = None,
        title: str = "Selecionar Contactos"
    ):
        # Guarda temporariamente o callback para usar depois do super()
        self._temp_on_confirm = on_confirm
        self._result: List[Contact] = []
        
        columns = [
            {"title": "", "key": "_select", "weight": 0, "width": 40, "type": "checkbox"},
            {"title": "Nome", "key": "nome", "weight": 1, "min_width": 200},
            {"title": "Telemóvel", "key": "telemovel_normalizado", "weight": 0, "width": 150}
        ]
        
        super().__init__(
            parent,
            title=title,
            size=(800, 700),
            columns=columns,
            data=contacts,
            mode=BaseListWindow.MODE_SELECTION
        )
        
        # Define o callback DEPOIS do super() para não ser sobrescrito!
        self._on_confirm_callback = self._temp_on_confirm
    
    def _build_footer(self):
        self.footer_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.footer_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=10)

        # Botões de seleção (esquerda)
        selection_frame = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        selection_frame.pack(side="left", padx=10)

        ctk.CTkButton(
            selection_frame,
            text="Selecionar Todos",
            width=120,
            command=self.select_all
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            selection_frame,
            text="Desmarcar Todos",
            width=120,
            command=self.deselect_all
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            selection_frame,
            text="Inverter",
            width=80,
            command=self.invert_selection
        ).pack(side="left", padx=3)

        # Contador
        self.count_label = ctk.CTkLabel(
            selection_frame,
            text="0 selecionados",
            text_color="gray"
        )
        self.count_label.pack(side="left", padx=15)

        # Botões de ação (direita)
        action_frame = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        action_frame.pack(side="right", padx=10)

        ctk.CTkButton(
            action_frame,
            text="Cancelar",
            width=80,
            fg_color="gray",
            command=self._cancel
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            action_frame,
            text="Concluir",
            width=100,
            fg_color=self.theme.colors.success,
            command=self._confirm
        ).pack(side="left", padx=5)

    def _on_data_populated(self):
        # Verifica correspondência entre dados e checkboxes
        self._setup_checkbox_bindings()

    def _setup_checkbox_bindings(self):
        def make_callback():
            return lambda *args: self._update_count()
        
        for var in self._checkboxes.values():
            var.trace_add("write", make_callback())
        self._update_count()
    
    def _update_count(self):
        count = sum(1 for var in self._checkboxes.values() if var.get())
        self.count_label.configure(text=f"{count} selecionados" if count != 1 else f"{count} selecionado")
    
    def _cancel(self):
        self._result = []
        self._on_close()
    
    def _confirm(self):
        self._result = self.get_selected_items()
        if self._on_confirm_callback:
            self._on_confirm_callback(self._result)
        
        self._on_close()
    
    def get_result(self) -> List[Contact]:
        return self._result