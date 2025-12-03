from dataclasses import dataclass
from typing import Dict, Any
import customtkinter as ctk


@dataclass
class ThemeColors:
    # Contacto
    inactive: str = "#ff4444"      # Vermelho - desativado
    pending: str = "#ffaa00"       # Amarelo - sem envio
    active: str = "#44ff44"        # Verde - ativo
    deselected: str = "#888888"       # Cinza - não selecionado
    
    # UI
    background: str = "#1a1a1a"
    surface: str = "#2d2d2d"
    primary: str = "#3b82f6"
    success: str = "#22c55e"
    warning: str = "#f59e0b"
    error: str = "#ef4444"
    text: str = "#ffffff"
    text_secondary: str = "#9ca3af"
    border: str = "#404040"


@dataclass
class AppSettings:
    app_name: str = "Sistema de Gestão de Contactos"
    version: str = "3.0.1"
    
    # Janela principal
    main_window_size: tuple = (1000, 750)
    min_window_size: tuple = (800, 600)

class ThemeManager:    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.colors = ThemeColors()
        self.settings = AppSettings()
        self._apply_theme()
    
    def _apply_theme(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
    
    def get_contact_color(self, ativo: bool, ultimo_envio: str, not_selected: bool = False) -> str:
        if not_selected:
            return self.colors.deselected
        if not ativo:
            return self.colors.inactive
        if not ultimo_envio or ultimo_envio.strip() == "":
            return self.colors.pending
        return self.colors.active