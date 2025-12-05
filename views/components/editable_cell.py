import customtkinter as ctk
from typing import Any, Callable, Optional, List
from abc import ABC, abstractmethod

# Importa o ThemeManager
try:
    from config.settings import ThemeManager
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from config.settings import ThemeManager

class EditableCell(ABC):
    def __init__(
        self,
        parent: ctk.CTkFrame,
        value: Any,
        on_change: Optional[Callable[[Any, Any], None]] = None,
        **kwargs
    ):
        self.parent = parent
        self._value = value
        self._on_change = on_change
        self._is_editing = False
        self._widget: Optional[ctk.CTkBaseClass] = None
        self._edit_widget: Optional[ctk.CTkBaseClass] = None
        
        # Obtém ThemeManager
        self.theme = ThemeManager()
        
        # Cria widget de exibição
        self._create_display_widget(**kwargs)
    
    @property
    def value(self) -> Any:
        return self._value
    
    @value.setter
    def value(self, new_value: Any):
        old_value = self._value
        self._value = new_value
        self._update_display()
        
        if self._on_change and old_value != new_value:
            self._on_change(old_value, new_value)
    
    @abstractmethod
    def _create_display_widget(self, **kwargs):
        pass # Implementado nas subclasses
    
    @abstractmethod
    def _update_display(self):
        pass # Implementado nas subclasses
    
    def start_edit(self):
        if self._is_editing:
            return
        self._is_editing = True
        self._create_edit_widget()
    
    def cancel_edit(self):
        if not self._is_editing:
            return
        self._is_editing = False
        self._destroy_edit_widget()
    
    def confirm_edit(self):
        if not self._is_editing:
            return
        
        new_value = self._get_edit_value()
        self._is_editing = False
        self._destroy_edit_widget()
        self.value = new_value
    
    @abstractmethod
    def _create_edit_widget(self):
        pass # Implementado nas subclasses
    
    @abstractmethod
    def _get_edit_value(self) -> Any:
        pass
    
    def _destroy_edit_widget(self):
        if self._edit_widget:
            self._edit_widget.destroy()
            self._edit_widget = None
        
        # Mostra widget de exibição
        if self._widget:
            self._widget.pack(fill="x", padx=5)
    
    def destroy(self):
        if self._widget:
            self._widget.destroy()
        if self._edit_widget:
            self._edit_widget.destroy()
    
    def grid(self, **kwargs):
        if self._widget:
            self._widget.grid(**kwargs)
    
    def pack(self, **kwargs):
        if self._widget:
            self._widget.pack(**kwargs)


class EditableTextCell(EditableCell):    
    def _create_display_widget(
        self,
        width: int = 100,
        anchor: str = "w",
        font: Optional[tuple] = None,
        text_color: Optional[str] = None,
        truncate: int = 50,
        **kwargs
    ):
        self._truncate = truncate
        # Usa cor do tema se não foi especificada
        self._text_color = text_color or self.theme.get_text()
        
        self._widget = ctk.CTkLabel(
            self.parent,
            text=self._format_text(self._value),
            width=width,
            anchor=anchor,
            font=font,
            text_color=self._text_color,
            fg_color="transparent"
        )
        
        # Bind para edição
        self._widget.bind("<Double-Button-1>", lambda e: self.start_edit())
        self._widget.configure(cursor="hand2")
    
    def _format_text(self, text: Any) -> str:
        text_str = str(text) if text else ""
        if self._truncate and len(text_str) > self._truncate:
            return text_str[:self._truncate] + "..."
        return text_str
    
    def _update_display(self):
        if self._widget:
            self._widget.configure(text=self._format_text(self._value))
    
    def _create_edit_widget(self):
        # Esconde label
        if self._widget:
            self._widget.pack_forget()
        
        # Cria Entry com cores do tema
        self._edit_widget = ctk.CTkEntry(
            self.parent,
            fg_color=self.theme.get_surface(),
            text_color=self.theme.get_text(),
            border_color=self.theme.get_border()
        )
        self._edit_widget.insert(0, str(self._value) if self._value else "")
        self._edit_widget.pack(fill="x", padx=5)
        self._edit_widget.focus_set()
        self._edit_widget.select_range(0, "end")
        
        # Binds
        self._edit_widget.bind("<Return>", lambda e: self.confirm_edit())
        self._edit_widget.bind("<Escape>", lambda e: self.cancel_edit())
        self._edit_widget.bind("<FocusOut>", lambda e: self.confirm_edit())
    
    def _get_edit_value(self) -> str:
        if self._edit_widget:
            return self._edit_widget.get()  # type: ignore
        return str(self._value)


class EditableToggleCell(EditableCell):    
    def _create_display_widget(
        self,
        on_text: str = "",
        off_text: str = "",
        **kwargs
    ):
        self._var = ctk.BooleanVar(value=bool(self._value))
        
        self._widget = ctk.CTkSwitch(
            self.parent,
            text="",
            variable=self._var,
            width=50,
            command=self._on_toggle
        )
    
    def _on_toggle(self):
        new_value = self._var.get()
        old_value = self._value
        self._value = new_value
        
        if self._on_change and old_value != new_value:
            self._on_change(old_value, new_value)
    
    def _update_display(self):
        if hasattr(self, '_var'):
            self._var.set(bool(self._value))
    
    def _create_edit_widget(self):
        pass # Implementado nas subclasses
    
    def _get_edit_value(self) -> bool:
        return self._var.get()
    
    def start_edit(self):
        pass # Implementado nas subclasses


class EditableComboCell(EditableCell):    
    def __init__(
        self,
        parent: ctk.CTkFrame,
        value: Any,
        options: List[str],
        on_change: Optional[Callable[[Any, Any], None]] = None,
        **kwargs
    ):
        self._options = options
        super().__init__(parent, value, on_change, **kwargs)
    
    def _create_display_widget(
        self,
        width: int = 120,
        **kwargs
    ):
        self._widget = ctk.CTkComboBox(
            self.parent,
            values=self._options,
            width=width,
            command=self._on_select,
            fg_color=self.theme.get_surface(),
            text_color=self.theme.get_text(),
            border_color=self.theme.get_border(),
            button_color=self.theme.get_primary(),
            button_hover_color=self.theme.get_primary(),
            dropdown_fg_color=self.theme.get_surface(),
            dropdown_text_color=self.theme.get_text()
        )
        
        if self._value and self._value in self._options:
            self._widget.set(self._value)
    
    def _on_select(self, choice: str):
        old_value = self._value
        self._value = choice
        
        if self._on_change and old_value != choice:
            self._on_change(old_value, choice)
    
    def _update_display(self):
        if self._widget and self._value:
            self._widget.set(self._value)  # type: ignore
    
    def _create_edit_widget(self):
        pass # Combo não usa modo de edição separado
    
    def _get_edit_value(self) -> str:
        if self._widget:
            return self._widget.get()  # type: ignore
        return str(self._value)
    
    def start_edit(self):
        pass # não usa


class EditableCellFactory:    
    @staticmethod
    def create(
        cell_type: str,
        parent: ctk.CTkFrame,
        value: Any,
        on_change: Optional[Callable] = None,
        **kwargs
    ) -> EditableCell:
        if cell_type == "text":
            return EditableTextCell(parent, value, on_change, **kwargs)
        elif cell_type == "toggle":
            return EditableToggleCell(parent, value, on_change, **kwargs)
        elif cell_type == "combo":
            options = kwargs.pop("options", [])
            return EditableComboCell(parent, value, options, on_change, **kwargs)
        else:
            raise ValueError(f"Tipo de célula desconhecido: {cell_type}")