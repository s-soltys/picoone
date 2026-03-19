import json
import select
import socket
from utime import ticks_diff, ticks_ms

from led_patterns import PATTERN_NAMES
from morse import enqueue as morse_send, is_playing as morse_playing
from notes import add_note, delete_note, edit_note, load_notes
from sysinfo import get_info
from wifi_manager import (
    connect_to,
    delete_profile,
    get_current,
    get_profiles,
    move_profile,
    scan_networks,
    set_profile,
)


_CSS = """*{box-sizing:border-box}
body{margin:0;font-family:system-ui,sans-serif;background:#111;color:#eee}
#app{min-height:100vh}
.app-shell{max-width:460px;margin:0 auto;padding:24px 18px 32px}
.title{margin:0;font-size:1.8rem;letter-spacing:.02em}
.sub{color:#8a8a8a;margin:6px 0 0;font-size:.95rem;line-height:1.5}
.toolbar{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:18px}
.toolbar .btn{padding:10px 14px}
.panel{background:#1a1a1a;border:1px solid #333;border-radius:16px;padding:18px 16px;margin-bottom:14px}
.panel h2{margin:0 0 6px;font-size:1.1rem}
.panel p{margin:0;color:#8a8a8a;font-size:.9rem;line-height:1.4}
.home-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.card{display:block;text-decoration:none;color:inherit;background:#1a1a1a;border:2px solid #333;border-radius:16px;padding:18px 16px;transition:background .15s,border-color .15s;min-width:0}
.card h2{margin:0;font-size:1.1rem;line-height:1.1}
.card p{margin:12px 0 0;color:#8a8a8a;font-size:.9rem;line-height:1.35}
.card:hover,.card:focus{background:#202020;border-color:#555}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
button,.btn{padding:12px 10px;border:2px solid #333;border-radius:12px;background:#1a1a1a;color:#ddd;font-size:.95rem;cursor:pointer;transition:background .15s,border-color .15s}
button:hover,.btn:hover{background:#222;border-color:#555}
button.active{background:#0d5;color:#000;border-color:#0d5;font-weight:700}
button.primary,.btn.primary{background:#28a;border-color:#28a;color:#fff}
button.primary:hover,.btn.primary:hover{background:#39b;border-color:#39b}
button.warn{background:#c33;border-color:#c33;color:#fff}
button[disabled]{opacity:.55;cursor:default}
.row{display:flex;justify-content:space-between;gap:12px;padding:10px 0;border-bottom:1px solid #262626}
.row:last-child{border-bottom:0}
.row .k{color:#8a8a8a;font-size:.9rem}
.row .v{font-size:.9rem;text-align:right}
.stack{display:flex;flex-direction:column;gap:12px}
.note-form{display:flex;flex-direction:column;gap:10px;margin-bottom:14px}
.note{background:#151515;border:1px solid #333;border-radius:12px;padding:12px 12px 14px;position:relative;white-space:pre-wrap;word-wrap:break-word}
.acts{display:flex;gap:10px;flex-wrap:wrap}
.acts span,.text-btn{color:#bdbdbd;cursor:pointer;font-size:.86rem}
.acts span:hover,.text-btn:hover{color:#fff}
.empty{color:#666;font-style:italic;font-size:.92rem}
.field{width:100%;padding:10px 12px;border:2px solid #333;border-radius:12px;background:#111;color:#eee;font-size:.95rem;font-family:inherit}
textarea.field{min-height:82px;resize:vertical}
input[type=range]{width:100%}
.ctr{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
.status{border-radius:12px;padding:12px 14px;font-size:.92rem;line-height:1.4}
.status.good{background:#0d5;color:#000}
.status.bad{background:#c33;color:#fff}
.status.neutral{background:#202020;color:#ddd;border:1px solid #333}
.split{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
.meta{color:#8a8a8a;font-size:.82rem;margin-top:4px}
.nav{display:flex;gap:8px;flex-wrap:wrap}
.pill{display:inline-block;padding:4px 8px;border-radius:999px;background:#202020;border:1px solid #333;color:#bdbdbd;font-size:.78rem}
.section-title{margin:6px 0 10px;font-size:1rem;color:#9b9b9b}
.net,.prof{background:#151515;border:1px solid #333;border-radius:12px;padding:12px}
.conn-form{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.spacer{height:6px}
.footer-note{color:#767676;font-size:.82rem;line-height:1.4}
.touch-wrap{display:flex;flex-direction:column;gap:12px}
.touch-canvas{display:block;width:100%;height:auto;border:2px solid #333;border-radius:18px;background:#151515;cursor:pointer;touch-action:none;user-select:none;-webkit-user-select:none}
.touch-canvas:focus{outline:none;border-color:#888}
.touch-canvas.active{border-color:#0d5}
.touch-state{text-align:center;font-size:.95rem}
.touch-hint{color:#8a8a8a;font-size:.9rem;line-height:1.4;text-align:center}
.loading{display:flex;align-items:center;justify-content:center;min-height:100vh;padding:24px;text-align:center;color:#9a9a9a}
@media (max-width:560px){
  .home-grid{grid-template-columns:1fr}
}
@media (max-width:420px){
  .app-shell{padding:18px 14px 28px}
  .grid{grid-template-columns:1fr}
  .toolbar{align-items:flex-start;flex-direction:column}
}
"""


