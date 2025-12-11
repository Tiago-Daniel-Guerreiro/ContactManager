import customtkinter as ctk
from typing import Optional, Callable
from utils.theme.icon_helper import set_window_icon_unified


class DisclaimerWindow(ctk.CTkToplevel):
    
    def __init__(self, parent: Optional[ctk.CTk] = None, on_accept: Optional[Callable] = None, 
                 on_decline: Optional[Callable] = None, can_close: bool = False):
        super().__init__(parent)
        
        self.on_accept = on_accept
        self.on_decline = on_decline
        self.can_close = can_close
        self.user_response = None
        self.parent_window = parent
        
        # Configurações da janela
        self.title("Aviso Legal - ContactManager")
        self.geometry("700x550")
        self.resizable(False, False)
        
        # Tornar modal se não permitir fechar
        if not can_close:
            if parent:
                self.transient(parent)
            self.grab_set()
            
            # Manter sempre por cima
            self.attributes('-topmost', True)
            
            # Desabilitar o botão de fechar se não pode fechar
            self.protocol("WM_DELETE_WINDOW", self._on_window_close)
        else:
            if parent:
                self.transient(parent)
        
        self._build_ui()
        
        # Centralizar na tela
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (700 // 2)
        y = (self.winfo_screenheight() // 2) - (550 // 2)
        self.geometry(f"+{x}+{y}")
        
        # Foco na janela
        self.focus_force()
        
        # Aplica ícone com delay para garantir que a janela está pronta
        self.after(150, lambda: set_window_icon_unified(self, "Aviso Legal"))
    
    def _build_ui(self):
        # Container principal
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Título
        title_label = ctk.CTkLabel(
            main_frame,
            text="AVISO LEGAL E TERMOS DE RESPONSABILIDADE",
            font=("Segoe UI", 18, "bold"),
            text_color=("#c75450", "#ff6b6b")
        )
        title_label.pack(pady=(0, 15))

        # Texto do disclaimer
        disclaimer_text = """
ISENÇÃO DE RESPONSABILIDADE

O autor deste projeto não se responsabiliza por qualquer uso indevido, violação de políticas ou leis aplicáveis decorrentes da utilização desta aplicação.

RESPONSABILIDADE DO UTILIZADOR

Esta aplicação foi desenvolvida como ferramenta de automação para envio de mensagens através de WhatsApp e SMS. O utilizador é o único responsável por:

- Garantir que possui autorização para contactar os destinatários
- Cumprir com as políticas de uso do WhatsApp e operadoras móveis
- Respeitar as leis de proteção de dados (RGPD/GDPR)
- Evitar spam, assédio ou qualquer forma de comunicação indesejada
- Usar a aplicação de forma ética e legal

RISCOS E CONSEQUÊNCIAS

O uso inadequado desta aplicação pode resultar em:

- Bloqueio permanente da conta WhatsApp
- Sanções por parte das operadoras móveis
- Processos legais por violação de privacidade
- Multas por incumprimento do RGPD
- Danos à reputação pessoal ou empresarial

RECOMENDAÇÕES

Antes de utilizar esta aplicação, recomenda-se que:

- Leia e compreenda as políticas do WhatsApp Business
- Consulte um advogado sobre as implicações legais
- Obtenha consentimento explícito dos destinatários
- Mantenha registos de autorizações de contacto
- Use a aplicação apenas para fins legítimos

PROTEÇÃO DE DADOS

O utilizador compromete-se a:

- Tratar os dados pessoais de forma segura
- Não partilhar informações sensíveis
- Cumprir com os princípios do RGPD
- Implementar medidas de segurança adequadas

LIMITAÇÃO DE GARANTIA

Esta aplicação é fornecida "tal como está", sem garantias de qualquer tipo. O autor não garante:

- Funcionamento contínuo e sem erros
- Compatibilidade com todas as versões do WhatsApp
- Ausência de bloqueios ou restrições
- Resultados específicos de entrega

AO ACEITAR ESTES TERMOS, DECLARA QUE:

- Leu e compreendeu completamente este aviso
- Assume total responsabilidade pelo uso da aplicação
- Utilizará a ferramenta de forma ética e legal
- Está ciente dos riscos e possíveis consequências
- Não responsabilizará o autor por quaisquer danos

SE NÃO CONCORDA COM ESTES TERMOS, NÃO UTILIZE ESTA APLICAÇÃO.
"""
        
        # Texto selecionável, mas não editável (usando CTkTextbox)
        text_box = ctk.CTkTextbox(
            main_frame,
            font=("Segoe UI", 13),
            wrap="word",
            width=620,
            height=400
        )
        text_box.insert("1.0", disclaimer_text.strip())
        text_box.configure(state="disabled")  # Desabilita edição, mas permite seleção
        text_box.pack(fill="both", expand=True, padx=10, pady=10)
        text_box.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Frame dos botões
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(10, 0))
        
        if not self.can_close:
            # Modo inicial - obrigatório aceitar ou recusar
            
            # Botão Recusar
            decline_btn = ctk.CTkButton(
                button_frame,
                text="Recusar e Sair",
                font=("Segoe UI", 13, "bold"),
                fg_color=("#c75450", "#8b0000"),
                hover_color=("#a03a38", "#6b0000"),
                height=40,
                width=200,
                command=self._on_decline
            )
            decline_btn.pack(side="left", padx=(0, 10))
            
            # Botão Aceitar
            accept_btn = ctk.CTkButton(
                button_frame,
                text="Aceitar e Continuar",
                font=("Segoe UI", 13, "bold"),
                fg_color=("#2d7a3e", "#1e5a2e"),
                hover_color=("#236030", "#154020"),
                height=40,
                width=200,
                command=self._on_accept
            )
            accept_btn.pack(side="right")
            
        else:
            """
            exit_btn = ctk.CTkButton(
                button_frame,
                text="Sair",
                font=("Segoe UI", 13, "bold"),
                fg_color=("#c75450", "#8b0000"),
                hover_color=("#a03a38", "#6b0000"),
                height=40,
                width=150,
                command=self._on_decline
            )

            exit_btn.pack(side="left", padx=(0, 10))
            """
            # Modo visualização - apenas botão OK
            ok_btn = ctk.CTkButton(
                button_frame,
                text="OK",
                font=("Segoe UI", 13, "bold"),
                height=40,
                width=150,
                command=self._on_ok
            )
            ok_btn.pack(side="right")
    
    def _on_accept(self):
        self.user_response = True
        if self.on_accept:
            self.on_accept()
        self.grab_release()
        
        # Remove atributo topmost antes de fechar
        self.attributes('-topmost', False)
        
        # Primeiro destrói esta janela
        self.destroy()
        
        # DEPOIS levanta a janela pai, se necessário
        # A chamada em main.py já vai fazer isso com delays apropriados
    
    def _on_decline(self):
        self.user_response = False
        if self.on_decline:
            self.on_decline()
        self.grab_release()
        
        # Remove atributo topmost antes de fechar
        self.attributes('-topmost', False)
        
        # Destroi esta janela
        self.destroy()
    
    def _on_ok(self):
        self.destroy()
    
    def _on_window_close(self):
        if self.can_close:
            self.destroy()
        # Caso contrário, ignora a tentativa de fechar


def show_disclaimer_blocking(parent: Optional[ctk.CTk] = None) -> bool:
    result = {"accepted": False}
    
    def on_accept():
        result["accepted"] = True
    
    def on_decline():
        result["accepted"] = False
    
    window = DisclaimerWindow(
        parent=parent,
        on_accept=on_accept,
        on_decline=on_decline,
        can_close=False
    )
    
    # Aguarda até a janela ser destruída
    if parent:
        parent.wait_window(window)
    else:
        window.wait_window()
    
    return result["accepted"]


def show_disclaimer_info(parent: ctk.CTk):
    DisclaimerWindow(parent=parent, can_close=True)
