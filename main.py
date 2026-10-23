# main.py — HIPÓLITO Stripe — Servidor principal
# Este arquivo fica NO SERVIDOR e NÃO é enviado ao navegador.
import os, sys, json, time, uuid, re, random, secrets, threading, io, hashlib
from datetime import datetime
from functools import wraps

def install(pkg):
    try: __import__(pkg.replace('-','_').replace('.','_'))
    except: os.system(f"{sys.executable} -m pip install {pkg} --quiet 2>nul")

for d in ['flask','flask-cors','werkzeug','requests','colorama']:
    install(d)

from flask import Flask, request, jsonify, session, redirect, url_for, send_from_directory, abort
from flask_cors import CORS
import requests as http_requests
from colorama import init, Fore, Style
init(autoreset=True)

# ========== IMPORTA O CORE ==========
import stripe as hipolito_core   # o arquivo stripe.py fica ao lado do main.py

# ========== CONFIG SENSÍVEL (só no servidor) ==========
PORT = int(os.environ.get('PORT', 5000))
BASE_URL = os.environ.get('RENDER_EXTERNAL_URL', f'http://localhost:{PORT}')

BOT_TOKEN = "8952767112:AAGsG1yxraZXY0IkZ3QmIGu5_jfTXhhhGas"
ADMIN_ID = 8617449427
ADMIN_PASSWORD = "hipolito"
TELEGRAM_CHANNEL = "https://t.me/hipolitoofc"
ADMIN_TAG = "@hipolitoofc"

# Keys (base64 ofuscado só pra não ficar literal no fonte)
KEYS_RAW = json.loads(__import__('base64').b64decode(
    "eyJjeWJlciI6IHsidXNlciI6ICJAaGlwb2xpdG9vZmMiLCAicGxhbm8iOiAiUFJPIiwgImV4cGlyYWNhbyI6ICIxNC8wNy8yMDI4IiwgInN0YXR1cyI6ICJhdGl2byJ9fQ=="
).decode('utf-8'))

# ========== APP ==========
app = Flask(__name__, static_folder=None)
app.config['SECRET_KEY'] = secrets.token_hex(64)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 60 * 60 * 24 * 7  # 7 dias

CORS(app, resources={r"/api/*": {"origins": "*"}})

API_STORAGE_FILE = "apis_criadas.json"
os.makedirs('scripts_gerados', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# ========== RATE LIMIT ==========
_rate = {}
def rate_limit(max_req=10, window=60):
    def deco(f):
        @wraps(f)
        def wrap(*a, **kw):
            ip = request.remote_addr or 'x'
            now = time.time()
            hits = [t for t in _rate.get(ip, []) if now - t < window]
            if len(hits) >= max_req:
                return jsonify({'status': 'error', 'message': 'Muitas requisições. Aguarde.'}), 429
            hits.append(now)
            _rate[ip] = hits
            return f(*a, **kw)
        return wrap
    return deco

# ========== STORAGE APIs ==========
def load_apis():
    if os.path.exists(API_STORAGE_FILE):
        try: return json.load(open(API_STORAGE_FILE, 'r', encoding='utf-8'))
        except: return []
    return []

def save_apis(data):
    with open(API_STORAGE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ========== TELEGRAM ==========
def tg_send(text, chat_id=ADMIN_ID):
    try:
        http_requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'},
            timeout=10
        )
    except Exception as e:
        print(f"[TG MSG ERR] {e}")

def tg_send_doc(file_bytes, filename, caption, chat_id=ADMIN_ID):
    try:
        http_requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
            data={'chat_id': chat_id, 'caption': caption[:1000]},
            files={'document': (filename, io.BytesIO(file_bytes), 'text/x-php')},
            timeout=30
        )
    except Exception as e:
        print(f"[TG DOC ERR] {e}")

def tg_polling():
    offset = 0
    while True:
        try:
            r = http_requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
                params={'offset': offset, 'timeout': 30},
                timeout=40
            ).json()
            if not r.get('ok'):
                time.sleep(5); continue
            for upd in r.get('result', []):
                offset = upd['update_id'] + 1
                msg = upd.get('message')
                if not msg: continue
                chat_id = msg['chat']['id']
                if str(chat_id) != str(ADMIN_ID):
                    continue
                txt = (msg.get('text') or '').strip()
                if txt == '/api':
                    apis = load_apis()
                    if not apis:
                        tg_send("❌ Nenhuma API criada ainda.", chat_id); continue
                    last = apis[-1]
                    tg_send_doc(
                        last.get('code','').encode('utf-8'),
                        last.get('filename', 'api.php'),
                        f"🔹 <b>ÚLTIMA API</b>\nArquivo: <code>{last.get('filename','?')}</code>\nData: {last.get('data','?')}\nUser: <code>{last.get('user','?')}</code>",
                        chat_id
                    )
                elif txt == '/apis':
                    apis = load_apis()
                    if not apis:
                        tg_send("❌ Nenhuma API criada ainda.", chat_id); continue
                    tg_send(f"📦 <b>{len(apis)} API(s)</b>\nEnviando todas...", chat_id)
                    for a in apis:
                        tg_send_doc(
                            a.get('code','').encode('utf-8'),
                            a.get('filename', 'api.php'),
                            f"🔹 <code>{a.get('filename','?')}</code>\nData: {a.get('data','?')}\nUser: <code>{a.get('user','?')}</code>",
                            chat_id
                        )
                        time.sleep(1)
                elif txt == '/start':
                    tg_send(
                        "🤖 <b>HIPÓLITO STRIPE BOT</b>\n\n"
                        "Comandos:\n"
                        "/api - Última API criada\n"
                        "/apis - Todas as APIs criadas\n"
                        "/status - Status do servidor",
                        chat_id
                    )
                elif txt == '/status':
                    apis = load_apis()
                    tg_send(f"✅ Online\n📦 APIs: {len(apis)}\n🌐 {BASE_URL}", chat_id)
        except Exception as e:
            print(f"[TG POLL ERR] {e}")
            time.sleep(5)

