import subprocess
import sys
import os
from pathlib import Path

# Cores para console (Windows)
class Cores:
    NORMAL = '\033[0m'
    NEGRITO = '\033[1m'
    VERDE = '\033[92m'
    AMARELO = '\033[93m'
    VERMELHO = '\033[91m'
    CIANO = '\033[96m'
    ROXO = '\033[95m'

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def pausar():
    input("\nPressione ENTER para continuar...")

def verificar_instalar_dependencias():
    print(f"{Cores.CIANO}{Cores.NEGRITO}Contact Manager - Verificação de Dependências{Cores.NORMAL}\n")
    print(f"{Cores.AMARELO}Verificando bibliotecas necessárias...{Cores.NORMAL}\n")
    
    # Lista de dependências (pacote_pip, nome_import, descrição)
    dependencias = [
        ("customtkinter", "customtkinter", "Interface gráfica moderna"),
        ("pandas", "pandas", "Manipulação de dados"),
        ("openpyxl", "openpyxl", "Suporte a Excel"),
        ("selenium", "selenium", "Automação WhatsApp"),
        ("webdriver-manager", "webdriver_manager", "Gerenciamento de drivers"),
        ("requests", "requests", "Requisições HTTP"),
        ("Pillow", "PIL", "Processamento de imagens"),
    ]
    
    instaladas = []
    faltando = []
    
    # Verifica cada dependência
    for pacote_pip, nome_import, descricao in dependencias:
        try:
            __import__(nome_import)
            print(f"  {Cores.VERDE}{Cores.NORMAL} {pacote_pip:30s} - {descricao}")
            instaladas.append(pacote_pip)
        except ImportError:
            print(f"  {Cores.VERMELHO}X{Cores.NORMAL} {pacote_pip:30s} - {descricao} {Cores.VERMELHO}(FALTANDO){Cores.NORMAL}")
            faltando.append((pacote_pip, descricao))
    
    print(f"Total: {Cores.VERDE}{len(instaladas)} instaladas{Cores.NORMAL} | {Cores.VERMELHO}{len(faltando)} faltando{Cores.NORMAL}")
    
    # Se todas estiverem instaladas
    if not faltando:
        print(f"{Cores.VERDE}{Cores.NEGRITO}Todas as dependências estão instaladas!{Cores.NORMAL}\n")
        print(f"{Cores.CIANO}O Contact Manager está pronto para uso.{Cores.NORMAL}")
        return True
    
    # Se houver dependências faltando
    print(f"{Cores.AMARELO}As seguintes bibliotecas precisam ser instaladas:{Cores.NORMAL}\n")
    for pacote, descricao in faltando:
        print(f"  • {pacote} - {descricao}")
    
    print(f"\n{Cores.CIANO}{'='*70}{Cores.NORMAL}")
    resposta = input(f"{Cores.CIANO}Deseja instalar automaticamente? (s/n): {Cores.NORMAL}").strip().lower()
    
    if resposta != 's':
        print(f"\n{Cores.VERMELHO}Instalação cancelada pelo usuário.{Cores.NORMAL}")
        print(f"{Cores.AMARELO}Nota: O programa não funcionará sem as dependências.{Cores.NORMAL}")
        return False
    
    # Instalar dependências
    print(f"\n{Cores.CIANO}{'='*70}{Cores.NORMAL}")
    print(f"{Cores.AMARELO}Instalando dependências...{Cores.NORMAL}\n")
    
    sucesso = True
    for pacote, descricao in faltando:
        print(f"{Cores.CIANO}Instalando {pacote}...{Cores.NORMAL}")
        try:
            # Instala o pacote usando pip
            resultado = subprocess.run(
                [sys.executable, "-m", "pip", "install", pacote],
                capture_output=True,
                text=True,
                timeout=300  # Timeout de 5 minutos
            )
            
            if resultado.returncode == 0:
                print(f"  {Cores.VERDE}{pacote} instalado com sucesso!{Cores.NORMAL}\n")
            else:
                print(f"  {Cores.VERMELHO}Erro ao instalar {pacote}{Cores.NORMAL}")
                print(f"  {Cores.AMARELO}Detalhes: {resultado.stderr[:200]}{Cores.NORMAL}\n")
                sucesso = False
        except subprocess.TimeoutExpired:
            print(f"  {Cores.VERMELHO}Timeout ao instalar {pacote}{Cores.NORMAL}\n")
            sucesso = False
        except Exception as e:
            print(f"  {Cores.VERMELHO}Erro ao instalar {pacote}: {e}{Cores.NORMAL}\n")
            sucesso = False
    
    
    if sucesso:
        print(f"{Cores.VERDE}{Cores.NEGRITO}Todas as dependências foram instaladas com sucesso!{Cores.NORMAL}\n")
        print(f"{Cores.CIANO}O Contact Manager está pronto para uso.{Cores.NORMAL}")
        print(f"{Cores.AMARELO}Execute 'main.py' para iniciar o programa.{Cores.NORMAL}")
        return True
    else:
        print(f"{Cores.VERMELHO}{Cores.NEGRITO}✗ Algumas dependências não foram instaladas.{Cores.NORMAL}\n")
        print(f"{Cores.AMARELO}Tente instalar manualmente usando:{Cores.NORMAL}")
        for pacote, _ in faltando:
            print(f"  pip install {pacote}")
        return False

