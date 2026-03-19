import socket
import json
from led_patterns import PATTERN_NAMES
from notes import load_notes, add_note, delete_note, edit_note
from sysinfo import get_info
from morse import enqueue as morse_send, is_playing as morse_playing
from uptime import load_entries as uptime_entries, save_current as uptime_save, get_current_uptime, format_duration
from reaction import get_state as rxn_state, start as rxn_start, react as rxn_react
from pomodoro import get_status as pom_status, configure as pom_configure, start as pom_start, stop as pom_stop

# ---------------------------------------------------------------------------
# Shared CSS
# ---------------------------------------------------------------------------
_CSS = """*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;background:#111;color:#eee;
     display:flex;flex-direction:column;align-items:center;padding:24px}
h1{margin-bottom:4px;font-size:1.6rem}
p.sub{color:#888;margin-bottom:24px;font-size:.9rem}
a.back{color:#888;text-decoration:none;font-size:.9rem;margin-bottom:18px}
a.back:hover{color:#ccc}
.card{width:100%%;max-width:420px;background:#1a1a1a;border:2px solid #333;
      border-radius:14px;padding:24px 20px;margin-bottom:14px;
      text-decoration:none;color:#eee;display:block;transition:all .15s}
.card:hover{border-color:#555;background:#222}
.card h2{font-size:1.1rem;margin-bottom:4px}
.card p{color:#888;font-size:.85rem}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;width:100%%;max-width:420px}
button,.btn{padding:12px 8px;border:2px solid #333;border-radius:10px;
       background:#1a1a1a;color:#ccc;font-size:.95rem;cursor:pointer;transition:all .15s}
button:hover,.btn:hover{background:#222;border-color:#555}
button.active{background:#0d5;color:#000;border-color:#0d5;font-weight:700}
.wrap{width:100%%;max-width:420px}
.note-form{display:flex;gap:8px;margin-bottom:14px}
.note-form textarea{flex:1;padding:10px;border:2px solid #333;border-radius:10px;
     background:#1a1a1a;color:#eee;font-size:.9rem;resize:vertical;
     min-height:60px;font-family:inherit}
.note-form .btn{white-space:nowrap;align-self:flex-end;padding:10px 16px;
     background:#28a;border-color:#28a;color:#fff}
.note-form .btn:hover{background:#39b}
.note{background:#1a1a1a;border:1px solid #333;border-radius:10px;
      padding:12px;margin-bottom:8px;position:relative;word-wrap:break-word;
      white-space:pre-wrap;font-size:.9rem;line-height:1.4}
.note .acts{position:absolute;top:8px;right:8px;display:flex;gap:6px}
.note .acts span{cursor:pointer;opacity:.5;font-size:.85rem}
.note .acts span:hover{opacity:1}
.empty{color:#555;font-style:italic;font-size:.9rem}
.row{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #222}
.row .k{color:#888;font-size:.9rem}.row .v{font-size:.9rem}
input[type=text],input[type=number],textarea{padding:10px;border:2px solid #333;
     border-radius:10px;background:#1a1a1a;color:#eee;font-size:.9rem;font-family:inherit}
input[type=range]{width:100%%}
.big{font-size:3rem;font-weight:700;text-align:center;margin:18px 0}
.med{font-size:1.4rem;text-align:center;margin:10px 0;color:#888}
.ctr{display:flex;gap:10px;justify-content:center;margin:14px 0}"""

# ---------------------------------------------------------------------------
# Home page
# ---------------------------------------------------------------------------
_HOME = """<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PicoOne</title><style>%s</style></head><body>
<h1>PicoOne</h1><p class="sub">picoone.local</p>
<a class="card" href="/led"><h2>LED Control</h2><p>15 patterns &mdash; tap to switch</p></a>
<a class="card" href="/notes"><h2>Notes</h2><p>Quick notes stored on the Pico</p></a>
<a class="card" href="/sysinfo"><h2>System Info</h2><p>Temperature, RAM, WiFi &mdash; live</p></a>
<a class="card" href="/morse"><h2>Morse Code</h2><p>Type text, LED blinks it out</p></a>
<a class="card" href="/uptime"><h2>Uptime Scoreboard</h2><p>Boot history &amp; durations</p></a>
<a class="card" href="/reaction"><h2>Reaction Game</h2><p>Test your reflexes via LED</p></a>
<a class="card" href="/pomodoro"><h2>Pomodoro Timer</h2><p>Focus timer with LED cues</p></a>
</body></html>"""