# ========== ROTAS ==========
@app.route('/')
def index():
    if session.get('authenticated'):
        return redirect(url_for('app_page'))
    return redirect(url_for('login_page'))

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'GET':
        if session.get('authenticated'):
            return redirect(url_for('app_page'))
        return hipolito_core.render_login(
            channel=TELEGRAM_CHANNEL,
            admin_tag=ADMIN_TAG,
            error=request.args.get('error', ''),
        )

    key = request.form.get('key', '').strip()
    if not key:
        return redirect(url_for('login_page', error='empty'))

    # Key válida = key cadastrada OU senha admin
    if key in KEYS_RAW:
        data = KEYS_RAW[key]
        if data.get('status') == 'desativado':
            return redirect(url_for('login_page', error='desativado'))
        session['authenticated'] = True
        session['user'] = data.get('user', '@hipolitoofc')
        session['plano'] = data.get('plano', 'PRO')
        session['expiracao'] = data.get('expiracao', 'N/A')
        session['key'] = key
    elif key == ADMIN_PASSWORD:
        session['authenticated'] = True
        session['user'] = '@hipolitoofc'
        session['plano'] = 'ADMIN'
        session['expiracao'] = '∞'
        session['key'] = 'admin'
    else:
        time.sleep(0.4)
        return redirect(url_for('login_page', error='invalid_key'))

    session.permanent = True
    return redirect(url_for('app_page'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/app')
def app_page():
    if not session.get('authenticated'):
        return redirect(url_for('login_page'))
    return hipolito_core.render_app(
        user=session.get('user', 'Unknown'),
        plano=session.get('plano', 'N/A'),
        expiracao=session.get('expiracao', 'N/A'),
        channel=TELEGRAM_CHANNEL,
        admin_tag=ADMIN_TAG,
    )

@app.route('/api/generate', methods=['POST'])
@rate_limit(max_req=8, window=60)
def generate_api():
    if not session.get('authenticated'):
        return jsonify({'status': 'error', 'message': 'Não autenticado'}), 401

    data = request.json or {}
    curls_text = (data.get('curls') or '').strip()
    if not curls_text:
        return jsonify({'status': 'error', 'message': 'Nenhum cURL fornecido'}), 400

    try:
        result = hipolito_core.build_api(curls_text, admin_tag=ADMIN_TAG)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Erro: {str(e)}'}), 500

    if not result.get('ok'):
        return jsonify({'status': 'error', 'message': result.get('message', 'Falha ao processar')}), 400

    php_code = result['php_code']
    filename = result['filename']

    filepath = os.path.join('scripts_gerados', filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(php_code)

    apis = load_apis()
    record = {
        'id': uuid.uuid4().hex[:8],
        'filename': filename,
        'data': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        'user': session.get('user', '?'),
        'requests_count': result['total_requests'],
        'code': php_code,
    }
    apis.append(record)
    save_apis(apis)

    # Envia pro Telegram (admin)
    tg_sent = False
    try:
        caption = (
            f"🚀 <b>NOVA API CRIADA</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📄 Arquivo: <code>{filename}</code>\n"
            f"👤 User: <code>{session.get('user','?')}</code>\n"
            f"📅 Data: {record['data']}\n"
            f"🔗 Requisições: {result['total_requests']}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<b>HIPÓLITO STRIPE</b>"
        )
        tg_send_doc(php_code.encode('utf-8'), filename, caption)
        tg_sent = True
    except Exception as e:
        print(f"[TG SEND ERR] {e}")

    return jsonify({
        'status': 'success',
        'message': f"API gerada com sucesso! {result['total_requests']} requisições.",
        'php_code': php_code,
        'filename': filename,
        'total_requests': result['total_requests'],
        'requests': result['requests_info'],
        'usage': f'php -S localhost:8000 {filename}',
        'tg_sent': tg_sent,
    })

@app.route('/ping')
def ping():
    return jsonify({'status': 'online', 'service': 'HIPOLITO-STRIPE', 'apis': len(load_apis())})

if __name__ == '__main__':
    threading.Thread(target=tg_polling, daemon=True).start()
    print(f"\n{Fore.CYAN}{'='*55}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}HIPÓLITO STRIPE — Alto Coder Professional{Style.RESET_ALL}")
    print(f"{Fore.WHITE}http://localhost:{PORT}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Telegram: /api e /apis respondem só pro admin{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*55}{Style.RESET_ALL}\n")
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)
