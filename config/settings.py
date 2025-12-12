from dataclasses import dataclass
from typing import Dict, Any, Literal
import customtkinter as ctk

ThemeType = Literal["light", "dark"]

@dataclass
class ThemeColors:    
    # Cores de status dos contactos (iguais em ambos os temas)
    inactive: str = "#ff4444"      # Vermelho - desativado
    pending: str = "#cc6e03"       # Laranja - sem envio
    active: str = "#44ff44"        # Verde - ativo
    deselected: str = "#888888"    # Cinza - não selecionado
    
    # Cores da UI - Tema escuro
    background_dark: str = "#1a1a1a"
    surface_dark: str = "#2d2d2d"
    primary_dark: str = "#3b82f6"
    success_dark: str = "#22c55e"
    warning_dark: str = "#f59e0b"
    error_dark: str = "#ef4444"
    text_dark: str = "#ffffff"
    text_secondary_dark: str = "#9ca3af"
    border_dark: str = "#404040"
    
    # Cores da UI - Tema claro
    background_light: str = "#ffffff"
    surface_light: str = "#f5f5f5"
    primary_light: str = "#668fe7"
    success_light: str = "#16a34a"
    warning_light: str = "#9f5200"
    error_light: str = "#dc2626"
    text_light: str = "#1a1a1a"
    text_secondary_light: str = "#6b7280"
    border_light: str = "#e5e5e5"
    
    # Propriedades de compatibilidade com código antigo (usa tema escuro por padrão)
    @property
    def background(self) -> str:
        return self.background_dark
    
    @property
    def surface(self) -> str:
        return self.surface_dark
    
    @property
    def primary(self) -> str:
        return self.primary_dark
    
    @property
    def success(self) -> str:
        return self.success_dark
    
    @property
    def warning(self) -> str:
        return self.warning_dark
    
    @property
    def error(self) -> str:
        return self.error_dark
    
    @property
    def text(self) -> str:
        return self.text_dark
    
    @property
    def text_secondary(self) -> str:
        return self.text_secondary_dark
    
    @property
    def border(self) -> str:
        return self.border_dark
    
    def get_background(self, theme: ThemeType) -> str:
        return self.background_dark if theme == "dark" else self.background_light
    
    def get_surface(self, theme: ThemeType) -> str:
        return self.surface_dark if theme == "dark" else self.surface_light
    
    def get_primary(self, theme: ThemeType) -> str:
        return self.primary_dark if theme == "dark" else self.primary_light
    
    def get_success(self, theme: ThemeType) -> str:
        return self.success_dark if theme == "dark" else self.success_light
    
    def get_warning(self, theme: ThemeType) -> str:
        return self.warning_dark if theme == "dark" else self.warning_light
    
    def get_error(self, theme: ThemeType) -> str:
        return self.error_dark if theme == "dark" else self.error_light
    
    def get_text(self, theme: ThemeType) -> str:
        return self.text_dark if theme == "dark" else self.text_light
    
    def get_text_secondary(self, theme: ThemeType) -> str:
        return self.text_secondary_dark if theme == "dark" else self.text_secondary_light
    
    def get_border(self, theme: ThemeType) -> str:
        return self.border_dark if theme == "dark" else self.border_light


@dataclass
class AppSettings:
    app_name: str = "Sistema de Gestão de Contactos"
    version: str = "8.1.4"
    
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
        
        # Detecta tema do sistema
        from utils.theme.theme_detector import get_windows_theme
        self._current_theme: ThemeType = get_windows_theme()
        
        # Aplica tema
        self._apply_theme()
    
    def _apply_theme(self):
        ctk.set_appearance_mode(self._current_theme)
        ctk.set_default_color_theme("blue")
    
    @property
    def current_theme(self) -> ThemeType:
        return self._current_theme
    
    def set_theme(self, theme: ThemeType):
        self._current_theme = theme
        self._apply_theme()
    
    def toggle_theme(self):
        self._current_theme = "light" if self._current_theme == "dark" else "dark"
        self._apply_theme()
    
    # Métodos auxiliares para acessar cores do tema atual
    def get_background(self) -> str:
        return self.colors.get_background(self._current_theme)
    
    def get_surface(self) -> str:
        return self.colors.get_surface(self._current_theme)
    
    def get_primary(self) -> str:
        return self.colors.get_primary(self._current_theme)
    
    def get_success(self) -> str:
        return self.colors.get_success(self._current_theme)
    
    def get_warning(self) -> str:
        return self.colors.get_warning(self._current_theme)
    
    def get_error(self) -> str:
        return self.colors.get_error(self._current_theme)
    
    def get_text(self) -> str:
        return self.colors.get_text(self._current_theme)
    
    def get_text_secondary(self) -> str:
        return self.colors.get_text_secondary(self._current_theme)
    
    def get_border(self) -> str:
        return self.colors.get_border(self._current_theme)
    
    def get_contact_color(self, ativo: bool, ultimo_envio: str, not_selected: bool = False) -> str:
        if not_selected:
            return self.colors.deselected
        if not ativo:
            return self.colors.inactive
        if not ultimo_envio or ultimo_envio.strip() == "":
            return self.colors.pending
        return self.colors.active