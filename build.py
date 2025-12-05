import subprocess
import sys
import shutil
from pathlib import Path

def main():
    print("Build do ContactManager")
    
    # Limpa build anterior
    print("\nPasso 0: Limpando builds anteriores...")
    for dir_path in ["build", "dist", ".pytest_cache", "__pycache__"]:
        if Path(dir_path).exists():
            try:
                shutil.rmtree(dir_path)
                print(f"  Removido: {dir_path}")
            except Exception as e:
                print(f"  Erro ao remover {dir_path}: {e}")
    
    # Verifica se os ícones .ico já existem
    print("\nPasso 1: Verificando ícones...")
    
    icon_light = Path("icon_light.ico")
    icon_dark = Path("icon_dark.ico")
    
    if not icon_light.exists() or not icon_dark.exists():
        print("Ícones .ico não encontrados!")
        print("  - icon_light.ico")
        print("  - icon_dark.ico")
        print("\nContinuando build sem ícones...")
    else:
        print("Ícones encontrados:")
        print(f"  - {icon_light}")
        print(f"  - {icon_dark}")
        
    print("\nPasso 2: Compilando com PyInstaller...")

    # Tenta encontrar pyinstaller em várias localizações
    venv_pyinstaller = Path(sys.executable).parent / "pyinstaller.exe"
    venv_scripts = Path(sys.executable).parent / "pyinstaller"
    
    pyinstaller_cmd = None
    
    # Tenta venv primeiro
    if venv_pyinstaller.exists():
        pyinstaller_cmd = str(venv_pyinstaller)
        print(f"Usando PyInstaller do venv: {pyinstaller_cmd}")
    elif venv_scripts.exists():
        pyinstaller_cmd = str(venv_scripts)
        print(f"Usando PyInstaller do venv (script): {pyinstaller_cmd}")
    else:
        # Tenta usar como módulo Python
        pyinstaller_cmd = [sys.executable, "-m", "PyInstaller"]
        print("Usando PyInstaller como módulo Python")

    try:
        # Monta o comando corretamente
        if isinstance(pyinstaller_cmd, list):
            cmd = pyinstaller_cmd + ["main.spec"]
        else:
            cmd = [pyinstaller_cmd, "main.spec"]
            
        result = subprocess.run(
            cmd,
            check=True
        )
        print(f"\nExecutável criado em: dist/ContactManager.exe")
        print("  Ícones empacotados dentro do .exe")
        return 0
        
    except subprocess.CalledProcessError as e:
        print("\nErro no build")
        print("\nVerifique:")
        print("  1. PyInstaller está instalado: pip install pyinstaller")
        print("  2. Todas as dependências estão instaladas")
        print("  3. O arquivo main.spec está correto")
        return 1
    except FileNotFoundError:
        print("\nPyInstaller não encontrado")
        print("\nInstale o PyInstaller com:")
        print("  pip install pyinstaller")
        return 1

if __name__ == '__main__':
    sys.exit(main())
