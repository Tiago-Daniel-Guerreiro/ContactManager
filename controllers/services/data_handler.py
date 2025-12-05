
"""
Data Handler - Gerenciamento de dados de contactos e envios
"""
import json
import re
import os
import hashlib
from io import BytesIO
from datetime import datetime, date
from typing import Optional, Set, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd
import requests

class SendStatus(Enum):
    PENDING = "pendente"
    SENT = "enviado"
    FAILED = "falhou"
    SKIPPED = "ignorado"
    DESELECTED = "bloqueado"

@dataclass
class ContactData:
    nome: str
    contacto_original: str 
    contacto: str = ""
    ultimo_envio: str = ""
    ativo: bool = True
    selecionado: bool = True
    _validated: bool = False
    
    def __post_init__(self):
        self.contacto_normalizado = self._normalize_phone(self.contacto_original)
        self._validated = self._validate()
    
    def _normalize_phone(self, phone: str) -> str:
        if not phone:
            return ""
        
        # Remove tudo exceto dígitos
        digits_only = re.sub(r'[^\d]', '', str(phone))
        
        if not digits_only:
            return ""
        
        # Remove 00 do início (código internacional)
        if digits_only.startswith('00'):
            digits_only = digits_only[2:]
        
        # Se começa com 351, remove
        if digits_only.startswith('351'):
            digits_only = digits_only[3:]
        
        # Número português deve ter 9 dígitos e começar com 9, 2 ou 3
        if len(digits_only) == 9 and digits_only[0] in '923':
            return f"+351{digits_only}"
        
        # Se tem mais de 9 dígitos, pode ser internacional
        if len(digits_only) > 9:
            return f"+{digits_only}"
        
        return ""  # Número inválido
    
    def _validate(self) -> bool:
        if not self.nome or not self.nome.strip():
            return False
        if not self.contacto_normalizado:
            return False
        # Número português: +351 seguido de 9 dígitos
        if self.contacto_normalizado.startswith('+351'):
            return len(self.contacto_normalizado) == 13
        return len(self.contacto_normalizado) >= 10
    
    @property
    def is_valid(self) -> bool:
        return self._validated
    
    def to_dict(self) -> dict:
        return {
            "nome": self.nome,
            "telemovel": self.contacto_original,
            "telemovel_normalizado": self.contacto_normalizado,
            "ultimo_envio": self.ultimo_envio,
            "ativo": self.ativo,
            "selecionado": self.selecionado
        }
    
    def __eq__(self, other):
        if not isinstance(other, ContactData):
            return False
        return self.contacto_normalizado == other.contacto_normalizado
    
    def __hash__(self):
        return hash(self.contacto_normalizado)

