import customtkinter as ctk
from typing import List, Dict, Any, Optional, Callable
from .base_window import BaseWindow


class BaseListWindow(BaseWindow):
    # Modos disponíveis
    MODE_EDITOR = "editor"
    MODE_PREVIEW = "preview"
    MODE_SELECTION = "selection"
    
    def __init__(
        self,
        parent: ctk.CTk,
        title: str = "Lista",
        size: tuple = (800, 600),
        columns: Optional[List[Dict[str, Any]]] = None,
        data: Optional[List[Any]] = None,
        mode: str = "preview",
        **kwargs
    ):
        # Configuração de colunas
        self.columns = columns or []
        self.data = data or []
        self.mode = mode
        
        # Estado interno
        self._rows: List[ctk.CTkFrame] = []
        self._selected_row: Optional[int] = None
        self._edit_widgets: Dict[str, ctk.CTkEntry] = {}
        self._checkboxes: Dict[int, ctk.BooleanVar] = {}
        
        # Callbacks
        self._on_select_callback: Optional[Callable] = None
        self._on_edit_callback: Optional[Callable] = None
        self._on_confirm_callback: Optional[Callable] = None
        
        super().__init__(parent, title, size, **kwargs)
    
    def _build_ui(self):
        # Configurar grid do main_frame
        self.configure_grid_weights(
            self.main_frame,
            rows=[(0, 0), (1, 1), (2, 0)],  # header fixo, content expansível, footer fixo
            cols=[(0, 1)]
        )

        self._build_header()
        self._build_content()
        self._build_footer()
        self._populate_data()
        self._on_data_populated()  # Hook para subclasses
    
    def _build_header(self):
        header_frame = ctk.CTkFrame(self.main_frame)
        header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 0))
        
        # Configura colunas do header
        for i, col in enumerate(self.columns):
            weight = col.get("weight", 1)
            min_width = col.get("min_width", 0)
            width = col.get("width", None)
            cell_type = col.get("type", "label")
            
            # Se tem width fixo, usa weight=0 e minsize
            if width is not None:
                header_frame.grid_columnconfigure(i, weight=0, minsize=width)
            else:
                header_frame.grid_columnconfigure(i, weight=weight, minsize=min_width)
            
            label = ctk.CTkLabel(
                header_frame,
                text=col.get("title", f"Col {i}"),
                font=("", 12, "bold"),
            )
            label.grid(row=0, column=i, sticky="ew", padx=5, pady=8)
    
    def _build_content(self):
        # Frame container
        content_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        content_container.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        content_container.grid_rowconfigure(0, weight=1)
        content_container.grid_columnconfigure(0, weight=1)
        
        # ScrollableFrame para o conteúdo
        self.scroll_frame = ctk.CTkScrollableFrame(
            content_container,
            fg_color="transparent"
        )
        self.scroll_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configura colunas do scroll_frame para match com header
        for i, col in enumerate(self.columns):
            weight = col.get("weight", 1)
            min_width = col.get("min_width", 0)
            width = col.get("width", None)
            
            # Se tem width fixo, usa weight=0 e minsize
            if width is not None:
                self.scroll_frame.grid_columnconfigure(i, weight=0, minsize=width)
            else:
                self.scroll_frame.grid_columnconfigure(i, weight=weight, minsize=min_width)
    
    def _build_footer(self):
        self.footer_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.footer_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
    
    def _on_data_populated(self):
        pass
    
    def _populate_data(self):
        # Limpa rows existentes
        for row in self._rows:
            row.destroy()
        self._rows.clear()
        self._edit_widgets.clear()
        self._checkboxes.clear()
        
        # Cria novas rows
        for row_idx, item in enumerate(self.data):
            self._create_row(row_idx, item)
    
    def _create_row(self, row_idx: int, item: Any):
        # Frame da linha com cores do tema
        row_frame = ctk.CTkFrame(
            self.scroll_frame, 
            height=35,
            fg_color=self.theme.get_surface()  # Usa cor do tema
        )
        row_frame.grid(row=row_idx, column=0, columnspan=len(self.columns), 
                       sticky="ew", pady=1)
        row_frame.grid_propagate(False)  # Mantém altura fixa
        
        # Configura colunas
        for i, col in enumerate(self.columns):
            weight = col.get("weight", 1)
            min_width = col.get("min_width", 0)
            width = col.get("width", None)
            
            # Se tem width fixo, usa weight=0 e minsize
            if width is not None:
                row_frame.grid_columnconfigure(i, weight=0, minsize=width)
            else:
                row_frame.grid_columnconfigure(i, weight=weight, minsize=min_width)
        
        # Preenche células
        for col_idx, col in enumerate(self.columns):
            self._create_cell(row_frame, row_idx, col_idx, col, item)
        
        # Bind de seleção
        row_frame.bind("<Button-1>", lambda e, idx=row_idx: self._on_row_click(idx))
        
        self._rows.append(row_frame)
    
    def _create_cell(
        self, 
        parent: ctk.CTkFrame, 
        row_idx: int, 
        col_idx: int, 
        col: Dict, 
        item: Any
    ):
        key = col.get("key", "")
        value = self._get_item_value(item, key)
        cell_type = col.get("type", "label")
        
        if cell_type == "checkbox" and self.mode == self.MODE_SELECTION:
            initial_value = getattr(item, 'selecionado', False) if hasattr(item, 'selecionado') else False
            var = ctk.BooleanVar(value=initial_value)
            self._checkboxes[row_idx] = var
            item_name = getattr(item, 'nome', 'N/A') if hasattr(item, 'nome') else item.get('nome', 'N/A') if isinstance(item, dict) else 'N/A'
            cb = ctk.CTkCheckBox(parent, text="", variable=var, width=30)
            cb.grid(row=0, column=col_idx, sticky="w", padx=5)
        
        elif cell_type == "toggle" and self.mode == self.MODE_EDITOR:
            # Toggle para campo booleano editável
            var = ctk.BooleanVar(value=bool(value))
            switch = ctk.CTkSwitch(
                parent, 
                text="",
                variable=var,
                width=50,
                command=lambda v=var, k=key, i=row_idx: self._on_toggle_change(i, k, v.get())
            )
            switch.grid(row=0, column=col_idx, sticky="w", padx=5)
        
        elif cell_type == "icon":
            # Célula com ícone (X ou ✓) - centralizado
            icon = "✗" if not value else "✓"
            color = self.theme.colors.success if value else self.theme.colors.error
            lbl = ctk.CTkLabel(parent, text=icon, text_color=color, font=("", 14))
            lbl.grid(row=0, column=col_idx, sticky="ew", padx=5)
        
        else:
            # Label normal (potencialmente editável)
            display_value = self._format_value(value, col.get("format"))
            color = col.get("color") or self._get_row_color(item)
            
            lbl = ctk.CTkLabel(
                parent,
                text=str(display_value)[:50],  # Trunca texto longo
                anchor="w",
                text_color=color
            )
            lbl.grid(row=0, column=col_idx, sticky="ew", padx=5)
            
            # Bind para edição inline se modo editor
            if self.mode == self.MODE_EDITOR and col.get("editable", False):
                lbl.bind("<Double-Button-1>", 
                         lambda e, r=row_idx, c=col_idx, k=key: self._start_edit(r, c, k))
                lbl.configure(cursor="hand2")
    
    def _get_item_value(self, item: Any, key: str) -> Any:
        if isinstance(item, dict):
            return item.get(key, "")
        return getattr(item, key, "")
    
    def _format_value(self, value: Any, format_type: Optional[str]) -> str:
        if value is None or value == "" or str(value).strip() == "":
            return ""
        if str(value).upper() == "NAT":
            return ""
        if format_type == "date" and value:
            return str(value)[:10]
        if format_type == "truncate":
            return str(value)[:30] + "..." if len(str(value)) > 30 else str(value)
        return str(value)
    
    def _get_row_color(self, item: Any) -> str:
        # Usa a cor de texto correta para o tema atual
        return self.theme.get_text()
    
    def _on_row_click(self, row_idx: int):
        # Apenas marca a seleção sem mudar a cor visual da linha
        self._selected_row = row_idx
        
        # Callback
        if self._on_select_callback and row_idx < len(self.data):
            self._on_select_callback(self.data[row_idx])
    
    def _start_edit(self, row_idx: int, col_idx: int, key: str):
        if self.mode != self.MODE_EDITOR:
            return
        
        row_frame = self._rows[row_idx]
        
        # Remove label existente
        for widget in row_frame.grid_slaves(row=0, column=col_idx):
            widget.destroy()
        
        # Obtém valor atual
        current_value = self._get_item_value(self.data[row_idx], key)
        
        # Cria Entry
        entry = ctk.CTkEntry(row_frame)
        entry.insert(0, str(current_value))
        entry.grid(row=0, column=col_idx, sticky="ew", padx=5)
        entry.focus_set()
        entry.select_range(0, "end")
        
        # Bind para confirmar/cancelar
        entry.bind("<Return>", lambda e: self._confirm_edit(row_idx, col_idx, key, entry))
        entry.bind("<Escape>", lambda e: self._cancel_edit(row_idx, col_idx, key))
        entry.bind("<FocusOut>", lambda e: self._confirm_edit(row_idx, col_idx, key, entry))
        
        # Guarda referência
        edit_key = f"{row_idx}_{col_idx}"
        self._edit_widgets[edit_key] = entry
    
    def _confirm_edit(self, row_idx: int, col_idx: int, key: str, entry: ctk.CTkEntry):
        new_value = entry.get()
        
        # Atualiza dados
        item = self.data[row_idx]
        if isinstance(item, dict):
            old_value = item.get(key)
            item[key] = new_value
        else:
            old_value = getattr(item, key, None)
            
            # Se está editando telefone, valida antes
            if key == "telemovel":
                from models.contact import Contact
                
                # Valida o número antes de normalizar
                if not Contact.validate_phone(new_value):
                    self._show_validation_error("Número de telefone inválido\nDevem ser 9-12 dígitos")
                    self._recreate_cell(row_idx, col_idx, key)
                    return
            
            # Tenta atualizar usando o método editar (que valida e normaliza)
            if hasattr(item, 'editar'):
                success = item.editar(key, new_value)
                if not success:
                    self._show_validation_error(f"Erro ao atualizar o campo '{key}'")
                    self._recreate_cell(row_idx, col_idx, key)
                    return
            else:
                setattr(item, key, new_value)
        
        # Callback
        if self._on_edit_callback:
            self._on_edit_callback(row_idx, key, old_value, new_value)
        
        # Recria célula (vai mostrar o valor normalizado)
        self._recreate_cell(row_idx, col_idx, key)
    
    def _cancel_edit(self, row_idx: int, col_idx: int, key: str):
        self._recreate_cell(row_idx, col_idx, key)
    
    def _recreate_cell(self, row_idx: int, col_idx: int, key: str):
        row_frame = self._rows[row_idx]
        
        # Remove widgets existentes
        for widget in row_frame.grid_slaves(row=0, column=col_idx):
            widget.destroy()
        
        # Recria célula
        col = self.columns[col_idx]
        self._create_cell(row_frame, row_idx, col_idx, col, self.data[row_idx])
    
    def _show_validation_error(self, message: str):
        from tkinter import messagebox
        
        # Mostra pop-up de erro
        messagebox.showerror("Erro de Validação", message)
    
    def _on_toggle_change(self, row_idx: int, key: str, value: bool):
        item = self.data[row_idx]
        if isinstance(item, dict):
            item[key] = value
        elif hasattr(item, 'editar'):
            item.editar(key, value)
        else:
            setattr(item, key, value)
        
        if self._on_edit_callback:
            self._on_edit_callback(row_idx, key, not value, value)
        
    def set_on_select(self, callback: Callable):
        self._on_select_callback = callback
    
    def set_on_edit(self, callback: Callable):
        self._on_edit_callback = callback
    
    def set_on_confirm(self, callback: Callable):
        self._on_confirm_callback = callback
    
    def get_selected_items(self) -> List[Any]:
        if self.mode != self.MODE_SELECTION:
            return [self.data[self._selected_row]] if self._selected_row is not None else []
        
        # Debug: mostra correspondência
        for idx in sorted(self._checkboxes.keys()):
            data_item = self.data[idx] if idx < len(self.data) else None
            item_name = getattr(data_item, 'nome', 'N/A') if hasattr(data_item, 'nome') else (data_item.get('nome', 'N/A') if isinstance(data_item, dict) else 'OUT_OF_BOUNDS')
            checkbox_value = self._checkboxes[idx].get()
        
        selected = [
            self.data[idx] 
            for idx, var in self._checkboxes.items() 
            if var.get()
        ]
                
        return selected
    
    def select_all(self):
        for var in self._checkboxes.values():
            var.set(True)
    
    def deselect_all(self):
        for var in self._checkboxes.values():
            var.set(False)
    
    def invert_selection(self):
        for var in self._checkboxes.values():
            var.set(not var.get())
    
    def refresh_data(self, new_data: Optional[List[Any]] = None):
        if new_data is not None:
            self.data = new_data
        self._populate_data()