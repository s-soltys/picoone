import socket
import json
import select
from utime import ticks_diff, ticks_ms
from led_patterns import PATTERN_NAMES
from notes import load_notes, add_note, delete_note, edit_note
from sysinfo import get_info
from morse import enqueue as morse_send, is_playing as morse_playing
from wifi_manager import scan_networks, get_profiles, set_profile, delete_profile, move_profile, get_current, connect_to

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
<title>PicoOne</title><style>%s
.home-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;width:100%%;max-width:420px}
.home-grid .card{width:auto;margin:0}
</style></head><body>
<h1>PicoOne</h1><p class="sub">pico.local</p>
<div class="home-grid">
<a class="card" href="/led"><h2>LED Control</h2><p>15 patterns</p></a>
<a class="card" href="/notes"><h2>Notes</h2><p>Quick notes</p></a>
<a class="card" href="/sysinfo"><h2>System Info</h2><p>Live stats</p></a>
<a class="card" href="/morse"><h2>Morse Code</h2><p>LED blinks text</p></a>
<a class="card" href="/wifi"><h2>WiFi</h2><p>Manage networks</p></a>
</div>
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
      ['Uptime',d.uptime],['WiFi Network',d.ssid],['WiFi RSSI',d.rssi+' dBm'],['IP',d.ip]];
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
# WiFi page
# ---------------------------------------------------------------------------
_WIFI = """<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PicoOne &mdash; WiFi</title><style>%s
.prof{background:#1a1a1a;border:1px solid #333;border-radius:10px;padding:12px;margin-bottom:8px;
      display:flex;justify-content:space-between;align-items:center}
.prof .info{flex:1}
.prof .name{font-size:.95rem}
.prof .meta{color:#888;font-size:.8rem;margin-top:4px}
.prof .acts{display:flex;gap:8px;flex-wrap:wrap}
.prof .acts span{cursor:pointer;opacity:.5;font-size:.85rem}
.prof .acts span:hover{opacity:1}
h2.sec{margin:20px 0 10px;font-size:1rem;color:#888}
.cur{background:#0d5;color:#000;border-radius:10px;padding:12px;margin-bottom:16px;font-size:.9rem}
.wifi-msg{color:#888;font-size:.9rem;min-height:1.2rem;margin:0 0 16px}
.nav{display:flex;gap:8px;margin-bottom:16px}
.nav a{text-decoration:none}
.form-card{background:#1a1a1a;border:1px solid #333;border-radius:10px;padding:12px}
.form-card input{width:100%%;margin-bottom:8px}
.row-btns{display:flex;gap:8px;flex-wrap:wrap}
.muted{color:#888;font-size:.8rem;margin-top:8px}
</style></head><body>
<h1>WiFi Manager</h1>
<a class="back" href="/">&larr; Home</a>
<div class="wrap">
<div id="cur"></div>
<div id="wm" class="wifi-msg"></div>
<div class="nav"><a class="btn" href="/wifi/scan">Scan Networks</a></div>
<h2 class="sec">Saved Networks (priority order)</h2>
<div id="profs">Loading...</div>
<h2 class="sec" id="ft">Add Network</h2>
<div class="form-card">
<input id="ssid" type="text" placeholder="SSID">
<input id="pw" type="password" placeholder="Password (leave blank for open network)">
<div class="row-btns">
<button id="savebtn" onclick="saveProfile()">Save Network</button>
<button id="cancelbtn" onclick="cancelEdit()" style="display:none">Cancel</button>
</div>
<div class="muted">Save networks here, then use Join from the saved list when needed.</div>
</div>
</div>
<script>
function esc(s){
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function setWifiMsg(msg){
  document.getElementById('wm').textContent=msg || '';
}
var _profiles=[];
var _edit=-1;
function profileActions(i,count){
  var parts=[];
  parts.push('<span onclick="connProfile(' + i + ')">join</span>');
  parts.push('<span onclick="editProfile(' + i + ')">edit</span>');
  if(i>0)parts.push('<span onclick="mv(' + i + ',-1)">&uarr;</span>');
  if(i<count-1)parts.push('<span onclick="mv(' + i + ',1)">&darr;</span>');
  parts.push('<span onclick="rm(' + i + ')">del</span>');
  return parts.join('');
}
function renderProfiles(d){
  if(!d.length)return '<div class="empty">No saved networks.</div>';
  return d.map(function(p,i){
    var meta=p.password ? 'Password saved' : 'Open network';
    return [
      '<div class="prof">',
      '<div class="info"><div class="name">',esc(p.ssid),'</div><div class="meta">',meta,'</div></div>',
      '<div class="acts">',profileActions(i,d.length),'</div>',
      '</div>'
    ].join('');
  }).join('');
}
function setProfiles(d){
  _profiles=d;
  document.getElementById('profs').innerHTML=renderProfiles(d);
}
function resetForm(){
  _edit=-1;
  document.getElementById('ssid').value='';
  document.getElementById('pw').value='';
  document.getElementById('ft').textContent='Add Network';
  document.getElementById('savebtn').textContent='Save Network';
  document.getElementById('cancelbtn').style.display='none';
}
function editProfile(i){
  var p=_profiles[i];
  _edit=i;
  document.getElementById('ssid').value=p.ssid;
  document.getElementById('pw').value=p.password || '';
  document.getElementById('ft').textContent='Edit Network';
  document.getElementById('savebtn').textContent='Update Network';
  document.getElementById('cancelbtn').style.display='inline-block';
}
function cancelEdit(){
  resetForm();
}
function connectRequest(ssid,pw){
  setWifiMsg('Starting connection to ' + ssid + '...');
  return fetch('/api/wifi/connect',{method:'POST',body:ssid+'\\n'+(pw || '')}).then(function(r){
    return r.json();
  }).then(function(d){
    if(d.ok && d.pending){
      setWifiMsg('Trying to join ' + ssid + '. This page may stop updating while PicoOne switches networks. Reopen http://pico.local/ after it reconnects.');
    }else if(d.busy){
      setWifiMsg('Another Wi-Fi connection attempt is already in progress.');
    }else{
      setWifiMsg('Failed to start connection to ' + ssid + '.');
    }
  }).catch(function(){
    setWifiMsg('Connection request did not complete. Refresh and try again.');
  });
}
function connProfile(i){
  var p=_profiles[i];
  connectRequest(p.ssid,p.password || '');
}
function saveProfile(){
  var ssid=document.getElementById('ssid').value.trim();
  var pw=document.getElementById('pw').value;
  if(!ssid){setWifiMsg('SSID is required.');return;}
  fetch('/api/wifi/profile',{method:'POST',body:String(_edit)+'\\n'+ssid+'\\n'+pw}).then(function(r){
    return r.json();
  }).then(function(d){
    setProfiles(d);
    resetForm();
    setWifiMsg('Saved ' + ssid + '.');
  }).catch(function(){
    setWifiMsg('Saving the network failed.');
  });
}
function load(){
  return fetch('/api/wifi/status').then(function(r){return r.json();}).then(function(d){
    if(d.connected){
      document.getElementById('cur').innerHTML='<div class="cur">Connected to <b>'+esc(d.ssid)+'</b> &mdash; '+d.ip+' ('+d.rssi+' dBm)</div>';
    }else{
      document.getElementById('cur').innerHTML='<div class="cur" style="background:#c33;color:#fff">Not connected</div>';
    }
  }).then(function(){
    return fetch('/api/wifi/profiles');
  }).then(function(r){
    return r.json();
  }).then(function(d){
    setProfiles(d);
  });
}
function mv(i,dir){
  fetch('/api/wifi/move?i='+i+'&d='+dir,{method:'POST'}).then(function(r){
    return r.json();
  }).then(function(d){
    setProfiles(d);
    resetForm();
  });
}
function rm(i){
  fetch('/api/wifi/del?i='+i,{method:'POST'}).then(function(r){
    return r.json();
  }).then(function(d){
    setProfiles(d);
    resetForm();
  });
}
resetForm();
load();
</script></body></html>"""