_INDEX_HTML = """<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PicoOne</title>
<style>%s</style>
</head><body>
<div id="app" class="loading">Loading...</div>
<script>window.__PICO_BOOTSTRAP__=%s;window.setTimeout(function(){if(!window.__pico_app_started){var root=document.getElementById('app');if(root){root.innerHTML='PicoOne needs to load Preact from the CDN. Connect this browser to the internet and reload.';}}},4000);</script>
<script src="https://unpkg.com/preact@10.26.4/dist/preact.umd.js"></script>
<script src="https://unpkg.com/preact@10.26.4/hooks/dist/hooks.umd.js"></script>
<script src="https://unpkg.com/htm@3.1.1/dist/htm.umd.js"></script>
<script src="/static/app.js"></script>
</body></html>"""


_REDIRECT_HTML = """<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PicoOne</title>
</head><body>
<script>location.replace('/#%s');</script>
<p>Redirecting to <a href="/#%s">PicoOne</a>...</p>
</body></html>"""


_STATIC_APP_JS = "web_app.js"
_LEGACY_ROUTES = {
    "/led": "/led",
    "/touch": "/touch",
    "/notes": "/notes",
    "/sysinfo": "/sysinfo",
    "/morse": "/morse",
    "/wifi": "/wifi",
    "/wifi/scan": "/wifi/scan",
}


def _json_script_value(value):
    return json.dumps(value).replace("</", "<\\/")


def _read_static_text(path):
    try:
        with open(path, "r") as f:
            return f.read()
    except OSError:
        return "document.getElementById('app').textContent='Missing static asset: {}';".format(path)


def _build_bootstrap(led_ctrl):
    return {
        "pattern_names": list(PATTERN_NAMES),
        "led_mode": led_ctrl.mode,
        "notes": load_notes(),
        "sysinfo": get_info(),
        "wifi_current": get_current(),
        "wifi_profiles": get_profiles(),
    }


def _build_shell(led_ctrl):
    return _INDEX_HTML % (_CSS, _json_script_value(_build_bootstrap(led_ctrl)))


def _build_redirect(path):
    route = _LEGACY_ROUTES.get(path, "/")
    return _REDIRECT_HTML % (route, route)


def _url_decode(s):
    r = s.replace("+", " ")
    parts = r.split("%")
    out = [parts[0]]
    for p in parts[1:]:
        try:
            out.append(chr(int(p[:2], 16)) + p[2:])
        except (ValueError, IndexError):
            out.append("%" + p)
    return "".join(out)


def _read_body(cl, request):
    if "\r\n\r\n" not in request:
        return ""
    headers, body = request.split("\r\n\r\n", 1)
    length = 0
    for line in headers.split("\r\n")[1:]:
        if line.lower().startswith("content-length:"):
            try:
                length = int(line.split(":", 1)[1].strip())
            except ValueError:
                length = 0
            break
    while len(body) < length:
        chunk = cl.recv(length - len(body))
        if not chunk:
            break
        body += chunk.decode("utf-8", "ignore")
    if length:
        return body[:length]
    return body


