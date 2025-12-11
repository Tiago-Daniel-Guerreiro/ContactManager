import time
import os
import psutil
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from typing import Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
from utils.logger import get_logger
from models.Result import Result, statusType, messageType
from models.contact import Contact

SOURCE = "WhatsApp_Sender"

class WhatsAppSender:    
    WHATSAPP_URL = "https://web.whatsapp.com"
    WPP_JS_URL = "https://github.com/wppconnect-team/wa-js/releases/download/nightly/wppconnect-wa.js"
    
    def __init__(self):
        self.driver: Optional[webdriver.Edge] = None 
        self.session_dir = os.path.abspath(
            os.path.join(os.path.expanduser("~"), ".whatsapp_edge_session_fast")
        )
        self.logger = get_logger()
        self._invalid_numbers: set = set()
        self._wpp_js_cache: Optional[str] = None

    def initialize(self, **kwargs) -> Tuple[bool, str]:
        return self._initialize_internal()

    def wait_forlogin(self, timeout: int = 120) -> Tuple[bool, str]:
        return self.wait_for_login(timeout)

    def send_message(self, phone: str, message: str, contact_name: str = "", message_type: messageType = messageType.GENERAL) -> Result:
        result = self.verify_stop_and_send(phone, message, contact_name, message_type)
        
        if result.status == statusType.INVALID:
            # Armazena versão apenas com dígitos e com código de país (sem + / espaços)
            try:
                phone_digits: str = self._format_phone(phone).split('@')[0]
            except Exception:
                phone_digits = ''.join(filter(str.isdigit, phone))
                if len(phone_digits) == 9:
                    phone_digits = f"351{phone_digits}"
            self._invalid_numbers.add(phone_digits)
            
        return result
    
    def send_message_report(
        self, 
        contact_name: str, 
        phone: str, 
        message: str, 
        message_type: messageType = messageType.GENERAL
    ) -> Result:
        return self.send_message(phone, message, contact_name, message_type)

    @property
    def is_logged_in(self) -> bool:
        if not self.driver: 
            return False
        try:
            result = self.driver.execute_script(
                "return (typeof WPP !== 'undefined' && WPP.isReady);"
            )
            return bool(result)
        except:
            return False

    def _kill_specific_session_processes(self):
        self.logger.debug("Encerrando processos anteriores...", source=SOURCE)
        target_folder = os.path.basename(self.session_dir).lower()
        killed = 0
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                p_info = proc.info
                p_name = (p_info.get('name') or "").lower()
                p_cmd = " ".join(p_info.get('cmdline') or []).lower()
                
                if 'msedgedriver' in p_name:
                    proc.kill()
                    killed += 1
                    continue
                
                if ('msedge' in p_name or 'webview' in p_name):
                    if target_folder in p_cmd:
                        proc.kill()
                        killed += 1
            except:
                continue
                
        if killed > 0:
            self.logger.debug(f"{killed} processo(s) encerrado(s)", source=SOURCE)
            time.sleep(2)

    def _prepare_session(self):
        self.logger.debug(f"Preparando sessão em: {self.session_dir}", source=SOURCE)
        os.makedirs(self.session_dir, exist_ok=True)
        
        lock_files = ["SingletonLock", "SingletonSocket", "SingletonCookie", "lockfile"]
        for f in lock_files:
            lock_path = os.path.join(self.session_dir, f)
            try: 
                if os.path.exists(lock_path):
                    os.remove(lock_path)
            except:
                pass

    def _get_edge_driver_service(self) -> Service:
        local_driver = os.path.join(os.getcwd(), "msedgedriver.exe")
        if os.path.exists(local_driver): 
            self.logger.debug(f"Usando msedgedriver local: {local_driver}", source=SOURCE)
            return Service(executable_path=local_driver)
        
        try:
            self.logger.debug("A tentar webdriver-manager...", source=SOURCE)
            from webdriver_manager.microsoft import EdgeChromiumDriverManager
            driver_path = EdgeChromiumDriverManager().install()
            self.logger.debug(f"Driver obtido: {driver_path}", source=SOURCE)
            return Service(executable_path=driver_path)
        except Exception as e:
            self.logger.warning(f"WebDriver Manager falhou: {e}", source=SOURCE)
        
        self.logger.debug("Usando Service padrão (PATH do sistema)", source=SOURCE)
        return Service()

    def _initialize_internal(self) -> Tuple[bool, str]:
        try:
            self.logger.info("Iniciando o WhatsApp Sender.", source=SOURCE)
            
            self._kill_specific_session_processes()
            self._prepare_session()
            
            self.logger.debug("Configurando navegador...", source=SOURCE)
            options = Options()
            options.add_argument(f"--user-data-dir={self.session_dir}")
            options.add_argument("--profile-directory=Default")
            options.add_argument("--remote-debugging-port=9225")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-popup-blocking")
            options.add_argument("--log-level=3")
            options.add_argument("--silent")
            
            options.add_experimental_option("detach", True)
            options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])

            service = self._get_edge_driver_service()
            service.creation_flags = 0x08000000 | 0x00000008 | 0x00000200
            
            self.logger.debug("Iniciando Edge...", source=SOURCE)
            try:
                self.driver = webdriver.Edge(service=service, options=options)
            except Exception as e:
                if "user data" in str(e).lower():
                    self.logger.warning("Conflito detectado, a tentar novamente...", source=SOURCE)
                    self._kill_specific_session_processes()
                    time.sleep(2)
                    self.driver = webdriver.Edge(service=service, options=options)
                else:
                    raise
            
            self.driver.set_page_load_timeout(60)
            self.driver.set_script_timeout(30)
            self.driver.implicitly_wait(10)
            
            self.logger.info("Abrindo WhatsApp Web...", source=SOURCE)
            self.driver.get(self.WHATSAPP_URL)
            
            try:
                self.driver.minimize_window()
            except:
                pass
            
            self.logger.info("Navegador iniciado com sucesso!", source=SOURCE)
            return True, "Navegador Iniciado"
            
        except WebDriverException as e:
            error_msg = f"Erro do WebDriver: {str(e)[:200]}"
            self.logger.error(f"Erro: {error_msg}", source=SOURCE)
            return False, error_msg
        except Exception as e:
            error_msg = f"Erro na inicialização: {str(e)[:200]}"
            self.logger.error(f"Erro: {error_msg}", source=SOURCE)
            return False, error_msg

    def _download_wpp_js(self) -> Optional[str]:
        if self._wpp_js_cache:
            return self._wpp_js_cache
            
        self.logger.info("Baixando WPP.js...", source=SOURCE)
        try:
            response = requests.get(self.WPP_JS_URL, timeout=30)
            response.raise_for_status()
            self._wpp_js_cache = response.text
            self.logger.info(f"WPP.js baixado ({len(self._wpp_js_cache)} bytes)", source=SOURCE)
            return self._wpp_js_cache
        except Exception as e:
            self.logger.error(f"Erro ao baixar WPP.js: {e}", source=SOURCE)
            return None

    def _inject_wpp_js(self) -> bool:
        if self.driver is None: 
            return False
            
        try:
            # Verifica se já está pronto
            try:
                is_ready = self.driver.execute_script(
                    "return typeof WPP !== 'undefined' && WPP.isReady === true;"
                )
                if is_ready:
                    self.logger.info("WPP.js já está carregado e pronto", source=SOURCE)
                    return True
            except:
                pass

            # Baixa o JS
            js_content = self._download_wpp_js()
            if not js_content:
                return False
            
            # Aguarda a página estar completamente carregada
            self.logger.debug("Aguardando página carregar completamente...", source=SOURCE)
            for _ in range(30):
                ready_state = self.driver.execute_script("return document.readyState;")
                if ready_state == "complete":
                    break
                time.sleep(1)
            
            # Verifica se os módulos do WhatsApp estão carregados
            self.logger.debug("Verificando módulos do WhatsApp...", source=SOURCE)
            for i in range(30):
                has_modules = self.driver.execute_script("""
                    return typeof window.require !== 'undefined' || 
                           typeof window.webpackChunkwhatsapp_web_client !== 'undefined';
                """)
                if has_modules:
                    self.logger.debug(f"Módulos encontrados após {i+1}s", source=SOURCE)
                    break
                time.sleep(1)
            else:
                self.logger.warning("Módulos não encontrados, a tentar mesmo assim...", source=SOURCE)
            
            # Injeta o script
            self.logger.debug("Injetando WPP.js...", source=SOURCE)
            self.driver.execute_script(js_content)
            time.sleep(2)
            
            # Verifica se WPP foi definido
            wpp_exists = self.driver.execute_script("return typeof WPP !== 'undefined';")
            self.logger.debug(f"WPP definido: {wpp_exists}", source=SOURCE)
            
            if not wpp_exists:
                self.logger.error("WPP não foi definido após injeção", source=SOURCE)
                return False
            
            # Inicializa usando a Promise do webpack
            self.logger.debug("Inicializando via WPP.webpack.isReady...", source=SOURCE)
            
            # Tenta inicializar de diferentes formas
            init_result = self.driver.execute_script("""
                return new Promise((resolve) => {
                    if (typeof WPP === 'undefined') {
                        resolve({success: false, error: 'WPP undefined'});
                        return;
                    }
                    
                    // Se já está pronto
                    if (WPP.isReady) {
                        resolve({success: true, method: 'already_ready'});
                        return;
                    }
                    
                    // Tenta injetar o loader
                    try {
                        if (WPP.webpack && typeof WPP.webpack.injectLoader === 'function') {
                            WPP.webpack.injectLoader();
                        }
                    } catch(e) {
                        console.log('injectLoader error:', e);
                    }
                    
                    // Aguarda ficar pronto
                    let attempts = 0;
                    const checkReady = () => {
                        attempts++;
                        if (WPP.isReady) {
                            resolve({success: true, method: 'polling', attempts: attempts});
                        } else if (attempts < 100) {
                            setTimeout(checkReady, 500);
                        } else {
                            // Verifica se as funções existem mesmo sem isReady
                            const hasAPI = WPP.contact && typeof WPP.contact.queryExists === 'function';
                            resolve({
                                success: hasAPI, 
                                method: 'fallback', 
                                hasAPI: hasAPI,
                                isReady: WPP.isReady
                            });
                        }
                    };
                    
                    setTimeout(checkReady, 1000);
                });
            """)
            
            self.logger.debug(f"Resultado da inicialização: {init_result}", source=SOURCE)
            
            if init_result and init_result.get('success'):
                self.logger.info(f"WPP.js pronto via {init_result.get('method')}", source=SOURCE)
                return True
            
            # Fallback: verifica se a API funciona
            self.logger.debug("Verificando se API funciona (fallback)...", source=SOURCE)
            try:
                api_works = self.driver.execute_script("""
                    try {
                        return {
                            hasContact: typeof WPP.contact !== 'undefined',
                            hasChat: typeof WPP.chat !== 'undefined',
                            hasQueryExists: typeof WPP.contact.queryExists === 'function',
                            hasSendText: typeof WPP.chat.sendTextMessage === 'function'
                        };
                    } catch(e) {
                        return {error: e.toString()};
                    }
                """)
                self.logger.debug(f"  Status da API: {api_works}", source=SOURCE)
                
                if (api_works.get('hasContact') and 
                    api_works.get('hasChat') and 
                    api_works.get('hasQueryExists')):
                    self.logger.info("A API parece funcional!", source=SOURCE)
                    return True
            except Exception as e:
                self.logger.error(f"Erro ao verificar API: {e}", source=SOURCE)
            
            self.logger.error("Falha na inicialização do WPP.js", source=SOURCE)
            return False
            
        except Exception as e:
            self.logger.error(f"Erro na injeção JS: {e}", source=SOURCE)
            import traceback
            self.logger.error(traceback.format_exc(), source=SOURCE)
            return False

    def wait_for_login(self, timeout: int = 120) -> Tuple[bool, str]:
        if self.driver is None: 
            return False, "Driver não iniciado"
        
        # Verifica se já está logado
        try:
            if len(self.driver.find_elements(By.CSS_SELECTOR, '#pane-side')) > 0:
                self.logger.info("Já está logado!", source=SOURCE)
                time.sleep(3)
                if self._inject_wpp_js():
                    return True, "Já logado e API Pronta"
                return False, "Já logado mas falha na API"
        except:
            pass
            
        self.logger.info(f"Aguardando login (timeout: {timeout}s)...", source=SOURCE)
        self.logger.info("Escaneie o QR Code no celular", source=SOURCE)
        
        try:
            self.driver.maximize_window()
        except:
            pass
        
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '#pane-side'))
            )
            self.logger.info("Login detectado!", source=SOURCE)
            
            try:
                self.driver.minimize_window()
            except:
                pass
            
            # Espera mais tempo para o WhatsApp carregar completamente
            self.logger.debug("Aguardando WhatsApp carregar...", source=SOURCE)
            time.sleep(5)
            
            if self._inject_wpp_js():
                self.logger.info("Pronto para enviar mensagens!", source=SOURCE)
                return True, "Logado e API Pronta"
            else:
                return False, "Logado mas falha na API JS"
                
        except TimeoutException:
            return False, f"Timeout de {timeout}s - QR não escaneado"
        except Exception as e:
            return False, f"Erro: {str(e)[:100]}"

    def _format_phone(self, phone: str) -> str:
        # Garante que devolve um ID válido para a API: apenas dígitos + código do país, sem '+' nem espaços
        # Ex: '912345678' -> '351912345678@c.us'; '+351 912 345 678' -> '351912345678@c.us'
        raw = ''.join(filter(str.isdigit, str(phone)))

        # Se vier apenas com 9 dígitos (número nacional), assume Portugal (351)
        if len(raw) == 9:
            raw = f"351{raw}"

        return f"{raw}@c.us"

    def _safe_async_script(self, script: str, *args, timeout: int = 20) -> Any:
        if not self.driver:
            raise Exception("Driver não disponível")
        
        original_timeout = 30
        try:
            original_timeout = self.driver.timeouts.script
        except:
            pass
        
        try:
            self.driver.set_script_timeout(timeout)
            result = self.driver.execute_async_script(script, *args)
            return result
        finally:
            try:
                self.driver.set_script_timeout(original_timeout)
            except:
                pass

    def verify_stop_and_send(self, phone: str, message: str, contact_name: str = "", message_type: messageType = messageType.GENERAL) -> Result:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        phone_id = self._format_phone(phone)
        clean_phone: str = phone_id.split('@')[0]  # Apenas dígitos

        if self.driver is None:
            return Result(contact_name, clean_phone, statusType.ERROR, "Driver Off", timestamp, message_type)

        if clean_phone in self._invalid_numbers:
            return Result(contact_name, clean_phone, statusType.INVALID, "Número Inválido (Cache)", timestamp, message_type)

        try:
            self.logger.debug(f"Processando: {clean_phone}", source=SOURCE)
            
            # Verificar se número existe
            exists_script = """
                var callback = arguments[arguments.length - 1];
                try {
                    WPP.contact.queryExists(arguments[0])
                        .then(function(result) { callback(result); })
                        .catch(function(err) { callback(null); });
                } catch(e) {
                    callback(null);
                }
            """
            
            try:
                contact_info = self._safe_async_script(exists_script, phone_id, timeout=15)
            except TimeoutException:
                self.logger.warning(f"Timeout ao verificar número: {clean_phone}", source=SOURCE)
                return Result(contact_name, clean_phone, statusType.INVALID, "Número Inválido (Timeout)", timestamp, message_type)
            except Exception as e:
                self.logger.warning(f"Erro ao verificar número: {clean_phone} - {e}", source=SOURCE)
                return Result(contact_name, clean_phone, statusType.INVALID, "Número Inválido (Erro)", timestamp, message_type)
            
            if not contact_info:
                self.logger.info(f"Número inválido: {clean_phone}", source=SOURCE)
                return Result(contact_name, clean_phone, statusType.INVALID, "Número Inválido", timestamp, message_type)

            actual_id = phone_id
            try:
                actual_id = contact_info.get('wid', {}).get('_serialized', phone_id)
            except:
                pass
                
            self.logger.debug(f"Número válido: {actual_id}", source=SOURCE)

            # Verificar última mensagem (PARAR)
            hist_script = """
                var callback = arguments[arguments.length - 1];
                try {
                    WPP.chat.getMessages(arguments[0], {count: 10})
                        .then(function(msgs) {
                            var received = msgs.filter(function(m) { return !m.fromMe; }).reverse();
                            if (received.length > 0) {
                                callback(received[0].body || received[0].content || '');
                            } else {
                                callback(null);
                            }
                        })
                        .catch(function(err) { callback(null); });
                } catch(e) {
                    callback(null);
                }
            """
            
            try:
                last_msg = self._safe_async_script(hist_script, actual_id, timeout=15)
                
                if last_msg and str(last_msg).strip().upper() == "PARAR":
                    self.logger.info(f"Parar detectado: {clean_phone}", source=SOURCE)
                    return Result(contact_name, clean_phone, statusType.ERROR, "PARAR Detectado", timestamp, message_type)
            except Exception as e:
                self.logger.warning(f"Erro ao verificar histórico: {e}", source=SOURCE)

            # Enviar mensagem
            self.logger.debug(f"Enviando mensagem...", source=SOURCE)
            send_script = """
                var callback = arguments[arguments.length - 1];
                try {
                    WPP.chat.sendTextMessage(arguments[0], arguments[1])
                        .then(function(result) { 
                            callback({success: true, result: result}); 
                        })
                        .catch(function(err) { 
                            callback({success: false, error: String(err)}); 
                        });
                } catch(e) {
                    callback({success: false, error: String(e)});
                }
            """
            
            result = self._safe_async_script(send_script, actual_id, message, timeout=20)
            
            if result and result.get('success'):
                self.logger.info(f"Enviado para: {clean_phone}", source=SOURCE)
                return Result(contact_name, clean_phone, statusType.SUCCESS, "Enviado", timestamp, message_type)
            else:
                err = result.get('error') if result else "Erro desconhecido"
                err_str = str(err).lower()
                
                # Erros que indicam número inválido/sem WhatsApp
                if any(x in err_str for x in ['no lid for user', 'lid', 'not found', 'does not exist']):
                    self.logger.warning(f"Número inválido/sem WhatsApp: {clean_phone} - {err}", source=SOURCE)
                    return Result(contact_name, clean_phone, statusType.INVALID, f"Número Inválido: {err}", timestamp, message_type)
                
                self.logger.error(f"Erro ao enviar: {err}", source=SOURCE)
                return Result(contact_name, clean_phone, statusType.ERROR, f"Erro: {err}", timestamp, message_type)

        except TimeoutException:
            self.logger.error(f"Timeout para: {clean_phone}", source=SOURCE)
            return Result(contact_name, clean_phone, statusType.ERROR, "Timeout", timestamp, message_type)
        except Exception as e:
            self.logger.error(f"Erro: {e}", source=SOURCE)
            return Result(contact_name, clean_phone, statusType.ERROR, str(e)[:100], timestamp, message_type)

    def close(self):
        self.logger.info("Encerrando navegador...", source=SOURCE)
        if self.driver:
            try: 
                self.driver.quit()
                self.logger.info("Navegador encerrado", source=SOURCE)
            except Exception as e:
                self.logger.error(f"Erro ao encerrar: {e}", source=SOURCE)
        self.driver = None

if __name__ == "__main__":
    print("Teste do WhatsApp Sender")    
    sender = WhatsAppSender()
    
    success, msg = sender.initialize()
    print(f"\nInicialização: {success} - {msg}")
    
    if not success:
        print("\nFalha na inicialização!")
        exit(1)
    
    print("\nEscaneie o QR Code...")
    success, msg = sender.wait_for_login(timeout=120)
    print(f"\nLogin: {success} - {msg}")
    
    if not success:
        print("\nFalha no login!")
        sender.close()
        exit(1)
    
    test_phone = input("Introduza um número para teste (ex: 920 100 200): ")
    test_message = "Teste do WhatsApp Sender!"
    
    result = sender.send_message(test_phone, test_message)

    print(f"\nResultado: {result}")
    
    input("\nPressione ENTER para fechar...")
    sender.close()