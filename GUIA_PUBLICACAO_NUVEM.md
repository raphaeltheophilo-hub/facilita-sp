# GUIA DE PUBLICAÇÃO NA NUVEM — FACILITA SP
## Render + Neon (ambos gratuitos)

Este guia leva você do zero até o sistema online em cerca de 30 minutos,
sem nenhum conhecimento técnico necessário.

---

# VISÃO GERAL

Você vai usar dois serviços gratuitos:

| Serviço | O que faz | Site |
|---|---|---|
| **GitHub** | Guarda o código do sistema | github.com |
| **Neon** | Banco de dados na nuvem (substitui o SQLite) | neon.tech |
| **Render** | Servidor que roda o sistema online | render.com |

A sequência é: GitHub → Neon → Render.

---

# PARTE 1 — GITHUB (guardar o código)

O GitHub é como um "pendrive na nuvem" para código. O Render vai ler o
código de lá automaticamente.

## Passo 1 — Criar conta no GitHub

1. Acesse **https://github.com**
2. Clique em **"Sign up"**
3. Preencha e-mail, senha e nome de usuário
4. Confirme o e-mail recebido

## Passo 2 — Criar um repositório (pasta no GitHub)

1. Após fazer login, clique no **"+"** no canto superior direito
2. Clique em **"New repository"**
3. Em **"Repository name"**, digite: `facilita-sp`
4. Deixe marcado como **"Private"** (privado — só você vê)
5. Clique em **"Create repository"**

## Passo 3 — Enviar os arquivos

Na página do repositório recém-criado:

1. Clique em **"uploading an existing file"**
   (ou "add file" → "Upload files")
2. Arraste **todos os arquivos** da pasta `facilita_sp_cloud`:
   - `app.py`
   - `db.py`
   - `utils.py`
   - `auth.py`
   - `requirements.txt`
   - `render.yaml`
3. Para a pasta `.streamlit/config.toml`:
   - Clique em **"choose your files"**
   - Navegue até a pasta `.streamlit` e selecione `config.toml`
   - O GitHub vai criar a pasta automaticamente
4. No campo **"Commit changes"** (lá embaixo), deixe o texto padrão
5. Clique em **"Commit changes"** (botão verde)

Pronto — o código está no GitHub.

---

# PARTE 2 — NEON (banco de dados)

O Neon é um banco de dados PostgreSQL gratuito na nuvem.
Ele guarda todos os dados permanentemente, mesmo quando o servidor reinicia.

## Passo 4 — Criar conta no Neon

1. Acesse **https://neon.tech**
2. Clique em **"Sign up"** (pode usar a conta do GitHub para facilitar)
3. Faça login

## Passo 5 — Criar o banco de dados

1. Após login, clique em **"Create project"**
2. Em **"Project name"**, digite: `facilita-sp`
3. Em **"Database name"**, deixe como está (`neondb`)
4. Em **"Region"**, escolha: **South America (São Paulo)** — se disponível,
   ou **US East** como alternativa
5. Clique em **"Create project"**

## Passo 6 — Copiar a connection string (endereço do banco)

Após criar o projeto, o Neon vai mostrar uma tela com as credenciais.

1. Procure a seção **"Connection string"** ou **"Connection details"**
2. Selecione o formato **"Connection string"**
3. Você verá algo assim (com seus dados reais):
   ```
   postgresql://usuario:senha@ep-algo-123456.sa-east-1.aws.neon.tech/neondb?sslmode=require
   ```
4. Clique no ícone de **copiar** ao lado dessa string
5. **Guarde em um bloco de notas** — você vai precisar no próximo passo

> ⚠️ Essa string contém sua senha. Não compartilhe com ninguém.

---

# PARTE 3 — RENDER (o servidor)

O Render vai pegar o código do GitHub, instalar tudo e colocar o sistema online.

## Passo 7 — Criar conta no Render

1. Acesse **https://render.com**
2. Clique em **"Get Started for Free"**
3. Clique em **"Continue with GitHub"** (use a mesma conta GitHub)
4. Autorize o Render a acessar sua conta GitHub

## Passo 8 — Criar o serviço web

1. No painel do Render, clique em **"New +"** → **"Web Service"**
2. Em **"Connect a repository"**, você verá seu repositório `facilita-sp`
3. Clique em **"Connect"** ao lado dele

## Passo 9 — Configurar o serviço

Na tela de configuração:

| Campo | O que colocar |
|---|---|
| **Name** | `facilita-sp` |
| **Region** | `Oregon (US West)` ou qualquer um |
| **Branch** | `main` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `streamlit run app.py --server.port $PORT --server.address 0.0.0.0` |
| **Instance Type** | `Free` |

