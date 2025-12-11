import json
import re
import os
import hashlib
from io import BytesIO
from datetime import datetime, date
from typing import Optional, Set, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from models.contact import Contact
from controllers.services.contact_service import ContactService
import pandas as pd
import requests
from utils.time import str_datetime, str_timestamp
from utils.logger import get_logger

SOURCE = "DataHandler"

class SendStatus(Enum):
    PENDING = "pendente"
    SENT = "enviado"
    FAILED = "falhou"
    SKIPPED = "ignorado"
    DESELECTED = "bloqueado"

class DataHandler:    
    def __init__(self, contact_service:ContactService):
        if contact_service is None:
            raise ValueError("ContactService é obrigatório")
        
        self.source_file: Optional[str] = None
        self._contact_service = contact_service
        self.logger = get_logger()

    def load_json(self, filepath: str) -> bool:
        return self._contact_service.load_json(filepath)
    
    def load_excel_online(self, url: str, merge: bool = False) -> Tuple[bool, str, List[str]]:
        try:
            # Tratamento da URL
            if 'docs.google.com/spreadsheets' in url and '/edit' in url:
                url = url.replace('/edit', '/export?format=xlsx').replace(url.split('/d/')[1].split('/')[1], '')

            r = requests.get(url)
            r.raise_for_status()
            
            # Lê tudo como string para facilitar a limpeza
            df = pd.read_excel(BytesIO(r.content), header=None, dtype=str)

            new_contacts = []
            seen_phones = set()

            # Processamento
            for row in df.values:
                # Limpeza inicial da linha (remove NaNs e vazios)
                cells = []
                for c in row:
                    if pd.notna(c):
                        cell_str = str(c).strip()
                        if cell_str != '':
                            cells.append(cell_str)

                if not cells: 
                    continue

                # Variáveis para guardar os dados desta linha
                phone = None
                nome = "Desconhecido"
                ultimo_envio = ""
                ativo = True
                ativo_checked = False

                for cell in cells:
                    cell_lower = cell.lower()

                    # Verifica se é uma bool
                    if not ativo_checked:
                        if cell_lower in ['false', 'não', 'nao', '0', 'no']:
                            ativo = False
                            ativo_checked = True
                            continue
                        elif cell_lower in ['true', 'sim', 'yes', '1']:
                            ativo_checked = True
                            continue # É um booleano, então não é nome nem data

                    # Verifica se é um numero de telémovel
                    if phone is None and Contact.validate_phone(cell):
                        phone = cell
                        continue # Identificado, passa para a próxima célula

                    # Verifica é DATA
                    if ultimo_envio is None and str_datetime(cell):
                        ultimo_envio = cell
                        continue

                    # Verifica se é NOME (Fallback)
                    # Se não é telefone, não é bool, não é data -> deve ser o nome
                    if nome == "Desconhecido":
                        nome = cell
                
                # Só adiciona se encontrou um telefone válido e não é duplicado
                if phone and phone not in seen_phones:
                    new_contacts.append(Contact(
                        nome=nome,
                        telemovel=phone,
                        ultimo_envio=ultimo_envio,
                        ativo=ativo,
                        selecionado=True
                    ))
                    seen_phones.add(phone)

            # Finalização
            if merge and self.contacts:
                self.contacts = self._contact_service.merge_contacts(new_contacts)
            else:
                self.contacts = new_contacts

            self.logger
            return True, f"Importados {len(new_contacts)} contactos.", []

        except Exception as e:
            return False, f"Erro: {e}", []
            
    def mark_as_inactive(self, phone: str) -> bool:
        normalized = Contact.normalize_phone(str(phone))
        for contact in self._contact_service.contacts:
            if contact.telemovel == normalized:
                contact.ativo = False
                return True
        return False
    
    def save_json(self, filepath: Optional[str] = None) -> bool:
        if filepath is not None:
            save_path = filepath
        else:
            save_path = self.source_file

        if not save_path or not save_path.endswith('.json'):
            save_path = f'contactos_backup_{date.today().isoformat()}.json' 
            
        # Se não tiver pach ou se não for json
        return self._contact_service.save_json(save_path)

    def get_preview_data(self, message: str, welcome: str = "") -> List[dict]:
        preview = []
        
        for contact in self._contact_service.contacts:
            if not contact.ativo:
                status = "Bloqueado: "
            else:
                status = "Será enviado"
            
            personal_msg = message.replace("{nome}", contact.nome)
            personal_welcome = welcome.replace("{nome}", contact.nome) if welcome.strip() else ""
            
            preview.append({
                "nome": contact.nome,
                "telefone": contact.telemovel,
                "mensagem": personal_msg,
                "boas_vindas": personal_welcome if not contact.ultimo_envio else "(não aplicável)",
                "status": status
            })
        
        return preview