_WIFI_SCAN = """<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PicoOne &mdash; WiFi Scan</title><style>%s
.net{background:#1a1a1a;border:1px solid #333;border-radius:10px;padding:12px;margin-bottom:8px;
     display:flex;justify-content:space-between;align-items:center}
.net .info{flex:1}
.net .ssid{font-size:.95rem}
.net .meta{color:#888;font-size:.8rem}
.conn-form{margin-top:8px;display:none;gap:8px}
.conn-form input{flex:1}
.conn-form.show{display:flex}
h2.sec{margin:20px 0 10px;font-size:1rem;color:#888}
.cur{background:#0d5;color:#000;border-radius:10px;padding:12px;margin-bottom:16px;font-size:.9rem}
.wifi-msg{color:#888;font-size:.9rem;min-height:1.2rem;margin:0 0 16px}
.nav{display:flex;gap:8px;margin-bottom:16px}
.nav a{text-decoration:none}
</style></head><body>
<h1>WiFi Scan</h1>
<a class="back" href="/wifi">&larr; Saved Networks</a>
<div class="wrap">
<div id="cur"></div>
<div id="wm" class="wifi-msg"></div>
<div class="nav"><a class="btn" href="/wifi">Saved Networks</a></div>
<h2 class="sec">Available Networks</h2>
<div id="scan">Scanning...</div>
</div>
<script>
function esc(s){
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function setWifiMsg(msg){
  document.getElementById('wm').textContent=msg || '';
}
var _nets=[];
function renderNetwork(n,i){
  var saved=n.saved ? ' &middot; saved' : '';
  var sec=n.secure ? ' &middot; secured' : ' &middot; open';
  return [
    '<div class="net"><div class="info">',
    '<div class="ssid">',esc(n.ssid),'</div>',
    '<div class="meta">',n.rssi,' dBm',saved,sec,'</div>',
    '<div class="conn-form" id="cf',i,
    '"><input type="password" id="pw',i,
    '" placeholder="Password"><button onclick="conn(',i,
    ')">Connect</button></div>',
    '</div><button onclick="toggle(',i,
    ')" style="padding:8px 12px;font-size:.8rem">Join</button></div>'
  ].join('');
}
function connectRequest(ssid,pw){
  setWifiMsg('Starting connection to ' + ssid + '...');
  return fetch('/api/wifi/connect',{method:'POST',body:ssid+'\\n'+(pw || '')}).then(function(r){
    return r.json();
  }).then(function(d){
    if(d.ok && d.pending){
      setWifiMsg('Trying to join ' + ssid + '. This page may stop updating while PicoOne switches networks. Reopen http://pico.local/ after it reconnects.');
    }else if(d.busy){
      setWifiMsg('Another Wi-Fi connection attempt is already in progress.');
    }else{
      setWifiMsg('Failed to start connection to ' + ssid + '.');
    }
  }).catch(function(){
    setWifiMsg('Connection request did not complete. Refresh and try again.');
  });
}
function load(){
  return fetch('/api/wifi/status').then(function(r){return r.json();}).then(function(d){
    if(d.connected){
      document.getElementById('cur').innerHTML='<div class="cur">Connected to <b>'+esc(d.ssid)+'</b> &mdash; '+d.ip+' ('+d.rssi+' dBm)</div>';
    }else{
      document.getElementById('cur').innerHTML='<div class="cur" style="background:#c33;color:#fff">Not connected</div>';
    }
  });
}
function scan(){
  document.getElementById('scan').innerHTML='Scanning...';
  return fetch('/api/wifi/scan').then(function(r){
    return r.json();
  }).then(function(d){
    _nets=d;
    document.getElementById('scan').innerHTML=d.length ? d.map(renderNetwork).join('') : '<div class="empty">No networks found.</div>';
  });
}
function toggle(i){
  var el=document.getElementById('cf'+i);
  el.classList.toggle('show');
}
function conn(i){
  var ssid=_nets[i].ssid;
  var pw=document.getElementById('pw'+i).value;
  connectRequest(ssid,pw);
}
load().then(scan);
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
        ("WiFi Network", info["ssid"]),
        ("WiFi RSSI", "{} dBm".format(info["rssi"])),
        ("IP", info["ip"]),
    ]
    return "".join('<div class="row"><span class="k">{}</span><span class="v">{}</span></div>'.format(k, v) for k, v in rows)


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


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
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


def _send(cl, ctype, body):
    if isinstance(body, str):
        body = body.encode()
    cl.send(
        "HTTP/1.0 200 OK\r\nContent-Type: {}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n".format(
            ctype, len(body)
        )
    )
    i = 0
    while i < len(body):
        chunk = body[i:i + 512]
        cl.send(chunk)
        i += len(chunk)


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
    events = poller.poll(100)  # wait up to 100ms
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

        # Ignore favicon requests
        if path == "/favicon.ico":
            cl.send("HTTP/1.0 204 No Content\r\n\r\n")
            cl.close()
            return

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

        # --- Pages ---
        elif path == "/led":
            _send(cl, "text/html", _LED % (_CSS, _build_buttons(led_ctrl.mode)))

        elif path == "/notes":
            _send(cl, "text/html", _NOTES % (_CSS, _build_notes_html(load_notes())))

        elif path == "/sysinfo":
            _send(cl, "text/html", _SYSINFO % (_CSS, _build_sysinfo_html(get_info())))

        elif path == "/morse":
            _send(cl, "text/html", _MORSE % _CSS)

        elif path == "/wifi":
            _send(cl, "text/html", _WIFI % _CSS)

        elif path == "/wifi/scan":
            _send(cl, "text/html", _WIFI_SCAN % _CSS)

        # --- API: WiFi ---
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

        else:
            _send(cl, "text/html", _HOME % _CSS)

    except Exception as e:
        print("client error:", e)
    finally:
        cl.close()