# ---------------------------------------------------------------------------
# LED page
# ---------------------------------------------------------------------------
_LED = """<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PicoOne — LED</title><style>%s</style></head><body>
<h1>LED Control</h1>
<a class="back" href="/">&larr; Home</a>
<div class="grid">%s</div>
<script>
function pick(m){
  fetch('/set?mode='+m).then(r=>r.json()).then(d=>{
    document.querySelectorAll('button').forEach(b=>{
      b.classList.toggle('active',parseInt(b.dataset.m)===d.mode);
    });
  });
}
</script></body></html>"""

# ---------------------------------------------------------------------------
# Notes page
# ---------------------------------------------------------------------------
_NOTES = """<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PicoOne — Notes</title><style>%s</style></head><body>
<h1>Notes</h1>
<a class="back" href="/">&larr; Home</a>
<div class="wrap">
<div class="note-form">
<textarea id="nt" placeholder="Write a note..."></textarea>
<div class="btn" onclick="addNote()">Add</div>
</div>
<div id="notes">%s</div>
</div>
<script>
function addNote(){
  var t=document.getElementById('nt');
  if(!t.value.trim())return;
  fetch('/notes/add',{method:'POST',body:t.value}).then(r=>r.json()).then(d=>{
    t.value='';renderNotes(d.notes);
  });
}
function delNote(i){
  fetch('/notes/del?i='+i,{method:'POST'}).then(r=>r.json()).then(d=>renderNotes(d.notes));
}
function editNote(i){
  var el=document.getElementById('n'+i);
  var txt=el.innerText;
  var nv=prompt('Edit note:',txt);
  if(nv!==null&&nv.trim()){
    fetch('/notes/edit',{method:'POST',body:i+'\\n'+nv}).then(r=>r.json()).then(d=>renderNotes(d.notes));
  }
}
function renderNotes(notes){
  var c=document.getElementById('notes');
  if(!notes.length){c.innerHTML='<div class="empty">No notes yet.</div>';return;}
  c.innerHTML=notes.map(function(n,i){
    return '<div class="note"><span id="n'+i+'">'+esc(n)+'</span>'+
      '<div class="acts"><span onclick="editNote('+i+')">edit</span>'+
      '<span onclick="delNote('+i+')">del</span></div></div>';
  }).join('');
}
function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
</script></body></html>"""

# ---------------------------------------------------------------------------
# System Info page
# ---------------------------------------------------------------------------
_SYSINFO = """<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PicoOne — System Info</title><style>%s</style></head><body>
<h1>System Info</h1>
<a class="back" href="/">&larr; Home</a>
<div class="wrap" id="si">%s</div>
<script>
function refresh(){
  fetch('/api/sysinfo').then(r=>r.json()).then(d=>{
    var h='';
    var rows=[['Temperature',d.temp_c+' C'],['CPU',d.cpu_mhz+' MHz'],
      ['RAM',d.ram_free_kb+' / '+d.ram_total_kb+' KB ('+d.ram_pct+'%% used)'],
      ['Uptime',d.uptime],['WiFi RSSI',d.rssi+' dBm'],['IP',d.ip]];
    rows.forEach(function(r){h+='<div class="row"><span class="k">'+r[0]+'</span><span class="v">'+r[1]+'</span></div>';});
    document.getElementById('si').innerHTML=h;
  });
}
setInterval(refresh,2000);
</script></body></html>"""

# ---------------------------------------------------------------------------
# Morse page
# ---------------------------------------------------------------------------
_MORSE = """<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PicoOne — Morse Code</title><style>%s</style></head><body>
<h1>Morse Code</h1>
<a class="back" href="/">&larr; Home</a>
<div class="wrap">
<input id="mt" type="text" placeholder="Type your message..." style="width:100%%;margin-bottom:12px">
<div style="margin-bottom:12px">
<label style="color:#888;font-size:.85rem">Speed: <span id="wv">12</span> WPM</label>
<input type="range" id="ws" min="5" max="25" value="12" oninput="document.getElementById('wv').textContent=this.value">
</div>
<div class="ctr"><button onclick="sendMorse()">Send via LED</button></div>
<p id="ms" class="med"></p>
</div>
<script>
function sendMorse(){
  var t=document.getElementById('mt').value;
  var w=document.getElementById('ws').value;
  if(!t.trim())return;
  document.getElementById('ms').textContent='Sending...';
  fetch('/api/morse?wpm='+w,{method:'POST',body:t}).then(r=>r.json()).then(d=>{
    document.getElementById('ms').textContent=d.ok?'Blinking now!':'Busy';
  });
}
</script></body></html>"""

# ---------------------------------------------------------------------------
# Uptime page
# ---------------------------------------------------------------------------
_UPTIME = """<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PicoOne — Uptime</title><style>%s</style></head><body>
<h1>Uptime Scoreboard</h1>
<a class="back" href="/">&larr; Home</a>
<div class="wrap">%s</div>
</body></html>"""

