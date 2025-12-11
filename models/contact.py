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
    ultimo_envio: str = ""
    ativo: bool = True
    selecionado: bool = True

    def __init__(self, nome: str, telemovel: str, ultimo_envio: str = "", ativo: bool = True, selecionado: bool = True):
        # Atribui valores primeiro
        self.nome = nome
        self.telemovel = self.normalize_phone(telemovel)
        self.ultimo_envio = ultimo_envio
        self.ativo = ativo
        self.selecionado = selecionado
        
        # Define se é válido baseado na validação do telefone
        self.is_valid = self.validate_phone(self.telemovel)

    @staticmethod
    def normalize_phone(phone: str, prefix: str = "+351") -> str:
        if not phone:
            return ""
        
        # Remove tudo exceto dígitos
        digits = re.sub(r'\D', '', str(phone))

        if len(digits) < 9:
            return ""
        
        remaining_prefix_digits = digits[:-9]  # Dígitos antes dos últimos 9 (prefixo)
        valid_9_digits = digits[-9:]  # Últimos 9 dígitos (número)
        
        # Determina qual prefixo usar
        if remaining_prefix_digits:  # Se há prefixo nos dígitos
            # Usa o prefixo que veio no input (ex: +22 para Moçambique)
            used_prefix = f"+{remaining_prefix_digits}"
        else:
            # Sem prefixo, usa o padrão (+351 para Portugal)
            used_prefix = prefix
        
        # Formata como '+prefixo XXX XXX XXX'
        return f"{used_prefix} {valid_9_digits[0:3]} {valid_9_digits[3:6]} {valid_9_digits[6:9]}"

    @staticmethod
    def validate_phone(phone: str) -> bool:
        if not phone:
            return False

        # Conta apenas dígitos
        digits = re.sub(r'\D', '', str(phone))

        # Deve ter no mínimo 9 e no máximo 12 dígitos (9 + 3 para prefixo)
        return 9 <= len(digits) <= 12
    
    def verificar_enviar_boas_vindas(self, ignore_selection: bool = False) -> bool:
        selection_check = True if ignore_selection else self.selecionado
        return (
            self.ativo and 
            selection_check and 
            (not self.ultimo_envio or self.ultimo_envio.strip() == "")
        )
    
    def verificar_enviar_mensagem_geral(self, ignore_selection: bool = False) -> bool:
        selection_check = True if ignore_selection else self.selecionado

        return (
            self.ativo and 
            selection_check
        )
    
    def pode_receber_mensagem(self) -> tuple[bool, str]:
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
            "telefone": self.telemovel,
            "nome": self.nome,
            "tipo": tipo,
            "contact": self
        }
    
    def editar(self, chave: str, valor) -> bool:
        if not hasattr(self, chave) or chave.startswith('_'):
            return False
        # Validações especiais
        if chave == "telemovel":
            # Normaliza o telefone
            normalized = self.normalize_phone(valor)
            if not normalized:
                return False
            setattr(self, chave, normalized)
            self.is_valid = self.validate_phone(self.telemovel)
        elif chave in ("ativo", "selecionado"):
            setattr(self, chave, bool(valor))
        else:
            setattr(self, chave, valor)
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
            "ultimo_envio": self.ultimo_envio,
            "ativo": self.ativo,
            "selecionado": self.selecionado,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Contact':
        telemovel = data.get("telemovel", "")
        return cls(
            nome=data.get("nome", ""),
            telemovel=telemovel,
            ultimo_envio=data.get("ultimo_envio", ""),
            ativo=data.get("ativo", True),
            selecionado=data.get("selecionado", True),
        )