import subprocess
import sys
import shutil
import argparse
import platform
from pathlib import Path
from utils.environment import platform_is_windows, platform_is_linux, platform_is_mac
def get_target_platform(args):
    if args.windows:
        return "windows"
    if args.linux:
        return "linux"

    # Auto-detecta sistema atual
    if platform_is_mac():
        return "macos"
    if platform_is_windows():
        return "windows"
    if platform_is_linux():
        return "linux"
            
    return "unknown"

def get_executable_name(target_platform):
    if target_platform == "windows":
        return "ContactManager.exe"
    else:
        return "ContactManager"

def main():
    parser = argparse.ArgumentParser(description="Build do ContactManager")
    parser.add_argument("--windows", action="store_true", help="Build para Windows")
    parser.add_argument("--linux", action="store_true", help="Build para Linux")
    args = parser.parse_args()
    
    # Valida argumentos mutuamente exclusivos
    if args.windows and args.linux:
        print("Erro: --windows e --linux são mutuamente exclusivos")
        return 1
    
    target_platform = get_target_platform(args)
    executable_name = get_executable_name(target_platform)

    if target_platform == "linux" or target_platform=="macos":
        print(f"O programa pode não funcionar em {target_platform}, pois a compatibilidade ainda está em desenvolvimento.")

    print(f"Build do ContactManager para {target_platform}")
    print(f"Executável: {executable_name}")
    print(f"Sistema atual: {platform.system()} {platform.release()}")
    
    if target_platform != platform.system().lower():
        print(f"AVISO: Cross-compilation de {platform.system().lower()} para {target_platform}")
        print("       Pode não funcionar corretamente")
    
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
    
    icon_png = Path("icon.png")
    icon_ico = Path("icon.ico")

    if not icon_png.exists() or not icon_ico.exists():
        print("Ícones não encontrados!")
        print("  - icon.png")
        print("  - icon.ico")
        print("\nContinuando build sem ícones...")
    else:
        print("Ícones encontrados:")
        print(f"  - {icon_png}")
        print(f"  - {icon_ico}")
        
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
        if result == 1:
            print("\nHouve um erro no processo de build.")
            return 1
        
        print(f"\nExecutável criado em: dist/{executable_name}")
        print("  Ícones empacotados dentro do executável")
        return 0
        
    except subprocess.CalledProcessError as e:
        print("\nErro no build")
        print("\nVerifique:")
        print("  1. PyInstaller está instalado: pip install pyinstaller")
        print("  2. Todas as dependências estão instaladas: pip install -r requirements.txt")
        print("  3. O arquivo main.spec está correto")
        print("  4. Se cross-compilation, certifique-se que é suportada")
        return 1
    
    except FileNotFoundError:
        print("\nPyInstaller não encontrado")
        print("\nInstale o PyInstaller com:")
        print("  pip install pyinstaller")
        print("Ou instale todas as dependências:")
        print("  pip install -r requirements.txt")
        return 1

if __name__ == '__main__':
    print("ContactManager Build")
    print("Uso:")
    print("  python build.py           # Build para sistema atual")
    print("  python build.py --windows # Build para Windows")
    print("  python build.py --linux   # Build para Linux")
    print()
    sys.exit(main())
