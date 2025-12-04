from typing import List, Callable, Optional, TYPE_CHECKING
from datetime import datetime
from pathlib import Path

from models.contact import Contact
from controllers.services.message_service import MessageService, MessageType
from controllers.services.report_service import SendReport, ReportService

if TYPE_CHECKING:
    from controllers.services.whatsapp_sender import WhatsAppSender
    from controllers.services.sms_sender import SMSSender


class SendResult:
    def __init__(self, success: bool, message: str, timestamp: str):
        self.success = success
        self.message = message
        self.timestamp = timestamp


class SendCoordinator:
    def __init__(self, sender, message_service: Optional[MessageService] = None):
        self.sender = sender
        self.message_service = message_service or MessageService()
        self.is_sending = False
        self.reports: List[SendReport] = []
    
    def send_to_contacts(
        self,
        contacts: List[Contact],
        message_template: str,
        welcome_template: Optional[str],
        send_all_mode: bool,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> List[SendReport]:
        self.is_sending = True
        self.reports = []
        
        total = len(contacts)
        sent_count = 0
        
        for idx, contact in enumerate(contacts):
            if not self.is_sending:
                self._log(log_callback, "Envio cancelado pelo utilizador")
                break
            
            try:
                # Prepara mensagens (pode retornar boas-vindas + geral)
                welcome_msg, general_msg = self.message_service.prepare_message(
                    contact=contact,
                    message_template=message_template,
                    welcome_template=welcome_template,
                    send_all_mode=send_all_mode
                )
                
                # ENVIO 1: Boas-vindas (se aplicável)
                if welcome_msg:
                    self._log(log_callback, f"[{idx+1}/{total}] {contact.nome}: Enviando boas-vindas...")
                    
                    result = self._send_single_message(
                        contact=contact,
                        message=welcome_msg,
                        message_type=MessageType.WELCOME,
                        log_callback=log_callback
                    )
                    
                    if result.success:
                        sent_count += 1
                        self._log(log_callback, f"[{idx+1}/{total}] {contact.nome}: Boas-vindas enviadas")
                    else:
                        self._log(log_callback, f"[{idx+1}/{total}] {contact.nome}: Erro nas boas-vindas - {result.message}")
                
                # Envio 2: Mensagem geral (sempre enviada)
                if general_msg:  # Garante que general_msg não é None
                    result = self._send_single_message(
                        contact=contact,
                        message=general_msg,
                        message_type=MessageType.GENERAL,
                        log_callback=log_callback
                    )
                    
                    if result.success:
                        sent_count += 1
                        contact.ultimo_envio = result.timestamp
                        msg_label = "geral" if not welcome_msg else "geral (após boas-vindas)"
                        self._log(log_callback, f"[{idx+1}/{total}] {contact.nome}: Mensagem {msg_label} enviada")
                    else:
                        self._log(log_callback, f"[{idx+1}/{total}] {contact.nome}: Falha - {result.message}")
                else:
                    self._log(log_callback, f"[{idx+1}/{total}] {contact.nome}: Mensagem geral vazia, pulando")
                
                # Atualiza progresso
                if progress_callback:
                    progress_callback(idx + 1, total)
                    
            except Exception as e:
                error_msg = str(e)
                self._log(log_callback, f"[{idx+1}/{total}] {contact.nome}: Erro - {error_msg}")
                
                self.reports.append(SendReport(
                    contact_name=contact.nome,
                    contact_phone=contact.telemovel_normalizado,
                    status="erro",
                    message=error_msg,
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    message_type=MessageType.GENERAL
                ))
        
        self._log(log_callback, f"Envio concluído: {sent_count} mensagens enviadas com sucesso")
        return self.reports
    
    def _send_single_message(
        self,
        contact: Contact,
        message: str,
        message_type: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> SendResult:
        try:
            # Envia a mensagem via sender (WhatsApp ou SMS)
            result = self.sender.send_message(
                phone=contact.telemovel,
                message=message,
                log_callback=log_callback
            )
            
            # Cria relatório
            report = SendReport(
                contact_name=contact.nome,
                contact_phone=contact.telemovel_normalizado,
                status="sucesso" if result.success else "erro",
                message=f"Enviado ({message_type})" if result.success else (result.message or "Erro desconhecido"),
                timestamp=result.timestamp,
                message_type=message_type
            )
            
            self.reports.append(report)
            return result
            
        except Exception as e:
            # Em caso de exceção, cria relatório de erro
            error_msg = str(e)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            report = SendReport(
                contact_name=contact.nome,
                contact_phone=contact.telemovel_normalizado,
                status="erro",
                message=error_msg,
                timestamp=timestamp,
                message_type=message_type
            )
            
            self.reports.append(report)
            return SendResult(success=False, message=error_msg, timestamp=timestamp)
    
    def stop(self):
        self.is_sending = False
    
    def _log(self, log_callback: Optional[Callable[[str], None]], message: str):
        if log_callback:
            log_callback(message)
    
    def generate_and_open_report(
        self,
        method: str,
        base_dir: Path,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        if not self.reports:
            self._log(log_callback, "Nenhum relatório para gerar")
            return False
        
        try:
            # Cria arquivo de relatório
            report_file = ReportService.create_report_filename(method, base_dir)
            
            # Gera HTML
            success = ReportService.generate_html_report(
                reports=self.reports,
                method=method,
                output_file=report_file
            )
            
            if success:
                self._log(log_callback, f"Relatório criado: {report_file.name}")
                
                # Abre no navegador
                ReportService.open_report(report_file, log_callback)
                return True
            else:
                self._log(log_callback, "Erro ao gerar relatório")
                return False
                
        except Exception as e:
            self._log(log_callback, f"Erro ao gerar relatório: {e}")
            return False
