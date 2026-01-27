"""Fingerprint collection web server for Telegram Web App."""
import json
import hashlib
import hmac
import logging
import aiohttp
from urllib.parse import parse_qs
from aiohttp import web

from bot.config import BOT_TOKEN
from bot import database as db

logger = logging.getLogger(__name__)

# HTML page for fingerprint collection
FINGERPRINT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PayPort Verification</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--tg-theme-bg-color, #fff);
            color: var(--tg-theme-text-color, #000);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            text-align: center;
            max-width: 320px;
        }
        .spinner {
            width: 50px;
            height: 50px;
            border: 4px solid var(--tg-theme-hint-color, #ccc);
            border-top-color: var(--tg-theme-button-color, #3390ec);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        h2 { margin-bottom: 10px; font-size: 18px; }
        p { color: var(--tg-theme-hint-color, #999); font-size: 14px; }
        .success { color: #4caf50; }
        .error { color: #f44336; }
    </style>
</head>
<body>
    <div class="container">
        <div class="spinner" id="spinner"></div>
        <h2 id="status">Verifying...</h2>
        <p id="message">Please wait a moment</p>
    </div>
    
    <script>
        const tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();
        
        async function collectFingerprint() {
            const fp = {};
            
            // Basic info
            fp.screen_resolution = screen.width + 'x' + screen.height;
            fp.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
            fp.language = navigator.language || navigator.userLanguage;
            fp.platform = navigator.platform;
            fp.user_agent = navigator.userAgent;
            fp.color_depth = screen.colorDepth;
            fp.pixel_ratio = window.devicePixelRatio;
            fp.hardware_concurrency = navigator.hardwareConcurrency || 'unknown';
            fp.touch_support = 'ontouchstart' in window;
            
            // Canvas fingerprint
            try {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                canvas.width = 200;
                canvas.height = 50;
                ctx.textBaseline = 'top';
                ctx.font = '14px Arial';
                ctx.fillStyle = '#f60';
                ctx.fillRect(0, 0, 100, 50);
                ctx.fillStyle = '#069';
                ctx.fillText('PayPort FP', 2, 2);
                ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
                ctx.fillText('PayPort FP', 4, 17);
                fp.canvas_hash = await hashString(canvas.toDataURL());
            } catch (e) {
                fp.canvas_hash = 'error';
            }
            
            // WebGL fingerprint
            try {
                const canvas = document.createElement('canvas');
                const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                if (gl) {
                    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                    fp.webgl_vendor = gl.getParameter(debugInfo ? debugInfo.UNMASKED_VENDOR_WEBGL : gl.VENDOR);
                    fp.webgl_renderer = gl.getParameter(debugInfo ? debugInfo.UNMASKED_RENDERER_WEBGL : gl.RENDERER);
                    fp.webgl_hash = await hashString(fp.webgl_vendor + fp.webgl_renderer);
                }
            } catch (e) {
                fp.webgl_hash = 'error';
            }
            
            // Fonts detection (simplified)
            try {
                const testFonts = ['Arial', 'Verdana', 'Times New Roman', 'Courier New', 'Georgia', 'Comic Sans MS'];
                const detected = [];
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                const testString = 'mmmmmmmmmmlli';
                ctx.font = '72px monospace';
                const baseWidth = ctx.measureText(testString).width;
                for (const font of testFonts) {
                    ctx.font = '72px ' + font + ', monospace';
                    if (ctx.measureText(testString).width !== baseWidth) {
                        detected.push(font);
                    }
                }
                fp.fonts_hash = await hashString(detected.join(','));
            } catch (e) {
                fp.fonts_hash = 'error';
            }
            
            // Telegram data
            if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
                fp.telegram_id = tg.initDataUnsafe.user.id;
                fp.is_premium = tg.initDataUnsafe.user.is_premium ? 1 : 0;
            }
            
            return fp;
        }
        
        async function hashString(str) {
            const encoder = new TextEncoder();
            const data = encoder.encode(str);
            const hashBuffer = await crypto.subtle.digest('SHA-256', data);
            const hashArray = Array.from(new Uint8Array(hashBuffer));
            return hashArray.map(b => b.toString(16).padStart(2, '0')).join('').substring(0, 32);
        }
        
        async function sendFingerprint() {
            try {
                const fp = await collectFingerprint();
                fp.init_data = tg.initData;
                
                const response = await fetch('/api/fingerprint', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(fp)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    document.getElementById('spinner').style.display = 'none';
                    document.getElementById('status').textContent = '✅ Verified';
                    document.getElementById('status').className = 'success';
                    document.getElementById('message').textContent = 'Click Continue to start questionnaire';
                    
                    // Prepare data to send
                    const dataToSend = JSON.stringify({ verified: true, fp_id: result.fp_id });
                    console.log('Sending data:', dataToSend);
                    
                    // Use MainButton to ensure data is sent reliably
                    tg.MainButton.setText('Continue / Продолжить');
                    tg.MainButton.show();
                    tg.MainButton.onClick(() => {
                        try {
                            tg.sendData(dataToSend);
                            console.log('Data sent successfully');
                            tg.close();
                        } catch (e) {
                            console.error('Error sending data:', e);
                            // Retry once
                            setTimeout(() => {
                                tg.sendData(dataToSend);
                                tg.close();
                            }, 500);
                        }
                    });
                } else {
                    throw new Error(result.error || 'Unknown error');
                }
            } catch (e) {
                document.getElementById('spinner').style.display = 'none';
                document.getElementById('status').textContent = '❌ Error';
                document.getElementById('status').className = 'error';
                document.getElementById('message').textContent = e.message;
                
                setTimeout(() => {
                    tg.sendData(JSON.stringify({ verified: false, error: e.message }));
                    tg.close();
                }, 2000);
            }
        }
        
        // Start fingerprinting
        sendFingerprint();
    </script>
</body>
</html>
"""


def validate_telegram_data(init_data: str) -> dict:
    """Validate Telegram Web App init data.
    
    Returns user data if valid, None otherwise.
    """
    if not init_data:
        return None
    
    try:
        parsed = parse_qs(init_data)
        
        # Get hash
        received_hash = parsed.get('hash', [None])[0]
        if not received_hash:
            return None
        
        # Build data check string
        data_pairs = []
        for key, value in parsed.items():
            if key != 'hash':
                data_pairs.append(f"{key}={value[0]}")
        data_pairs.sort()
        data_check_string = '\n'.join(data_pairs)
        
        # Compute secret key
        secret_key = hmac.new(
            b'WebAppData',
            BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()
        
        # Compute hash
        computed_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if computed_hash != received_hash:
            logger.warning("Invalid Telegram hash")
            return None
        
        # Parse user data
        user_data = parsed.get('user', [None])[0]
        if user_data:
            return json.loads(user_data)
        
        return None
    except Exception as e:
        logger.error(f"Error validating Telegram data: {e}")
        return None


async def handle_fingerprint_page(request):
    """Serve the fingerprint collection page."""
    return web.Response(
        text=FINGERPRINT_HTML,
        content_type='text/html'
    )


async def handle_fingerprint_submit(request):
    """Handle fingerprint submission from Web App."""
    try:
        data = await request.json()
        
        # Get real IP
        ip_address = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
        if not ip_address:
            ip_address = request.headers.get('X-Real-IP', '')
        if not ip_address:
            ip_address = request.remote
        
        data['ip_address'] = ip_address
        
        # Validate Telegram data
        init_data = data.pop('init_data', '')
        user = validate_telegram_data(init_data)
        
        telegram_id = data.get('telegram_id')
        if user:
            telegram_id = user.get('id')
            data['is_premium'] = 1 if user.get('is_premium') else 0
        
        if not telegram_id:
            return web.json_response({'success': False, 'error': 'No telegram_id'})
        
        # Save fingerprint
        fp_id = await db.save_fingerprint(telegram_id, data)
        
        # Check for matches
        matches = await db.find_matching_fingerprints(data, exclude_telegram_id=telegram_id)
        
        logger.info(f"Fingerprint saved: {fp_id}, IP: {ip_address}, matches: {len(matches)}")
        
        # If pending verification exists, send "Continue" button to user
        pending = await db.get_pending_verification(telegram_id)
        if pending:
            await send_continue_message(telegram_id)
        
        return web.json_response({
            'success': True,
            'fp_id': fp_id,
            'matches_count': len(matches)
        })
        
    except Exception as e:
        logger.error(f"Fingerprint error: {e}")
        return web.json_response({'success': False, 'error': str(e)})


def create_fingerprint_app() -> web.Application:
    """Create aiohttp app for fingerprint server."""
    app = web.Application()
    app.router.add_get('/fingerprint', handle_fingerprint_page)
    app.router.add_post('/api/fingerprint', handle_fingerprint_submit)
    return app


async def send_continue_message(telegram_id: int):
    """Send a message with a Continue button to the user via Telegram API.
    
    NOTE: This is a fallback in case web_app_data is not delivered.
    """
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": telegram_id,
            "text": "✅ Верификация пройдена.\nНажмите «Продолжить», чтобы начать анкету.",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "▶️ Продолжить", "callback_data": "start_after_verification"}]
                ]
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=10) as resp:
                if resp.status != 200:
                    logger.warning(f"Failed to send continue message: {resp.status}")
    except Exception as e:
        logger.error(f"Error sending continue message: {e}")
