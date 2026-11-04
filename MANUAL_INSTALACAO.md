# 📖 Manual de Instalação e Configuração em Novo Servidor / Máquina
## Escola de Artes Helena Barufaldi — Sistema de Gestão Escolar

Este documento detalha o passo a passo completo para instalar, configurar e colocar em produção o sistema em qualquer novo computador ou servidor local (Linux, Windows ou macOS).

---

## 📌 Índice
1. [Requisitos Mínimos](#1-requisitos-mínimos)
2. [Como Transferir o Projeto para a Nova Máquina](#2-como-transferir-o-projeto-para-a-nova-máquina)
3. [Instalação e Execução Rápida (Linux / macOS)](#3-instalação-e-execução-rápida-linux--macos)
4. [Instalação e Execução no Windows](#4-instalação-e-execução-no-windows)
5. [Acesso na Rede Local (Outros Computadores da Escola)](#5-acesso-na-rede-local-outros-computadores-da-escola)
6. [Credenciais de Primeiro Acesso](#6-credenciais-de-primeiro-acesso)
7. [Configuração como Serviço do Sistema (Inicialização Automática com o Computador)](#7-configuração-como-serviço-do-sistema-inicialização-automática)
8. [Rotina de Backups em Pendrive e Restauração](#8-rotina-de-backups-em-pendrive-e-restauração)
9. [Solução de Dúvidas e Problemas Frequentes](#9-solução-de-dúvidas-e-problemas-frequentes)

---

## 1. Requisitos Mínimos

### Hardware Recomendado:
- **Processador:** Dual-Core 2.0 GHz ou superior.
- **Memória RAM:** 2 GB ou mais (o sistema é extremamente leve, consumindo menos de 200 MB de RAM).
- **Armazenamento:** 500 MB livres em disco.
- **Rede:** Conexão Ethernet (cabo) ou Wi-Fi na rede da escola.

### Software Necessário:
- **Python:** Versão 3.10 ou superior (testado e homologado no Python 3.11, 3.12 e 3.13).
- **Navegador Web:** Google Chrome, Mozilla Firefox, Microsoft Edge ou Safari atualizados.
- *(Opcional)* **Node.js 18+**: Somente se você desejar alterar ou recompilar o código-fonte do frontend. O pacote já vem com a compilação pronta para uso no diretório `frontend/dist/`.

---

## 2. Como Transferir o Projeto para a Nova Máquina

### Opção A: Via Git (Recomendado se o código estiver em repositório)
```bash
git clone <URL_DO_REPOSITORIO> sistema_escola
cd sistema_escola
```

### Opção B: Via Pendrive / Arquivo Compactado (.ZIP)
1. Na máquina de origem, compacte a pasta do projeto **ignorando** as pastas temporárias `venv/` e `node_modules/`.
2. No Linux/macOS, você pode gerar um `.tar.gz` limpo:
   ```bash
   tar -czvf sistema_escola.tar.gz --exclude="venv" --exclude="node_modules" --exclude=".pytest_cache" sistema_escola/
   ```
3. Copie o arquivo compactado para a nova máquina e descompacte no diretório desejado (ex: `/home/usuario/sistema_escola` ou `C:\sistema_escola`).

---

## 3. Instalação e Execução Rápida (Linux / macOS)

### Passo 1: Instalar o Python e dependências de sistema (caso ainda não tenha)
No Ubuntu/Debian:
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip sqlite3
```

### Passo 2: Entrar na pasta e rodar o script unificado
O projeto possui o script inteligente [`iniciar.sh`](file:///home/debian/antigravity/sistema_escola/iniciar.sh), que cria o ambiente virtual, instala as dependências do `requirements.txt` e inicia o servidor:

```bash
cd sistema_escola
chmod +x iniciar.sh
./iniciar.sh
```

Pronto! O terminal exibirá:
```text
====================================================================
 🎨 ESCOLA DE ARTES HELENA BARUFALDI — SISTEMA DE GESTÃO LOCAL
====================================================================
 🌐 Aplicação Web Completa:  http://localhost:8080
 📖 Documentação da API:    http://localhost:8080/api/v1/docs
====================================================================
```

Abra o navegador no endereço: **[http://localhost:8080](http://localhost:8080)**

---

## 4. Instalação e Execução no Windows

Caso a máquina servidora da escola utilize Windows (Windows 10, 11 ou Windows Server):

### Passo 1: Instalar o Python
1. Baixe o instalador oficial do Python em [python.org](https://www.python.org/downloads/).
2. ⚠️ **Muito Importante:** Na primeira tela do instalador, marque a caixa **"Add python.exe to PATH"** antes de clicar em *Install Now*.

### Passo 2: Abrir o Prompt de Comando (CMD) ou PowerShell
Navegue até a pasta onde descompactou o projeto:
```cmd
cd C:\sistema_escola
```

### Passo 3: Criar o ambiente virtual e instalar dependências
```cmd
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
```

### Passo 4: Iniciar o sistema
```cmd
python run.py
```

Abra o navegador no endereço: **[http://localhost:8080](http://localhost:8080)**

> **Dica Windows:** Você pode criar um arquivo `iniciar.bat` na raiz do projeto com o conteúdo:
> ```bat
> @echo off
> cd /d %~dp0
> call venv\Scripts\activate
> python run.py
> pause
> ```
> Assim, qualquer pessoa na escola pode iniciar o sistema com apenas **2 cliques**!

---

## 5. Acesso na Rede Local (Outros Computadores da Escola)

Como o sistema foi projetado para operar em **servidor local com 2 usuários simultâneos** (ex: Secretaria e Direção), ele já escuta em todas as interfaces de rede (`0.0.0.0:8080`).

### Como descobrir o IP do Servidor:
- **No Linux:** execute `ip addr` ou `hostname -I` (ex: `192.168.1.100`).
- **No Windows:** execute `ipconfig` e localize o *Endereço IPv4* (ex: `192.168.1.100`).

### Como acessar a partir de outro computador/notebook na mesma rede:
No navegador do outro computador (conectado ao mesmo Wi-Fi ou cabo da escola), digite:
👉 **`http://192.168.1.100:8080`**  *(substitua pelo IP real do servidor)*

> ⚠️ **Atenção ao Protocolo:**
> Utilize sempre **`http://`** (sem o **`s`**). O erro `SSL_ERROR_RX_RECORD_TOO_LONG` ocorre caso o navegador tente forçar conexão HTTPS em uma porta HTTP local.

### Liberação do Firewall (se o outro computador não conseguir conectar):
- **No Linux (UFW):**
  ```bash
  sudo ufw allow 8080/tcp
  ```
- **No Windows:**
  No *Painel de Controle -> Firewall do Windows Defender -> Permitir um aplicativo*, libere a porta `8080` (TCP) ou permita o executável `python.exe`.

---

## 6. Credenciais de Acesso (Administrador)

Na primeira execução, o banco de dados é criado automaticamente com uma carga inicial de dados (as 6 salas de aula com teto de 9 alunos e as 9 modalidades de arte):

- **Configuração de Usuário:** O e-mail e a senha do administrador inicial são definidos através das variáveis de ambiente `FIRST_SUPERUSER_EMAIL` e `FIRST_SUPERUSER_PASSWORD` (ou no arquivo `.env`).
- **Perfil:** Direção (Acesso irrestrito a todos os módulos).
- Em ambiente de produção, configure sempre uma senha forte diretamente nas variáveis do servidor.

---

## 7. Configuração como Serviço do Sistema (Inicialização Automática)

Para que o sistema ligue automaticamente sempre que o computador do servidor for ligado (sem precisar abrir o terminal e rodar `./iniciar.sh` manualmente):

### No Linux (usando systemd):

1. Crie o arquivo de serviço:
   ```bash
   sudo nano /etc/systemd/system/sistema-escola.service
   ```

2. Cole o conteúdo abaixo (ajuste o usuário e o caminho da pasta se necessário):
   ```ini
   [Unit]
   Description=Sistema de Gestao - Escola de Artes Helena Barufaldi
   After=network.target

   [Service]
   Type=simple
   User=debian
   WorkingDirectory=/home/debian/sistema_escola
   ExecStart=/home/debian/sistema_escola/venv/bin/python run.py
   Restart=always
   RestartSec=5
   Environment=PYTHONPATH=/home/debian/sistema_escola/backend

   [Install]
   WantedBy=multi-user.target
   ```

3. Ative e inicie o serviço:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable sistema-escola
   sudo systemctl start sistema-escola
   ```

4. Para conferir o status:
   ```bash
   sudo systemctl status sistema-escola
   ```

---

## 8. Rotina de Backups em Pendrive e Restauração

O sistema armazena todos os dados de forma atômica no arquivo SQLite `escola_artes.db`.

### Como fazer Backup:
1. **Pela Interface Web:**
   - Acesse o menu **"Backups do Sistema"**.
   - Clique em **"Criar Snapshot Agora"**.
   - Na lista, clique no ícone de download ao lado do backup gerado para salvar o arquivo `.db` no seu computador ou diretamente no pendrive.
2. **Via Terminal:**
   ```bash
   sqlite3 escola_artes.db ".backup backups/backup_manual.db"
   ```

### Como Restaurar um Banco de Dados de um Backup Anterior:
1. Encerre o servidor (`CTRL+C` ou `sudo systemctl stop sistema-escola`).
2. Substitua o arquivo `escola_artes.db` pelo arquivo de backup desejado:
   ```bash
   cp backups/backup_desejado.db escola_artes.db
   ```
3. Inicie o sistema novamente (`./iniciar.sh` ou `sudo systemctl start sistema-escola`). Todos os alunos, matrículas, notas, diários e títulos estarão exatamente no estado em que o backup foi gerado.

---

## 9. Solução de Dúvidas e Problemas Frequentes

| Situação | Causa Provável | Solução |
|---|---|---|
| **Erro `SSL_ERROR_RX_RECORD_TOO_LONG`** | O navegador tentou acessar via `https://` em vez de `http://`. | Digite explicitamente **`http://`** no início do endereço (ex: `http://localhost:8080`). |
| **"Nenhum professor cadastrado" ao criar turma** | Ainda não foram adicionados professores no sistema. | Acesse a aba **"Professores & Docentes"** no menu e cadastre pelo menos um professor, ou use o atalho "+ Cadastrar Novo Professor" dentro do formulário da turma. |
| **Outro computador não abre a página** | Firewall bloqueando a porta 8080 ou IP incorreto. | Verifique o IP do servidor (`ip addr` ou `ipconfig`) e libere a porta 8080 no firewall (`sudo ufw allow 8080/tcp`). |
| **Porta 8080 em uso** | Outro programa já está utilizando a porta 8080 na máquina. | Altere o parâmetro `port=8080` no arquivo `run.py` para outra porta disponível (ex: `8090`). |
| **Como rodar a suíte de testes?** | Validação das regras de negócio do briefing. | Execute `make test` ou `./venv/bin/pytest -v`. Todos os 101 testes devem passar com 100% de sucesso. |

---

**Escola de Artes Helena Barufaldi** — *Nova Odessa / SP*  
*Documento homologado para implantação em servidor local.*
