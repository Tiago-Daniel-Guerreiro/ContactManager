from dataclasses import dataclass
from enum import Enum

class statusType(Enum):
    SUCCESS = "sucesso"
    ERROR = "erro"
    INVALID = "inválido"
    
class messageType(Enum):
    WELCOME = "boas-vindas"
    GENERAL = "geral"
    
@dataclass
class Result:
    contact_name: str
    contact_phone: str
    status: statusType  # 'sucesso', 'erro', 'inválido'
    message: str
    timestamp: str
    message_type: messageType  # 'boas-vindas' ou 'geral'