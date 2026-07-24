# Publicar o Assistente de PCD no PythonAnywhere

Guia para deixar o sistema acessível pela internet (endereço fixo, sempre no ar)
usando o **PythonAnywhere**. Leia primeiro a seção de limitações.

---

## ⚠️ Limitações importantes do plano GRÁTIS (leia antes)

1. **As funções de IA NÃO funcionam no plano grátis.** Contas gratuitas do
   PythonAnywhere só conseguem acessar sites de uma *lista branca* na saída de
   internet, e o **OpenRouter (openrouter.ai) não está nessa lista**. Ou seja:
   - ❌ Consultar o MAPPA (resposta da IA) — não funciona.
   - ❌ Extrair dados de documento por IA — não funciona.
   - ✅ Todo o resto funciona: criar/editar PCD, gerar os `.docx`, validações
     de prazo/hierarquia/impedimento, visualizar e baixar documentos.

   Para as funções de IA funcionarem online, é preciso a conta **paga** do
   PythonAnywhere (~US$ 5/mês, sem a restrição de saída), ou hospedar em outro
   serviço sem essa trava.

2. **OCR de imagem pode não funcionar** (o Tesseract pode não estar disponível).
   Extração de PDF/DOCX com texto continua funcionando; só a leitura de imagem
   escaneada é que pode falhar.

3. **Dados reais de PCD**: o plano grátis roda num servidor de terceiros. Para
   dados disciplinares REAIS (sigilo funcional / LGPD), isso não é adequado -
   use só com dados fictícios/de treino, ou infraestrutura oficial da PMMG.

---

## Passo a passo

Substitua `USUARIO` pelo seu nome de usuário do PythonAnywhere em todos os
comandos/caminhos.

### 1. Criar a conta
Crie uma conta gratuita em https://www.pythonanywhere.com (plano "Beginner").

### 2. Baixar o código (console Bash)
Na aba **Consoles** → abra um **Bash**. Como o repositório é privado, o clone
pede um token do GitHub. Crie um token de leitura em
https://github.com/settings/tokens (fine-grained, só leitura, só este repo) e
use assim (o token fica salvo só na sua conta do PythonAnywhere):

```bash
git clone https://SEU_TOKEN@github.com/ralmeida433-cell/procedimentoadm.git
```

### 3. Ambiente virtual e dependências
Ainda no Bash:

```bash
mkvirtualenv --python=/usr/bin/python3.10 pcd-venv
pip install -r procedimentoadm/pcd_automation/requirements.txt
```

### 4. Criar o arquivo de segredos (.env) no servidor
O `.env` NÃO vem no clone (fica fora do Git por segurança). Crie um novo, na
aba **Files**, em `/home/USUARIO/procedimentoadm/pcd_automation/.env`, com:

```
OPENROUTER_API_KEY=sk-or-v1-suachave
PCD_SENHA=escolha-uma-senha-forte
PCD_SECRET_KEY=cole-aqui-uma-sequencia-aleatoria-longa
```

- `PCD_SENHA` é a senha que vai proteger o acesso ao site (ATIVA o login).
- `PCD_SECRET_KEY` pode ser qualquer texto aleatório longo (assina os cookies).

### 5. Criar o web app
Aba **Web** → **Add a new web app** → **Manual configuration** (NÃO escolha o
setup automático do Flask) → **Python 3.10**.

### 6. Apontar o virtualenv
Ainda na aba **Web**, no campo **Virtualenv**, informe:

```
/home/USUARIO/.virtualenvs/pcd-venv
```

### 7. Configurar o arquivo WSGI
Na aba **Web**, clique no link do **WSGI configuration file**. Apague TODO o
conteúdo e deixe só isto (ajustando `USUARIO`):

```python
import sys
caminho = "/home/USUARIO/procedimentoadm/pcd_automation"
if caminho not in sys.path:
    sys.path.insert(0, caminho)
from wsgi import application  # noqa
```

### 8. Recarregar e acessar
Clique no botão verde **Reload** (aba Web). Acesse:

```
https://USUARIO.pythonanywhere.com
```

Vai aparecer a tela de login — use a senha que você colocou em `PCD_SENHA`.

---

## Atualizar o site depois de mudanças no código

Quando você (ou o assistente) alterar o código e fizer `git push`, atualize o
servidor: no Bash do PythonAnywhere,

```bash
cd ~/procedimentoadm && git pull
```

e depois clique em **Reload** na aba **Web**.
