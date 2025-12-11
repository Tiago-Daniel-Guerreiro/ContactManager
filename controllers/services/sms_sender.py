import re
import time
from typing import Optional, Callable, List, Generator
from datetime import datetime
from dataclasses import dataclass

from utils.logger import get_logger
from models.contact import Contact
from models.Result import Result, statusType, messageType
from controllers.services.ADB_Manager import ADB_Manager, DeviceInfo

SOURCE = "SMS_Sender"

@dataclass
class SMSMessage:
    address: str
    address_normalized: str
    body: str
    msg_type: str  # 'sent', 'received', 'unknown'
    timestamp: Optional[datetime] = None
    raw_date: Optional[int] = None

class SMS_Sender:    
    def __init__(self):
        self.adb_manager = ADB_Manager()
        self.logger = get_logger()
        
    @property
    def device_connected(self) -> bool:
        return self.adb_manager.device_connected
    
    @property
    def device_info(self) -> Optional[DeviceInfo]:
        return self.adb_manager.device_info
    
    @property
    def device_id(self) -> Optional[str]:
        return self.adb_manager.device_id
        
    def set_device_callbacks(
        self, 
        on_connected: Optional[Callable[[DeviceInfo], None]] = None,
        on_disconnected: Optional[Callable[[Optional[DeviceInfo]], None]] = None
    ):
        self.adb_manager.set_device_callbacks(on_connected, on_disconnected)

    def find_adb(self) -> bool:
        return self.adb_manager.find_adb()

    def check_device(self) -> bool:
        return self.adb_manager.check_device()

    def start_device_monitoring(self, interval: float = 2.0):
        self.adb_manager.start_device_monitoring(interval)

    def stop_device_monitoring(self):
        self.adb_manager.stop_device_monitoring()

    def wait_for_device(self, timeout: int = 60) -> bool:
        return self.adb_manager.wait_for_device(timeout)

    def get_device_info_external(self, device_id: str):
        model, brand, android_version, full_name = self.adb_manager.get_device_full_info(device_id)
        self.logger.info(f"Dispositivo: {full_name}", source=SOURCE)
        return model, brand, full_name
    
    def _normalize_phone_for_sms(self, phone: str) -> str:
        return phone.replace(' ', '').replace('-', '')
    
    def _get_screen_resolution(self):
        try:
            result = self.adb_manager.run_adb("shell", "wm", "size")
            if result.returncode == 0:
                match = re.search(r'(\d+)x(\d+)', result.stdout)
                if match:
                    width = int(match.group(1))
                    height = int(match.group(2))
                    self.logger.debug(f"Resolução: {width}x{height}", source=SOURCE)
                    return width, height
        except Exception as e:
            self.logger.error("Erro ao obter resolução", error=e, source=SOURCE)
        
        self.logger.warning("Usando resolução padrão 1080x2400", source=SOURCE)
        return 1080, 2400
        
    def _query_sms(
        self, 
        uri: str = "content://sms", 
        projection: str = "address,body,type,date"
    ) -> Optional[str]:
        try:
            result = self.adb_manager.run_adb(
                "shell", "content", "query",
                "--uri", uri,
                "--projection", projection,
                "--sort", "date DESC"
            )
            
            if result.returncode != 0:
                self.logger.warning(
                    f"Falha na query SMS: {result.stderr}", 
                    source=SOURCE
                )
                return None
                
            return result.stdout
            
        except Exception as e:
            self.logger.error("Erro na query SMS", error=e, source=SOURCE)
            return None
    
    def _parse_sms_line(self, line: str) -> Optional[SMSMessage]:
        if "address=" not in line:
            return None
        
        try:
            after_address = line.split("address=")[1]
            parts = after_address.split(", body=", 1)
            
            if len(parts) < 2:
                return None
            
            addr_raw = parts[0].strip()
            addr_normalized = self._normalize_phone_for_sms(
                Contact.normalize_phone(addr_raw)
            )
            
            # Extrair body (remover campos seguintes)
            body_content = parts[1]
            for delimiter in [", type=", ", date="]:
                if delimiter in body_content:
                    body_content = body_content.split(delimiter)[0]
                    break
            body_content = body_content.strip()
            
            # Extrair tipo
            msg_type = 'unknown'
            type_match = re.search(r'type=(\d+)', line)
            if type_match:
                type_code = type_match.group(1)
                msg_type = 'sent' if type_code == '2' else 'received'
            
            # Extrair data
            timestamp = None
            raw_date = None
            date_match = re.search(r'date=(\d+)', line)
            if date_match:
                try:
                    raw_date = int(date_match.group(1))
                    timestamp = datetime.fromtimestamp(raw_date / 1000)
                except (ValueError, OSError):
                    pass
            
            return SMSMessage(
                address=addr_raw,
                address_normalized=addr_normalized,
                body=body_content,
                msg_type=msg_type,
                timestamp=timestamp,
                raw_date=raw_date
            )
            
        except Exception:
            return None
    
    def _iter_sms_messages(
        self, 
        uri: str = "content://sms",
        projection: str = "address,body,type,date",
        phone_filter: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Generator[SMSMessage, None, None]:
        output = self._query_sms(uri, projection)
        if not output:
            return
        
        target_norm = None
        if phone_filter:
            target_norm = self._normalize_phone_for_sms(
                Contact.normalize_phone(phone_filter)
            )
        
        count = 0
        for line in output.splitlines():
            msg = self._parse_sms_line(line)
            
            if msg is None:
                continue
            
            # Aplicar filtro de telefone se especificado
            if target_norm and msg.address_normalized != target_norm:
                continue
            
            yield msg
            count += 1
            
            if limit and count >= limit:
                break
    
    def check_for_stop_response(
        self, 
        phone: str, 
        log_callback: Optional[Callable] = None
    ) -> bool:
        try:
            for msg in self._iter_sms_messages(
                uri="content://sms/inbox",
                projection="address,body",
                phone_filter=phone
            ):
                if msg.body.upper().strip() == 'PARAR':
                    log_msg = f"{phone} respondeu PARAR"
                    self.logger.info(log_msg, source=SOURCE)
                    if log_callback:
                        log_callback(log_msg)
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error("Erro ao verificar PARAR", error=e, source=SOURCE)
            return False
    
    def get_last_messages(self, phone: str, limit: int = 10) -> List[SMSMessage]:
        target_norm = Contact.normalize_phone(phone)
        self.logger.debug(
            f"Procurando mensagens para: {phone} (Norm: {target_norm})", 
            source=SOURCE
        )
    
        messages: List[SMSMessage] = []
        
        try:
            for msg in self._iter_sms_messages(phone_filter=phone, limit=limit):
                messages.append(msg)
                
                # Log da mensagem
                msg_type_pt = 'enviada' if msg.msg_type == 'sent' else 'recebida'
                date_str = (
                    msg.timestamp.strftime('%Y-%m-%d %H:%M:%S') 
                    if msg.timestamp else 'desconhecida'
                )
                self.logger.info(
                    f"   [{msg_type_pt}] [{date_str}] {msg.body[:50]}...", 
                    source=SOURCE
                )
            
            self.logger.info(
                f"   Encontradas {len(messages)} mensagens de/para {phone}", 
                source=SOURCE
            )
            
        except Exception as e:
            self.logger.error(
                f"Exceção ao buscar mensagens: {e}", 
                error=e, 
                source=SOURCE
            )
        
        return messages
        
    def _count_sent_sms(self) -> int:
        try:
            result = self.adb_manager.run_adb(
                "shell",
                "content query --uri content://sms/sent"
            )
            if result.returncode == 0:
                count = result.stdout.count("Row:")
                self.logger.debug(f"Contagem SMS = {count}", source=SOURCE)
                return count
            self.logger.warning(
                f"Erro ao contar SMS (returncode={result.returncode})", 
                source=SOURCE
            )
            return -1
        except Exception as e:
            self.logger.error("Exceção ao contar SMS", error=e, source=SOURCE)
            return -1
    
    def _send_sms(self, phone: str, message: str) -> bool:
        try:
            message_escaped = (
                message
                .replace('"', '\\"')
                .replace("'", "\\'")
                .replace('$', '\\$')
                .replace('`', '\\`')
            )
            phone_clean = self._normalize_phone_for_sms(phone)
            
            count_before = self._count_sent_sms()
            self.logger.info(f"SMS enviados antes: {count_before}", source=SOURCE)
            
            self.logger.info("A abrir aplicação de mensagens...", source=SOURCE)
            
            result = self.adb_manager.run_adb(
                "shell",
                f'am start -a android.intent.action.SENDTO -d sms:{phone_clean} '
                f'--es sms_body "{message_escaped}" --ez exit_on_sent true'
            )
            
            if result.returncode != 0:
                self.logger.error(f"Erro ao abrir app: {result.stderr}", source=SOURCE)
                return False
            
            self.logger.info("Aguardando app abrir...", source=SOURCE)
            time.sleep(3)
            
            width, height = self._get_screen_resolution()
            
            # Tentativas de clique em diferentes posições do botão enviar
            tap_positions = [
                (0.92, 0.96, "Tentativa 1: Clique no canto direito..."),
                (0.90, 0.92, "Tentativa 2: Posição alternativa..."),
                (0.85, 0.94, "Tentativa 3: Última posição...")
            ]
            
            for x_ratio, y_ratio, log_msg in tap_positions:
                self.logger.info(log_msg, source=SOURCE)
                x = int(width * x_ratio)
                y = int(height * y_ratio)
                self.adb_manager.run_adb("shell", "input", "tap", str(x), str(y))
                time.sleep(2)
                
                count_after = self._count_sent_sms()
                if count_after > count_before:
                    self.logger.info(
                        f"SMS enviado! ({count_after - count_before} novo)", 
                        source=SOURCE
                    )
                    self.adb_manager.run_adb("shell", "input", "keyevent", "3")
                    return True
                
                self.logger.warning(f"{log_msg.split(':')[0]} falhou.", source=SOURCE)
            
            self.logger.warning("Todas as tentativas falharam", source=SOURCE)
            self.adb_manager.run_adb("shell", "input", "keyevent", "3")
            return False
            
        except Exception as e:
            try:
                self.adb_manager.run_adb("shell", "input", "keyevent", "3")
            except Exception:
                pass
            self.logger.error("Erro no envio SMS", error=e, source=SOURCE)
            return False

    def send_message(
        self, 
        phone: str, 
        message: str,
        contact_name: str = "",
        message_type: messageType = messageType.GENERAL
    ) -> Result:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = message.replace('\\n', '\n')
        resultado = Result(
            contact_name=contact_name,
            contact_phone=phone,
            status=statusType.ERROR,
            message=message,
            timestamp=timestamp,
            message_type=message_type
        )
        
        if not self.device_connected:
            self.logger.warning("O Dispositivo não está conectado", source=SOURCE)
            return resultado
        
        self.logger.debug(f"A enviar SMS para {phone}...", source=SOURCE)
        success = self._send_sms(phone, message)
        
        if success:
            self.logger.debug(f"SMS enviada para {phone}", source=SOURCE)
            resultado.status = statusType.SUCCESS
            return resultado
        else:
            self.logger.debug(f"Erro ao enviar SMS para {phone}", source=SOURCE)
            return resultado
    
    def close(self):
        self.adb_manager.close()

if __name__ == "__main__":
    print("Teste na leitura de mensagens\n")
    sender = SMS_Sender()
    
    try:
        adb_found = sender.find_adb()
        if not adb_found:
            print("Erro: ADB não encontrado")
            exit(1)
        
        success = sender.check_device()
        if not success:
            print("Erro: Não foi possível conectar ao dispositivo")
            exit(1)
        
        if sender.device_info:
            print(f"Conectado ao dispositivo: {sender.device_info.model}\n")
        
        phone = input("Introduza o número de telefone (formato 900 800 100): ")
        print(f"\nProcurando mensagens de {phone}...")
        sender.get_last_messages(phone, limit=5)
        
        phone = input("Introduza o número de telefone (formato +351900800100): ")
        print(f"\nProcurando mensagens de {phone}...")
        sender.get_last_messages(phone, limit=5)
        
    finally:
        sender.close()
        print("\nTeste concluído!")