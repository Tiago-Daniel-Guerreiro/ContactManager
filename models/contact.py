from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum, auto
import re

class SendStatus(Enum):
    PENDING = auto()
    SENT = auto()
    FAILED = auto()
    DESELECTED = auto()
    SKIPPED = auto()

@dataclass
class Contact:
    nome: str
    telemovel: str
    telemovel_normalizado: str = ""
    ultimo_envio: str = ""
    ativo: bool = True
    selecionado: bool = True
    is_valid: bool = True
    _deleted: bool = field(default=False, init=False, repr=False)
    
    def __post_init__(self):
        if not self.telemovel_normalizado:
            self.telemovel_normalizado = self._normalize_phone(self.telemovel)
            self.is_valid = self._validate_phone(self.telemovel_normalizado)
    
    @staticmethod
    def _normalize_phone(phone: str) -> str:
        if not phone:
            return ""
        
        # Remove tudo exceto dígitos
        digits = re.sub(r'\D', '', str(phone))
        
        # Remove prefixo +351 se presente
        if digits.startswith('351') and len(digits) > 9:
            digits = digits[3:]
        
        # Valida se tem pelo menos 9 dígitos
        if len(digits) < 9:
            return ""
        
        # Pega os últimos 9 dígitos (caso tenha mais)
        digits = digits[-9:]
        
        # Formata como 'XXX XXX XXX'
        return f"{digits[0:3]} {digits[3:6]} {digits[6:9]}"
    
    @staticmethod
    def _validate_phone(phone: str) -> bool:
        if not phone:
            return False
        
        # Conta apenas dígitos
        digits = re.sub(r'\D', '', str(phone))
        return len(digits) >= 9
    
    def verificar_enviar_boas_vindas(self, ignore_selection: bool = False) -> bool:
        selection_check = True if ignore_selection else self.selecionado
        return (
            self.ativo and 
            selection_check and 
            self.is_valid and
            (not self.ultimo_envio or self.ultimo_envio.strip() == "")
        )
    
    def verificar_enviar_mensagem_geral(self, ignore_selection: bool = False) -> bool:
        selection_check = True if ignore_selection else self.selecionado
        return (
            self.ativo and 
            selection_check and 
            self.is_valid
        )
    
    def pode_receber_mensagem(self) -> tuple[bool, str]:
        if not self.is_valid:
            return False, "Número inválido"
        if not self.ativo:
            return False, "Contacto inativo"
        if not self.selecionado:
            return False, "Contacto não selecionado"
        return True, "OK"
    
    def enviar_mensagem(self, tipo: str = "geral") -> dict:
        pode, motivo = self.pode_receber_mensagem()
        
        if not pode:
            return {
                "success": False,
                "reason": motivo,
                "contact": self
            }
        
        if tipo == "boas_vindas" and not self.verificar_enviar_boas_vindas():
            return {
                "success": False,
                "reason": "Já recebeu boas-vindas",
                "contact": self
            }
        
        return {
            "success": True,
            "telefone": self.telemovel_normalizado,
            "nome": self.nome,
            "tipo": tipo,
            "contact": self
        }
    
    def editar(self, chave: str, valor) -> bool:
        if self._deleted:
            return False
        
        if not hasattr(self, chave) or chave.startswith('_'):
            return False
        
        # Validações especiais
        if chave == "telemovel":
            setattr(self, chave, valor)
            self.telemovel_normalizado = self._normalize_phone(valor)
            self.is_valid = self._validate_phone(self.telemovel_normalizado)
        elif chave in ("ativo", "selecionado"):
            setattr(self, chave, bool(valor))
        else:
            setattr(self, chave, valor)
        
        return True
    
    def eliminar(self) -> bool:
        self._deleted = True
        self.ativo = False
        return True
    
    def registar_envio(self, status: SendStatus):
        if status == SendStatus.SENT:
            # Formato: YYYY-MM-DD - HH:MM:SS.ffffff
            self.ultimo_envio = datetime.now().strftime("%Y-%m-%d - %H:%M:%S.%f")
        elif status == SendStatus.SKIPPED:
            self.selecionado = False
    
    def get_ultimo_envio_display(self) -> str:
        if not self.ultimo_envio or self.ultimo_envio.strip() in ("", "NaT", "None"):
            return ""
        return self.ultimo_envio
    
    def to_dict(self) -> dict:
        return {
            "nome": self.nome,
            "telemovel": self.telemovel,
            "telemovel_normalizado": self.telemovel_normalizado,
            "ultimo_envio": self.ultimo_envio,
            "ativo": self.ativo,
            "selecionado": self.selecionado,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Contact':
        return cls(
            nome=data.get("nome", ""),
            telemovel=data.get("telemovel", data.get("contacto_original", "")),
            telemovel_normalizado=data.get("telemovel_normalizado", data.get("contacto_normalizado", "")),
            ultimo_envio=data.get("ultimo_envio", ""),
            ativo=data.get("ativo", True),
            selecionado=data.get("selecionado", True),
        )