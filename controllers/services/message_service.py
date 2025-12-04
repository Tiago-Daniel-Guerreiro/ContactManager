from typing import Tuple, Optional
from models.contact import Contact


class MessageType:
    WELCOME = 'boas-vindas'
    GENERAL = 'geral'


class MessageService:
    @staticmethod
    def prepare_message(
        contact: Contact,
        message_template: str,
        welcome_template: Optional[str] = None,
        send_all_mode: bool = False
    ) -> Tuple[Optional[str], Optional[str]]:
        # Verifica se é primeiro contacto
        is_first_contact = contact.verificar_enviar_boas_vindas(ignore_selection=send_all_mode)
        
        # Prepara mensagem de boas-vindas (se aplicável)
        welcome_message = None
        if is_first_contact and welcome_template and welcome_template.strip():
            welcome_message = MessageService.personalize_message(welcome_template, contact)
        
        # Prepara mensagem geral (sempre enviada)
        general_message = MessageService.personalize_message(message_template, contact)
        
        return welcome_message, general_message
    
    @staticmethod
    def personalize_message(template: str, contact: Contact) -> str:
        # Converte \n literal em quebra de linha real
        message = template.replace('\\n', '\n')
        
        # Substitui placeholders
        message = message.replace('{nome}', contact.nome)
        
        return message
    
    @staticmethod
    def get_message_type_label(is_welcome: bool) -> str:
        return MessageType.WELCOME if is_welcome else MessageType.GENERAL
    
    @staticmethod
    def validate_templates(general_template: str, welcome_template: Optional[str] = None) -> Tuple[bool, str]:
        if not general_template or not general_template.strip():
            return False, "Mensagem geral é obrigatória"
        
        # Template de boas-vindas é opcional, não precisa validar
        
        return True, ""
