from typing import List, Tuple, Optional, Callable
from pathlib import Path
import json
from datetime import datetime

from models.contact import Contact, SendStatus
from controllers.services.data_handler import DataHandler

class ContactService:
    def __init__(self, data_handler: DataHandler):
        self.data_handler = data_handler
        self.contacts: List[Contact] = []
        self.data_source = None  # 'json', 'excel', None
        self.data_source_path = None
    
    def load_json(self, path: str, merge: bool = False) -> Tuple[bool, str, List[str]]:
        success, msg, warnings = self.data_handler.load_json(path)
        
        if not success:
            return False, msg, warnings
        
        # Converte para Contact objects
        new_contacts = self._convert_to_contacts(self.data_handler.contacts)
        
        if merge and self.contacts:
            self.contacts = self._merge_contacts(self.contacts, new_contacts)
        else:
            self.contacts = new_contacts
        
        self.data_source = 'json'
        self.data_source_path = path
        
        return True, msg, warnings
    
    def load_excel(self, url: str, merge: bool = False) -> Tuple[bool, str, List[str]]:
        success, msg, warnings = self.data_handler.load_excel_online(url)
        
        if not success:
            return False, msg, warnings
        
        # Converte para Contact objects
        new_contacts = self._convert_to_contacts(self.data_handler.contacts)
        
        if merge and self.contacts:
            self.contacts = self._merge_contacts(self.contacts, new_contacts)
        else:
            self.contacts = new_contacts
        
        self.data_source = 'excel'
        self.data_source_path = url
        
        return True, msg, warnings
        
    def _convert_to_contacts(self, contact_datas) -> List[Contact]:
        contacts = []
        for cd in contact_datas:
            try:
                contact = Contact(
                    nome=cd.nome,
                    telemovel=cd.contacto_original,
                    ultimo_envio=cd.ultimo_envio,
                    ativo=cd.ativo,
                    selecionado=getattr(cd, 'selecionado', True),
                )
                contacts.append(contact)
            except Exception as e:
                print(f"Erro ao converter contacto: {e}")
                continue
        
        return contacts
        
    def _merge_contacts(
        self, 
        existing: List[Contact], 
        new: List[Contact],
        on_duplicate: Optional[Callable[[Contact, Contact], Contact]] = None
    ) -> List[Contact]:
        # Index dos existentes por telefone normalizado
        by_phone = {c.telemovel_normalizado: c for c in existing if c.telemovel_normalizado}
        
        result = list(existing)
        
        for new_contact in new:
            if not new_contact.telemovel_normalizado:
                continue
            
            phone = new_contact.telemovel_normalizado
            
            if phone in by_phone:
                # Duplicata - usa callback ou ignora
                if on_duplicate:
                    merged = on_duplicate(by_phone[phone], new_contact)
                    idx = result.index(by_phone[phone])
                    result[idx] = merged
            else:
                # Novo contacto
                result.append(new_contact)
                by_phone[phone] = new_contact
        
        return result
        
    def save_json(self, path: str) -> Tuple[bool, str]:
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            
            # Serializa contactos não deletados
            data = [
                c.to_dict() for c in self.contacts 
                if not hasattr(c, '_deleted') or not c._deleted
            ]
                        
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.data_source_path = path
            return True, f"Contactos salvos em {path}"
        except Exception as e:
            return False, f"Erro ao guardar: {str(e)}"
        
    def get_active_contacts(self) -> List[Contact]:
        return [
            c for c in self.contacts 
            if not (hasattr(c, '_deleted') and c._deleted)
        ]
    
    def get_elegible_for_welcome(self) -> List[Contact]:
        return [
            c for c in self.get_active_contacts()
            if c.verificar_enviar_boas_vindas()
        ]
    
    def get_elegible_for_general(self) -> List[Contact]:
        return [
            c for c in self.get_active_contacts()
            if c.verificar_enviar_mensagem_geral()
        ]
    
    def get_sendable_contacts(self, mode: str = "all") -> List[Contact]:
        if mode == "welcome":
            return self.get_elegible_for_welcome()
        return self.get_elegible_for_general()
        
    def validate_contact_data(self, nome: str, telemovel: str) -> Tuple[bool, str]:
        if not nome or not nome.strip():
            return False, "Nome é obrigatório"
        
        if not telemovel or not telemovel.strip():
            return False, "Telefone é obrigatório"
        # Normaliza o telefone removendo espaços, traços e outros caracteres não numéricos
        digits = ''.join(filter(str.isdigit, telemovel))
        # Pega apenas os últimos 9 dígitos
        normalized = digits[-9:]
        # Junta cada 3 dígitos com espaço
        normalized = ' '.join([normalized[i:i+3] for i in range(0, len(normalized), 3)])
        # Verifica se o telefone tem pelo menos 9 dígitos
        if len(normalized) < 9:
            return False, "Número inválido (mínimo 9 dígitos)"
        
        return True, ""
        
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