# ---------------------------------------------------------------------------
# Reaction page
# ---------------------------------------------------------------------------
_REACTION = """<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PicoOne — Reaction Game</title><style>%s</style></head><body>
<h1>Reaction Game</h1>
<a class="back" href="/">&larr; Home</a>
<div class="wrap" style="text-align:center">
<p class="med" id="inst">When the LED turns on, tap the button!</p>
<div class="big" id="rt">-</div>
<p class="med" id="best"></p>
<div class="ctr">
<button id="gb" onclick="go()">Start</button>
<button id="rb" onclick="tap()" style="display:none">TAP!</button>
</div>
</div>
<script>
var polling;
function go(){
  fetch('/api/reaction/start',{method:'POST'}).then(r=>r.json()).then(function(){
    document.getElementById('gb').style.display='none';
    document.getElementById('rb').style.display='';
    document.getElementById('inst').textContent='Wait for the LED...';
    document.getElementById('rt').textContent='-';
  });
}
function tap(){
  fetch('/api/reaction/tap',{method:'POST'}).then(r=>r.json()).then(function(d){
    document.getElementById('rb').style.display='none';
    document.getElementById('gb').style.display='';
    if(d.last_ms<0){
      document.getElementById('rt').textContent='Too early!';
      document.getElementById('inst').textContent='You tapped before the LED lit.';
    }else{
      document.getElementById('rt').textContent=d.last_ms+' ms';
      document.getElementById('inst').textContent='LED blinks '+Math.max(1,Math.floor(d.last_ms/100))+' times';
    }
    if(d.best_ms>0)document.getElementById('best').textContent='Best: '+d.best_ms+' ms';
  });
}
</script></body></html>"""

# ---------------------------------------------------------------------------
# Pomodoro page
# ---------------------------------------------------------------------------
_POMODORO = """<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PicoOne — Pomodoro</title><style>%s</style></head><body>
<h1>Pomodoro Timer</h1>
<a class="back" href="/">&larr; Home</a>
<div class="wrap" style="text-align:center">
<div class="big" id="tm">--:--</div>
<p class="med" id="ph">Idle</p>
<div style="display:flex;gap:12px;margin:14px 0;justify-content:center">
<label style="color:#888;font-size:.85rem">Work <input id="wm" type="number" value="25" min="1" max="120" style="width:60px"> min</label>
<label style="color:#888;font-size:.85rem">Break <input id="bm" type="number" value="5" min="1" max="60" style="width:60px"> min</label>
</div>
<div class="ctr">
<button onclick="pomStart()">Start</button>
<button onclick="pomStop()">Stop</button>
</div>
</div>
<script>
function fmt(s){var m=Math.floor(s/60),ss=s%%60;return (m<10?'0':'')+m+':'+(ss<10?'0':'')+ss;}
function pomStart(){
  var w=document.getElementById('wm').value;
  var b=document.getElementById('bm').value;
  fetch('/api/pom/start?w='+w+'&b='+b,{method:'POST'}).then(r=>r.json()).then(upd);
}
function pomStop(){fetch('/api/pom/stop',{method:'POST'}).then(r=>r.json()).then(upd);}
function upd(d){
  document.getElementById('tm').textContent=fmt(d.remaining);
  var labels={'idle':'Idle','work':'Working (LED slow pulse)','break_':'Break (LED fast pulse)','alert':'Transition!'};
  document.getElementById('ph').textContent=labels[d.state]||d.state;
}
function poll(){fetch('/api/pom/status').then(r=>r.json()).then(upd);}
setInterval(poll,1000);poll();
</script></body></html>"""


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------
def _build_buttons(active_mode):
    b = ""
    for i, name in enumerate(PATTERN_NAMES):
        cls = ' class="active"' if i == active_mode else ""
        b += '<button data-m="{i}"{cls} onclick="pick({i})">{name}</button>\n'.format(
            i=i, cls=cls, name=name
        )
    return b


def _build_notes_html(notes):
    if not notes:
        return '<div class="empty">No notes yet.</div>'
    parts = []
    for i, n in enumerate(notes):
        safe = n.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        parts.append(
            '<div class="note"><span id="n{i}">{n}</span>'
            '<div class="acts"><span onclick="editNote({i})">edit</span>'
            '<span onclick="delNote({i})">del</span></div></div>'.format(i=i, n=safe)
        )
    return "".join(parts)


