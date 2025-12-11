import customtkinter as ctk
from typing import Optional, Callable, Union
from views.base.base_window import BaseWindow
from models.contact import Contact


class AddContactWindow(BaseWindow):
    def __init__(
        self,
        parent: Union[ctk.CTk, ctk.CTkToplevel],
        on_save: Optional[Callable[[Contact], None]] = None
    ):
        self.on_save = on_save
        self.result: Optional[Contact] = None
        
        super().__init__(
            parent,
            title="Adicionar Contacto",
            size=(500, 350),
            resizable=(False, False),
            modal=True,
            center=True
        )
    
    def _build_ui(self):
        # Frame principal
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        frame.grid_columnconfigure(0, weight=1)

        # Título
        title_label = ctk.CTkLabel(
            frame, 
            text="Novo Contacto", 
            font=("", 18, "bold")
        )
        title_label.pack(pady=(0, 15))

        # Campo Nome
        ctk.CTkLabel(frame, text="Nome:", font=("", 12, "bold")).pack(anchor="w", pady=(0, 2))
        self.nome_entry = ctk.CTkEntry(
            frame, 
            placeholder_text="Ex: João Silva", 
            height=35, 
            font=("", 12)
        )
        self.nome_entry.pack(fill="x", pady=(0, 10))
        self.nome_entry.focus()

        # Campo Telemóvel
        ctk.CTkLabel(frame, text="Telemóvel:", font=("", 12, "bold")).pack(anchor="w", pady=(0, 2))
        self.telemovel_entry = ctk.CTkEntry(
            frame, 
            placeholder_text="Ex: +351 91 234 5678", 
            height=35, 
            font=("", 12)
        )
        self.telemovel_entry.pack(fill="x", pady=(0, 15))

        # Frame para botões
        button_frame = ctk.CTkFrame(frame, fg_color="transparent")
        button_frame.pack(fill="x")
        button_frame.grid_columnconfigure(1, weight=1)

        # Botão Cancelar
        ctk.CTkButton(
            button_frame,
            text="Cancelar",
            width=100,
            command=self._on_cancel
        ).grid(row=0, column=0, padx=5)

        # Botão Guardar
        ctk.CTkButton(
            button_frame,
            text="Guardar",
            width=100,
            fg_color=self.theme.colors.success,
            command=self._on_save
        ).grid(row=0, column=2, padx=5)

        # Bind para Enter guardar
        self.bind("<Return>", lambda e: self._on_save())

    def _on_save(self):
        nome = self.nome_entry.get().strip()
        telemovel = self.telemovel_entry.get().strip()

        if not nome:
            return

        # Cria contacto
        self.result = Contact(nome=nome, telemovel=telemovel)

        # Callback
        if self.on_save:
            self.on_save(self.result)

        self._on_close()

    def _on_cancel(self):
        self.result = None
        self._on_close()

    def _on_close(self):
        self.grab_release()
        self.destroy()