def verificar_python_version():
    version = sys.version_info
    print(f"{Cores.CIANO}Versão do Python: {version.major}.{version.minor}.{version.micro}{Cores.NORMAL}\n")

    if version.major < 3 or (version.major == 3 and version.minor < 13):
        print(f"{Cores.VERMELHO}AVISO: Python 3.13+ é recomendado. Sua versão pode não ser compatível.{Cores.NORMAL}\n")
        return False
    
    print(f"{Cores.VERDE}Versão do Python adequada.{Cores.NORMAL}\n")
    return True

def criar_requirements_txt():
    requirements_path = Path(__file__).parent / "requirements.txt"
    
    conteudo = """# Contact Manager - Dependências
customtkinter==5.2.1
pandas==2.1.4
openpyxl==3.1.2
selenium==4.16.0
webdriver-manager==4.0.1
requests==2.31.0
Pillow==10.1.0
"""
    
    try:
        with open(requirements_path, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        print(f"{Cores.VERDE}Arquivo requirements.txt criado com sucesso!{Cores.NORMAL}")
        print(f"  Local: {requirements_path}\n")
        return True
    except Exception as e:
        print(f"{Cores.VERMELHO}✗ Erro ao criar requirements.txt: {e}{Cores.NORMAL}\n")
        return False

def menu_principal():
    while True:
        limpar_tela()
        print(f"{Cores.CIANO}{Cores.NEGRITO}Contact Manager - Support Tool{Cores.NORMAL}")
        
        print(f"{Cores.AMARELO}Escolha uma opção:{Cores.NORMAL}\n")
        print(f"  {Cores.VERDE}1){Cores.NORMAL} Verificar e instalar dependências")
        print(f"  {Cores.VERDE}2){Cores.NORMAL} Verificar versão do Python")
        print(f"  {Cores.VERDE}3){Cores.NORMAL} Criar arquivo requirements.txt")
        print(f"  {Cores.VERDE}4){Cores.NORMAL} Verificar tudo (recomendado)")
        print(f"  {Cores.VERMELHO}0){Cores.NORMAL} Sair\n")
        
        opcao = input(f"{Cores.CIANO}Escolha uma opção: {Cores.NORMAL}").strip()
        
        limpar_tela()
        
        if opcao == '1':
            verificar_instalar_dependencias()
            pausar()
        elif opcao == '2':
            verificar_python_version()
            pausar()
        elif opcao == '3':
            criar_requirements_txt()
            pausar()
        elif opcao == '4':
            print(f"{Cores.CIANO}{Cores.NEGRITO}Verificação Completa do Sistema{Cores.NORMAL}\n")
            print(f"{Cores.CIANO}{'='*70}{Cores.NORMAL}\n")
            
            # Verifica Python
            print(f"{Cores.AMARELO}[1/3] Verificando Python...{Cores.NORMAL}\n")
            verificar_python_version()
            
            # Cria requirements.txt
            print(f"\n{Cores.AMARELO}[2/3] Criando requirements.txt...{Cores.NORMAL}\n")
            criar_requirements_txt()
            
            # Verifica dependências
            print(f"\n{Cores.AMARELO}[3/3] Verificando dependências...{Cores.NORMAL}\n")
            verificar_instalar_dependencias()
            
            pausar()
        elif opcao == '0':
            limpar_tela()
            print(f"{Cores.VERDE}Obrigado por usar o Contact Manager Support!{Cores.NORMAL}\n")
            break
        else:
            print(f"{Cores.VERMELHO}Opção inválida!{Cores.NORMAL}")
            pausar()

if __name__ == '__main__':
    try:
        menu_principal()
    except (KeyboardInterrupt, EOFError):
        print(f"\n\n{Cores.ROXO}Programa encerrado pelo usuário.{Cores.NORMAL}\n")
    except Exception as e:
        print(f"\n{Cores.VERMELHO}{Cores.NEGRITO}Erro fatal: {e}{Cores.NORMAL}\n")
        pausar()
