from typing import List, Tuple, Optional, Callable
from pathlib import Path
import json
from datetime import datetime
from models.contact import Contact, SendStatus
from utils.time import str_timestamp, str_datetime
from utils.logger import get_logger

SOURCE = "ContactService"

class ContactService:
    def __init__(self):
        self.contacts: List[Contact] = []
        self.data_source = None  # 'json', 'excel', None
        self.logger = get_logger()

    def merge_contacts(self, new: List[Contact]):
        len_contacts = len(self.contacts)

        # Indexar existentes (Chave: Telefone -> Valor: Objeto Contact)
        by_phone = {ex_c.telemovel: ex_c for ex_c in self.contacts}

        for new_c in new:
            if new_c.telemovel not in by_phone:
                self.contacts.append(new_c)
                by_phone[new_c.telemovel] = new_c
            else:
                existing_c = by_phone[new_c.telemovel]
                # Lógica do Ativo (ex: fica ativo se pelo menos um deles for ativo)
                existing_c.ativo = existing_c.ativo or new_c.ativo
                # Atualiza o nome e data do último envio se o novo for mais recente
                if str_timestamp(new_c.ultimo_envio) > str_timestamp(existing_c.ultimo_envio):
                    existing_c.ultimo_envio = new_c.ultimo_envio
                    existing_c.nome = new_c.nome

        self.logger.info(f"Foram adicionados: {len(new) - len_contacts}/{len(new)} contactos novos")

    def save_json(self, path: str) -> bool:
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            data = []
            # Serializa contactos não deletados
            for c in self.contacts :
                data.append(c.to_dict())
               
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.data_source_path = path
            self.logger.info(f"Contactos salvos em {path}")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao guardar em {path}", error=e, source=SOURCE)
            return False
        
    def load_json(self, path: str) -> bool:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            contacts = [Contact.from_dict(d) for d in data]
            self.contacts = contacts
            self.data_source_path = path
            self.data_source = "json"
            self.logger.info(f"Contactos carregados de {path}")
            return True
        except FileNotFoundError as e:
            self.logger.error(f"Ficheiro não encontrado em {path}", error=e, source=SOURCE)
            return False
        except json.JSONDecodeError as e:
            self.logger.error(f"Erro ao decodificar JSON em {path}", error=e, source=SOURCE)
            return False
        except Exception as e:
            self.logger.error("Erro ao carregar contactos", error=e, source=SOURCE)
            return False
        
    def get_active_contacts(self) -> List[Contact]:
        return [c for c in self.contacts if c.ativo]
    
    def get_elegible_for_welcome(self) -> List[Contact]:
        return [c for c in self.get_active_contacts() if c.verificar_enviar_boas_vindas()]

    def get_elegible_for_general(self) -> List[Contact]:
        return [c for c in self.get_active_contacts() if c.verificar_enviar_mensagem_geral()]
    
    def get_sendable_contacts(self, mode: str = "all") -> List[Contact]:
        if mode == "welcome":
            return self.get_elegible_for_welcome()
        return self.get_elegible_for_general()
        
    def get_stats(self) -> dict:
        active = self.get_active_contacts()
        return {
            "total": len(self.contacts),
            "active": len(active),
            "inactive": len(self.contacts) - len(active),
            "not_selected": sum(1 for c in active if not c.selecionado),
            "sent": sum(1 for c in active if c.ultimo_envio),
            "pending": len(self.get_elegible_for_welcome()),
        }
