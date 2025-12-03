import time
import os
import psutil
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
from webdriver_manager.microsoft import EdgeChromiumDriverManager

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
    
    def _is_edge_using_session(self) -> bool:
        try:
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    if proc.info['name'] and 'msedge' in proc.info['name'].lower():
                        cmdline = proc.info.get('cmdline', [])
                        if cmdline:
                            cmdline_str = ' '.join(cmdline)
                            if self.session_dir in cmdline_str or '.whatsapp_edge_session' in cmdline_str:
                                return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except:
            pass
        return False
    
    def _close_edge_with_session(self, log_callback: Optional[Callable] = None) -> bool:
        closed = False
        try:
            for proc in psutil.process_iter(['name', 'cmdline', 'pid']):
                try:
                    if proc.info['name'] and 'msedge' in proc.info['name'].lower():
                        cmdline = proc.info.get('cmdline', [])
                        if cmdline:
                            cmdline_str = ' '.join(cmdline)
                            if self.session_dir in cmdline_str or '.whatsapp_edge_session' in cmdline_str:
                                if log_callback:
                                    log_callback(f"A fechar Edge (PID: {proc.info['pid']})...")
                                proc.terminate()
                                proc.wait(timeout=5)
                                closed = True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                    continue
        except:
            pass
        
        if closed:
            time.sleep(2)
        
        return closed
    
    def _kill_edge_driver_processes(self):
        try:
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] and 'msedgedriver' in proc.info['name'].lower():
                        proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except:
            pass
    
    def initialize(self, log_callback: Optional[Callable] = None) -> Tuple[bool, str]:
        try:
            if log_callback:
                log_callback("A inicializar Microsoft Edge...")
            
            # Verificar se Edge está a usar a sessão
            if self._is_edge_using_session():
                if log_callback:
                    log_callback("Edge detectado a usar sessão do WhatsApp...")
                self._close_edge_with_session(log_callback)
            
            # Limpar drivers órfãos
            self._kill_edge_driver_processes()
            
            # Criar pasta da sessão
            os.makedirs(self.session_dir, exist_ok=True)
            
            options = Options()
            
            # Perfil persistente
            options.add_argument(f"--user-data-dir={self.session_dir}")
            options.add_argument("--profile-directory=Default")
            
            # Configurações de estabilidade
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-popup-blocking")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--log-level=3")
            
            # Remover indicadores de automação
            options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Configurar serviço do Edge
            service = None
            
            try:
                if log_callback:
                    log_callback("A configurar Edge WebDriver...")
                driver_path = EdgeChromiumDriverManager().install()
                service = Service(driver_path)
            except ImportError:
                if log_callback:
                    log_callback("A usar driver do sistema...")
                service = Service()
            except Exception as e:
                if log_callback:
                    log_callback(f"Aviso webdriver-manager: {e}")
                service = Service()
            
            # Esconder janela de consola do driver
            if service:
                service.creation_flags = 0x08000000  # CREATE_NO_WINDOW
            
            # Criar driver
            self.driver = webdriver.Edge(service=service, options=options)
            
            # Remover flag webdriver
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Timeouts
            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(10)
            
            if log_callback:
                log_callback("A aceder ao WhatsApp Web...")
            
            self.driver.get("https://web.whatsapp.com")
            time.sleep(3)
            
            return True, "Edge iniciado com sucesso"
            
        except Exception as e:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            
            error_msg = str(e)
            
            # Erros específicos
            if "user data directory is already in use" in error_msg:
                return False, (
                    "A pasta de sessão está em uso.\n"
                    "Feche todas as janelas do Edge e tente novamente."
                )
            elif "Could not reach host" in error_msg:
                return False, "Erro de rede. Verifica a conexão à internet."
            elif "session not created" in error_msg:
                return False, "Não foi possível criar sessão. Feche o Edge e tente novamente."
            
            return False, f"Erro ao iniciar Edge: {error_msg}"
    
    def wait_for_login(self, timeout: int = 120, log_callback: Optional[Callable] = None) -> Tuple[bool, str]:
        try:
            if not self.driver:
                return False, "Driver não inicializado"
                
            if log_callback:
                log_callback("A aguardar login (escaneie o QR code se necessário)...")
            
            try:
                self.driver.maximize_window()
            except:
                pass
            
            # Dar tempo para o browser responder
            time.sleep(2)
            
            wait = WebDriverWait(self.driver, timeout)
            # Seletores de login completo - ordenados por probabilidade
            login_selectors = [
                '#pane-side',                          # Chat list pane (mais confiável)
                'div[data-tab="3"]',                   # Chat list tab
                '[aria-label="Lista de conversas"]',   # Portuguese
                '[aria-label="Chat list"]',            # English
                'button[aria-label="Menu"]',           # Menu button (significa que está logado)
                'div._11JPr',                          # Chat container class
            ]
            
            last_error = ""
            for selector in login_selectors:
                try:
                    if log_callback:
                        log_callback(f"A procurar por '{selector[:30]}...'")
                    element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    if element and element.is_displayed():
                        self.is_logged_in = True
                        if log_callback:
                            log_callback("Login efetuado com sucesso!")
                        time.sleep(1)  # Dar tempo para a página estabilizar
                        return True, "Login OK"
                except Exception as e:
                    last_error = str(e)
                    continue
            
            # Se chegou aqui, não encontrou nenhum elemento
            return False, f"Timeout - não foi possível detetar login. Última tentativa: {last_error}"
        except Exception as e:
            return False, f"Erro no login: {e}"
    
    def is_really_logged_in(self) -> bool:
        if not self.driver or not self.is_logged_in:
            return False
        try:
            # Verificar se o elemento de lista de chat está presente
            elements = self.driver.find_elements(By.CSS_SELECTOR, '#pane-side')
            return len(elements) > 0 and elements[0].is_displayed()
        except:
            return False
    
    def _normalize_phone(self, phone: str) -> str:
        clean = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        if clean.startswith('+'):
            clean = clean[1:]
        return clean
    
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
            time.sleep(5)
            try:
                error_xpath = [
                    '//div[contains(text(), "número de telefone partilhado através de url é inválido")]',
                    '//div[contains(text(), "phone number shared via url is invalid")]',
                ]
                for xpath in error_xpath:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    if elements:
                        return SendResult(False, "Número inválido no WhatsApp", "", timestamp)
            except:
                pass
            wait = WebDriverWait(self.driver, 30)
            input_box = None
            input_selectors = [
                'div[contenteditable="true"][data-tab="10"]',
                'div[contenteditable="true"][title="Escreva uma mensagem"]',
                'div[contenteditable="true"][title="Type a message"]',
                'footer div[contenteditable="true"]',
                'div[role="textbox"]'
            ]
            for selector in input_selectors:
                try:
                    input_box = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    if input_box:
                        break
                except:
                    continue
            if not input_box:
                return SendResult(False, "Não foi possível abrir conversa", "", timestamp)
            input_box.click()
            time.sleep(0.5)
            # Limpar campo de mensagem (Ctrl+A + Delete)
            input_box.send_keys(Keys.CONTROL, 'a')
            input_box.send_keys(Keys.DELETE)
            time.sleep(0.2)
            lines = message.split('\n')
            for i, line in enumerate(lines):
                input_box.send_keys(line)
                if i < len(lines) - 1:
                    input_box.send_keys(Keys.SHIFT, Keys.ENTER)
            time.sleep(0.5)
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
            time.sleep(2)
            self._last_sent_phone = phone
            if log_callback:
                log_callback(f" Mensagem enviada para {phone}")
            return SendResult(True, "Enviado com sucesso", phone, timestamp)
        except Exception as e:
            return SendResult(False, f"Erro: {e}", "", timestamp)
    
    def check_for_stop_response(self, phone: str, log_callback: Optional[Callable] = None) -> bool:
        try:
            phone_clean = self._normalize_phone(phone)
            if self.driver:
                self.driver.get(f"https://web.whatsapp.com/send?phone={phone_clean}")
                time.sleep(5)
                messages = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    'div.message-in span.selectable-text'
                )
                for msg in messages[-15:]:
                    text = msg.text.strip().upper()
                    if text == "PARAR":
                        if log_callback:
                            log_callback(f"O {phone} respondeu PARAR")
                        return True
                return False
            else:
                return False
        except:
            return False
    
    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
            self.is_logged_in = False