def _build_sysinfo_html(info):
    rows = [
        ("Temperature", "{} C".format(info["temp_c"])),
        ("CPU", "{} MHz".format(info["cpu_mhz"])),
        ("RAM", "{} / {} KB ({}% used)".format(info["ram_free_kb"], info["ram_total_kb"], info["ram_pct"])),
        ("Uptime", info["uptime"]),
        ("WiFi RSSI", "{} dBm".format(info["rssi"])),
        ("IP", info["ip"]),
    ]
    return "".join('<div class="row"><span class="k">{}</span><span class="v">{}</span></div>'.format(k, v) for k, v in rows)


def _build_uptime_html():
    uptime_save()
    entries = uptime_entries()
    cur = get_current_uptime()
    html = '<div class="row"><span class="k">Current session</span><span class="v" style="color:#0d5">{}</span></div>'.format(format_duration(cur))
    if entries:
        for e in entries:
            html += '<div class="row"><span class="k">Boot #{}</span><span class="v">{}</span></div>'.format(e["id"], format_duration(e["seconds"]))
    else:
        html += '<div class="empty">No history yet.</div>'
    return html


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
    if "\r\n\r\n" in request:
        return request.split("\r\n\r\n", 1)[1]
    return ""


def _json_notes():
    return json.dumps({"notes": load_notes()})


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
def start_server(led_ctrl, port=80):
    addr = socket.getaddrinfo("0.0.0.0", port)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(2)
    s.setblocking(False)
    print("Web server listening on port", port)
    return s


def _send(cl, ctype, body):
    cl.send("HTTP/1.0 200 OK\r\nContent-Type: {}\r\nConnection: close\r\n\r\n".format(ctype))
    if isinstance(body, str):
        body = body.encode()
    i = 0
    while i < len(body):
        chunk = body[i:i + 512]
        cl.send(chunk)
        i += len(chunk)


def handle_client(s, led_ctrl):
    try:
        cl, addr = s.accept()
    except OSError:
        return
    try:
        cl.settimeout(5)
        request = cl.recv(2048).decode("utf-8")
        path = ""
        if request.startswith("GET ") or request.startswith("POST "):
            path = request.split(" ", 2)[1]

        # --- API: LED mode ---
        if path.startswith("/set?"):
            try:
                qs = path.split("?", 1)[1]
                params = dict(p.split("=") for p in qs.split("&") if "=" in p)
                mode = int(params.get("mode", -1))
                led_ctrl.set_mode(mode)
            except Exception:
                pass
            _send(cl, "application/json", json.dumps({"mode": led_ctrl.mode}))

        # --- API: Notes ---
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

        # --- API: System Info ---
        elif path == "/api/sysinfo":
            _send(cl, "application/json", json.dumps(get_info()))

        # --- API: Morse ---
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

        # --- API: Reaction ---
        elif path == "/api/reaction/start" and "POST" in request:
            rxn_start()
            _send(cl, "application/json", json.dumps(rxn_state()))

        elif path == "/api/reaction/tap" and "POST" in request:
            result = rxn_react()
            _send(cl, "application/json", json.dumps(result))

        # --- API: Pomodoro ---
        elif path == "/api/pom/status":
            _send(cl, "application/json", json.dumps(pom_status()))

        elif path.startswith("/api/pom/start") and "POST" in request:
            try:
                qs = path.split("?", 1)[1]
                params = dict(p.split("=") for p in qs.split("&") if "=" in p)
                pom_configure(int(params.get("w", 25)), int(params.get("b", 5)))
            except Exception:
                pass
            pom_start()
            _send(cl, "application/json", json.dumps(pom_status()))

        elif path == "/api/pom/stop" and "POST" in request:
            pom_stop()
            _send(cl, "application/json", json.dumps(pom_status()))

        # --- Pages ---
        elif path == "/led":
            _send(cl, "text/html", _LED % (_CSS, _build_buttons(led_ctrl.mode)))

        elif path == "/notes":
            _send(cl, "text/html", _NOTES % (_CSS, _build_notes_html(load_notes())))

        elif path == "/sysinfo":
            _send(cl, "text/html", _SYSINFO % (_CSS, _build_sysinfo_html(get_info())))

        elif path == "/morse":
            _send(cl, "text/html", _MORSE % _CSS)

        elif path == "/uptime":
            _send(cl, "text/html", _UPTIME % (_CSS, _build_uptime_html()))

        elif path == "/reaction":
            _send(cl, "text/html", _REACTION % _CSS)

        elif path == "/pomodoro":
            _send(cl, "text/html", _POMODORO % _CSS)

        else:
            _send(cl, "text/html", _HOME % _CSS)

    except Exception as e:
        print("client error:", e)
    finally:
        cl.close()