class DataHandler:    
    def __init__(self):
        self.contacts: List[ContactData] = []
        self.source_file: Optional[str] = None
        self.source_type: Optional[str] = None
        
    def load_json(self, filepath: str) -> Tuple[bool, str, List[str]]:
        warnings = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.contacts = []
            duplicates = set()
            seen_phones = set()
            
            contacts_list = data if isinstance(data, list) else data.get('contactos', data.get('contacts', []))
            
            for i, item in enumerate(contacts_list, 1):
                contact = ContactData(
                    nome=str(item.get('nome', item.get('name', ''))).strip(),
                    contacto_original=str(item.get('telemovel', item.get('contacto', item.get('telefone', item.get('phone', ''))))).strip(),
                    ultimo_envio=str(item.get('ultimo_envio', item.get('last_sent', ''))).strip(),
                    ativo=item.get('ativo', item.get('active', True)),
                    selecionado=item.get('selecionado', item.get('selected', True))
                )
                
                # Validação
                if not contact.is_valid:
                    warnings.append(f"Linha {i}: Contacto inválido - {item}")
                    continue
                
                # Verificar duplicados
                if contact.contacto_normalizado in seen_phones:
                    duplicates.add(contact.contacto_normalizado)
                    warnings.append(f"Linha {i}: Duplicado - {contact.nome} ({contact.contacto_normalizado})")
                    continue
                
                seen_phones.add(contact.contacto_normalizado)
                self.contacts.append(contact)
            
            self.source_file = filepath
            self.source_type = 'json'
            
            msg = f"Carregados {len(self.contacts)} contactos válidos"
            if warnings:
                msg += f" ({len(warnings)} avisos)"
            
            return True, msg, warnings
        
        except FileNotFoundError:
            return False, f"Ficheiro não encontrado: {filepath}", []
        except json.JSONDecodeError as e:
            return False, f"Erro ao ler JSON: {e}", []
        except Exception as e:
            return False, f"Erro: {e}", []
    
    def load_excel_online(self, url: str) -> Tuple[bool, str, List[str]]:
        warnings = []
        try:
            # Verifica se openpyxl está disponível
            try:
                import openpyxl
            except ImportError:
                return False, "Biblioteca 'openpyxl' não instalada. Execute: pip install openpyxl", []
            
            # Conversão de URLs
            if 'docs.google.com/spreadsheets' in url:
                if '/edit' in url:
                    sheet_id = url.split('/d/')[1].split('/')[0]
                    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            df = pd.read_excel(BytesIO(response.content), engine='openpyxl')
            
            self.contacts = []
            seen_phones = set()
            
            # Mapeia colunas
            col_map = self._map_columns(df.columns)
            
            for row_idx, row in enumerate(df.iterrows(), start=2):
                idx, row = row
                line_num = row_idx
                
                nome = str(row.get(col_map.get('nome', 'nome'), '')).strip()
                contacto = str(row.get(col_map.get('contacto', 'contacto'), '')).strip()
                
                if nome == 'nan' or contacto == 'nan' or not nome or not contacto:
                    continue
                
                ultimo_envio = str(row.get(col_map.get('ultimo_envio', 'ultimo_envio'), '')).strip()
                if ultimo_envio == 'nan':
                    ultimo_envio = ''
                
                ativo = row.get(col_map.get('ativo', 'ativo'), True)
                if isinstance(ativo, str):
                    ativo = ativo.lower() in ['true', 'sim', 'yes', '1', 'verdadeiro']
                elif pd.isna(ativo):
                    ativo = True
                
                selecionado = row.get(col_map.get('selecionado', 'selecionado'), True)
                if isinstance(selecionado, str):
                    selecionado = selecionado.lower() in ['true', 'sim', 'yes', '1', 'verdadeiro']
                elif pd.isna(selecionado):
                    selecionado = True
                
                contact = ContactData(
                    nome=nome,
                    contacto_original=contacto,
                    ultimo_envio=ultimo_envio,
                    ativo=bool(ativo),
                    selecionado=bool(selecionado)
                )
                
                if not contact.is_valid:
                    warnings.append(f"Linha {line_num}: Contacto inválido - {nome} ({contacto})")
                    continue
                
                if contact.contacto_normalizado in seen_phones:
                    warnings.append(f"Linha {line_num}: Duplicado - {nome}")
                    continue
                
                seen_phones.add(contact.contacto_normalizado)
                self.contacts.append(contact)
            
            self.source_file = url
            self.source_type = 'excel'
            
            msg = f"Carregados {len(self.contacts)} contactos válidos"
            if warnings:
                msg += f" ({len(warnings)} avisos)"
            
            return True, msg, warnings
        
        except Exception as e:
            return False, f"Erro: {e}", []
    
    def _map_columns(self, columns) -> dict:
        col_map = {}
        for col in columns:
            col_lower = str(col).lower().strip()
            if col_lower in ['nome', 'name']:
                col_map['nome'] = col
            elif col_lower in ['contacto', 'telefone', 'phone', 'telemovel', 'telemóvel', 'numero', 'número']:
                col_map['contacto'] = col
            elif col_lower in ['ultimo_envio', 'last_sent', 'último envio', 'ultimo envio']:
                col_map['ultimo_envio'] = col
            elif col_lower in ['ativo', 'active', 'activo']:
                col_map['ativo'] = col
        return col_map
    
    def get_send_candidates(self, message: str) -> List[ContactData]:
        return [
            contact for contact in self.contacts 
            if contact.ativo and contact.is_valid
        ]
    
    def can_send(self, contact: ContactData, message: str) -> Tuple[bool, str]:
        if not contact.ativo:
            return False, "Contacto inativo"
        
        if not contact.is_valid:
            return False, "Número inválido"
        
        return True, "OK"
    
    def mark_as_inactive(self, phone: str) -> bool:
        normalized = ContactData(nome="temp", contacto_original=str(phone)).contacto_normalizado
        for contact in self.contacts:
            if contact.contacto_normalizado == normalized:
                contact.ativo = False
                return True
        return False
    
    def save_json(self, filepath: Optional[str] = None) -> Tuple[bool, str]:
        try:
            filepath = filepath or self.source_file
            if not filepath or not filepath.endswith('.json'):
                filepath = f'contactos_backup_{date.today().isoformat()}.json'
            
            # Garante que o diretório existe
            from pathlib import Path
            file_path = Path(filepath)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Salva apenas contactos não deletados com os campos necessários
            # Compatível com Contact e ContactData
            data = []
            for c in self.contacts:
                # Tenta usar Contact.to_dict() se disponível
                if hasattr(c, 'to_dict') and callable(c.to_dict):
                    try:
                        data.append(c.to_dict())
                        continue
                    except:
                        pass
                
                # Fallback para construir manualmente (compatível com ambos)
                contact_dict = {
                    "nome": getattr(c, 'nome', ''),
                    "telemovel": getattr(c, 'telemovel', getattr(c, 'contacto_original', '')),
                    "telemovel_normalizado": getattr(c, 'telemovel_normalizado', getattr(c, 'contacto_normalizado', '')),
                    "ultimo_envio": getattr(c, 'ultimo_envio', ''),
                    "ativo": getattr(c, 'ativo', True),
                    "selecionado": getattr(c, 'selecionado', True)
                }
                data.append(contact_dict)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True, f"Contactos salvos em {filepath}"
        except Exception as e:
            return False, f"Erro ao guardar: {str(e)}"
    
    def get_preview_data(self, message: str, welcome: str = "") -> List[dict]:
        preview = []
        
        for contact in self.contacts:
            if not contact.ativo or not contact.is_valid:
                status = "Bloqueado: " + ("Inativo" if not contact.ativo else "Número inválido")
            else:
                status = "Será enviado"
            
            personal_msg = message.replace("{nome}", contact.nome)
            personal_welcome = welcome.replace("{nome}", contact.nome) if welcome.strip() else ""
            
            preview.append({
                "nome": contact.nome,
                "telefone": contact.contacto_normalizado,
                "mensagem": personal_msg,
                "boas_vindas": personal_welcome if not contact.ultimo_envio else "(não aplicável)",
                "status": status
            })
        
        return preview