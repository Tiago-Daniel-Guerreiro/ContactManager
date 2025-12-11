from typing import List, Optional, Callable, Tuple
from datetime import datetime
import threading
from pathlib import Path

from models.contact import Contact, SendStatus
from models.Result import Result, statusType, messageType
from controllers.services.whatsapp_sender import WhatsAppSender
from controllers.services.contact_service import ContactService
from utils.logger import get_logger

SOURCE = "ContactController"

class ContactController:
    def __init__(self):
        self._is_sending = False
        self._stop_requested = False
        self._session_send_count = 0
        
        # Logger centralizado
        self.logger = get_logger()
        
        # Callbacks para UI
        self._on_contacts_changed: Optional[Callable] = None
        self._on_send_progress: Optional[Callable] = None
        self._on_send_complete: Optional[Callable] = None
        self._on_log: Optional[Callable] = None
        
        # Serviços (injetados)
        self._contact_service: Optional[ContactService] = None
        self._sender = None
        self._message_service = None
    
    @property
    def contacts(self) -> List[Contact]:
        if self._contact_service:
            return self._contact_service.contacts
        return []
    
    @property
    def active_contacts(self) -> List[Contact]:
        if self._contact_service:
            return self._contact_service.get_active_contacts()
        return []
    
    @property
    def is_sending(self) -> bool:
        return self._is_sending
    
    @property
    def session_send_count(self) -> int:
        return self._session_send_count
        
    def set_contact_service(self, service: ContactService):
        self._contact_service = service
    
    def set_sender(self, sender):
        self._sender = sender
    
    def set_message_service(self, service):
        self._message_service = service
    
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
        
    def load_from_json(self, path: str) -> bool:
        if not self._contact_service:
            return False
        
        success = self._contact_service.load_json(path)
        if success:
            self._notify_contacts_changed()
        return success
    
    def save_contacts(self, path: Optional[str] = None) -> bool:
        if not self._contact_service:
            return False
        
        if path is None:
            path = getattr(self._contact_service, 'data_source_path', None)
        
        if not path:
            return False
            
        success = self._contact_service.save_json(path)
        return success
        
    def add_contact(self, contact: Contact):
        if self._contact_service:
            self._contact_service.contacts.append(contact)
            self._notify_contacts_changed()
    
    def remove_contact(self, contact: Contact):
        if self._contact_service and contact in self._contact_service.contacts:
            self._contact_service.contacts.remove(contact)
            self._notify_contacts_changed()
    
    def update_contact(self, contact: Contact, key: str, value) -> bool:
        result = contact.editar(key, value)
        if result:
            self._notify_contacts_changed()
        return result
    
    def get_eligible_for_welcome(self) -> List[Contact]:
        if self._contact_service:
            return self._contact_service.get_elegible_for_welcome()
        return []
    
    def get_eligible_for_general(self) -> List[Contact]:
        if self._contact_service:
            return self._contact_service.get_elegible_for_general()
        return []
    
    def initialize_sender(self, method: str):
        try:
            match method:
                case "whatsapp":
                    self.initialize_whatsapp()
                case "sms":
                    self.initialize_sms()
                case _:
                    self.logger.error(f"Método desconhecido: {method}")
                    return False
                
        except Exception as e:
            self.logger.error(f"Falha ao iniciar {method}")
            self.logger.debug(f"Erro ao inicializar {method}: {e}")
            return False
                
    def initialize_whatsapp(self):
        from controllers.services.whatsapp_sender import WhatsAppSender
        import threading
        
        if not isinstance(self._sender, WhatsAppSender):
            self._sender = WhatsAppSender()
        
        whatsapp_sender = self._sender
        
        if hasattr(whatsapp_sender, "is_logged_in") and whatsapp_sender.is_logged_in:
            self.logger.info("WhatsApp já está com login")
            return True
        
        self.logger.info("A iniciar o WhatsApp Web...")
        success = whatsapp_sender.initialize()

        if not success:
            self.logger.error("Falha ao inicializar WhatsApp Web")
            return False
        
        self.logger.info("Aguardando login (escaneie o QR code se necessário)...")
        
        # Aguarda login em thread separada para não bloquear
        def wait_login_thread():
            success = whatsapp_sender.wait_forlogin(timeout=120)
            if success:
                self.logger.info("WhatsApp: Login confirmado")
            else:
                self.logger.error(f"WhatsApp: Erro no login")
        
        login_thread = threading.Thread(target=wait_login_thread, daemon=True)
        login_thread.start()
        
        return True
                        
    def initialize_sms(self):
        from controllers.services.sms_sender import SMS_Sender
        
        if not isinstance(self._sender, SMS_Sender):
            self._sender = SMS_Sender()
        
        self.logger.info("SMS requer inicialização via interface")

        return False
        
    def validate_sender(self, method: str) -> Tuple[bool, str]:
        if not self._sender:
            return False, f"{method.capitalize()} não inicializado. Clique em 'Inicializar' primeiro."

        try:
            from controllers.services.whatsapp_sender import WhatsAppSender
            from controllers.services.sms_sender import SMS_Sender
        except ImportError:
            WhatsAppSender = None
            SMS_Sender = None

        if method == "whatsapp":
            if not self._sender:
                return False, "WhatsApp não inicializado. Clique em 'Inicializar' primeiro."
            if WhatsAppSender and not (isinstance(self._sender, WhatsAppSender) and getattr(self._sender, 'is_logged_in', False)):
                return False, "WhatsApp não está logado. Clique em 'Inicializar' primeiro."
        elif method == "sms":
            if not self._sender:
                return False, "SMS não inicializado. Clique em 'Inicializar' primeiro."
            if SMS_Sender and not (isinstance(self._sender, SMS_Sender) and getattr(self._sender, 'device_connected', False)):
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
            self.logger.warning("Já existe um envio em progresso", source=SOURCE)
            return
        
        if not self._sender:
            self.logger.error("Serviço de envio não configurado", source=SOURCE)
            return
        
        # Valida sender
        is_valid, error_msg = self.validate_sender(method)
        if not is_valid:
            self.logger.error(f"Erro: {error_msg}", source=SOURCE)
            return
        
        # Valida templates se message_service disponível
        if self._message_service:
            valid, error_msg = self._message_service.validate_templates(
                message_template, 
                welcome_template
            )
            if not valid:
                self.logger.error(f"Erro: {error_msg}", source=SOURCE)
                return
        
        if not contacts:
            self.logger.warning("Nenhum contacto para enviar", source=SOURCE)
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
            self.logger.info(f"Iniciando envio para {total} contactos...", source=SOURCE)
            self.logger.debug(f"Delay configurado: {delay}s entre mensagens", source=SOURCE)
            
            # Já há 3s de espera após o login, não precisa de mais delay aqui
            
            sent = 0
            failed = 0
            reports: List[Result] = []
            
            for i, contact in enumerate(contacts):
                if self._stop_requested:
                    self.logger.warning("Envio interrompido pelo utilizador", source=SOURCE)
                    break
                
                # Atualiza progresso
                progress = (i + 1) / total
                self._notify_progress(progress, i + 1, total)
                
                self.logger.debug(f"[{i+1}/{total}] Processando: {contact.nome}", source=SOURCE)
                
                # Verifica se pode enviar
                can_send, reason = contact.pode_receber_mensagem()
                if not can_send:
                    self.logger.warning(f"{contact.nome}: {reason}", source=SOURCE)
                    continue
                
                # Verifica resposta PARAR (se WhatsApp)
                if check_stop_response and self._check_stop_response(contact):
                    contact.registar_envio(SendStatus.DESELECTED)
                    contact.ativo = False  # Marca como inativo
                    self.logger.warning(f"{contact.nome}: Pediu para parar (marcado como inativo)", source=SOURCE)
                    continue
                
                self.logger.debug(f"Preparando mensagens para {contact.nome}...", source=SOURCE)
                
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
                    self.logger.info(f"[{i+1}/{total}] {contact.nome}: Enviando boas-vindas...", source=SOURCE)
                    self.logger.debug(f"Mensagem boas-vindas: {welcome_msg[:50]}...", source=SOURCE)
                    
                    result = self._send_message(contact, welcome_msg, messageType.WELCOME)
                    reports.append(result)
                    
                    if result.status == statusType.SUCCESS:
                        sent += 1
                        contact.registar_envio(SendStatus.SENT)
                        self._session_send_count += 1
                        self.logger.info(f"[{i+1}/{total}] {contact.nome}: ✓ Boas-vindas enviadas", source=SOURCE)
                    else:
                        failed += 1
                        self.logger.error(f"[{i+1}/{total}] {contact.nome}: ✗ Erro ao enviar boas-vindas - {result.message}", source=SOURCE)
                    
                    self.logger.debug(f"Aguardando {delay}s antes da próxima mensagem...", source=SOURCE)
                    time.sleep(delay)
                
                # ENVIO 2: Mensagem geral
                if general_msg:
                    self.logger.info(f"[{i+1}/{total}] {contact.nome}: Enviando mensagem geral...", source=SOURCE)
                    self.logger.debug(f"Mensagem geral: {general_msg[:50]}...", source=SOURCE)
                    
                    result = self._send_message(contact, general_msg, messageType.GENERAL)
                    reports.append(result)
                    
                    if result.status == statusType.SUCCESS:
                        sent += 1
                        contact.registar_envio(SendStatus.SENT)
                        self._session_send_count += 1
                        self.logger.info(f"[{i+1}/{total}] {contact.nome}: ✓ Mensagem enviada", source=SOURCE)
                    else:
                        failed += 1
                        contact.registar_envio(SendStatus.FAILED)
                        self.logger.error(f"[{i+1}/{total}] {contact.nome}: ✗ Erro ao enviar - {result.message}", source=SOURCE)
                
                self.logger.debug(f"Aguardando {delay}s antes do próximo contacto...", source=SOURCE)
                time.sleep(delay)
            
            # Salva contactos
            self.logger.debug("Salvando contactos...", source=SOURCE)
            self._auto_save()
            
            # Gera relatório se tiver reports
            if reports:
                self._generate_report(reports)
            
            self._notify_complete(sent, failed, total)
            self._notify_contacts_changed()
                    
        except Exception as e:
            self.logger.error(f"Erro crítico no envio", error=e, source=SOURCE)
        finally:
            self._is_sending = False
            
            self.logger.debug("Finalizando processo de envio...", source=SOURCE)
            # Cleanup do WhatsApp se estiver a usar
            if isinstance(self._sender, WhatsAppSender):
                try:
                    self.logger.info("Encerrando WhatsApp...", source=SOURCE)
                    self._sender.close()
                except Exception as e:
                    self.logger.error(f"Erro ao encerrar WhatsApp", error=e, source=SOURCE)
    
    def _generate_report(self, reports: List[Result]):
        from controllers.services.report_service import ReportGenerator
        import threading
        
        try:
            self.logger.debug("Gerando relatório HTML...", source=SOURCE)
            method = "whatsapp" if isinstance(self._sender, WhatsAppSender) else "sms"
            
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            
            filename = f"relatorio_{method}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            report_path = reports_dir / filename
            
            if ReportGenerator.generate_html_report(reports, method, report_path):
                self.logger.info(f"Relatório gerado: {report_path}", source=SOURCE)
                
                # Abre relatório em thread separada para não bloquear UI
                # Não fecha o navegador - deixa usuario controlar
                def open_report():
                    try:
                        ReportGenerator.open_report(report_path)
                    except Exception as e:
                        self.logger.error(f"Erro ao abrir relatório", error=e, source=SOURCE)
                
                thread = threading.Thread(target=open_report, daemon=True)
                thread.start()
        except Exception as e:
            self.logger.error(f"Erro ao gerar relatório",error=e, source=SOURCE)
    
    def _update_progress_wrapper(self, current: int, total: int):
        progress = current / total if total > 0 else 0
        self._notify_progress(progress, current, total)
    
    def stop_sending(self):
        self._stop_requested = True
        self.logger.warning("Pedido de paragem recebido...", source=SOURCE)
    
    def _auto_save(self):
        if self._contact_service:
            try:
                path = getattr(self._contact_service, 'data_source_path', None)
                if path:
                    success = self._contact_service.save_json(path)
                    if not success:
                        self.logger.error("Erro ao salvar contactos", source=SOURCE)
            except Exception as e:
                self.logger.error(f"Erro ao salvar contactos",error=e, source=SOURCE)
    
    def _send_message(self, contact: Contact, message: str, msg_type: messageType) -> Result:
        try:
            resultado = Result(
                    contact_name=contact.nome,
                    contact_phone=contact.telemovel,
                    status=statusType.ERROR,
                    message="Sender não configurado",
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    message_type=msg_type
                )
            
            if self._sender is None:
                return resultado # Mensagem de erro padrão
            
            # Ambas as classes (WhatsAppSender e SMS_Sender) usam send_message
            if hasattr(self._sender, 'send_message') and callable(getattr(self._sender, 'send_message', None)):
                result = self._sender.send_message(
                    contact.telemovel,
                    message,
                    contact.nome,
                    msg_type
                )
                
                # Se o número for inválido, marca o contacto como inválido
                if result.status == statusType.INVALID:
                    self.logger.warning(f"Marcando {contact.nome} como número inválido", source=SOURCE)
                    contact.is_valid = False
                    # Adiciona ao cache do WhatsAppSender se existir
                    if isinstance(self._sender, WhatsAppSender):
                        phone_digits = ''.join(filter(str.isdigit, contact.telemovel))
                        self._sender._invalid_numbers.add(phone_digits)
                
                return result

            resultado.message = "Método send_message não disponível"
            return resultado
        except Exception as e:
            self.logger.error(f"Erro ao enviar para {contact.nome}", error=e, source=SOURCE)
            resultado.message = "Erro ao enviar mensagem"
            return resultado
    
    def _check_stop_response(self, contact: Contact) -> bool:
        try:
            # Checa dinamicamente se o método existe e é chamável
            # (Apenas SMS_Sender tem este método, WhatsAppSender não)
            if self._sender and hasattr(self._sender, 'check_for_stop_response'):
                check_method = getattr(self._sender, 'check_for_stop_response', None)
                if callable(check_method):
                    result = check_method(contact.telemovel)
                    return bool(result)
        except Exception:
            pass
        return False
        
    def _notify_contacts_changed(self):
        if self._on_contacts_changed:
            self._on_contacts_changed(self.contacts)
    
    def _notify_progress(self, progress: float, current: int, total: int):
        if self._on_send_progress:
            self._on_send_progress(progress, current, total)
    
    def _notify_complete(self, sent: int, failed: int, total: int):
        if self._on_send_complete:
            self._on_send_complete(sent, failed, total)
        
        self.logger.info(f"Concluído: {sent} enviados, {failed} falhados de {total}", source=SOURCE)

    def get_statistics(self) -> dict:
        total = len(self.contacts)
        active = len(self.active_contacts)
        pending_welcome = len(self.get_eligible_for_welcome())
        
        return {
            "total": total,
            "active": active,
            "inactive": total - active,
            "pending_welcome": pending_welcome,
            "session_sent": self._session_send_count
        }