def _json_notes():
    return json.dumps({"notes": load_notes()})


def start_server(led_ctrl, port=80):
    addr = socket.getaddrinfo("0.0.0.0", port)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(4)
    print("Web server listening on port", port)
    return s


_poller = None
_pending_wifi_connect = None


def _get_poller(s):
    global _poller
    if _poller is None:
        _poller = select.poll()
        _poller.register(s, select.POLLIN)
    return _poller


def _send_all(cl, data):
    if isinstance(data, str):
        data = data.encode()
    view = memoryview(data)
    sent_total = 0
    while sent_total < len(view):
        sent = cl.send(view[sent_total:])
        if sent is None or sent <= 0:
            raise OSError("socket send failed")
        sent_total += sent


def _send(cl, ctype, body):
    if isinstance(body, str):
        body = body.encode()
    _send_all(
        cl,
        "HTTP/1.0 200 OK\r\nContent-Type: {}; charset=utf-8\r\nContent-Length: {}\r\nConnection: close\r\n\r\n".format(
            ctype, len(body)
        ),
    )
    _send_all(cl, body)


def _queue_wifi_connect(ssid, password, delay_ms=800):
    global _pending_wifi_connect
    if _pending_wifi_connect is not None:
        return False
    ssid = ssid.strip()
    if not ssid:
        return False
    _pending_wifi_connect = {
        "ssid": ssid,
        "password": password,
        "due": ticks_ms() + delay_ms,
    }
    return True


def _run_pending_wifi_connect():
    global _pending_wifi_connect
    job = _pending_wifi_connect
    if job is None:
        return
    if ticks_diff(ticks_ms(), job["due"]) < 0:
        return
    _pending_wifi_connect = None
    try:
        print("WiFi connect:", job["ssid"])
        ok = connect_to(job["ssid"], job["password"])
        print("WiFi connect result:", ok)
    except Exception as e:
        print("wifi connect error:", e)


