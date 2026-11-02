# 🎨 Escola de Artes Helena Barufaldi — Sistema de Gestão

Sistema completo de gestão acadêmica, pedagógica, financeira e operacional desenvolvido para a **Escola de Artes Helena Barufaldi** (Nova Odessa - SP).

O sistema foi concebido para atender às dores centrais levantadas no briefing com o cliente, centralizando cadastros manuais, controlando a frequência e reposições, automatizando o faturamento e a régua de cobrança, e fornecendo demonstrativos contábeis (DRE e Fluxo de Caixa).

---

## 📌 Sumário
- [Recursos e Regras de Negócio](#-recursos-e-regras-de-negócio)
- [Tecnologias Utilizadas](#-tecnologias-utilizadas)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Pré-requisitos](#-pré-requisitos)
- [Instalação e Execução](#-instalação-e-execução)
- [Acesso à API e Documentação Swagger](#-acesso-à-api-e-documentação-swagger)
- [Execução da Suíte de Testes](#-execução-da-suíte-de-testes)
- [Segurança, Auditoria e LGPD](#-segurança-auditoria-e-lgpd)
- [Rotinas de Backup e Restauração](#-rotinas-de-backup-e-restauração)

---

## 🚀 Recursos e Regras de Negócio

### 1. Autenticação e Perfis (RBAC)
- Autenticação JWT com senhas criptografadas em `bcrypt`.
- 5 perfis de acesso: **Direção**, **Coordenação**, **Secretaria**, **Financeiro** e **Professor**.
- Trilha de auditoria em banco de dados (`AuditLog`) registrando IP, data/hora e operador, com mascaramento contra vazamento de senhas e dados sensíveis.

### 2. Infraestrutura e Turmas
- **Capacidade Máxima Estrita**: Teto inegociável de **9 alunos por sala** garantido em duas camadas (validação Pydantic e `CHECK CONSTRAINT` no banco de dados SQLite).
- **Anti-Conflito de Agendamento**: Bloqueio automático com `HTTP 409 Conflict` se uma mesma sala ou o mesmo professor for alocado em turmas no mesmo dia e com horários sobrepostos.
- **Classificação Etária**: Turmas categorizadas em `INFANTIL` (7-10), `JUVENIL` (11-17), `ADULTO` (18-65) e `TERCEIRA_IDADE` (65+).
- **Carga Inicial Automática (Seed)**: 6 salas de aula físicas e 9 modalidades artísticas (Desenho Publicitário, Desenho Artístico, Desenho Moda, Desenho Infantil, Óleo sobre tela, Aquarela, Arteterapia, Fotografia e Mangá).

### 3. Alunos, Responsáveis e Matrículas
- **Responsável Único**: Regra explícita do cliente que impede que um aluno possua mais de um responsável cadastrado (`UniqueConstraint` e verificação de API).
- **Obrigatoriedade para Menores**: Menores de 18 anos exigem obrigatoriamente responsável legal e financeiro (Nome, CPF, Endereço, Telefone 19, E-mail).
- **Contratos e Renovação**: Renovação **NÃO automática** (exige novo contrato assinado). Cancelamento e trancamento exigem justificativa e calculam multa contratual.
- **Lista de Espera**: Fila ordenada por posição quando a turma atinge a lotação de 9 alunos.

### 4. Pedagógico, Frequência e Reposições
- **Diário de Classe**: Registro de tema da aula, conteúdos programáticos, materiais utilizados e observações.
- **Chamada por Aula**: Lançamento de frequência individual ou em lote (`PRESENTE`, `FALTA`, `JUSTIFICADA`).
- 🔒 **Regra de Reposição de Aulas**: Reposições permitidas **estritamente dentro do mês corrente da falta ou até a 1ª semana (dia 07) do mês seguinte**. Agendamentos fora desse prazo são rejeitados com `HTTP 422`.

### 5. Financeiro, Inadimplência e DRE
- **Formas de Pagamento Homologadas**: Exclusivamente **PIX, Cartão, Boleto e Dinheiro**. Qualquer outra forma é rejeitada.
- **Faturamento em Lote**: Emissão mensal de títulos aplicando descontos da matrícula (`irmao`, `indicacao`, `bolsa`).
- **Régua de Cobrança**: Identificação de títulos vencidos e cálculo automático de multa contratual (2%) e juros de mora pro-rata (1% a.m.).
- **Demonstrativos**:
  - **Fluxo de Caixa**: Total de entradas discriminadas por forma de pagamento, saídas operacionais e saldo do período.
  - **DRE**: Demonstração do Resultado do Exercício com Receita Bruta, Deduções e Descontos, Receita Líquida, Despesas Operacionais e Resultado Líquido.

### 6. Comunicação e Backup Local
- **Links para WhatsApp**: Geração de URLs `wa.me` com mensagens pré-formatadas para lembretes de cobrança com chave PIX, boas-vindas e comunicados.
- **Relatórios**: Dashboard executivo com ocupação de salas e exportação de dados em CSV (`alunos_helena_barufaldi.csv` e `financeiro_helena_barufaldi.csv`).
- **Backup Local**: Snapshot atômico do banco de dados na pasta `backups/` com download facilitado para pendrive.

---

## 🛠️ Tecnologias Utilizadas

- **Backend**: Python 3.13 + FastAPI + Uvicorn
- **Banco de Dados**: SQLite com `WAL Mode` (Write-Ahead Logging) e `PRAGMA foreign_keys = ON`
- **ORM & Migrações**: SQLAlchemy 2.x
- **Validação e Tipagem**: Pydantic v2 + Pydantic-Settings
- **Segurança**: Passlib (Bcrypt) + Python-Jose (JWT HS256)
- **Testes**: Pytest + HTTPX + AnyIO

---

## 📁 Estrutura do Projeto

```text
sistema_escola/
├── .agents/                    # Definições de skills e agentes
├── backend/
│   ├── app/
│   │   ├── core/               # Configurações, segurança JWT e auditoria
│   │   ├── models/             # Modelos SQLAlchemy (Users, Rooms, Courses, Teachers, ClassGroups, Students, Enrollments, Attendance, Financial)
│   │   ├── schemas/            # Schemas Pydantic v2 com validações estritas de negócio
│   │   ├── routers/            # Endpoints da API RESTful (auth, users, lgpd, rooms, courses, teachers, classes, students, enrollments, attendance, financial, communication, reports, backup)
│   │   ├── services/           # Lógica de comunicação (WhatsApp, e-mails)
│   │   ├── database.py         # Conexão SQLite e gerador de sessão get_db
│   │   ├── initial_data.py     # Seed automático do admin, salas e modalidades
│   │   └── main.py             # Instância do FastAPI, Lifespan e CORS
│   └── tests/                  # Suíte completa de 101 testes automatizados
├── backups/                    # Diretório local para snapshots do banco de dados
├── escola_artes.db             # Arquivo SQLite do banco de dados
├── pytest.ini                  # Configurações do Pytest (descoberta deve_*)
├── requirements.txt            # Dependências Python congeladas
└── README.md                   # Documentação do projeto
```

---

## 📋 Pré-requisitos

- **Python**: versão 3.10 ou superior (testado e homologado no Python 3.13.5).
- **Git** (opcional, para versionamento).

---

## ⚙️ Instalação e Execução

### 1. Clonar ou navegar até o diretório do projeto:
```bash
cd /home/debian/antigravity/sistema_escola
```

### 2. Criar e ativar o ambiente virtual:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar as dependências:
```bash
pip install -r requirements.txt
```

### 4. Iniciar o servidor da API:
```bash
PYTHONPATH=backend uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

> **Nota:** No primeiro início, o banco de dados `escola_artes.db` é criado automaticamente, junto com o seed do usuário administrador (`admin@hbartes.com`), as 6 salas padrão (capacidade 9) e as 9 modalidades de arte.

---

## 🔑 Credenciais Padrão (Primeiro Acesso)

- **E-mail:** `admin@hbartes.com`
- **Senha:** `admin123`
- **Perfil:** Direção (Acesso Total)

---

## 📖 Acesso à API e Documentação Swagger

Com o servidor em execução, abra o navegador nos seguintes endereços:

- **Swagger UI (Documentação Interativa):**
  [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
- **ReDoc (Documentação Alternativa):**
  [http://localhost:8000/api/v1/redoc](http://localhost:8000/api/v1/redoc)
- **Status da API:**
  [http://localhost:8000/](http://localhost:8000/)

### Principais Grupos de Endpoints
| Módulo | Prefixo | Descrição |
|---|---|---|
| **Autenticação** | `/api/v1/auth` | Login (JSON ou OAuth2), renovação e `/me` |
| **Colaboradores** | `/api/v1/users` | Gestão de usuários da escola (restrito à Direção) |
| **Salas** | `/api/v1/rooms` | Gestão das 6 salas com teto de 9 alunos |
| **Modalidades** | `/api/v1/courses` | Cursos e valores de mensalidade base |
| **Professores** | `/api/v1/teachers` | Especialidades, disponibilidade e substitutos |
| **Turmas** | `/api/v1/classes` | Horários das 13 turmas e validação anti-conflito |
| **Alunos** | `/api/v1/students` | Cadastro de alunos, responsáveis e ficha de saúde |
| **Matrículas** | `/api/v1/enrollments` | Matrículas, contratos, descontos e lista de espera |
| **Pedagógico** | `/api/v1/attendance` | Diário de classe, chamada, reposições e portfólio |
| **Financeiro** | `/api/v1/financial` | Títulos, baixa em PIX/Cartão/Boleto/Dinheiro, DRE e Fluxo de Caixa |
| **Comunicação** | `/api/v1/communication` | Gerador de links para WhatsApp Web/Mobile |
| **Relatórios** | `/api/v1/reports` | Dashboard executivo e exportação em CSV |
| **Backup** | `/api/v1/backup` | Criação e download de backups locais |

---

## 🧪 Execução da Suíte de Testes

O projeto possui **101 testes automatizados** com 100% de cobertura das regras de negócio do cliente.

Para rodar todos os testes:
```bash
source venv/bin/activate
PYTHONPATH=backend pytest -v
```

Para rodar testes de um módulo específico:
```bash
# Testes financeiros (formas de pagamento, lote, DRE, inadimplência)
PYTHONPATH=backend pytest backend/tests/test_financial.py -v

# Testes de turmas e validação anti-conflito
PYTHONPATH=backend pytest backend/tests/test_class_groups.py -v

# Testes de reposição e diário de classe
PYTHONPATH=backend pytest backend/tests/test_attendance.py -v
```

---

## 🔒 Segurança, Auditoria e LGPD

1. **Proteção de Senhas**: As senhas são processadas com `bcrypt` (fator de custo 12) e nunca são armazenadas em texto puro ou retornadas nas respostas de API.
2. **Privacidade de Menores (LGPD)**: O acesso aos dados pessoais de menores e responsáveis é restrito a perfis autorizados (Direção, Coordenação e Secretaria).
3. **Trilha de Auditoria**: Qualquer operação crítica (login, cadastro de usuários, registros financeiros, consentimentos) gera um log de auditoria com IP do cliente e usuário responsável.

---

## 💾 Rotinas de Backup e Restauração

Conforme o requisito de **servidor local** da Escola de Artes:

- Para gerar um backup instantâneo via terminal:
  ```bash
  sqlite3 escola_artes.db ".backup backups/backup_manual.db"
  ```
- Para gerar via API (ou interface):
  ```bash
  curl -X POST http://localhost:8000/api/v1/backup/create -H "Authorization: Bearer <TOKEN_DIRECAO>"
  ```
- Os backups são armazenados na pasta `backups/` e podem ser copiados para pendrives ou discos externos.

---

**Escola de Artes Helena Barufaldi** — *Nova Odessa, SP*  
*Site oficial:* [hbartes.netlify.app](https://hbartes.netlify.app)
