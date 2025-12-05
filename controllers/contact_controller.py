from typing import List, Optional, Callable, Tuple
from datetime import datetime
import threading
from pathlib import Path

from models.contact import Contact, SendStatus
from controllers.services.report_service import SendReport, ReportService
from controllers.services.whatsapp_sender import WhatsAppSender

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
        self._message_service = None
        self._send_coordinator = None
    
    def _log(self, msg: str):
        if self._on_log:
            try:
                self._on_log(msg)
            except:
                print(f"{msg}")
        else:
            print(f"{msg}")
        
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
    
    def set_message_service(self, service):
        self._message_service = service
    
    def set_send_coordinator(self, coordinator):
        self._send_coordinator = coordinator
    
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
    
    def initialize_sender(self, method: str, on_complete: Optional[Callable] = None):
        try:
            if method == "whatsapp":
                from controllers.services.whatsapp_sender import WhatsAppSender
                import threading
                
                if not isinstance(self._sender, WhatsAppSender):
                    self._sender = WhatsAppSender()
                
                whatsapp_sender = self._sender
                
                if hasattr(whatsapp_sender, "is_logged_in") and whatsapp_sender.is_logged_in:
                    self._log("WhatsApp já está inicializado")
                    if on_complete:
                        on_complete(True, "WhatsApp já estava logado")
                    return True
                
                self._log("Inicializando WhatsApp Web...")
                success = whatsapp_sender.initialize(log_callback=self._log)
                
                if not success:
                    self._log("Erro ao inicializar WhatsApp Web")
                    if on_complete:
                        on_complete(False, "Falha ao inicializar WhatsApp")
                    return False
                
                self._log("Aguardando login (escaneie o QR code se necessário)...")
                
                # Aguarda login em thread separada para não bloquear
                def wait_login_thread():
                    success, msg = whatsapp_sender.wait_for_login(timeout=120, log_callback=self._log)
                    if success:
                        self._log("WhatsApp: Login confirmado")
                        if on_complete:
                            on_complete(True, "WhatsApp pronto")
                    else:
                        self._log(f"Erro no WhatsApp: {msg}")
                        if on_complete:
                            on_complete(False, msg)
                
                login_thread = threading.Thread(target=wait_login_thread, daemon=True)
                login_thread.start()
                
                return True
            
            elif method == "sms":
                from controllers.services.sms_sender import SMSSender
                
                if not isinstance(self._sender, SMSSender):
                    self._sender = SMSSender()
                
                sms_sender = self._sender
                
                if hasattr(sms_sender, "device_connected") and sms_sender.device_connected:
                    self._log("Dispositivo SMS já conectado")
                    if on_complete:
                        on_complete(True, "SMS já estava conectado")
                    return True
                
                # Para SMS, precisamos abrir uma janela de inicialização
                # Isso será tratado pelo main_window
                self._log("SMS requer inicialização via interface")
                if on_complete:
                    on_complete(False, "SMS requer configuração manual")
                return False
            
            else:
                self._log(f"Método desconhecido: {method}")
                return False
                
        except Exception as e:
            self._log(f"Erro ao inicializar {method}: {e}")
            if on_complete:
                on_complete(False, str(e))
            return False
    
    def validate_sender(self, method: str) -> Tuple[bool, str]:
        if not self._sender:
            return False, f"{method.capitalize()} não inicializado. Clique em 'Inicializar' primeiro."

        try:
            from controllers.services.whatsapp_sender import WhatsAppSender
            from controllers.services.sms_sender import SMSSender
        except ImportError:
            WhatsAppSender = None
            SMSSender = None

        if method == "whatsapp":
            if not self._sender:
                return False, "WhatsApp não inicializado. Clique em 'Inicializar' primeiro."
            if WhatsAppSender and not (isinstance(self._sender, WhatsAppSender) and getattr(self._sender, 'is_logged_in', False)):
                return False, "WhatsApp não está logado. Clique em 'Inicializar' primeiro."
        elif method == "sms":
            if not self._sender:
                return False, "SMS não inicializado. Clique em 'Inicializar' primeiro."
            if SMSSender and not (isinstance(self._sender, SMSSender) and getattr(self._sender, 'device_connected', False)):
                return False, "Nenhum dispositivo Android conectado. Clique em 'Inicializar' primeiro."
        return True, ""
        
    def start_sending(
        self,
        method: str,
        contacts: List[Contact],
        message_template: str,
        welcome_template: str = "",
        delay: int = 3,
        check_stop_response: bool = True
    ):
        if self._is_sending:
            self._log("Já existe um envio em progresso")
            return
        
        if not self._sender:
            self._log("Serviço de envio não configurado")
            return
        
        # Valida sender
        is_valid, error_msg = self.validate_sender(method)
        if not is_valid:
            self._log(f"Erro: {error_msg}")
            return
        
        # Valida templates se message_service disponível
        if self._message_service:
            valid, error_msg = self._message_service.validate_templates(
                message_template, 
                welcome_template
            )
            if not valid:
                self._log(f"Erro: {error_msg}")
                return
        
        if not contacts:
            self._log("Nenhum contacto para enviar")
            return
        
        self._is_sending = True
        self._stop_requested = False
        
        # Inicia thread de envio com lógica integrada (não precisa mais do coordinator)
        thread = threading.Thread(
            target=self._send_with_coordinator,
            args=(contacts, message_template, welcome_template, delay, check_stop_response),
            daemon=True
        )
        thread.start()
    
    def _send_with_coordinator(
        self,
        contacts: List[Contact],
        message_template: str,
        welcome_template: str,
        delay: int,
        check_stop_response: bool
    ):
        import time
        
        try:
            total = len(contacts)
            self._log(f"Enviando para {total} contactos...")
            
            # Já há 3s de espera após o login, não precisa de mais delay aqui
            
            sent = 0
            failed = 0
            reports = []
            
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
                
                # Verifica resposta PARAR (se WhatsApp)
                if check_stop_response and self._check_stop_response(contact):
                    contact.registar_envio(SendStatus.DESELECTED)
                    self._log(f"{contact.nome}: Pediu para parar")
                    continue
                
                # Prepara mensagens usando message_service
                if self._message_service:
                    welcome_msg, general_msg = self._message_service.prepare_message(
                        contact=contact,
                        message_template=message_template,
                        welcome_template=welcome_template,
                        send_all_mode=True
                    )
                else:
                    # Fallback sem message_service
                    welcome_msg = welcome_template.replace("{nome}", contact.nome) if welcome_template else None
                    general_msg = message_template.replace("{nome}", contact.nome) if message_template else None
                
                # ENVIO 1: Boas-vindas (se aplicável)
                if welcome_msg:
                    self._log(f"[{i+1}/{total}] {contact.nome}: Enviando boas-vindas...")
                    
                    success = self._send_message(contact, welcome_msg)
                    
                    if success:
                        sent += 1
                        contact.registar_envio(SendStatus.SENT)
                        self._session_send_count += 1
                        self._log(f"[{i+1}/{total}] {contact.nome}: OK (boas-vindas)")
                        
                        # Registra no relatório
                        reports.append(SendReport(
                            contact_name=contact.nome,
                            contact_phone=contact.telemovel_normalizado,
                            status="sucesso",
                            message="Boas-vindas enviadas",
                            timestamp=datetime.now().strftime("%H:%M:%S"),
                            message_type="boas-vindas"
                        ))
                    else:
                        failed += 1
                        self._log(f"[{i+1}/{total}] {contact.nome}: ERRO (boas-vindas)")
                        
                        reports.append(SendReport(
                            contact_name=contact.nome,
                            contact_phone=contact.telemovel_normalizado,
                            status="erro",
                            message="Falha ao enviar boas-vindas",
                            timestamp=datetime.now().strftime("%H:%M:%S"),
                            message_type="boas-vindas"
                        ))
                    
                    # Aguarda antes de enviar mensagem geral
                    time.sleep(delay)
                
                # ENVIO 2: Mensagem geral
                if general_msg:
                    self._log(f"[{i+1}/{total}] {contact.nome}: Enviando mensagem geral...")
                    
                    success = self._send_message(contact, general_msg)
                    
                    if success:
                        sent += 1
                        contact.registar_envio(SendStatus.SENT)
                        self._session_send_count += 1
                        self._log(f"[{i+1}/{total}] {contact.nome}: OK (geral)")
                        
                        reports.append(SendReport(
                            contact_name=contact.nome,
                            contact_phone=contact.telemovel_normalizado,
                            status="sucesso",
                            message="Mensagem enviada",
                            timestamp=datetime.now().strftime("%H:%M:%S"),
                            message_type="geral"
                        ))
                    else:
                        failed += 1
                        contact.registar_envio(SendStatus.FAILED)
                        self._log(f"[{i+1}/{total}] {contact.nome}: ERRO (geral)")
                        
                        reports.append(SendReport(
                            contact_name=contact.nome,
                            contact_phone=contact.telemovel_normalizado,
                            status="erro",
                            message="Falha ao enviar",
                            timestamp=datetime.now().strftime("%H:%M:%S"),
                            message_type="geral"
                        ))
                time.sleep(delay)
            
            # Salva contactos
            self._auto_save()
            
            # Gera relatório se tiver reports
            if reports and self._message_service:
                try:
                    from utils.get_patch import get_base_dir
                    
                    # Determina método baseado no tipo de sender
                    method = "whatsapp" if hasattr(self._sender, 'is_logged_in') else "sms"
                    
                    reports_dir = get_base_dir() / "reports"
                    reports_dir.mkdir(exist_ok=True)
                    
                    filename = f"relatorio_{method}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                    report_path = reports_dir / filename
                    
                    if ReportService.generate_html_report(reports, method, report_path):
                        self._log(f"Relatório gerado: {report_path}")
                        
                        # Abre relatório
                        import webbrowser
                        webbrowser.open(str(report_path))
                except Exception as e:
                    self._log(f"Erro ao gerar relatório: {e}")
            
            self._notify_complete(sent, failed, total)
            self._notify_contacts_changed()
                    
        except Exception as e:
            self._log(f"Erro no envio: {str(e)}")
        finally:
            self._is_sending = False
            
            # Cleanup do WhatsApp se estiver a usar
            if isinstance(self._sender, WhatsAppSender):
                try:
                    self._log("A encerrar WhatsApp...")
                    self._sender.cleanup(log_callback=self._log)
                except Exception as e:
                    self._log(f"Erro ao encerrar WhatsApp: {e}")
    
    def _update_progress_wrapper(self, current: int, total: int):
        progress = current / total if total > 0 else 0
        self._notify_progress(progress, current, total)
    
    def stop_sending(self):
        self._stop_requested = True
        if self._send_coordinator:
            self._send_coordinator.stop()
        self._log("A parar envio...")
    
    def _auto_save(self):
        if self._data_handler:
            try:
                # Sincroniza contactos com data_handler
                self._data_handler.contacts = [
                    type('ContactData', (), c.to_dict())() 
                    for c in self._contacts if not c._deleted
                ]
                
                success, msg = self._data_handler.save_json()
                if not success:
                    self._log(f"Erro ao salvar: {msg}")
            except Exception as e:
                self._log(f"Erro ao salvar contactos: {e}")
    
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
            if welcome_message and welcome_message.strip() and contact.verificar_enviar_boas_vindas():
                personal_welcome = welcome_message.replace("{nome}", contact.nome)
                self._log(f"[{i+1}/{total}] {contact.nome}: Enviando boas-vindas...")
                
                welcome_success = self._send_message(contact, personal_welcome)
                
                if welcome_success:
                    sent += 1
                    contact.registar_envio(SendStatus.SENT)
                    self._session_send_count += 1
                    self._log(f"[{i+1}/{total}] {contact.nome}: OK (boas-vindas)")
                else:
                    failed += 1
                    contact.registar_envio(SendStatus.FAILED)
                    self._log(f"[{i+1}/{total}] {contact.nome}: ERRO (boas-vindas)")
                
                # Aguarda antes de enviar a mensagem geral
                time.sleep(delay)
            
            # Envia mensagem principal (se houver)
            if message and message.strip():
                personal_msg = message.replace("{nome}", contact.nome)
                self._log(f"[{i+1}/{total}] {contact.nome}: Enviando mensagem geral...")
                
                success = self._send_message(contact, personal_msg)
                
                if success:
                    sent += 1
                    contact.registar_envio(SendStatus.SENT)
                    self._session_send_count += 1
                    self._log(f"[{i+1}/{total}] {contact.nome}: OK (geral)")
                else:
                    failed += 1
                    contact.registar_envio(SendStatus.FAILED)
                    self._log(f"[{i+1}/{total}] {contact.nome}: ERRO (geral)")
        
        # Conclusão
        self._is_sending = False
        self._notify_complete(sent, failed, total)
        self._notify_contacts_changed()
    
    def _send_message(self, contact: Contact, message: str) -> bool:
        try:
            if self._sender is None:
                return False
            # Envio dinâmico, sem depender de tipos estáticos
            # Ambas as classes (WhatsAppSender e SMSSender) usam send_message
            if hasattr(self._sender, 'send_message') and callable(getattr(self._sender, 'send_message', None)):
                result = self._sender.send_message(
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
            # Checa dinamicamente se o método existe e é chamável
            if self._sender and hasattr(self._sender, 'check_for_stop_response') and callable(getattr(self._sender, 'check_for_stop_response', None)):
                return self._sender.check_for_stop_response(
                    contact.telemovel_normalizado,
                    self._log
                )
        except Exception:
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