## Passo 10 — Adicionar a variável de ambiente (DATABASE_URL)

Esta é a etapa mais importante — é aqui que você conecta o sistema ao banco.

1. Role a página para baixo até **"Environment Variables"**
2. Clique em **"Add Environment Variable"**
3. No campo **"Key"**, digite exatamente:
   ```
   DATABASE_URL
   ```
4. No campo **"Value"**, cole a connection string que você copiou do Neon
   (aquela que começa com `postgresql://...`)
5. Clique em **"Save"**

## Passo 11 — Criar o serviço

1. Role até o final da página
2. Clique no botão **"Create Web Service"**
3. O Render vai começar a construir o sistema. Isso leva de **3 a 8 minutos**.
4. Você verá logs aparecendo na tela. Aguarde até aparecer:
   ```
   Your service is live 🎉
   ```

---

# PARTE 4 — PRIMEIRO ACESSO

## Passo 12 — Acessar o sistema

1. Após o deploy, o Render mostra o endereço do sistema no topo da página:
   ```
   https://facilita-sp.onrender.com
   ```
   (o endereço exato será diferente, mas nesse formato)
2. Clique no link ou copie e cole no navegador
3. A tela de login vai aparecer

**Login:** `admin`
**Senha:** `facilita2025`

## Passo 13 — Importar a planilha

1. No menu lateral, clique em **📤 Importar Planilha**
2. Faça upload do arquivo `Status_Facilita_SP_Municípios.xlsx`
3. Clique em **▶️ Importar**
4. Aguarde a mensagem de sucesso

**Pronto! O sistema está online e acessível por qualquer pessoa com o link e a senha.**

---

# PARTE 5 — USO DIÁRIO

## Compartilhar o acesso com a equipe

1. Envie o link `https://facilita-sp.onrender.com` para os colegas
2. Cada colega precisará de um login e senha
3. Para criar novos usuários: **⚙️ Configurações → Usuários → Adicionar**

## Atualizar a planilha

Na versão cloud, a atualização é sempre manual pela interface:
1. Acesse o sistema online
2. Vá em **📤 Importar Planilha**
3. Faça upload da nova versão do arquivo
4. Clique em **▶️ Importar**

## Atualizar o código no futuro

Se você precisar atualizar algum arquivo do sistema:
1. Acesse **github.com** → seu repositório `facilita-sp`
2. Clique no arquivo que quer substituir
3. Clique no ícone de **lápis** (editar) ou **"..."** → **"Delete"**
4. Para substituir: delete o arquivo antigo e faça upload do novo
5. O Render detecta automaticamente e publica a nova versão em ~5 minutos

---

# PROBLEMAS COMUNS

### "Application error" ao abrir
O serviço gratuito do Render hiberna após 15 minutos sem uso.
Na primeira abertura do dia, aguarde **30 a 60 segundos** enquanto ele "acorda".
Após isso, funciona normalmente.

> **Dica:** O plano gratuito do Render tem essa limitação. Se precisar que
> o sistema fique sempre disponível instantaneamente, o plano pago custa
> US$7/mês (~R$40/mês).

### "DATABASE_URL not set" ou erro de conexão
Verifique se a variável `DATABASE_URL` foi adicionada corretamente no Render.
Acesse: Render → seu serviço → **Environment** → confirme que `DATABASE_URL` existe.

### Dados sumiram após reinício
Isso não deve acontecer com o Neon, pois os dados ficam no banco.
Se acontecer, verifique se a `DATABASE_URL` está correta.

### Esqueci a senha do admin
Acesse **https://console.neon.tech**, abra seu projeto, clique em
**"SQL Editor"** e execute:
```sql
UPDATE usuarios
SET senha_hash = 'a1b2c3...'   -- gere um novo hash em sha256.online
WHERE login = 'admin';
```
Ou simplesmente delete a linha do admin e o sistema recria na próxima vez que iniciar.

---

# RESUMO RÁPIDO

```
1. GitHub   → criar conta → criar repositório "facilita-sp" → fazer upload dos arquivos
2. Neon     → criar conta → criar projeto → copiar connection string
3. Render   → criar conta com GitHub → New Web Service → conectar repositório
             → adicionar DATABASE_URL → Create Web Service → aguardar deploy
4. Acessar o link gerado → login admin/facilita2025 → importar planilha
```

---

*Facilita SP · Diretoria de Aumento da Produtividade · SDE-SP*
