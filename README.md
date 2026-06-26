# Adaptador de Questões — TDAH (Versão Web)
**Unilavras — Prof. Douglas Campideli Fonseca**

Aplicação web para adaptar questões de provas para alunos com TDAH.
Qualquer pessoa com o link pode usar, sem instalar nada.

---

## Como publicar na internet (passo a passo)

### Pré-requisito: conta no GitHub

O Render publica o projeto a partir do GitHub.
Se ainda não tem conta: https://github.com → Sign up (gratuito).

---

### Passo 1 — Criar repositório no GitHub

1. Acesse https://github.com e faça login
2. Clique no botão **"New"** (canto superior esquerdo)
3. Nome do repositório: `adaptador-tdah`
4. Deixe como **Private** (privado)
5. Clique em **"Create repository"**

---

### Passo 2 — Enviar os arquivos para o GitHub

Na página do repositório recém-criado, clique em **"uploading an existing file"**.

Arraste todos os arquivos desta pasta:
```
main.py
gerar_docx.js
requirements.txt
package.json
render.yaml
templates/
  index.html
static/      (pode deixar vazia)
```

Clique em **"Commit changes"**.

---

### Passo 3 — Criar conta no Render

1. Acesse https://render.com
2. Clique em **"Get Started for Free"**
3. Faça login com sua conta do GitHub (opção mais fácil)

---

### Passo 4 — Publicar o projeto no Render

1. No painel do Render, clique em **"New +"** → **"Web Service"**
2. Conecte o repositório `adaptador-tdah` do GitHub
3. Configure assim:
   - **Name:** adaptador-tdah
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt && npm install`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Clique em **"Advanced"** → **"Add Environment Variable"**:
   - Key: `ANTHROPIC_API_KEY`
   - Value: sua chave `sk-ant-...`
5. Clique em **"Create Web Service"**

Aguarde 3 a 5 minutos. O Render vai exibir uma URL do tipo:
```
https://adaptador-tdah.onrender.com
```

Esse é o link que você compartilha com qualquer pessoa.

---

## Uso do aplicativo

1. Acesse o link
2. Configure o título da avaliação (ex.: "AVIN — 2026-2")
3. Faça upload do PDF com as questões
4. Clique em "Adaptar questões"
5. Baixe os arquivos gerados:
   - **PDF — Questões** → para entregar ao aluno
   - **PDF — Com Gabarito** → para o professor
   - **DOCX — Word** → versão editável

---

## Custo

| Item | Custo |
|------|-------|
| Render (hospedagem) | Gratuito (plano free) |
| GitHub | Gratuito |
| API Anthropic (Claude) | ~US$ 0,003 por prova de 30 questões |

---

## Atualizar o aplicativo no futuro

Sempre que quiser atualizar, basta substituir os arquivos no GitHub.
O Render detecta automaticamente e republica em poucos minutos.

---

## Limitações do plano gratuito do Render

- O servidor "dorme" após 15 minutos sem uso
- Na primeira requisição após dormir, demora ~30 segundos para acordar
- Para uso contínuo sem delay, o plano pago custa US$ 7/mês

---

## Suporte

Em caso de erro, abra o painel do Render → seu serviço → aba **"Logs"**
e copie a mensagem de erro para diagnóstico.
