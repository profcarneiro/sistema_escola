# 🚀 Guia Completo de Deploy: Render + Supabase
## Escola de Artes Helena Barufaldi

Este guia passo a passo ensina como hospedar a aplicação no **Render (onrender.com)** com o banco de dados PostgreSQL no **Supabase**.

---

## 📌 Visão Geral da Arquitetura
- **Hospedagem Web (Backend + Frontend):** Render (Web Service via Docker).
- **Banco de Dados Relacional:** Supabase (PostgreSQL 15+ com Connection Pooler IPv4).
- **Criação de Tabelas e Carga Inicial:** Automática no primeiro boot do servidor (`Base.metadata.create_all`).

---

## 🛠️ Passo 1: Configurar o Banco no Supabase

1. Crie uma conta gratuita em [supabase.com](https://supabase.com).
2. Clique em **"New Project"**:
   - **Name:** `escola-artes-helenabarufaldi` (ou de sua preferência)
   - **Database Password:** Escolha uma senha forte e **guarde-a bem**.
   - **Region:** Escolha uma região próxima (ex: *East US / North Virginia* ou *São Paulo* se disponível).
3. Após o projeto ser criado (cerca de 1 a 2 minutos), obtenha a URL de Conexão:
   - No menu lateral esquerdo, clique no ícone de engrenagem **Project Settings**.
   - Acesse **Database**.
   - Role até a seção **Connection string** e clique na aba **URI**.
   - Mude o modo de *Direct Connection* para **Connection Pooling** (Modo: *Transaction* ou *Session*, porta `6543`).
   - A URL terá um formato semelhante a:
     ```text
     postgresql://postgres.[PROJECT_REF]:[SUA_SENHA]@aws-0-[REGION].pooler.supabase.com:6543/postgres
     ```
   - ⚠️ **Substitua `[SUA_SENHA]`** pela senha real que você definiu no projeto.

> 💡 **Por que usar o Connection Pooler no Supabase?**  
> Os servidores gratuitos do Render realizam conexões de saída via **IPv4**. O Supabase oferece IPv4 através do seu *Connection Pooler* (`pooler.supabase.com`), evitando problemas de resolução DNS / timeout.

---

## 🛠️ Passo 2: Subir o Código para o GitHub / GitLab

Se ainda não enviou o código para o GitHub:

1. Crie um novo repositório privado ou público no [GitHub](https://github.com).
2. No terminal da sua máquina:
   ```bash
   git add .
   git commit -m "feat: configuracao para deploy no render com supabase e dockerfile"
   git remote add origin https://github.com/<SEU_USUARIO>/<SEU_REPOSITORIO>.git
   git branch -M master
   git push -u origin master
   ```

---

## 🛠️ Passo 3: Criar o Serviço no Render

1. Crie uma conta gratuita em [render.com](https://render.com).
2. No painel do Render (Dashboard), clique em **New +** e selecione **Web Service**.
3. Conecte sua conta do GitHub e selecione o repositório do projeto.
4. Preencha as configurações do serviço:
   - **Name:** `escola-artes-helenabarufaldi` (o link será `https://escola-artes-helenabarufaldi.onrender.com`)
   - **Region:** A mesma ou mais próxima da região do Supabase (ex: *Ohio (US East)* ou *Oregon (US West)*)
   - **Branch:** `master` (ou `main`)
   - **Runtime:** **Docker** *(o Render detectará o `Dockerfile` automaticamente)*
   - **Instance Type:** **Free**

---

## 🛠️ Passo 4: Configurar as Variáveis de Ambiente no Render

Na seção **Environment Variables** da mesma página (ou no menu *Environment* após criar):

Adicione as seguintes variáveis:

| Chave (Key) | Valor (Value) | Descrição |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres.[REF]:[SENHA]@aws-0-[REGION].pooler.supabase.com:6543/postgres` | URI copiada do Supabase com sua senha |
| `SECRET_KEY` | *(Gere uma chave aleatória ou clique em Generate)* | Chave de assinatura dos tokens JWT |
| `ENVIRONMENT` | `production` | Desativa hot-reload e otimiza para produção |
| `FIRST_SUPERUSER_EMAIL` | `admin@hbartes.com` | E-mail do administrador inicial |
| `FIRST_SUPERUSER_PASSWORD` | `admin123` | Senha inicial (altere após o primeiro login) |
| `PORT` | `8080` | Porta interna (ou deixe que o Render preencha) |

5. Clique em **Create Web Service** no final da página.

---

## 🚀 Passo 5: Acompanhar o Deploy

1. O Render iniciará a build do Docker:
   - Compilação dos componentes React 18 e geração dos arquivos estáticos.
   - Instalação dos pacotes Python e driver PostgreSQL (`psycopg2-binary`).
   - Inicialização do Uvicorn.
2. Durante a primeira inicialização, o backend conectará ao Supabase e executará automaticamente:
   - Criação de todas as tabelas (alunos, turmas, cursos, matrículas, financeiro, etc.).
   - Carga inicial com as 6 salas padrão (capacidade 9) e as 9 modalidades de arte.
   - Cadastro do usuário administrador (`admin@hbartes.com`).
3. Quando o log exibir `Application startup complete` e o status mudar para **Live**, o sistema estará no ar!

Acesse:
👉 **`https://<SEU_APP>.onrender.com`**

---

## 🔑 Primeiro Acesso em Produção

- **URL:** `https://<seu-app>.onrender.com`
- **Swagger Docs:** `https://<seu-app>.onrender.com/api/v1/docs`
- **E-mail:** `admin@hbartes.com`
- **Senha Inicial:** `admin123` (ou a senha que você configurou em `FIRST_SUPERUSER_PASSWORD`)

> 🔒 **Dica de Segurança:** No primeiro acesso, crie seu usuário pessoal da Direção/Coordenação e altere a senha do admin padrão.
