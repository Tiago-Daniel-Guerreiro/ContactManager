#pip install requests psutil selenium webdriver-manager

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
from typing import Optional, Callable, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class WhatsAppResult:
    success: bool
    message: str
    phone_sent_to: str
    timestamp: str
    status_code: str

class WhatsAppSender:    
    WHATSAPP_URL = "https://web.whatsapp.com"
    WPP_JS_URL = "https://github.com/wppconnect-team/wa-js/releases/download/nightly/wppconnect-wa.js"
    
    def __init__(self, log_callback: Optional[Callable] = None):
        self.driver: Optional[webdriver.Edge] = None 
        self.session_dir = os.path.abspath(
            os.path.join(os.path.expanduser("~"), ".whatsapp_edge_session_fast")
        )
        self._log_callback = log_callback
        self._invalid_numbers: set = set()
        self._wpp_js_cache: Optional[str] = None
    
    def _log(self, message: str):
        if self._log_callback:
            try:
                self._log_callback(message)
            except:
                print(f"{message}")
                
    def initialize(self, log: Optional[Callable] = None, **kwargs) -> Tuple[bool, str]:
        if log: 
            self._log_callback = log
        return self._initialize_internal()

    def wait_forlogin(self, timeout: int = 120, log: Optional[Callable] = None) -> Tuple[bool, str]:
        if log:
            self._log_callback = log
        return self.wait_for_login(timeout)

    def send_message(self, phone: str, message: str, log: Optional[Callable] = None) -> WhatsAppResult:
        if log:
            self._log_callback = log
        result = self.verify_stop_and_send(phone, message)
        
        if result.status_code == "INVALIDO":
            clean_phone = ''.join(filter(str.isdigit, phone))
            self._invalid_numbers.add(clean_phone)
            
        return result

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
        self._log("Encerrando processos anteriores...")
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
            self._log(f"{killed} processo(s) encerrado(s)")
            time.sleep(2)

    def _prepare_session(self):
        self._log(f"Preparando sessão em: {self.session_dir}")
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
            self._log(f"Usando msedgedriver local: {local_driver}")
            return Service(executable_path=local_driver)
        
        try:
            self._log("Tentando webdriver-manager...")
            from webdriver_manager.microsoft import EdgeChromiumDriverManager
            driver_path = EdgeChromiumDriverManager().install()
            self._log(f"Driver obtido: {driver_path}")
            return Service(executable_path=driver_path)
        except Exception as e:
            self._log(f"WebDriver Manager falhou: {e}")
        
        self._log("Usando Service padrão (PATH do sistema)")
        return Service()

    def _initialize_internal(self) -> Tuple[bool, str]:
        try:
            self._log("Iniciando o WhatsApp Sender.")
            
            self._kill_specific_session_processes()
            self._prepare_session()
            
            self._log("Configurando navegador...")
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
            
            self._log("Iniciando Edge...")
            try:
                self.driver = webdriver.Edge(service=service, options=options)
            except Exception as e:
                if "user data" in str(e).lower():
                    self._log("Conflito detectado, tentando novamente...")
                    self._kill_specific_session_processes()
                    time.sleep(2)
                    self.driver = webdriver.Edge(service=service, options=options)
                else:
                    raise
            
            self.driver.set_page_load_timeout(60)
            self.driver.set_script_timeout(30)
            self.driver.implicitly_wait(10)
            
            self._log("Abrindo WhatsApp Web...")
            self.driver.get(self.WHATSAPP_URL)
            
            try:
                self.driver.minimize_window()
            except:
                pass
            
            self._log("Browser iniciado com sucesso!")
            return True, "Browser Iniciado"
            
        except WebDriverException as e:
            error_msg = f"Erro do WebDriver: {str(e)[:200]}"
            self._log(f"Erro: {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Erro na inicialização: {str(e)[:200]}"
            self._log(f"Erro: {error_msg}")
            return False, error_msg

    def _download_wpp_js(self) -> Optional[str]:
        if self._wpp_js_cache:
            return self._wpp_js_cache
            
        self._log("Baixando WPP.js...")
        try:
            response = requests.get(self.WPP_JS_URL, timeout=30)
            response.raise_for_status()
            self._wpp_js_cache = response.text
            self._log(f"WPP.js baixado ({len(self._wpp_js_cache)} bytes)")
            return self._wpp_js_cache
        except Exception as e:
            self._log(f"Erro ao baixar WPP.js: {e}")
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
                    self._log("WPP.js já está carregado e pronto")
                    return True
            except:
                pass

            # Baixa o JS
            js_content = self._download_wpp_js()
            if not js_content:
                return False
            
            # Aguarda a página estar completamente carregada
            self._log("Aguardando página carregar completamente...")
            for _ in range(30):
                ready_state = self.driver.execute_script("return document.readyState;")
                if ready_state == "complete":
                    break
                time.sleep(1)
            
            # Verifica se os módulos do WhatsApp estão carregados
            self._log("Verificando módulos do WhatsApp...")
            for i in range(30):
                has_modules = self.driver.execute_script("""
                    return typeof window.require !== 'undefined' || 
                           typeof window.webpackChunkwhatsapp_web_client !== 'undefined';
                """)
                if has_modules:
                    self._log(f"Módulos encontrados após {i+1}s")
                    break
                time.sleep(1)
            else:
                self._log("Módulos não encontrados, tentando mesmo assim...")
            
            # Injeta o script
            self._log("Injetando WPP.js...")
            self.driver.execute_script(js_content)
            time.sleep(2)
            
            # Verifica se WPP foi definido
            wpp_exists = self.driver.execute_script("return typeof WPP !== 'undefined';")
            self._log(f"WPP definido: {wpp_exists}")
            
            if not wpp_exists:
                self._log("WPP não foi definido após injeção")
                return False
            
            # Inicializa usando a Promise do webpack
            self._log("Inicializando via WPP.webpack.isReady...")
            
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
            
            self._log(f"Resultado da inicialização: {init_result}")
            
            if init_result and init_result.get('success'):
                self._log(f"WPP.js pronto via {init_result.get('method')}")
                return True
            
            # Fallback: verifica se a API funciona
            self._log("Verificando se API funciona (fallback)...")
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
                self._log(f"  Status da API: {api_works}")
                
                if (api_works.get('hasContact') and 
                    api_works.get('hasChat') and 
                    api_works.get('hasQueryExists')):
                    self._log("A API parece funcional!")
                    return True
            except Exception as e:
                self._log(f"Erro ao verificar API: {e}")
            
            self._log("Falha na inicialização do WPP.js")
            return False
            
        except Exception as e:
            self._log(f"Erro na injeção JS: {e}")
            import traceback
            self._log(traceback.format_exc())
            return False

    def wait_for_login(self, timeout: int = 120) -> Tuple[bool, str]:
        if self.driver is None: 
            return False, "Driver não iniciado"
        
        # Verifica se já está logado
        try:
            if len(self.driver.find_elements(By.CSS_SELECTOR, '#pane-side')) > 0:
                self._log("Já está logado!")
                time.sleep(3)
                if self._inject_wpp_js():
                    return True, "Já logado e API Pronta"
                return False, "Já logado mas falha na API"
        except:
            pass
            
        self._log(f"Aguardando login (timeout: {timeout}s)...")
        self._log("Escaneie o QR Code no celular")
        
        try:
            self.driver.maximize_window()
        except:
            pass
        
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '#pane-side'))
            )
            self._log("Login detectado!")
            
            try:
                self.driver.minimize_window()
            except:
                pass
            
            # Espera mais tempo para o WhatsApp carregar completamente
            self._log("Aguardando WhatsApp carregar...")
            time.sleep(5)
            
            if self._inject_wpp_js():
                self._log("Pronto para enviar mensagens!")
                return True, "Logado e API Pronta"
            else:
                return False, "Logado mas falha na API JS"
                
        except TimeoutException:
            return False, f"Timeout de {timeout}s - QR não escaneado"
        except Exception as e:
            return False, f"Erro: {str(e)[:100]}"

    def _format_phone(self, phone: str) -> str:
        digits = ''.join(filter(str.isdigit, phone))
        
        # Se o número tem apenas 9 dígitos (número português sem código do país)
        # adiciona o código +351
        if len(digits) == 9:
            digits = f"351{digits}"
        # Se começa com 9 e tem 11 ou 12 dígitos, pode estar faltando o 351
        elif len(digits) in [11, 12] and not digits.startswith('351'):
            # Verifica se não tem outro código de país comum
            if not any(digits.startswith(code) for code in ['1', '44', '49', '33', '34', '39']):
                digits = f"351{digits[-9:]}"  # Pega os últimos 9 dígitos e adiciona 351
        
        return f"{digits}@c.us"

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

    def verify_stop_and_send(self, phone: str, message: str) -> WhatsAppResult:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        phone_id = self._format_phone(phone)
        clean_phone = phone_id.split('@')[0] # Apenas dígitos

        if self.driver is None:
            return WhatsAppResult(False, "Driver Off", clean_phone, timestamp, "ERRO")

        if clean_phone in self._invalid_numbers:
            return WhatsAppResult(False, "Número Inválido (Cache)", clean_phone, timestamp, "INVALIDO")

        try:
            self._log(f"Processando: {clean_phone}")
            
            # 1. Verificar se número existe
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
                self._log(f"Timeout ao verificar número: {clean_phone}")
                return WhatsAppResult(False, "Número Inválido (Timeout)", clean_phone, timestamp, "INVALIDO")
            except Exception as e:
                self._log(f"Erro ao verificar número: {clean_phone} - {e}")
                return WhatsAppResult(False, "Número Inválido (Erro)", clean_phone, timestamp, "INVALIDO")
            
            if not contact_info:
                self._log(f"Número inválido: {clean_phone}")
                return WhatsAppResult(False, "Número Inválido", clean_phone, timestamp, "INVALIDO")

            actual_id = phone_id
            try:
                actual_id = contact_info.get('wid', {}).get('_serialized', phone_id)
            except:
                pass
                
            self._log(f"Número válido: {actual_id}")

            # 2. Verificar última mensagem (PARAR)
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
                    self._log(f"Parar detectado: {clean_phone}")
                    return WhatsAppResult(False, "PARAR Detectado", clean_phone, timestamp, "PARAR_DETECTADO")
            except Exception as e:
                self._log(f"Erro ao verificar histórico: {e}")

            # 3. Enviar mensagem
            self._log(f"Enviando mensagem...")
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
                self._log(f"Enviado para: {clean_phone}")
                return WhatsAppResult(True, "Enviado", clean_phone, timestamp, "ENVIADO")
            else:
                err = result.get('error') if result else "Erro desconhecido"
                err_str = str(err).lower()
                
                # Erros que indicam número inválido/sem WhatsApp
                if any(x in err_str for x in ['no lid for user', 'lid', 'not found', 'does not exist']):
                    self._log(f"Número inválido/sem WhatsApp: {clean_phone} - {err}")
                    return WhatsAppResult(False, f"Número Inválido: {err}", clean_phone, timestamp, "INVALIDO")
                
                self._log(f"Erro ao enviar: {err}")
                return WhatsAppResult(False, f"Erro: {err}", clean_phone, timestamp, "ERRO")

        except TimeoutException:
            self._log(f"Timeout para: {clean_phone}")
            return WhatsAppResult(False, "Timeout", clean_phone, timestamp, "ERRO")
        except Exception as e:
            self._log(f"Erro: {e}")
            return WhatsAppResult(False, str(e)[:100], clean_phone, timestamp, "ERRO")

    def close(self, log: Optional[Callable] = None):
        self._log("Encerrando navegador...")
        if self.driver:
            try: 
                self.driver.quit()
                self._log("Navegador encerrado")
            except Exception as e:
                self._log(f"Erro ao encerrar: {e}")
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