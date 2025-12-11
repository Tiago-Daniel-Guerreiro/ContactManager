# Gestor de Contactos

![Language](https://img.shields.io/badge/Python-3.13%2B-blue.svg)
![Automation](https://img.shields.io/badge/Automation-Selenium%20%7C%20WPPConnect-orange.svg)
![UI](https://img.shields.io/badge/UI-CustomTkinter-purple.svg)
![Status](https://img.shields.io/badge/Status-Beta-yellow.svg)

Aplicação de gestão de contactos e automação de mensagens, desenvolvida para processamento de alto volume com foco em velocidade e estabilidade.

Este projeto foi desenvolvido sob encomenda para uma empresa com uma necessidade crítica: implementar um sistema automatizado de envio rápido de mensagens (WhatsApp e SMS) num curto prazo de **menos de 1 semana**.

O desafio não era apenas criar um "bot", mas construir uma ferramenta, com interface gráfica amigável, capaz de processar grandes listas de contactos com velocidade superior à de um humano, mantendo a estabilidade.

## 🚀 Tecnologias Utilizadas

- **Linguagem:** Python 3.13.3
- **Interface Gráfica:** CustomTkinter (temas Dark/Light)
- **Automação Web:** Selenium WebDriver
- **Motor WhatsApp:** WPP.js / WPPConnect (API JavaScript injetada)
- **Integração Mobile:** ADB (Android Debug Bridge)
- **Manipulação de Dados:** Pandas, Openpyxl
- **Relatórios:** Geração automática em HTML

## 🎯 Objetivo Principal

O projeto foi guiado pela urgência e pela necessidade de performance:

- **Superar a Lentidão Humana:** A empresa precisava de volume. A solução tinha de ser drasticamente mais rápida do que uma pessoa a copiar e colar mensagens.
- **Fiabilidade Pragmática:** Com um prazo tão curto, o objetivo não foi criar a arquitetura "perfeita", mas sim uma solução que funcionasse sem falhas críticas no dia a dia.
- **Dualidade de Canais:** Garantir que, se o WhatsApp falhasse ou não fosse aplicável, houvesse um canal alternativo (SMS).

## ✔️ A Solução

O **Contact Manager** oferece um ambiente completo e otimizado para a gestão de envios em massa:

### 🚀 Módulos de Envio

#### **WhatsApp**

A evolução da performance através da injeção direta de código:

- **Abordagem Inicial:** Simulação de cliques (lento, ~4 msg/min).
- **Solução Final:** Injeção de JavaScript via consola do navegador (WPP.js).
- **Resultado:** Aumento para **até 45 mensagens/minuto em testes**.

#### **SMS**

- **Tecnologia:** Comandos ADB para instruir um telemóvel Android via USB.
- **Função:** Backup fiável para quando o WhatsApp não é aplicável.
- **Velocidade:** ~2-5 SMS por minuto.

### 🌟 Funcionalidades Principais

- **Importação de Contactos:** Suporte nativo a ficheiros **Excel**.
- **Mensagens Inteligentes:** Uso de variáveis dinâmicas (ex: `Olá {nome}`).
- **Gestão de Opt-out:** Deteção automática da palavra **"PARAR"**.
- **Validação de Números:** Verificação automática da existência da conta antes do envio.
- **Relatórios Detalhados:** Log em HTML com status exato e *timestamp* de cada envio.
- **Sessão Persistente:** Mantém o login do WhatsApp entre execuções.
- **Temas Visuais:** Alternância automática entre *Dark/Light Mode*.

## 🏗️ Arquitetura

Para organizar o código num tempo curto, adotei uma abordagem **MVC (Model-View-Controller)** adaptada:

- **Model:** Representa as entidades principais do sistema, como Contactos.
- **View:** Interface gráfica construída com CustomTkinter (janelas, botões, tabelas).
- **Controller:** Chama a lógica de negócio e responde às ações do utilizador.
- **Service:** Serviços especializados para automação.
- **Utils:** Código de suporte para várias partes da aplicação.

> ⚠️ **Nota:** Devido ao curto prazo de entrega, não foi possível fazer a separação completa da lógica, resultando em classes com múltiplas responsabilidades (ex: `main_window` com ~700 linhas).

## ⚙️ Principais Desafios

### 1. Evolução do Sistema de Envio WhatsApp

| Fase | Abordagem | Performance | Problema |
|------|-----------|-------------|----------|
| **1** | Simulação de cliques | ~2-4 msg/min | Lento, vulnerável a mudanças de layout |
| **2** | Pesquisa de alternativas | - | Análise de APIs e bibliotecas JS |
| **3** | WPP.js injetado | até 45 msg/min | Solução final implementada |

### 2. Refatoração Constante sob Pressão

Módulos inteiros foram reescritos à pressa para garantir funcionalidade a tempo da entrega. A decisão de mudar para WPP.js foi tomada **nos últimos dias do projeto** — arriscada, mas necessária.

### 3. Limitações do Sistema SMS

- **Ausência de API direta:** Necessário usar ADB como intermediário
- **Velocidade:** ~2-5 SMS/min (dependente do dispositivo)
- **Compatibilidade:** Requer Android físico com depuração USB

### 4. Problemas de Interface

Limitações do CustomTkinter com janelas secundárias (`Toplevel`) causam inconsistências visuais nos ícones de pop-ups.

### 5. Investigação Constante vs Tempo

Durante o desenvolvimento, **não havia tempo para esperar pela "solução perfeita"**:

- Enquanto implementava Fase 1 (cliques), investigava WPP.js em paralelo
- Quando WPP.js provou ser viável, foi integrada nos **últimos 1-2 dias** do projeto
- Decisão pragmática: implementação funcional > refatoração ideal

## 📊 Limitações e Decisões de Projeto

| Aspecto | Ideal | Implementado | Justificativa |
|---------|-------|--------------|---------------|
| Separação de responsabilidades | Classes pequenas e focadas | Classes maiores multi-função | Prazo não permitiu refatoração |
| Tratamento de erros | Específico e detalhado | Genérico em algumas áreas | Priorização de casos principais |
| Interface | Feedback visual completo | Dependência de logs para diagnóstico | Limitações do framework e tempo curto |
| Testes | Testes automatizados e completos | Testes manuais | Tempo insuficiente |

## 👤 O Meu Papel

Fui o **único desenvolvedor** responsável por todo o ciclo de vida deste projeto.

**Decisão crítica:** Perto do final do prazo, a abordagem de "simulação de cliques" estava funcional mas demasiado lenta. Como já investigava o WPP.js em paralelo, decidi implementar esta mudança estrutural nos últimos dias — uma aposta arriscada que salvou o projeto ao entregar a velocidade exigida.

## 📥 Como Utilizar

A aplicação está disponível como executável único, gerado com PyInstaller.

1. Aceda à secção **[Releases](../../releases)** deste repositório.
2. Faça o download da versão mais recente.
3. Execute diretamente no Windows (não é necessário ter Python instalado).

> **Nota:** Para outras plataformas (Linux/Mac), é necessário compilar o código-fonte localmente. Utilize o build.py, garantindo que o Python e todas as dependências estejam instalados. O sistema poderá não funcionar corretamente nessas plataformas, pois não foi possível assegurar a compatibilidade total dentro do prazo.
> 
## 📚 Aprendizados

### Competências Técnicas

- **Automação Web:** Injeção de código JavaScript em contexto web
- **Selenium Avançado:** APIs assíncronas e execução de scripts
- **Integração Mobile:** Comunicação entre processos via ADB
  
### Soft Skills

- **Pragmatismo vs Perfeccionismo:** Código "suficientemente bom" vs "perfeito"
- **Gestão de tempo:** Focar no essencial e entregar o que era mais importante primeiro.
- **Pesquisa em paralelo:** Investigar WPP.js enquanto desenvolvia versão básica

## 🔮 Próximos Passos

- **Modularização:** Separar os métodos de envio em módulos independentes para facilitar a manutenção e evolução
- **Contratos/Interfaces:** Definir interfaces para os serviços, permitindo substituição ou extensão sem alterar o restante do sistema
- **Dashboard de métricas:** Estatísticas em tempo real, histórico, análise por horário
- **Multi-conta:** Múltiplas sessões WhatsApp, load balancing, rotação automática

## ⚠️ Nota de Responsabilidade

Esta ferramenta foi desenvolvida estritamente de acordo com as especificações solicitadas pela empresa. O objetivo do desenvolvimento foi técnico.

O uso ético, legal e a conformidade com os Termos de Serviço das plataformas envolvidas (WhatsApp/Operadoras) são da **total e exclusiva responsabilidade da entidade ou utilizador que opera o software**.

O autor deste projeto não se responsabiliza por qualquer uso indevido, violação de políticas ou leis aplicáveis decorrentes da utilização desta aplicação. Recomenda-se que os utilizadores estejam plenamente cientes das implicações legais e éticas antes de implementar qualquer forma de automação em plataformas de comunicação.
