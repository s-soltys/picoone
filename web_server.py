import socket
import json
from led_patterns import PATTERN_NAMES
from notes import load_notes, add_note, delete_note, edit_note

HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PicoOne</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;background:#111;color:#eee;
     display:flex;flex-direction:column;align-items:center;padding:24px}
h1{margin-bottom:4px;font-size:1.6rem}
p.sub{color:#888;margin-bottom:20px;font-size:.9rem}
h2{margin:28px 0 12px;font-size:1.2rem;width:100%%;max-width:420px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;width:100%%;max-width:420px}
button,.btn{padding:12px 8px;border:2px solid #333;border-radius:10px;
       background:#1a1a1a;color:#ccc;font-size:.95rem;cursor:pointer;
       transition:all .15s}
button:hover,.btn:hover{background:#222;border-color:#555}
button.active{background:#0d5;color:#000;border-color:#0d5;font-weight:700}
.notes-sec{width:100%%;max-width:420px}
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
</style>
</head>
<body>
<h1>PicoOne</h1>
<p class="sub">picoone.local</p>

<h2>LED Patterns</h2>
<div class="grid">%s</div>

<h2>Notes</h2>
<div class="notes-sec">
<div class="note-form">
<textarea id="nt" placeholder="Write a note..."></textarea>
<div class="btn" onclick="addNote()">Add</div>
</div>
<div id="notes">%s</div>
</div>

<script>
function pick(m){
  fetch('/set?mode='+m).then(r=>r.json()).then(d=>{
    document.querySelectorAll('.grid button').forEach(b=>{
      b.classList.toggle('active',parseInt(b.dataset.m)===d.mode);
    });
  });
}
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
</script>
</body>
</html>"""


def _build_buttons(active_mode):
    buttons = ""
    for i, name in enumerate(PATTERN_NAMES):
        cls = ' class="active"' if i == active_mode else ""
        buttons += '<button data-m="{i}"{cls} onclick="pick({i})">{name}</button>\n'.format(
            i=i, cls=cls, name=name
        )
    return buttons


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


def build_page(active_mode):
    return HTML % (_build_buttons(active_mode), _build_notes_html(load_notes()))


def _url_decode(s):
    """Minimal percent-decode for form values."""
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
    """Read POST body from the request buffer."""
    if "\r\n\r\n" in request:
        return request.split("\r\n\r\n", 1)[1]
    return ""


def start_server(led_ctrl, port=80):
    addr = socket.getaddrinfo("0.0.0.0", port)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(2)
    s.setblocking(False)
    print("Web server listening on port", port)
    return s


def _json_notes():
    return json.dumps({"notes": load_notes()})


def handle_client(s, led_ctrl):
    try:
        cl, addr = s.accept()
    except OSError:
        return
    try:
        cl.settimeout(2)
        request = cl.recv(2048).decode("utf-8")

        if "GET /set?" in request:
            try:
                qs = request.split("GET /set?")[1].split(" HTTP")[0]
                params = dict(p.split("=") for p in qs.split("&") if "=" in p)
                mode = int(params.get("mode", -1))
                led_ctrl.set_mode(mode)
            except Exception:
                pass
            body = json.dumps({"mode": led_ctrl.mode})
            cl.send("HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
            cl.send(body)

        elif "POST /notes/add" in request:
            text = _read_body(cl, request)
            add_note(_url_decode(text))
            cl.send("HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
            cl.send(_json_notes())

        elif "POST /notes/del" in request:
            try:
                qs = request.split("POST /notes/del?")[1].split(" HTTP")[0]
                params = dict(p.split("=") for p in qs.split("&") if "=" in p)
                idx = int(params.get("i", -1))
                delete_note(idx)
            except Exception:
                pass
            cl.send("HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
            cl.send(_json_notes())

        elif "POST /notes/edit" in request:
            body = _read_body(cl, request)
            body = _url_decode(body)
            parts = body.split("\n", 1)
            if len(parts) == 2:
                try:
                    idx = int(parts[0])
                    edit_note(idx, parts[1])
                except Exception:
                    pass
            cl.send("HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
            cl.send(_json_notes())

        else:
            page = build_page(led_ctrl.mode)
            cl.send("HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n")
            cl.send(page)
    except Exception as e:
        print("client error:", e)
    finally:
        cl.close()
