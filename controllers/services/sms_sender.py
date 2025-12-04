import subprocess
import time
import threading
import re
import os
import zipfile
import urllib.request
import platform
from typing import Optional, Callable, Tuple, List
from dataclasses import dataclass
from datetime import datetime

@dataclass
class SMSResult:
    success: bool
    message: str
    phone_sent_to: str
    timestamp: str

@dataclass
class DeviceInfo:
    device_id: str
    model: str
    status: str
    connected_at: datetime

def get_adb_download_url() -> Tuple[str, str]:
    system = platform.system()

    match system:
        case "Windows":
            return (
                "https://dl.google.com/android/repository/platform-tools-latest-windows.zip",
                "platform-tools-windows.zip"
            )
        case "Darwin":  # macOS
            return (
                "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip",
                "platform-tools-darwin.zip"
            )
        case "Linux":
            return (
                "https://dl.google.com/android/repository/platform-tools-latest-linux.zip",
                "platform-tools-linux.zip"
            )
        case _:
            raise Exception(f"Sistema operacional não suportado: {system}")

def download_adb(
    destination_folder: str,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Tuple[bool, str, str]:
    try:
        # Cria pasta se não existir
        os.makedirs(destination_folder, exist_ok=True)
        
        # Obtém URL de download
        url, filename = get_adb_download_url()
        zip_path = os.path.join(destination_folder, filename)
        
        # Download com progresso
        def report_progress(block_num, block_size, total_size):
            if progress_callback:
                downloaded = block_num * block_size
                progress_callback(downloaded, total_size)
        
        urllib.request.urlretrieve(url, zip_path, reporthook=report_progress)
        
        # Extrai ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(destination_folder)
        
        # Remove ZIP
        os.remove(zip_path)
        
        # Determina caminho do ADB
        platform_tools_folder = os.path.join(destination_folder, "platform-tools")
        
        if platform.system() == "Windows":
            adb_path = os.path.join(platform_tools_folder, "adb.exe")
        else:
            adb_path = os.path.join(platform_tools_folder, "adb")
            # Torna executável no Linux/macOS
            os.chmod(adb_path, 0o755)
        
        # Verifica se funciona
        try:
            result = subprocess.run(
                [adb_path, "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return True, "ADB instalado com sucesso!", adb_path
            else:
                return False, "Erro ao verificar instalação do ADB", ""
        except Exception as e:
            return False, f"Erro ao verificar ADB: {e}", ""
            
    except Exception as e:
        return False, f"Erro ao instalar ADB: {e}", ""

class SMSSender:    
    def __init__(self, log_callback: Optional[Callable] = None):
        self.adb_path = "adb"
        self.device_connected = False
        self.device_id: Optional[str] = None
        self.device_info: Optional[DeviceInfo] = None
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._log_callback = log_callback
        self._on_device_connected: Optional[Callable] = None
        self._on_device_disconnected: Optional[Callable] = None
        self._last_known_devices: set = set()
    
    def _log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        print(formatted)
        if self._log_callback:
            self._log_callback(formatted)
    
    def set_log_callback(self, callback: Callable):
        self._log_callback = callback
    
    def set_device_callbacks(
        self, 
        on_connected: Optional[Callable] = None,
        on_disconnected: Optional[Callable] = None
    ):
        self._on_device_connected = on_connected
        self._on_device_disconnected = on_disconnected

    def _normalize_phone(self, phone: str) -> str:
        try:
            return "".join(filter(str.isdigit, str(phone)))[-9:]
        except:
            return ""
    
    def find_adb(self) -> Tuple[bool, str]:
        # Caminho onde o programa instala o ADB
        installed_adb_folder = os.path.join(os.path.expanduser("~"), ".android_tools", "platform-tools")
        installed_adb_windows = os.path.join(installed_adb_folder, "adb.exe")
        installed_adb_unix = os.path.join(installed_adb_folder, "adb")
        
        paths = [
            # Primeiro verifica o caminho onde o programa instalou
            installed_adb_windows if platform.system() == "Windows" else installed_adb_unix,
            # Depois verifica caminhos comuns
            "adb",
            r"C:\platform-tools\adb.exe",
            os.path.expanduser(r"~\AppData\Local\Android\Sdk\platform-tools\adb.exe"),
            os.path.expanduser(r"~\.android_tools\platform-tools\adb.exe"),
            "/usr/bin/adb",
            "/usr/local/bin/adb",
        ]
        
        for path in paths:
            try:
                result = subprocess.run(
                    [path, "version"], 
                    capture_output=True, 
                    text=True, 
                    timeout=5
                )
                if result.returncode == 0:
                    self.adb_path = path
                    version_line = result.stdout.split('\n')[0]
                    self._log(f"ADB encontrado: {path}")
                    self._log(f"   {version_line}")
                    return True, f"ADB: {path}"
            except FileNotFoundError:
                continue
            except Exception:
                continue
        
        self._log("ADB não encontrado no sistema")
        return False, "ADB não encontrado"
    
    def _get_connected_devices(self) -> List[Tuple[str, str]]:
        try:
            # Verifica se o adb_path é válido antes de executar
            if not self.adb_path:
                return []
            
            # Verifica se o arquivo existe (exceto se for apenas "adb" no PATH)
            if self.adb_path != "adb" and not os.path.exists(self.adb_path):
                return []
            
            result = subprocess.run(
                [self.adb_path, "devices"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            
            if result.returncode != 0:
                return []
            
            devices = []
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split('\t')
                if len(parts) >= 2:
                    device_id = parts[0]
                    status = parts[1]
                    devices.append((device_id, status))
            
            return devices
            
        except subprocess.TimeoutExpired:
            # Silencioso - não exibe log para timeout
            return []
        except FileNotFoundError:
            # Silencioso - ADB não encontrado
            return []
        except Exception as e:
            # Silencioso para outros erros - ADB provavelmente não está configurado
            return []
    
    def _get_device_model(self, device_id: str) -> str:
        try:
            result = subprocess.run(
                [self.adb_path, "-s", device_id, "shell", "getprop", "ro.product.model"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else "Dispositivo Android"
        except:
            return "Dispositivo Android"
    
    def _get_device_brand(self, device_id: str) -> str:
        try:
            result = subprocess.run(
                [self.adb_path, "-s", device_id, "shell", "getprop", "ro.product.brand"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except:
            return ""
    
    def _get_android_version(self, device_id: str) -> str:
        try:
            result = subprocess.run(
                [self.adb_path, "-s", device_id, "shell", "getprop", "ro.build.version.release"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except:
            return ""
    
    def check_device(self, log_callback: Optional[Callable] = None) -> Tuple[bool, str]:        
        # Usa callback passado ou o interno
        log_fn = log_callback or self._log
        
        devices = self._get_connected_devices()
        
        # Filtra dispositivos autorizados
        authorized = [(d, s) for d, s in devices if s == 'device']
        unauthorized = [(d, s) for d, s in devices if s == 'unauthorized']
        
        if authorized:
            device_id, status = authorized[0]
            self.device_id = device_id
            self.device_connected = True
            
            # Obtém informações detalhadas
            model = self._get_device_model(device_id)
            brand = self._get_device_brand(device_id)
            android_version = self._get_android_version(device_id)
            
            full_name = f"{brand} {model}".strip() if brand else model
            
            self.device_info = DeviceInfo(
                device_id=device_id,
                model=full_name,
                status=status,
                connected_at=datetime.now()
            )
            
            log_fn(f"Dispositivo Android conectado!")
            log_fn(f"   Modelo: {full_name}")
            log_fn(f"   Android: {android_version}")
            log_fn(f"   ID: {device_id}")
            
            return True, f"{full_name} ({device_id})"
        
        if unauthorized:
            device_id = unauthorized[0][0]
            log_fn(f"Dispositivo encontrado mas não autorizado: {device_id}")
            log_fn(f"   Aceite a conexão USB no telemóvel")
            return False, "Aceite a conexão USB no telemóvel"
        
        log_fn("Nenhum dispositivo Android encontrado")
        log_fn("   Verifique:")
        log_fn("   - Cabo USB conectado")
        log_fn("   - Depuração USB ativada")
        self.device_connected = False
        self.device_id = None
        self.device_info = None
        
        return False, "Nenhum dispositivo encontrado"
    
    def start_device_monitoring(self, interval: float = 2.0):
        if self._monitoring:
            self._log("Monitoramento já está ativo")
            return
        
        self._monitoring = True
        self._log("Iniciando monitoramento de dispositivos...")
        
        def monitor_loop():
            while self._monitoring:
                try:
                    devices = self._get_connected_devices()
                    current_device_ids = {d for d, s in devices if s == 'device'}
                    
                    # Detecta novos dispositivos
                    new_devices = current_device_ids - self._last_known_devices
                    for device_id in new_devices:
                        self._handle_device_connected(device_id)
                    
                    # Detecta dispositivos removidos
                    removed_devices = self._last_known_devices - current_device_ids
                    for device_id in removed_devices:
                        self._handle_device_disconnected(device_id)
                    
                    # Verifica dispositivos não autorizados
                    unauthorized = [d for d, s in devices if s == 'unauthorized']
                    for device_id in unauthorized:
                        if device_id not in self._last_known_devices:
                            self._log(f"Dispositivo detectado: {device_id}")
                            self._log(f"   Por favor, aceite a conexão USB no telemóvel")
                    
                    self._last_known_devices = current_device_ids
                    
                except Exception as e:
                    self._log(f"Erro no monitoramento: {e}")
                
                time.sleep(interval)
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        # Faz uma verificação inicial
        self.check_device()
    
    def _handle_device_connected(self, device_id: str):
        model = self._get_device_model(device_id)
        brand = self._get_device_brand(device_id)
        android_version = self._get_android_version(device_id)
        
        full_name = f"{brand} {model}".strip() if brand else model
        
        self._log("Dispositivo Android conectado!")
        self._log(f"   Modelo: {full_name}")
        self._log(f"   Android: {android_version}")
        self._log(f"   ID: {device_id}")
        
        self.device_id = device_id
        self.device_connected = True
        self.device_info = DeviceInfo(
            device_id=device_id,
            model=full_name,
            status='device',
            connected_at=datetime.now()
        )
        
        if self._on_device_connected:
            self._on_device_connected(self.device_info)
    
    def _handle_device_disconnected(self, device_id: str):
        self._log(f"O dispositivo foi desconectado: {device_id}")
        
        if self.device_id == device_id:
            self.device_id = None
            self.device_connected = False
            old_info = self.device_info
            self.device_info = None
            
            if self._on_device_disconnected:
                self._on_device_disconnected(old_info)
    
    def stop_device_monitoring(self):
        if self._monitoring:
            self._log("Parando monitoramento de dispositivos...")
            self._monitoring = False
            if self._monitor_thread:
                self._monitor_thread.join(timeout=5)
                self._monitor_thread = None
    
    def wait_for_device(self, timeout: int = 60) -> bool:
        self._log(f"Aguardando dispositivo Android (timeout: {timeout}s)...")
        self._log("   Conecte o telemóvel via USB e ative Depuração USB")
        
        start_time = time.time()
        check_count = 0
        
        while time.time() - start_time < timeout:
            check_count += 1
            devices = self._get_connected_devices()
            
            # Mostra progresso a cada 5 verificações
            if check_count % 5 == 0:
                elapsed = int(time.time() - start_time)
                self._log(f"   Procurando... ({elapsed}s)")
            
            # Verifica autorizados
            authorized = [(d, s) for d, s in devices if s == 'device']
            if authorized:
                self._handle_device_connected(authorized[0][0])
                return True
            
            # Verifica não autorizados
            unauthorized = [(d, s) for d, s in devices if s == 'unauthorized']
            if unauthorized:
                self._log(f"   Dispositivo detectado - aceite a conexão USB")
            
            time.sleep(2)
        
        self._log("Timeout - nenhum dispositivo conectado")
        return False
    
    def _run_adb(self, *args) -> subprocess.CompletedProcess:
        cmd = [self.adb_path]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(args)
        # errors='ignore' para evitar crash em caracteres estranhos
        return subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=30,
            encoding='utf-8',
            errors='ignore'
        )
    
    def _normalize_phone_for_sms(self, phone: str) -> str:
        return phone.replace(' ', '').replace('-', '')
    
    def _get_screen_resolution(self) -> Tuple[int, int]:
        try:
            result = self._run_adb("shell", "wm", "size")
            # Output: "Physical size: 1080x2400"
            if result.returncode == 0:
                match = re.search(r'(\d+)x(\d+)', result.stdout)
                if match:
                    width = int(match.group(1))
                    height = int(match.group(2))
                    return width, height
        except:
            pass
        return 1080, 2400  # Default comum
    
    def check_for_stop_response(self, phone: str, log_callback: Optional[Callable] = None) -> bool:
        try:
            target_norm = self._normalize_phone(phone)
            
            # Query só mensagens recebidas (inbox) com projection
            result = self._run_adb(
                "shell", "content", "query",
                "--uri", "content://sms/inbox",
                "--projection", "address,body",
                "--sort", "date DESC"
            )
            
            if result.returncode != 0:
                return False
            
            for line in result.stdout.splitlines():
                if "address=" not in line:
                    continue
                
                try:
                    # Extrai address e body usando split
                    after_address = line.split("address=")[1]
                    parts = after_address.split(", body=", 1)
                    
                    if len(parts) < 2:
                        continue
                    
                    addr_raw = parts[0].strip()
                    body_content = parts[1].strip()
                    
                    # Verifica se é do número alvo
                    if self._normalize_phone(addr_raw) != target_norm:
                        continue
                    
                    # Verifica se a mensagem é "PARAR"
                    if body_content.upper().strip() == 'PARAR':
                        msg = f"{phone} respondeu PARAR"
                        self._log(msg)
                        if log_callback:
                            log_callback(msg)
                        return True
                
                except Exception:
                    continue
            
            return False
            
        except Exception as e:
            self._log(f"Erro ao verificar PARAR: {e}")
            return False
    
    def _count_sent_sms(self) -> int:
        try:
            result = self._run_adb(
                "shell",
                "content query --uri content://sms/sent"
            )
            if result.returncode == 0:
                # Conta linhas que começam com "Row:" (cada linha é um SMS)
                count = result.stdout.count("Row:")
                self._log(f"   Debug: Contagem SMS = {count}")
                return count
            self._log(f"   Debug: Erro ao contar SMS (returncode={result.returncode})")
            return -1  # Retorna -1 para indicar erro
        except Exception as e:
            self._log(f"   Debug: Exceção ao contar SMS: {e}")
            return -1
    
    def get_last_messages(self, phone: str, limit: int = 10) -> list:
        target_norm = self._normalize_phone(phone)
        self._log(f"Procurando mensagens para: {phone} (Norm: {target_norm})")
        
        try:
            # Usa projection para output mais limpo
            result = self._run_adb(
                "shell", "content", "query",
                "--uri", "content://sms",
                "--projection", "address,body,type,date",
                "--sort", "date DESC"
            )
            
            if result.returncode != 0:
                self._log(f"   Erro na query: {result.stderr}")
                return []
            
            messages = []
            
            for line in result.stdout.splitlines():
                if "address=" not in line:
                    continue
                
                try:
                    # Extrai address: split em "address=" e depois em ", body="
                    after_address = line.split("address=")[1]
                    parts = after_address.split(", body=", 1)
                    
                    if len(parts) < 2:
                        continue
                    
                    addr_raw = parts[0].strip()
                    rest = parts[1]
                    
                    # Verifica se é o número alvo
                    if self._normalize_phone(addr_raw) != target_norm:
                        continue
                    
                    # Extrai body (até ao próximo campo ou fim)
                    body_content = rest
                    for delimiter in [", type=", ", date="]:
                        if delimiter in body_content:
                            body_content = body_content.split(delimiter)[0]
                            break
                    body_content = body_content.strip()
                    
                    msg_data = {
                        'address': addr_raw,
                        'body': body_content if body_content else "(sem conteúdo)",
                        'type': 'desconhecido',
                        'date': 'desconhecida'
                    }
                    
                    # Tenta extrair type (1=recebida, 2=enviada)
                    type_match = re.search(r'type=(\d+)', line)
                    if type_match:
                        msg_type = type_match.group(1)
                        msg_data['type'] = 'enviada' if msg_type == '2' else 'recebida'
                    
                    # Tenta extrair data
                    date_match = re.search(r'date=(\d+)', line)
                    if date_match:
                        try:
                            timestamp = int(date_match.group(1)) / 1000
                            msg_data['date'] = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            pass
                    
                    messages.append(msg_data)
                    self._log(f"   [{msg_data['type']}] {msg_data['body'][:50]}...")
                    
                    if len(messages) >= limit:
                        break
                
                except Exception:
                    continue  # Pula linhas mal formatadas
            
            self._log(f"   Encontradas {len(messages)} mensagens de/para {phone}")
            return messages
            
        except Exception as e:
            self._log(f"   Exceção ao buscar mensagens: {e}")
            import traceback
            self._log(f"   {traceback.format_exc()}")
            return []
        
    def _send_sms_direct(self, phone: str, message: str) -> Tuple[bool, str]:
        try:
            # Mantém \n como quebra de linha
            message_escaped = message.replace('"', '\\"').replace("'", "\\'").replace('$', '\\$').replace('`', '\\`')
            phone_clean = self._normalize_phone_for_sms(phone)
            
            count_before = self._count_sent_sms()
            self._log(f"   SMS enviados antes: {count_before}")
            
            self._log(f"   A abrir aplicação de mensagens...")
            
            result = self._run_adb(
                "shell",
                f'am start -a android.intent.action.SENDTO -d sms:{phone_clean} --es sms_body "{message_escaped}" --ez exit_on_sent true'
            )
            
            if result.returncode != 0:
                return False, f"Erro ao abrir app: {result.stderr}"
            
            # Aguarda a app abrir completamente
            self._log(f"   Aguardando app abrir...")
            time.sleep(3)
            
            # Tentativa 1: Clique por coordenadas (canto direito)
            self._log(f"   Tentativa 1: Clique no canto direito...")
            width, height = self._get_screen_resolution()
            x = int(width * 0.92)
            y = int(height * 0.96)
            self._run_adb("shell", "input", "tap", str(x), str(y))
            time.sleep(2)
            
            # Verifica se enviou
            count_after = self._count_sent_sms()
            if count_after > count_before:
                self._log(f"   SMS enviado! ({count_after - count_before} novo)")
                self._run_adb("shell", "input", "keyevent", "3")  # Volta para home
                return True, f"SMS enviado ({count_after - count_before} SMS)"
            
            # Tentativa 2: Clique mais acima
            self._log(f"   Tentativa 1 falhou. Tentando posição 2...")
            x = int(width * 0.90)
            y = int(height * 0.92)
            self._run_adb("shell", "input", "tap", str(x), str(y))
            time.sleep(2)
            
            count_after = self._count_sent_sms()
            if count_after > count_before:
                self._log(f"   SMS enviado! ({count_after - count_before} novo)")
                self._run_adb("shell", "input", "keyevent", "3")  # Volta para home
                return True, f"SMS enviado ({count_after - count_before} SMS)"
            
            # Tentativa 3: Clique no centro direito
            self._log(f"   Tentativa 2 falhou. Tentando posição 3...")
            x = int(width * 0.85)
            y = int(height * 0.94)
            self._run_adb("shell", "input", "tap", str(x), str(y))
            time.sleep(2)
            
            count_after = self._count_sent_sms()
            if count_after > count_before:
                self._log(f"   SMS enviado! ({count_after - count_before} novo)")
                self._run_adb("shell", "input", "keyevent", "3")  # Volta para home
                return True, f"SMS enviado ({count_after - count_before} SMS)"
            
            # Se chegou aqui, nenhuma tentativa funcionou
            self._log(f"   Todas as 3 tentativas falharam")
            self._run_adb("shell", "input", "keyevent", "3")  # Volta para home
            return False, "Nenhuma tentativa conseguiu enviar o SMS"
            
        except Exception as e:
            # Garante que volta para home
            try:
                self._run_adb("shell", "input", "keyevent", "3")
            except:
                pass
            return False, f"Erro: {e}"

    def send_message(
        self, 
        phone: str, 
        message: str, 
        log_callback: Optional[Callable] = None
    ) -> SMSResult:
        return self._send_sms_direct_with_verification(phone, message, log_callback)
    
    def _send_sms_direct_with_verification(
        self,
        phone: str,
        message: str,
        log_callback: Optional[Callable] = None
    ) -> SMSResult:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Converte \n literal em quebras de linha reais
        message = message.replace('\\n', '\n')
    
        if not self.device_connected:
            self._log("Erro: Dispositivo não conectado")
            return SMSResult(False, "Dispositivo não conectado", "", timestamp)
        
        self._log(f"A enviar SMS para {phone}...")
        if log_callback:
            log_callback(f"A enviar SMS para {phone}...")
        
        # Envia usando método direto
        success, method_msg = self._send_sms_direct(phone, message)
        
        if success:
            msg = f"SMS enviada para {phone}"
            self._log(msg)
            if log_callback:
                log_callback(msg)
            return SMSResult(True, method_msg, phone, timestamp)
        else:
            error_msg = f"Erro ao enviar: {method_msg}"
            self._log(error_msg)
            if log_callback:
                log_callback(error_msg)
            return SMSResult(False, method_msg, "", timestamp)
    
    def close(self):
        self.stop_device_monitoring()

if __name__ == "__main__":
    print("Teste na leitura de mensagens\n")
    # Cria instância do sender
    sender = SMSSender()
    
    try:
        # Procura ADB
        adb_found, adb_msg = sender.find_adb()
        if not adb_found:
            print("Erro: ADB não encontrado")
            exit(1)
        
        # Verifica dispositivo
        success, msg = sender.check_device()
        if not success:
            print(f"Erro: {msg}")
            exit(1)
        
        if sender.device_info:
            print(f"Conectado ao dispositivo: {sender.device_info.model}\n")
        
        # Teste de busca de mensagens
        phone = input("Introduza o número de telefone para buscar mensagens (em formato 900 800 100): ")
        print(f"\nProcurando mensagens de {phone}...")
        messages = sender.get_last_messages(phone, limit=5)
        
        if messages:
            print(f"\nEncontradas {len(messages)} mensagens:\n")
            for i, msg in enumerate(messages, 1):
                print(f"  {i}. [{msg.get('type', '?')}] [{msg.get('date', '?')}]")
                print(f"      {msg.get('body', 'sem conteúdo')[:80]}")
                print()
        else:
            print(f"\nNenhuma mensagem encontrada para {phone}")
        
        # Teste com formato internacional
        phone = input("Introduza o número de telefone para buscar mensagens (em formato +351900800100): ")
        print(f"\nProcurando mensagens de {phone}...")
        messages = sender.get_last_messages(phone, limit=5)
        
        if messages:
            print(f"\nEncontradas {len(messages)} mensagens:\n")
            for i, msg in enumerate(messages, 1):
                print(f"  {i}. [{msg.get('type', '?')}] [{msg.get('date', '?')}]")
                print(f"      {msg.get('body', 'sem conteúdo')[:80]}")
                print()
        else:
            print(f"\nNenhuma mensagem encontrada para {phone}")
    finally:
        sender.close()
        print("\nTeste concluído!")