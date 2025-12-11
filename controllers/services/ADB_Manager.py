import subprocess
import time
import threading
import os
import zipfile
import urllib.request
from utils.environment import platform_is_windows, platform_is_mac, platform_is_linux
from typing import Optional, Callable, Tuple, List
from dataclasses import dataclass
from datetime import datetime
from utils.logger import get_logger

SOURCE = "ADB_Manager"

@dataclass
class DeviceInfo:
    device_id: str
    model: str
    status: str
    connected_at: datetime

class ADB_Manager:
    def __init__(self):
        self.logger = get_logger()
        self.adb_path: str = "adb"
        self.device_id: Optional[str] = None
        self.device_connected: bool = False
        self.device_info: Optional[DeviceInfo] = None
        self._monitoring: bool = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._on_device_connected: Optional[Callable[[DeviceInfo], None]] = None
        self._on_device_disconnected: Optional[Callable[[Optional[DeviceInfo]], None]] = None
        self._last_known_devices: set = set()
        
    def set_device_callbacks(
        self, 
        on_connected: Optional[Callable[[DeviceInfo], None]] = None,
        on_disconnected: Optional[Callable[[Optional[DeviceInfo]], None]] = None
    ):
        self._on_device_connected = on_connected
        self._on_device_disconnected = on_disconnected

    def get_adb_download_url(self) -> Tuple[str, str]:
        if platform_is_windows():
            return (
                "https://dl.google.com/android/repository/platform-tools-latest-windows.zip",
                "platform-tools-windows.zip"
            )
        if platform_is_mac():
            return (
                "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip",
                "platform-tools-darwin.zip"
            )
        if platform_is_linux():
            return (
                "https://dl.google.com/android/repository/platform-tools-latest-linux.zip",
                "platform-tools-linux.zip"
            )
        
        raise Exception(f"Sistema operacional não suportado")

    def download_adb(
        self,
        destination_folder: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool | Tuple[bool, str]:
        try:
            os.makedirs(destination_folder, exist_ok=True)
            url, filename = self.get_adb_download_url()
            zip_path = os.path.join(destination_folder, filename)

            def report_progress(block_num, block_size, total_size):
                if progress_callback:
                    downloaded = block_num * block_size
                    progress_callback(downloaded, total_size)

            urllib.request.urlretrieve(url, zip_path, reporthook=report_progress)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(destination_folder)

            os.remove(zip_path)

            platform_tools_folder = os.path.join(destination_folder, "platform-tools")
            if platform_is_windows():
                adb_path = os.path.join(platform_tools_folder, "adb.exe")
            else:
                adb_path = os.path.join(platform_tools_folder, "adb")
                os.chmod(adb_path, 0o755)

            try:
                result = subprocess.run(
                    [adb_path, "version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    self.logger.info(f"ADB instalado em: {adb_path}", source=SOURCE)
                    self.adb_path = adb_path
                    return True, adb_path
                else:
                    self.logger.error(f"Erro ao verificar instalação do ADB: {result.stderr}", source=SOURCE)
                    return False
            except Exception as e:
                self.logger.error(f"Erro ao verificar ADB ", error=e, source=SOURCE)
                return False
        except Exception as e:
            self.logger.error(f"Erro ao instalar ADB ", error=e, source=SOURCE)
            return False

    def find_adb(self) -> bool:
        found = False
        try:
            home_dir = os.path.expanduser("~")
            dest_folder = os.path.join(home_dir, ".android_tools")
            result = self.download_adb(dest_folder)
            if isinstance(result, tuple) and result[0]:
                self.adb_path = result[1]
                found = True
            elif result is True:
                self.adb_path = os.path.join(dest_folder, "platform-tools", "adb.exe" if platform_is_windows() else "adb")
                found = True
        except Exception:
            pass
        if not found:
            self.logger.warning("ADB não encontrado ou não foi possível baixar.", source=SOURCE)
        return found

    def _get_creation_flags(self) -> int:
        return subprocess.CREATE_NO_WINDOW if platform_is_windows() else 0

    def run_adb(self, *args, timeout: int = 30) -> subprocess.CompletedProcess:
        cmd = [self.adb_path]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(args)
        return subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            encoding='utf-8',
            errors='ignore',
            creationflags=self._get_creation_flags()
        )

    def get_connected_devices(self) -> List[Tuple[str, str]]:
        if not self.adb_path:
            return []
        if self.adb_path != "adb" and not os.path.exists(self.adb_path):
            return []
        try:
            result = subprocess.run(
                [self.adb_path, "devices"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=self._get_creation_flags()
            )
            if result.returncode != 0:
                return []
            devices = []
            lines = result.stdout.strip().split('\n')[1:]
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
            self.logger.warning("Timeout ao executar 'adb devices'", source=SOURCE)
        except FileNotFoundError:
            self.logger.warning("ADB não encontrado ao listar dispositivos", source=SOURCE)
        except Exception as e:
            self.logger.error("Erro ao listar dispositivos ADB", error=e, source=SOURCE)
        return []

    def _get_device_property(self, device_id: str, property_name: str, default_value: str = "") -> str:
        try:
            result = subprocess.run(
                [self.adb_path, "-s", device_id, "shell", "getprop", property_name],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=self._get_creation_flags()
            )
            if result.returncode == 0:
                value = result.stdout.strip()
                return value if value else default_value
        except Exception as e:
            self.logger.debug(f"Erro ao obter propriedade {property_name}: {e}", source=SOURCE)
        return default_value

    def get_device_full_info(self, device_id: str) -> Tuple[str, str, str, str]:
        model = self._get_device_property(device_id, "ro.product.model", "Dispositivo Android")
        brand = self._get_device_property(device_id, "ro.product.brand", "")
        android_version = self._get_device_property(device_id, "ro.build.version.release", "")
        full_name = f"{brand} {model}".strip() if brand else model
        return model, brand, android_version, full_name

    def create_device_info(self, device_id: str, status: str = 'device') -> DeviceInfo:
        model, brand, android_version, full_name = self.get_device_full_info(device_id)
        return DeviceInfo(
            device_id=device_id,
            model=full_name,
            status=status,
            connected_at=datetime.now()
        )

    def check_device(self) -> bool:
        devices = self.get_connected_devices()
        device = None

        for (device_id, status) in devices:
            if status == 'unauthorized':
                self.logger.warning(f"Dispositivo encontrado mas não autorizado: {device_id}", source=SOURCE)
                self.logger.warning("   Aceite a conexão USB no telemóvel", source=SOURCE)
                return False
            if status == 'device':
                if device is None:
                    device = device_id
                else:
                    self.logger.warning("O programa não suporta múltiplos dispositivos conectados", source=SOURCE)
            else:
                self.logger.warning("Nenhum dispositivo Android encontrado", source=SOURCE)
                return False
        
        if device is None:
            return False

        self.device_id = device
        self.device_connected = True
        self.device_info = self.create_device_info(device, 'device')
        model, brand, android_version, full_name = self.get_device_full_info(device)
        
        self.logger.info("Dispositivo Android conectado!", source=SOURCE)
        self.logger.debug(f"   Modelo: {full_name}", source=SOURCE)
        self.logger.debug(f"   Android: {android_version}", source=SOURCE)
        self.logger.debug(f"   ID: {device}", source=SOURCE)
        
        return True

    def start_device_monitoring(self, interval: float = 2.0):
        if self._monitoring:
            self.logger.warning("Monitoramento já está ativo", source=SOURCE)
            return
        
        self._monitoring = True
        self.logger.info("Iniciando monitoramento de dispositivos...", source=SOURCE)
        
        def monitor_loop():
            while self._monitoring:
                try:
                    devices = self.get_connected_devices()
                    current_device_ids = set()
                    for device_id, status in devices:
                        if status == 'device':
                            current_device_ids.add(device_id)

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
                            self.logger.info(f"Dispositivo detectado: {device_id}", source=SOURCE)
                            self.logger.info("   Por favor, aceite a conexão USB no telemóvel", source=SOURCE)
                    
                    self._last_known_devices = current_device_ids
                    
                except Exception as e:
                    self.logger.error("Erro no monitoramento", error=e, source=SOURCE)
                
                time.sleep(interval)
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
        self.check_device()

    def _handle_device_connected(self, device_id: str):
        self.device_info = self.create_device_info(device_id, 'device')
        model, brand, android_version, full_name = self.get_device_full_info(device_id)
        
        self.logger.info("Dispositivo Android conectado!", source=SOURCE)
        self.logger.info(f"   Modelo: {full_name}", source=SOURCE)
        self.logger.info(f"   Android: {android_version}", source=SOURCE)
        self.logger.info(f"   ID: {device_id}", source=SOURCE)
        
        self.device_id = device_id
        self.device_connected = True
        
        if self._on_device_connected:
            self._on_device_connected(self.device_info)

    def _handle_device_disconnected(self, device_id: str):
        self.logger.info(f"O dispositivo foi desconectado: {device_id}", source=SOURCE)
        
        if self.device_id == device_id:
            self.device_id = None
            self.device_connected = False
            old_info = self.device_info
            self.device_info = None
            
            if self._on_device_disconnected:
                self._on_device_disconnected(old_info)

    def stop_device_monitoring(self):
        if self._monitoring:
            self.logger.info("Parando monitoramento de dispositivos...", source=SOURCE)
            self._monitoring = False
            if self._monitor_thread:
                self._monitor_thread.join(timeout=5)
                self._monitor_thread = None

    def wait_for_device(self, timeout: int = 60) -> bool:
        self.logger.info(f"Aguardando dispositivo Android (timeout: {timeout}s)...", source=SOURCE)
        self.logger.info("   Conecte o telemóvel via USB e ative Depuração USB", source=SOURCE)
        
        start_time = time.time()
        check_count = 0
        
        while time.time() - start_time < timeout:
            check_count += 1
            devices = self.get_connected_devices()
            
            if check_count % 5 == 0:
                elapsed = int(time.time() - start_time)
                self.logger.info(f"   Procurando... ({elapsed}s)", source=SOURCE)
            
            authorized = [(d, s) for d, s in devices if s == 'device']
            if authorized:
                self._handle_device_connected(authorized[0][0])
                return True
            
            unauthorized = [(d, s) for d, s in devices if s == 'unauthorized']
            if unauthorized:
                self.logger.info("   Dispositivo detectado - aceite a conexão USB", source=SOURCE)
            
            time.sleep(2)
        
        self.logger.warning("Timeout - nenhum dispositivo conectado", source=SOURCE)
        return False

    def close(self):
        self.stop_device_monitoring()
