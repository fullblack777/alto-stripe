# ⚡ Cyber Stripe - Alto Coder Professional v5.0

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![PHP](https://img.shields.io/badge/PHP-Generated-777BB4.svg)](https://www.php.net/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Online-success.svg)]()
[![Author](https://img.shields.io/badge/Author-@cybersecofc-purple.svg)]()
[![Telegram](https://img.shields.io/badge/Telegram-@cybersecofcadm-2CA5E0.svg)](https://t.me/cybersecofcadm)

**Cyber Stripe v5.0** é a ferramenta profissional definitiva para geração automática de APIs PHP a partir de cURLs do Stripe. Com parser inteligente, sistema de login por keys, interface luxuosa e anti-sleep para deploy 24/7.

---

## 📋 Sumário

- [Funcionalidades](#-funcionalidades)
- [Instalação](#-instalação)
- [Como Usar](#-como-usar)
- [Sistema de Login](#-sistema-de-login)
- [Gerando APIs](#-gerando-apis)
- [Estrutura do PHP Gerado](#-estrutura-do-php-gerado)
- [Parser de cURL](#-parser-de-curl)
- [Deploy](#-deploy)
- [Segurança](#-segurança)
- [FAQ](#-faq)
- [Suporte](#-suporte)

---

## ✨ Funcionalidades

### Principais
- ⚡ **Parser Inteligente de cURL** - Analisa e entende qualquer comando cURL do Stripe
- 🚀 **Geração Automática de API PHP** - Converte cURLs em API funcional com um clique
- 🔐 **Sistema de Login com Keys** - Acesso restrito e seguro
- 🎨 **Interface Premium** - Design luxuoso com tema dark e animações
- 📥 **Download e Cópia** - Baixe o PHP gerado ou copie com um clique
- 🔄 **Anti-Sleep** - Mantém o servidor ativo 24/7 no Render.com
- 🎵 **Música de Fundo** - Experiência imersiva com player integrado

### Técnicas
- ✅ Suporte a múltiplos cURLs simultâneos
- ✅ Detecção automática de tokens (pm_, pi_, tok_, seti_)
- ✅ Identificação de payment methods, tokens e payment intents
- ✅ Substituição automática de dados de cartão
- ✅ Geração de código PHP profissional e comentado
- ✅ Validação de resposta com detecção de status
- ✅ Sistema de cookies entre requisições

### Detecção de Status
- ✅ **approved** - Pagamento aprovado
- ✅ **declined** - Cartão recusado
- ✅ **live_cvv** - Cartão vivo (CVV incorreto)
- ✅ **live_insufficient** - Cartão vivo (saldo insuficiente)
- ✅ **declined_expired** - Cartão expirado

---

## 🔧 Instalação

### Pré-requisitos

- **Python** 3.8+
- **pip** (gerenciador de pacotes)

### Método 1: Clone e Instalação


# Clone o repositório
git clone https://github.com/seuusuario/cyber-stripe.git
cd cyber-stripe

# Instale as dependências
pip install flask requests

# Execute
python app.py
Método 2: Download Direto
bash
# Baixe o arquivo
wget https://github.com/seuusuario/cyber-stripe/raw/main/app.py

# Execute
python app.py
Método 3: Instalação Automática
O script instala dependências automaticamente na primeira execução:

bash
python app.py
# Tudo será configurado automaticamente!
🚀 Como Usar
1. Acesse a Interface
Após executar o script:

text
http://localhost:5000
2. Faça Login
Digite sua key de acesso na tela de login.

3. Cole seus cURLs
Na área de texto, cole os cURLs do Stripe:

bash
curl 'https://api.stripe.com/v1/payment_methods' \
  -H 'content-type: application/x-www-form-urlencoded' \
  --data-raw 'type=card&card[number]=4242424242424242&card[exp_month]=12&card[exp_year]=2026&card[cvc]=123'

curl 'https://seusite.com/checkout' \
  -H 'content-type: application/x-www-form-urlencoded' \
  --data-raw 'payment_method=pm_xxx&amount=100'
4. Gere a API
Clique em ⚡ GERAR API AGORA ou pressione Ctrl + Enter.

5. Baixe ou Copie
📋 COPIAR - Copia o código PHP para clipboard

💾 BAIXAR - Faz download do arquivo .php

6. Execute a API
bash
# Inicie o servidor PHP
php -S localhost:8000 api_stripe_abc123.php

# Acesse no navegador com os dados do cartão
http://localhost:8000/api_stripe_abc123.php?lista=4242424242424242|12|2026|123
🔐 Sistema de Login
Keys Disponíveis
As keys são configuradas no dicionário KEYS no código:

python
KEYS = {
    "sua-key-aqui": {
        "user": "@seuusuario", 
        "expira": "31/12/2026"
    }
}
Como Adicionar Novas Keys
python
KEYS = {
    "key-existente": {"user": "@user1", "expira": "31/12/2026"},
    
    # Adicione novas keys aqui:
    "nova-key-123": {"user": "@novouser", "expira": "01/01/2027"},
    "outra-key-456": {"user": "@outrouser", "expira": "15/06/2027"},
}
Como Desativar uma Key
python
KEYS = {
    "key-bloqueada": {
        "user": "@user", 
        "expira": "31/12/2026",
        "status": "desativado"  # Adicione esta linha
    }
}
📝 Gerando APIs
Formato de Entrada
O parser aceita cURLs em qualquer formato:

cURL Simples
bash
curl 'https://api.stripe.com/v1/payment_methods' --data-raw 'type=card&card[number]=4242424242424242'
cURL com Headers
bash
curl 'https://api.stripe.com/v1/payment_methods' \
  -H 'content-type: application/x-www-form-urlencoded' \
  -H 'authorization: Bearer pk_live_xxx' \
  --data-raw 'type=card'
Múltiplos cURLs
bash
curl 'https://api.stripe.com/v1/payment_methods' --data-raw 'type=card&card[number]=4242424242424242'

curl 'https://api.stripe.com/v1/payment_intents' --data-raw 'amount=100&currency=usd&payment_method=pm_xxx'

curl 'https://site.com/checkout' --data-raw 'payment_method=pm_xxx'
Tipos de Requisições Detectadas
Tipo	Descrição	Token Extraído
CREATE_PM	Cria Payment Method	pm_xxx
CREATE_TOKEN	Cria Token	tok_xxx
PAYMENT_INTENT	Cria Payment Intent	pi_xxx
SETUP_INTENT	Cria Setup Intent	seti_xxx
SITE_POST	Requisição para o site	-
Tokens Detectados
pm_ - Payment Method ID

pi_ - Payment Intent ID

pi_secret_ - Client Secret

tok_ - Token ID

seti_ - Setup Intent ID

csrf_token - Token CSRF
