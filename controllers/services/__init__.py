from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .data_handler import DataHandler
    from .whatsapp_sender import WhatsAppSender
    from .sms_sender import SMS_Sender


def get_data_handler():
    from .data_handler import DataHandler
    from .contact_service import ContactService
    service = ContactService()
    return DataHandler(service)


def get_whatsapp_sender():
    from .whatsapp_sender import WhatsAppSender
    return WhatsAppSender()

def get_sms_sender():
    from .sms_sender import SMS_Sender
    return SMS_Sender()

__all__ = [
    'get_data_handler',
    'get_whatsapp_sender',
    'get_sms_sender'
]