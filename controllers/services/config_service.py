import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from utils.logger import get_logger

class ConfigService:
    DEFAULT_CONFIG = {
        "method": "whatsapp",
        "delay": 5,
        "message": "Olá {nome}!\n",
        "welcome": "Bem vindo(a) {nome}. \nEnvie \"PARAR\" para não receber mais mensagens.",
        "sheets_url": ""
    }
    
    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger()
    
    def load(self) -> Dict[str, Any]:
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Merge com defaults para garantir que todos os campos existem
                return {**self.DEFAULT_CONFIG, **config}
            else:
                return self.DEFAULT_CONFIG.copy()
        except Exception as e:
            self.logger.error(f"Erro ao carregar configuração: {e}", "ConfigService")
            return self.DEFAULT_CONFIG.copy()
    
    def save(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True, "Configuração salva"
        except Exception as e:
            return False, f"Erro ao salvar configuração: {e}"
    
    def get(self, key: str, default: Any = None) -> Any:
        config = self.load()
        return config.get(key, default)
    
    def set(self, key: str, value: Any) -> Tuple[bool, str]:
        config = self.load()
        config[key] = value
        return self.save(config)
    
    @staticmethod
    def create_default_config(base_dir: Path) -> 'ConfigService':
        config_file = base_dir / "config" / "user_config.json"
        return ConfigService(config_file)