def handle_client(s, led_ctrl):
    _run_pending_wifi_connect()
    poller = _get_poller(s)
    events = poller.poll(100)
    if not events:
        return
    try:
        cl, addr = s.accept()
    except OSError:
        return
    try:
        cl.settimeout(5)
        request = cl.recv(2048).decode("utf-8", "ignore")
        path = ""
        if request.startswith("GET ") or request.startswith("POST "):
            path = request.split(" ", 2)[1]
        path_only = path.split("?", 1)[0]

        if path_only == "/favicon.ico":
            _send_all(cl, "HTTP/1.0 204 No Content\r\nConnection: close\r\n\r\n")
            cl.close()
            return

        if path.startswith("/set?"):
            try:
                qs = path.split("?", 1)[1]
                params = dict(p.split("=") for p in qs.split("&") if "=" in p)
                mode = int(params.get("mode", -1))
                led_ctrl.set_mode(mode)
            except Exception:
                pass
            _send(cl, "application/json", json.dumps({"mode": led_ctrl.mode}))

        elif path == "/api/led":
            _send(cl, "application/json", json.dumps({"mode": led_ctrl.mode, "pattern_names": list(PATTERN_NAMES)}))

        elif path.startswith("/api/led/touch-mode") and "POST" in request:
            active = False
            try:
                qs = path.split("?", 1)[1]
                params = dict(p.split("=") for p in qs.split("&") if "=" in p)
                active = params.get("active", "0") in ("1", "true", "on")
            except Exception:
                pass
            if active:
                led_ctrl.enable_touch_mode()
            else:
                led_ctrl.disable_touch_mode()
            _send(cl, "application/json", json.dumps({"ok": True, "active": led_ctrl.touch_mode_active}))

        elif path.startswith("/api/led/touch") and "POST" in request:
            pressed = False
            try:
                qs = path.split("?", 1)[1]
                params = dict(p.split("=") for p in qs.split("&") if "=" in p)
                pressed = params.get("state", "0") in ("1", "true", "on")
            except Exception:
                pass
            led_ctrl.set_touch_pressed(pressed)
            _send(cl, "application/json", json.dumps({"ok": True, "pressed": pressed}))

        elif path == "/api/bootstrap":
            _send(cl, "application/json", json.dumps(_build_bootstrap(led_ctrl)))

        elif path == "/notes/add" and "POST" in request:
            text = _read_body(cl, request)
            add_note(_url_decode(text))
            _send(cl, "application/json", _json_notes())

        elif path.startswith("/notes/del") and "POST" in request:
            try:
                qs = path.split("?", 1)[1]
                params = dict(p.split("=") for p in qs.split("&") if "=" in p)
                delete_note(int(params.get("i", -1)))
            except Exception:
                pass
            _send(cl, "application/json", _json_notes())

        elif path == "/notes/edit" and "POST" in request:
            body = _url_decode(_read_body(cl, request))
            parts = body.split("\n", 1)
            if len(parts) == 2:
                try:
                    edit_note(int(parts[0]), parts[1])
                except Exception:
                    pass
            _send(cl, "application/json", _json_notes())

        elif path == "/api/sysinfo":
            _send(cl, "application/json", json.dumps(get_info()))

        elif path.startswith("/api/morse") and "POST" in request:
            wpm = 12
            try:
                qs = path.split("?", 1)[1]
                params = dict(p.split("=") for p in qs.split("&") if "=" in p)
                wpm = int(params.get("wpm", 12))
            except Exception:
                pass
            text = _url_decode(_read_body(cl, request))
            if not morse_playing():
                morse_send(text, wpm)
                _send(cl, "application/json", '{"ok":true}')
            else:
                _send(cl, "application/json", '{"ok":false}')

        elif path == "/api/wifi/status":
            _send(cl, "application/json", json.dumps(get_current()))

        elif path == "/api/wifi/profiles":
            _send(cl, "application/json", json.dumps(get_profiles()))

        elif path == "/api/wifi/profile" and "POST" in request:
            body = _read_body(cl, request).replace("\r\n", "\n")
            parts = body.split("\n", 2)
            if len(parts) >= 3:
                try:
                    idx = int(parts[0])
                except ValueError:
                    idx = -1
                set_profile(idx, parts[1], parts[2])
            _send(cl, "application/json", json.dumps(get_profiles()))

        elif path == "/api/wifi/scan":
            _send(cl, "application/json", json.dumps(scan_networks()))

        elif path == "/api/wifi/connect" and "POST" in request:
            body = _read_body(cl, request).replace("\r\n", "\n")
            parts = body.split("\n", 1)
            if len(parts) == 2:
                ok = _queue_wifi_connect(parts[0], parts[1])
                _send(cl, "application/json", json.dumps({"ok": ok, "pending": ok, "busy": not ok}))
            else:
                _send(cl, "application/json", '{"ok": false, "pending": false, "busy": false}')

        elif path.startswith("/api/wifi/move") and "POST" in request:
            try:
                qs = path.split("?", 1)[1]
                params = dict(p.split("=") for p in qs.split("&") if "=" in p)
                move_profile(int(params.get("i", -1)), int(params.get("d", 0)))
            except Exception:
                pass
            _send(cl, "application/json", json.dumps(get_profiles()))

        elif path.startswith("/api/wifi/del") and "POST" in request:
            try:
                qs = path.split("?", 1)[1]
                params = dict(p.split("=") for p in qs.split("&") if "=" in p)
                delete_profile(int(params.get("i", -1)))
            except Exception:
                pass
            _send(cl, "application/json", json.dumps(get_profiles()))

        elif path_only == "/static/app.js":
            _send(cl, "application/javascript", _read_static_text(_STATIC_APP_JS))

        elif path_only in _LEGACY_ROUTES:
            _send(cl, "text/html", _build_redirect(path_only))

        else:
            _send(cl, "text/html", _build_shell(led_ctrl))

    except Exception as e:
        print("client error:", e)
    finally:
        cl.close()
