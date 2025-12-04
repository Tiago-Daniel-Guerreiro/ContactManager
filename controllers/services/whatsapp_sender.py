import time
import os
import psutil
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.keys import Keys
from typing import Optional, Callable, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class SendResult:
    success: bool
    message: str
    phone_sent_to: str
    timestamp: str

class WhatsAppSender:    
    def __init__(self):
        self.driver: Optional[webdriver.Edge] = None
        self.is_logged_in = False
        self.session_dir = os.path.join(os.path.expanduser("~"), ".whatsapp_edge_session")
        self._last_sent_phone: Optional[str] = None
    
    def _kill_all_edge_processes(self, log_callback: Optional[Callable] = None) -> bool:
        killed = False
        
        # Lista de processos a matar
        process_names = ['msedge.exe', 'msedgedriver.exe', 'msedgewebview2.exe']
        
        for attempt in range(3):  # Tentar 3 vezes
            try:
                for proc in psutil.process_iter(['name', 'pid']):
                    try:
                        proc_name = proc.info['name']
                        if proc_name and any(name.lower() in proc_name.lower() for name in process_names):
                            proc.kill()  # Usar kill() em vez de terminate()
                            killed = True
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue
            except Exception as e:
                if log_callback:
                    log_callback(f"Erro ao matar processos (tentativa {attempt+1}): {e}")
            
            if killed:
                time.sleep(2)  # Aguardar processos terminarem
        
        return killed
    
    def _cleanup_session_locks(self, log_callback: Optional[Callable] = None) -> bool:
        success = True
        lock_files = ["SingletonLock", "SingletonSocket", "SingletonCookie", "lockfile"]
        
        if not os.path.exists(self.session_dir):
            return True
            
        for fname in lock_files:
            fpath = os.path.join(self.session_dir, fname)
            if os.path.exists(fpath):
                for attempt in range(5):  # 5 tentativas
                    try:
                        os.remove(fpath)
                        if log_callback:
                            log_callback(f"Removido: {fname}")
                        break
                    except PermissionError:
                        time.sleep(0.5)
                        continue
                    except Exception as e:
                        if log_callback:
                            log_callback(f"Erro ao remover {fname}: {e}")
                        success = False
                        break
        
        return success
    
    def _is_session_locked(self) -> bool:
        lock_file = os.path.join(self.session_dir, "SingletonLock")
        if os.path.exists(lock_file):
            try:
                # Tentar abrir o ficheiro em modo exclusivo
                with open(lock_file, 'w') as f:
                    pass
                os.remove(lock_file)
                return False
            except:
                return True
        return False
    
    def _prepare_session_directory(self, log_callback: Optional[Callable] = None, force_clean: bool = False) -> bool:        
        # Se forçar limpeza, apagar tudo
        if force_clean and os.path.exists(self.session_dir):
            if log_callback:
                log_callback("A limpar sessão completamente...")
            try:
                shutil.rmtree(self.session_dir)
                time.sleep(1)
            except Exception as e:
                if log_callback:
                    log_callback(f"Erro ao limpar sessão: {e}")
        
        # Criar pasta se não existir
        os.makedirs(self.session_dir, exist_ok=True)
        
        # Limpar locks
        return self._cleanup_session_locks(log_callback)
    
    def _get_edge_driver_service(self, log_callback: Optional[Callable] = None) -> Service:        
        local_driver = os.path.join(os.getcwd(), "msedgedriver.exe")
        
        # 1. Tentar usar driver local primeiro
        if os.path.exists(local_driver):
            if log_callback:
                log_callback("A usar msedgedriver local encontrado.")
            return Service(local_driver)
        
        # 2. Tentar webdriver-manager
        try:
            if log_callback:
                log_callback("A tentar webdriver-manager...")
            from webdriver_manager.microsoft import EdgeChromiumDriverManager
            driver_path = EdgeChromiumDriverManager().install()
            if log_callback:
                log_callback(f"Driver instalado: {driver_path}")
            return Service(driver_path)
        except Exception as e:
            if log_callback:
                log_callback(f"webdriver-manager falhou: {e}")
        
        # 3. Tentar download manual
        try:
            if log_callback:
                log_callback("A tentar download manual do driver...")
            driver_path = self._download_edge_driver(log_callback)
            if driver_path and os.path.exists(driver_path):
                return Service(driver_path)
        except Exception as e:
            if log_callback:
                log_callback(f"Download manual falhou: {e}")
        
        # 4. Usar serviço padrão (pode funcionar se msedgedriver está no PATH)
        if log_callback:
            log_callback("A usar serviço padrão...")
        return Service()
    
    def _download_edge_driver(self, log_callback: Optional[Callable] = None) -> Optional[str]:
        import urllib.request
        import zipfile
        
        # Obter versão do Edge
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        ]
        
        edge_version = None
        for edge_path in edge_paths:
            if os.path.exists(edge_path):
                try:
                    import subprocess
                    result = subprocess.run(
                        ['powershell', '-Command', f'(Get-Item "{edge_path}").VersionInfo.FileVersion'],
                        capture_output=True, text=True
                    )
                    edge_version = result.stdout.strip()
                    break
                except:
                    continue
        
        if not edge_version:
            if log_callback:
                log_callback("Não foi possível detetar versão do Edge")
            return None
        
        if log_callback:
            log_callback(f"Versão do Edge: {edge_version}")
        
        # Download do driver
        url = f"https://msedgedriver.azureedge.net/{edge_version}/edgedriver_win64.zip"
        zip_path = os.path.join(os.getcwd(), "edgedriver_win64.zip")
        driver_path = os.path.join(os.getcwd(), "msedgedriver.exe")
        
        try:
            if log_callback:
                log_callback(f"A fazer download...")
            urllib.request.urlretrieve(url, zip_path)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(os.getcwd())
            
            os.remove(zip_path)
            
            if os.path.exists(driver_path):
                if log_callback:
                    log_callback("msedgedriver instalado com sucesso!")
                return driver_path
        except Exception as e:
            if log_callback:
                log_callback(f"Erro no download: {e}")
        
        return None

    def initialize(self, log_callback: Optional[Callable] = None, force_clean_session: bool = False) -> Tuple[bool, str]:
        try:
            if log_callback:
                log_callback("Inicializando WhatsApp...")
                log_callback("A inicializar Microsoft Edge...")

            # PASSO 1: Matar todos os processos Edge
            if log_callback:
                log_callback("A fechar processos Edge existentes...")
            self._kill_all_edge_processes(log_callback)
            
            # PASSO 2: Preparar pasta de sessão
            if log_callback:
                log_callback("A preparar pasta de sessão...")
            
            if self._is_session_locked():
                if log_callback:
                    log_callback("Sessão bloqueada, a forçar limpeza de locks...")
                self._kill_all_edge_processes(log_callback)  # Matar novamente
                time.sleep(2)
            if not self._prepare_session_directory(log_callback, force_clean_session):
                if log_callback:
                    log_callback("Aviso: Alguns locks não foram removidos, continuando...")

            # Passo 3: Configurar opções do Edge
            options = Options()
            
            # Perfil persistente
            options.add_argument(f"--user-data-dir={self.session_dir}")
            options.add_argument("--profile-directory=Default")
            
            # IMPORTANTE: Manter navegador aberto após script terminar
            options.add_experimental_option("detach", True)
            
            # Configurações de estabilidade
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-popup-blocking")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--log-level=3")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-infobars")
            
            # Remover indicadores de automação
            options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
            options.add_experimental_option('useAutomationExtension', False)

            # Passo 4: Configurar serviço do Edge
            if log_callback:
                log_callback("A configurar Edge WebDriver...")
            
            service = self._get_edge_driver_service(log_callback)
            
            # Esconder janela de consola do driver
            if service:
                service.creation_flags = 0x08000000  # CREATE_NO_WINDOW

            # Passo 5: Criar driver com retry
            max_retries = 3
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    if log_callback and attempt > 0:
                        log_callback(f"Tentativa {attempt + 1} de {max_retries}...")
                    
                    self.driver = webdriver.Edge(service=service, options=options)
                    break  # Sucesso!
                    
                except Exception as e:
                    last_error = str(e)
                    
                    if "user data directory is already in use" in last_error:
                        if log_callback:
                            log_callback("Sessão ainda em uso, a forçar limpeza...")
                        self._kill_all_edge_processes(log_callback)
                        time.sleep(2)
                        self._cleanup_session_locks(log_callback)
                        time.sleep(1)
                    else:
                        if log_callback:
                            log_callback(f"Erro na tentativa {attempt + 1}: {e}")
                        time.sleep(1)
                    
                    if attempt == max_retries - 1:
                        raise
            
            # Remover flag webdriver
            if self.driver:
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                #self.driver.implicitly_wait(10)

            if log_callback:
                log_callback("A aceder ao WhatsApp Web...")

            if self.driver:
                self.driver.get("https://web.whatsapp.com")
                return True, "Edge iniciado com sucesso"
            else:
                return False, "Falha ao inicializar o driver do Edge. Verifique se o msedgedriver está correto."

        except Exception as e:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None

            error_msg = str(e)

            if "user data directory is already in use" in error_msg:
                return False, (
                    "A pasta de sessão está em uso.\n\n"
                    "Soluções:\n"
                    "1. Feche TODAS as janelas do Edge\n"
                    "2. Abra o Gestor de Tarefas (Ctrl+Shift+Esc)\n"
                    "3. Termine todos os processos 'Microsoft Edge'\n"
                    "4. Aguarde 5 segundos e tente novamente\n\n"
                    "Ou use force_clean_session=True para limpar a sessão."
                )
            elif "Could not reach host" in error_msg or "offline" in error_msg.lower():
                return False, "Erro de rede. Verifica a conexão à internet."
            elif "session not created" in error_msg:
                return False, "Não foi possível criar sessão. Feche o Edge e tente novamente."
            elif "executable needs to be in PATH" in error_msg.lower():
                return False, (
                    "msedgedriver não encontrado!\n\n"
                    "Soluções:\n"
                    "1. Faça download em: https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/\n"
                    "2. Coloque msedgedriver.exe na pasta do projeto\n"
                    "3. Ou instale: pip install webdriver-manager"
                )

            return False, f"Erro ao iniciar Edge: {error_msg}"
    
    def wait_for_login(self, timeout: int = 60, log_callback: Optional[Callable] = None) -> Tuple[bool, str]:
        try:
            if not self.driver:
                return False, "Driver não inicializado"
                
            if log_callback:
                log_callback("A aguardar login (escaneie o QR code se necessário)...")
            
            try:
                self.driver.maximize_window()
            except:
                pass
                        
            wait = WebDriverWait(self.driver, timeout)
            login_selectors = [
                '#pane-side',
                'div[data-tab="3"]',
                '[aria-label="Lista de conversas"]',
                '[aria-label="Chat list"]',
            ]
            
            for selector in login_selectors:
                try:
                    element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    if element and element.is_displayed():
                        self.is_logged_in = True
                        if log_callback:
                            log_callback("Login efetuado com sucesso!")
                        time.sleep(1)
                        return True, "Login OK"
                except:
                    continue
            
            return False, "Timeout - QR code não foi escaneado a tempo"
        except Exception as e:
            return False, f"Erro no login: {e}"
    
    def is_really_logged_in(self) -> bool:
        if not self.driver or not self.is_logged_in:
            return False
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, '#pane-side')
            return len(elements) > 0 and elements[0].is_displayed()
        except:
            return False
    
    def _normalize_phone(self, phone: str) -> str:
        clean = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        if clean.startswith('+'):
            clean = clean[1:]
        return clean
    
    def _check_for_error_popup(self, log_callback: Optional[Callable] = None) -> Tuple[bool, str]:
        if not self.driver:
            return False, ""
        try:
            # 1. Verificar texto completo da página
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text.lower()
            
            # Frases que indicam erro
            error_phrases = [
                ('número de telemóvel', 'phone number'),
                ('não é válido', 'is not valid', 'not a valid'),
                ('número inválido', 'invalid number'),
                ('shared via this chat is invalid', 'número de telemóvel partilhado')
            ]
            
            # Contar quantas frases de erro encontramos
            found_errors = []
            for phrases in error_phrases:
                if any(phrase in page_text for phrase in phrases):
                    found_errors.append(phrases[0])
            
            # Se encontrar 2+ indicadores, é certamente um erro
            if len(found_errors) >= 2:
                if log_callback:
                    log_callback(f"Erro detectado: {', '.join(found_errors[:2])}")
                return True, "Número inválido ou sem WhatsApp"
            
            # 2. Verificar botões "OK" com contexto de erro
            try:
                buttons = self.driver.find_elements(By.CSS_SELECTOR, '[role="button"]')
                for btn in buttons:
                    if not btn.is_displayed():
                        continue
                    
                    btn_text = btn.text.strip().upper()
                    if btn_text in ['OK', 'OKAY']:
                        # Verificar o contexto (parent)
                        try:
                            parent = btn.find_element(By.XPATH, "../..")
                            parent_text = parent.text.lower()
                            
                            error_words = ['inválido', 'invalid', 'válido', 'valid', 'número', 'number', 'phone']
                            if any(word in parent_text for word in error_words):
                                if log_callback:
                                    log_callback(f"Modal de erro detectado: {parent_text[:80]}")
                                return True, "Número inválido ou sem WhatsApp"
                        except:
                            pass
            except:
                pass
            
            # 3. Verificar spans/divs com mensagens de erro específicas
            try:
                all_text_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'válido') or contains(text(), 'valid') or contains(text(), 'inválido') or contains(text(), 'invalid')]")
                
                for elem in all_text_elements:
                    if not elem.is_displayed():
                        continue
                    
                    elem_text = elem.text.lower()
                    if ('não' in elem_text or 'not' in elem_text) and ('válido' in elem_text or 'valid' in elem_text):
                        if log_callback:
                            log_callback(f"Mensagem de erro encontrada: {elem_text[:80]}")
                        return True, "Número inválido ou sem WhatsApp"
            except:
                pass
            
            return False, ""
            
        except Exception as e:
            if log_callback:
                log_callback(f"Erro ao verificar popup: {e}")
            return False, ""
    
    def send_message(
        self, 
        phone: str, 
        message: str, 
        log_callback: Optional[Callable] = None,
    ) -> SendResult:
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not self.is_really_logged_in():
            return SendResult(False, "Não está logado no WhatsApp", "", timestamp)
        
        if not self.driver:
            return SendResult(False, "Driver não disponível", "", timestamp)
            
        try:
            phone_clean = self._normalize_phone(phone)
            if log_callback:
                log_callback(f"A preparar envio para {phone}...")
            
            url = f"https://web.whatsapp.com/send?phone={phone_clean}"
            self.driver.get(url)
            
            # Aguardar carregamento inicial
            time.sleep(1.5)
            
            # Verificar erros IMEDIATAMENTE após carregamento
            if log_callback:
                log_callback(f"Verificando {phone}...")
            
            # Verificação rápida de erros (antes de qualquer timeout)
            has_error, error_msg = self._check_for_error_popup(log_callback)
            if has_error:
                return SendResult(False, error_msg, phone_clean, timestamp)
            
            # Tentar encontrar caixa de entrada com timeout de 15s
            # Se não encontrar, é erro (número sem WhatsApp)
            wait = WebDriverWait(self.driver, 15)
            input_box = None
            input_selectors = [
                'div[contenteditable="true"][data-tab="10"]',
                'div[contenteditable="true"][title="Escreva uma mensagem"]',
                'div[contenteditable="true"][title="Type a message"]',
                'footer div[contenteditable="true"]',
                'div[role="textbox"]'
            ]
            
            start_time = time.time()
            for selector in input_selectors:
                try:
                    # Verificar erros periodicamente durante a espera
                    remaining_time = 15 - (time.time() - start_time)
                    if remaining_time <= 0:
                        break
                    
                    # Verificar erro antes de esperar pelo elemento
                    has_error, error_msg = self._check_for_error_popup()
                    if has_error:
                        return SendResult(False, error_msg, phone_clean, timestamp)
                    
                    # Esperar pelo elemento com timeout reduzido
                    temp_wait = WebDriverWait(self.driver, min(3, remaining_time))
                    input_box = temp_wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    
                    if input_box:
                        break
                except:
                    # Verificar erro novamente após falha
                    has_error, error_msg = self._check_for_error_popup()
                    if has_error:
                        return SendResult(False, error_msg, phone_clean, timestamp)
                    continue
            
            # Última verificação de erro
            has_error, error_msg = self._check_for_error_popup()
            if has_error:
                return SendResult(False, error_msg, phone_clean, timestamp)
            
            # Se não encontrou caixa de entrada após 15s, é erro
            if not input_box:
                if log_callback:
                    log_callback(f"Timeout: Conversa não carregou em 15s")
                return SendResult(False, "Número inválido ou sem WhatsApp", phone_clean, timestamp)
            
            # Caixa de entrada encontrada, enviar mensagem
            input_box.click()
            #time.sleep(0.1)
            
            input_box.send_keys(Keys.CONTROL, 'a')
            input_box.send_keys(Keys.DELETE)
            #time.sleep(0.1)
            
            lines = message.split('\n')
            for i, line in enumerate(lines):
                input_box.send_keys(line)
                if i < len(lines) - 1:
                    input_box.send_keys(Keys.SHIFT, Keys.ENTER)
            
            time.sleep(0.1)
            
            send_button = None
            send_selectors = [
                'button[aria-label="Enviar"]',
                'button[aria-label="Send"]',
                'span[data-icon="send"]',
                'button[data-tab="11"]'
            ]
            
            for selector in send_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if elem.is_displayed():
                            send_button = elem
                            break
                    if send_button:
                        break
                except:
                    continue
            
            if send_button:
                send_button.click()
            else:
                input_box.send_keys(Keys.ENTER)
            
            #time.sleep(0.3) # Aguardar envio
            self._last_sent_phone = phone
            
            if log_callback:
                log_callback(f"Mensagem enviada para {phone}")
            
            return SendResult(True, "Enviado com sucesso", phone, timestamp)
            
        except Exception as e:
            return SendResult(False, f"Erro: {e}", "", timestamp)
    
    def check_for_stop_response(self, phone: str, log_callback: Optional[Callable] = None) -> bool:
        """
        Verifica se o contacto respondeu com "PARAR" no WhatsApp.
        
        Args:
            phone: Número de telefone para verificar
            log_callback: Callback para logging
            
        Returns:
            True se encontrou resposta "PARAR", False caso contrário
        """
        try:
            if not self.is_really_logged_in() or not self.driver:
                if log_callback:
                    log_callback("WhatsApp não está inicializado para verificar resposta")
                return False
            
            # Normaliza o número
            phone_clean = self._normalize_phone(phone)
            
            # Abre a conversa com o contacto
            try:
                url = f"https://web.whatsapp.com/send?phone={phone_clean}"
                self.driver.get(url)
                time.sleep(1.5)
            except Exception as e:
                if log_callback:
                    log_callback(f"Erro ao abrir conversa para verificar resposta: {e}")
                return False
            
            # Tenta encontrar as mensagens na conversa
            try:
                # Procura por elementos de mensagem recebida
                # WhatsApp exibe as mensagens em divs com atributos específicos
                wait = WebDriverWait(self.driver, 5)
                
                # Tenta encontrar mensagens recebidas
                received_messages = []
                
                # Seletores comuns para mensagens recebidas no WhatsApp Web
                message_selectors = [
                    'div[data-testid="msg-container"] div[data-testid="msg-container-received"]',
                    'div[data-testid="msg-container"] span',
                    'div.message-in',
                    'div[class*="message"] div[class*="received"]'
                ]
                
                for selector in message_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            for elem in elements:
                                try:
                                    text = elem.text.strip()
                                    if text.upper() == "PARAR":
                                        if log_callback:
                                            log_callback(f"{phone}: Respondeu PARAR")
                                        return True
                                except:
                                    continue
                    except:
                        continue
                
                # Se não encontrou, retorna False
                return False
                
            except Exception as e:
                if log_callback:
                    log_callback(f"Erro ao verificar mensagens: {e}")
                return False
                
        except Exception as e:
            if log_callback:
                log_callback(f"Erro ao verificar resposta PARAR: {e}")
            return False
    
    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
            self.is_logged_in = False