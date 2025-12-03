from typing import List, Optional, Callable, Tuple
from datetime import datetime
import threading

from models.contact import Contact, SendStatus

class ContactController:
    def __init__(self):
        self._contacts: List[Contact] = []
        self._data_source: Optional[str] = None
        self._is_sending = False
        self._stop_requested = False
        self._session_send_count = 0
        
        # Callbacks para UI
        self._on_contacts_changed: Optional[Callable] = None
        self._on_send_progress: Optional[Callable] = None
        self._on_send_complete: Optional[Callable] = None
        self._on_log: Optional[Callable] = None
        
        # Serviços (injetados)
        self._data_handler = None
        self._sender = None
        
    @property
    def contacts(self) -> List[Contact]:
        return self._contacts
    
    @property
    def active_contacts(self) -> List[Contact]:
        return [c for c in self._contacts if c.ativo and c.is_valid and not c._deleted]
    
    @property
    def is_sending(self) -> bool:
        return self._is_sending
    
    @property
    def session_send_count(self) -> int:
        return self._session_send_count
        
    def set_data_handler(self, handler):
        self._data_handler = handler
    
    def set_sender(self, sender):
        self._sender = sender
    
    def set_callbacks(
        self,
        on_contacts_changed: Optional[Callable] = None,
        on_send_progress: Optional[Callable] = None,
        on_send_complete: Optional[Callable] = None,
        on_log: Optional[Callable] = None
    ):
        self._on_contacts_changed = on_contacts_changed
        self._on_send_progress = on_send_progress
        self._on_send_complete = on_send_complete
        self._on_log = on_log
        
    def load_from_json(self, path: str) -> Tuple[bool, str, List[str]]:
        if not self._data_handler:
            return False, "DataHandler não configurado", []
        
        try:
            success, msg, warnings = self._data_handler.load_json(path)
            
            if success:
                self._contacts = [
                    Contact.from_dict(c.__dict__) 
                    for c in self._data_handler.contacts
                ]
                self._data_source = path
                self._notify_contacts_changed()
            
            return success, msg, warnings
            
        except Exception as e:
            return False, f"Erro ao carregar: {e}", []
    
    def load_from_excel(self, url: str) -> Tuple[bool, str, List[str]]:
        if not self._data_handler:
            return False, "DataHandler não configurado", []
        
        try:
            success, msg, warnings = self._data_handler.load_excel_online(url)
            
            if success:
                self._contacts = [
                    Contact.from_dict(c.__dict__) 
                    for c in self._data_handler.contacts
                ]
                self._data_source = url
                self._notify_contacts_changed()
            
            return success, msg, warnings
            
        except Exception as e:
            return False, f"Erro ao carregar: {e}", []
    
    def save_contacts(self) -> Tuple[bool, str]:
        if not self._data_handler:
            return False, "DataHandler não configurado"
        
        try:
            # Sincroniza contactos com data_handler
            self._data_handler.contacts = [
                type('ContactData', (), c.to_dict())() 
                for c in self._contacts if not c._deleted
            ]
            
            return self._data_handler.save_json()
            
        except Exception as e:
            return False, f"Erro ao guardar: {e}"
        
    def add_contact(self, contact: Contact):
        self._contacts.append(contact)
        self._notify_contacts_changed()
    
    def remove_contact(self, contact: Contact):
        contact.eliminar()
        self._notify_contacts_changed()
    
    def update_contact(self, contact: Contact, key: str, value) -> bool:
        result = contact.editar(key, value)
        if result:
            self._notify_contacts_changed()
        return result
    
    def get_eligible_for_welcome(self) -> List[Contact]:
        return [c for c in self.active_contacts if c.verificar_enviar_boas_vindas()]
    
    def get_eligible_for_general(self) -> List[Contact]:
        return [c for c in self.active_contacts if c.verificar_enviar_mensagem_geral()]
        
    def start_sending(
        self,
        contacts: List[Contact],
        message: str,
        welcome_message: str = "",
        delay: int = 3,
        check_stop_response: bool = True
    ):
        if self._is_sending:
            self._log("Já existe um envio em progresso")
            return
        
        if not self._sender:
            self._log("Serviço de envio não configurado")
            return
        
        self._is_sending = True
        self._stop_requested = False
        
        thread = threading.Thread(
            target=self._send_loop,
            args=(contacts, message, welcome_message, delay, check_stop_response),
            daemon=True
        )
        thread.start()
    
    def stop_sending(self):
        self._stop_requested = True
        self._log("A parar envio...")
    
    def _send_loop(
        self,
        contacts: List[Contact],
        message: str,
        welcome_message: str,
        delay: int,
        check_stop_response: bool
    ):
        import time
        
        sent = 0
        failed = 0
        total = len(contacts)
        
        for i, contact in enumerate(contacts):
            if self._stop_requested:
                self._log("Envio interrompido")
                break
            
            # Atualiza progresso
            progress = (i + 1) / total
            self._notify_progress(progress, i + 1, total)
            
            # Verifica se pode enviar
            can_send, reason = contact.pode_receber_mensagem()
            if not can_send:
                self._log(f"{contact.nome}: {reason}")
                continue
            
            # Verifica resposta PARAR
            if check_stop_response:
                if self._check_stop_response(contact):
                    contact.registar_envio(SendStatus.DESELECTED)
                    self._log(f"{contact.nome}: Pediu para parar")
                    continue
            
            # Prepara mensagem
            personal_msg = message.replace("{nome}", contact.nome)
            
            # Envia boas-vindas se aplicável
            if welcome_message and contact.verificar_enviar_boas_vindas():
                personal_welcome = welcome_message.replace("{nome}", contact.nome)
                self._send_message(contact, personal_welcome)
                time.sleep(2)
            
            # Envia mensagem principal
            success = self._send_message(contact, personal_msg)
            
            if success:
                sent += 1
                contact.registar_envio(SendStatus.SENT)
                self._session_send_count += 1
            else:
                failed += 1
                contact.registar_envio(SendStatus.FAILED)
            
            # Delay entre envios
            if i < total - 1 and not self._stop_requested:
                time.sleep(delay)
        
        # Conclusão
        self._is_sending = False
        self._notify_complete(sent, failed, total)
        self._notify_contacts_changed()
    
    def _send_message(self, contact: Contact, message: str) -> bool:
        try:
            if self._sender is None:
                return False
            
            if hasattr(self._sender, 'send_message'):
                result = self._sender.send_message(
                    contact.telemovel_normalizado,
                    message,
                    self._log
                )
                return getattr(result, 'success', False)
            elif hasattr(self._sender, 'send_sms'):
                result = self._sender.send_sms(
                    contact.telemovel_normalizado,
                    message,
                    self._log
                )
                return getattr(result, 'success', False)
            return False
        except Exception as e:
            self._log(f"Erro ao enviar para {contact.nome}: {e}")
            return False
    
    def _check_stop_response(self, contact: Contact) -> bool:
        try:
            if self._sender and hasattr(self._sender, 'check_for_stop_response'):
                return self._sender.check_for_stop_response(
                    contact.telemovel_normalizado,
                    self._log
                )
        except:
            pass
        return False
        
    def _notify_contacts_changed(self):
        if self._on_contacts_changed:
            self._on_contacts_changed(self._contacts)
    
    def _notify_progress(self, progress: float, current: int, total: int):
        if self._on_send_progress:
            self._on_send_progress(progress, current, total)
    
    def _notify_complete(self, sent: int, failed: int, total: int):
        if self._on_send_complete:
            self._on_send_complete(sent, failed, total)
        
        self._log(f"Concluído: {sent} enviados, {failed} falhados de {total}")
    
    def _log(self, message: str):
        if self._on_log:
            self._on_log(message)
        else:
            print(f"[ContactController] {message}")
        
    def get_statistics(self) -> dict:
        total = len(self._contacts)
        active = len(self.active_contacts)
        pending_welcome = len(self.get_eligible_for_welcome())
        
        return {
            "total": total,
            "active": active,
            "inactive": total - active,
            "pending_welcome": pending_welcome,
            "session_sent": self._session_send_count
        }