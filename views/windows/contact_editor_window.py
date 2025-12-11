import customtkinter as ctk
from typing import List, Callable, Optional
from views.base.base_list_window import BaseListWindow
from views.windows.add_contact_window import AddContactWindow
from models.contact import Contact
from tkinter import messagebox

class ContactEditorWindow(BaseListWindow):
    def __init__(
        self,
        parent: ctk.CTk,
        contacts: List[Contact],
        on_save: Optional[Callable] = None,
        send_all_mode: bool = False  # Novo parâmetro
    ):
        self._on_save = on_save
        self._modified = False
        self._editing_row = False  # Flag para controlar edição de linha
        self._send_all_mode = send_all_mode  # Guarda o modo
        
        columns = [
            {"title": "Nome", "key": "nome", "weight": 1, "editable": True, "min_width": 200},
            {"title": "Telemóvel", "key": "telemovel", "weight": 0, "editable": True, "width": 150},
            {"title": "Último Envio", "key": "ultimo_envio", "weight": 0, "format": "date", "width": 120},
            {"title": "Ativo", "key": "ativo", "weight": 0, "type": "toggle", "width": 60}
        ]
        
        super().__init__(
            parent,
            title="Editor de Contactos",
            size=(900, 600),
            columns=columns,
            data=contacts,
            mode=BaseListWindow.MODE_EDITOR
        )
        
        # Callback de edição
        self.set_on_edit(self._on_contact_edited)
    
    def _build_footer(self):
        super()._build_footer()
        
        stats_frame = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        stats_frame.pack(side="left", padx=10)
        
        self.stats_label = ctk.CTkLabel(
            stats_frame,
            text=self._get_stats_text(),
            font=("", 11),
            text_color="gray"
        )
        self.stats_label.pack()
        
        btn_frame = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        btn_frame.pack(side="right", padx=10)
        
        ctk.CTkButton(
            btn_frame,
            text="+ Adicionar",
            width=100,
            command=self._add_contact
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="Eliminar",
            width=100,
            fg_color=self.theme.colors.error,
            command=self._delete_selected
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="Guardar",
            width=100,
            fg_color=self.theme.colors.success,
            command=self._save
        ).pack(side="left", padx=5)
        
    def _get_stats_text(self) -> str:
        total = len(self.data)
        active = sum(1 for c in self.data if c.ativo)
        return f"Total: {total} | Ativos: {active}"
    
    def _get_row_color(self, item: Contact) -> str:
        # Se estiver no modo "Enviar para Todos", ignora o campo 'selecionado'
        # e trata todos os contactos ativos como se estivessem selecionados
        is_deselected = (not item.selecionado) if not self._send_all_mode else False
        
        return self.theme.get_contact_color(
            item.ativo, 
            item.ultimo_envio, 
            is_deselected
        )
    
    def _on_contact_edited(self, row_idx: int, key: str, old_val, new_val):
        self._modified = True
        self._update_stats()
        
        if key in ("ativo", "selecionado"):
            self._update_row_colors(row_idx)
    
    def _update_stats(self):
        self.stats_label.configure(text=self._get_stats_text())
    
    def _update_row_colors(self, row_idx: int):
        # Força recriação de células de texto
        for col_idx, col in enumerate(self.columns):
            if col.get("type") not in ("toggle", "checkbox"):
                self._recreate_cell(row_idx, col_idx, col.get("key", "")) # Atualiza cor da célula
                
    def _add_contact(self):
        def on_save(contact: Contact):
            # Valida o número antes de adicionar
            if not Contact.validate_phone(contact.telemovel):
                return

            # Marca como ativo e adiciona à lista
            contact.ativo = True
            self.data.append(contact)
            self._modified = True
            self.refresh_data()
            self._update_stats()
            self.after(100, lambda: self._on_row_click(len(self.data) - 1))

        # Cria e mostra janela
        AddContactWindow(self, on_save=on_save)

    def _delete_selected(self):
        # Filtra contactos ativos (não eliminados)
        active_contacts = [c for c in self.data if c.ativo]
        
        if not active_contacts:
            messagebox.showinfo("Sem Contactos", "Não há contactos para eliminar.")
            return
        
        # Cria janela de diálogo
        dialog = ctk.CTkToplevel(self)
        dialog.title("Eliminar Contacto")
        dialog.geometry("500x450")
        dialog.transient(self)
        dialog.grab_set()
        
        # Centraliza sobre a janela pai
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 500) // 2
        y = self.winfo_y() + (self.winfo_height() - 450) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Frame principal
        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Título
        ctk.CTkLabel(
            frame, 
            text="Selecione o contacto a eliminar:", 
            font=("", 14, "bold")
        ).pack(pady=(0, 10))
        
        # Frame com scroll para lista
        list_frame = ctk.CTkScrollableFrame(frame, height=300)
        list_frame.pack(fill="both", expand=True, pady=(0, 15))
                
        # Cria botões radio para cada contacto
        radio_var = ctk.StringVar(value="")
        
        for idx, contact in enumerate(active_contacts):
            # Frame para cada item
            item_frame = ctk.CTkFrame(list_frame, fg_color="transparent")
            item_frame.pack(fill="x", pady=2)
            
            # Radio button com info do contacto
            radio_text = f"{contact.nome} - {contact.telemovel}"
            if not contact.ativo:
                radio_text += " (Inativo)"
            
            radio = ctk.CTkRadioButton(
                item_frame,
                text=radio_text,
                variable=radio_var,
                value=str(idx),
                font=("", 11)
            )
            radio.pack(anchor="w", padx=5, pady=5)
        
        def on_delete():
            if not radio_var.get():
                messagebox.showwarning("Aviso", "Selecione um contacto para eliminar.")
                return
            
            idx = int(radio_var.get())
            contact = active_contacts[idx]
            
            # Confirmação
            if messagebox.askyesno(
                "Confirmar Eliminação",
                f"Tem certeza que deseja eliminar:\n\n"
                f"Nome: {contact.nome}\n"
                f"Telemóvel: {contact.telemovel}\n\n"
                f"Esta ação não pode ser desfeita."
            ):
                # Remove contacto da lista
                self.data.remove(contact)
                self._modified = True
                dialog.destroy()
                # Atualiza interface APÓS fechar dialog
                self.refresh_data()
                self._update_stats()
                self._selected_row = None
        
        def on_cancel():
            dialog.destroy()
        
        # Botões
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 0))
        
        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            width=100,
            fg_color="gray",
            command=on_cancel
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="Eliminar",
            width=120,
            fg_color=self.theme.colors.error,
            command=on_delete
        ).pack(side="right", padx=5)
        
        # Bind Escape para cancelar
        dialog.bind("<Escape>", lambda e: on_cancel())
    
    def _save(self):
        if self._on_save:
            self._on_save(self.data)
        self._modified = False
        # Fechar janela após guardar
        self._force_close()
    
    def _force_close(self):
        super()._on_close()
    
    def _can_close(self) -> bool:
        # Não pode fechar se está editando uma linha
        if self._selected_row is not None:
            return False
        return True
    
    def _on_close(self):
        # Verifica se pode fechar
        if not self._can_close():
            return
            
        if self._modified:
            if messagebox.askyesno(
                "Alterações não guardadas",
                "Tem alterações não guardadas. Deseja guardar antes de fechar?"
            ):
                self._save()
                return
        super()._on_close()
    
    def refresh_data(self, new_data: Optional[List[Contact]] = None):
        if new_data is not None:
            self.data = new_data
        
        # Exibe todos os contactos (os inativos ficam marcados como não selecionáveis)
        display_data = self.data
        
        # Limpa rows e repopula com dados
        for row in self._rows:
            row.destroy()
        self._rows.clear()
        self._edit_widgets.clear()
        self._checkboxes.clear()
        
        # Cria novas rows
        for row_idx, item in enumerate(display_data):
            self._create_row(row_idx, item)
        
        # Atualiza estatísticas
        self._update_stats()