import gc
import sys

from machine import freq

from core.display import BLACK, GREEN, GRAY, ORANGE, BLUE, CYAN, RED
from core.controls import A_LABEL, B_LABEL, HOME_HINT, X_LABEL
from core.server import PicoHTTPServer, json_response
from core.temperature import CoreTemperatureSensor, ticks_diff, ticks_ms
from core.ui import (
    WINDOW_CONTENT_X,
    WINDOW_CONTENT_Y,
    WINDOW_CONTENT_W,
    WINDOW_CONTENT_BOTTOM,
    WINDOW_TEXT_CHARS,
    draw_field,
    draw_window_footer,
    draw_window_shell,
    fit_text,
)


HOSTNAME_BASE = "pico"
HOSTNAME_LABEL = "pico.local"
START_RETRY_MS = 2000
TEMP_SAMPLE_MS = 1000


def _format_seconds(total_seconds):
    total_seconds = max(0, int(total_seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)


def _memory_kb():
    try:
        return gc.mem_free() // 1024
    except Exception:
        return None


def _freq_mhz():
    try:
        return freq() // 1000000
    except Exception:
        return None


def _firmware_text():
    try:
        return sys.implementation.name + " " + sys.version.split()[0]
    except Exception:
        return "unknown"


def _html_escape(value):
    text = "" if value is None else str(value)
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    return text


class ServerApp:
    app_id = "server"
    title = "Server"
    accent = BLUE
    launch_mode = "window"

    def __init__(self):
        self.server = PicoHTTPServer(port=80)
        self.server.set_handler(self._handle_request)
        self.sensor = CoreTemperatureSensor(TEMP_SAMPLE_MS)
        self.page = 0
        self.runtime = None
        self.note = "Open while connected to Wi-Fi"
        self.note_color = ORANGE
        self.bind_ip = ""
        self.bind_ssid = ""
        self.hostname_method = ""
        self.hostname_error = ""
        self.hostname_ok = False
        self.connection_key = ""
        self.last_start_attempt_ms = -START_RETRY_MS

    def draw_icon(self, lcd, cx, cy, selected, monochrome=False):
        ink = BLACK if monochrome and selected else BLUE
        detail = BLACK if monochrome and selected else CYAN
        lamp = BLACK if monochrome and selected else GREEN
        lcd.rect(cx - 10, cy - 8, 20, 16, ink)
        lcd.hline(cx - 6, cy - 3, 12, detail)
        lcd.hline(cx - 6, cy + 1, 12, detail)
        lcd.hline(cx - 6, cy + 5, 12, detail)
        lcd.fill_rect(cx - 8, cy - 5, 2, 2, lamp)
        lcd.fill_rect(cx - 8, cy - 1, 2, 2, lamp)
        lcd.fill_rect(cx - 8, cy + 3, 2, 2, lamp)

    def on_open(self, runtime):
        self.runtime = runtime
        self.page = 0
        self.sensor.reset()
        self.server.stop()
        self.server.reset_metrics()
        self.note = "Starting local web server"
        self.note_color = BLUE
        self.bind_ip = ""
        self.bind_ssid = ""
        self.hostname_method = ""
        self.hostname_error = ""
        self.hostname_ok = False
        self.connection_key = ""
        self.last_start_attempt_ms = -START_RETRY_MS
        self.sensor.sample(force=True)
        self._ensure_server(runtime, force=True)

    def on_close(self, runtime):
        self.server.stop()
        self.runtime = None

    def help_lines(self, runtime):
        return [
            "Server controls",
            A_LABEL + " switch page",
            B_LABEL + " restart server",
            X_LABEL + " clear metrics",
            HOME_HINT,
        ]

    def _wifi_state(self, runtime):
        status = runtime.wifi.status()
        ifconfig = status.get("ifconfig") or ("", "", "", "")
        ip = ifconfig[0] if len(ifconfig) > 0 else ""
        ssid = status.get("ssid") or ""
        return status, ssid, ip, ifconfig

    def _sync_note(self, text, color=BLACK):
        self.note = text
        self.note_color = color

    def _access_url(self):
        if not self.bind_ip:
            return ""
        return "http://" + self.bind_ip + "/"

    def _hostname_text(self):
        if self.hostname_ok:
            return HOSTNAME_LABEL
        if self.hostname_error:
            return HOSTNAME_LABEL + " off"
        return HOSTNAME_LABEL + " pending"

    def _serving_note(self):
        if self.bind_ip:
            return "Open " + self._access_url()
        return "Serving while app is open"

    def _ensure_server(self, runtime, force=False):
        status, ssid, ip, _ = self._wifi_state(runtime)
        if not status.get("supported"):
            self.server.stop()
            self.bind_ip = ""
            self.bind_ssid = ""
            self.connection_key = ""
            self._sync_note("No network module available", ORANGE)
            return

        if not status.get("connected") or not ip:
            self.server.stop()
            self.bind_ip = ""
            self.bind_ssid = ""
            self.connection_key = ""
            if status.get("connecting"):
                self._sync_note("Waiting for Wi-Fi link", ORANGE)
            else:
                self._sync_note("Join Wi-Fi to host", ORANGE)
            return

        connection_key = ssid + "|" + ip
        now = ticks_ms()
        should_start = force or not self.server.running() or connection_key != self.connection_key
        if not should_start:
            self.bind_ip = ip
            self.bind_ssid = ssid
            return

        if not force and ticks_diff(now, self.last_start_attempt_ms) < START_RETRY_MS:
            return

        self.last_start_attempt_ms = now
        self.server.stop()
        self.bind_ip = ip
        self.bind_ssid = ssid
        self.connection_key = connection_key

        host_result = runtime.wifi.apply_hostname(HOSTNAME_BASE)
        self.hostname_ok = bool(host_result.get("ok"))
        self.hostname_method = host_result.get("method", "")
        self.hostname_error = host_result.get("error", "")

        if self.server.start():
            self._sync_note(self._serving_note(), BLUE)
        else:
            self._sync_note("Server error: " + self.server.error, RED)

    def _device_status_payload(self):
        now = ticks_ms()
        wifi_status, ssid, ip, ifconfig = self._wifi_state(self.runtime)
        temp_c = self.sensor.last_temp_c
        mem_kb = _memory_kb()
        cpu_mhz = _freq_mhz()
        server_snapshot = self.server.snapshot(now)

        return {
            "access_url": self._access_url(),
            "hostname": HOSTNAME_LABEL,
            "hostname_ok": self.hostname_ok,
            "hostname_method": self.hostname_method,
            "hostname_error": self.hostname_error,
            "wifi": {
                "connected": wifi_status.get("connected", False),
                "connecting": wifi_status.get("connecting", False),
                "ssid": ssid,
                "ip": ip,
                "mask": ifconfig[1] if len(ifconfig) > 1 else "",
                "gateway": ifconfig[2] if len(ifconfig) > 2 else "",
                "dns": ifconfig[3] if len(ifconfig) > 3 else "",
            },
            "pico": {
                "temperature_c": None if temp_c is None else round(temp_c, 2),
                "sensor_voltage": None if self.sensor.last_voltage is None else round(self.sensor.last_voltage, 4),
                "temp_error": self.sensor.temp_error,
                "memory_kb_free": mem_kb,
                "cpu_mhz": cpu_mhz,
                "firmware": _firmware_text(),
            },
            "server": {
                "running": server_snapshot["running"],
                "port": server_snapshot["port"],
                "active_clients": server_snapshot["active_clients"],
                "server_uptime_s": server_snapshot["server_uptime_s"],
                "metrics_uptime_s": server_snapshot["metrics_uptime_s"],
                "error": server_snapshot["error"],
            },
        }

    def _metrics_payload(self):
        snapshot = self.server.snapshot(ticks_ms())
        return {
            "requests_total": snapshot["requests_total"],
            "requests_60s": snapshot["requests_60s"],
            "last_method": snapshot["last_method"],
            "last_path": snapshot["last_path"],
            "last_client": snapshot["last_client"],
            "last_request_age_s": snapshot["last_request_age_s"],
            "server_uptime_s": snapshot["server_uptime_s"],
            "metrics_uptime_s": snapshot["metrics_uptime_s"],
            "active_clients": snapshot["active_clients"],
            "last_error": snapshot["last_error"],
        }

    def _dashboard_html(self):
        status = self._device_status_payload()
        metrics = self._metrics_payload()
        access_url = status.get("access_url") or ""
        hostname_text = status["hostname"] if status.get("hostname_ok") else status["hostname"] + " unavailable"
        wifi_text = "Connected to " + (status["wifi"]["ssid"] or "network") if status["wifi"]["connected"] else "Disconnected"
        last_hit = metrics["last_method"] + " " + metrics["last_path"] if metrics["last_method"] else "No requests yet"
        mdns_text = status.get("hostname_method") or status.get("hostname_error") or "Unavailable"
        temp = status["pico"]["temperature_c"]
        temp_text = "Unavailable" if temp is None else "{:.1f} C".format(temp)
        cpu_text = "Unknown" if status["pico"]["cpu_mhz"] is None else str(status["pico"]["cpu_mhz"]) + " MHz"
        ram_text = "Unknown" if status["pico"]["memory_kb_free"] is None else str(status["pico"]["memory_kb_free"]) + " KB free"
        return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pico Server</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:#f3f5f7}
.hero{background:linear-gradient(135deg,#0d6efd,#20c997);color:#fff}
.mono{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}
.small-muted{font-size:.875rem;color:#6c757d}
.cardish{background:#fff;border-radius:1rem;box-shadow:0 .2rem .8rem rgba(0,0,0,.08);padding:1rem}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1rem}
.field-label{font-size:.75rem;text-transform:uppercase;color:#6c757d;margin-bottom:.15rem}
.field-value{font-weight:600}
.stack{display:grid;gap:.7rem}
</style>
</head>
<body>
<main class="container py-4">
  <section class="hero rounded-4 p-4 mb-4 shadow-sm">
    <div class="d-flex flex-wrap justify-content-between gap-3">
      <div>
        <h1 class="h3 mb-1">Pico Server</h1>
        <div class="opacity-75">Local dashboard served directly from the Pico</div>
      </div>
      <div class="text-end">
        <div class="fw-semibold" id="host-note">""" + _html_escape(hostname_text) + """</div>
        <div class="mono" id="access-url">""" + _html_escape(access_url or "No IP yet") + """</div>
      </div>
    </div>
  </section>

  <div class="alert alert-warning" id="load-error" style="display:none"></div>

  <section class="grid mb-3">
    <div class="cardish">
      <h2 class="h5 mb-3">Connection</h2>
      <div class="stack">
        <div><div class="field-label">Hostname</div><div class="field-value mono" id="hostname">""" + _html_escape(status["hostname"]) + """</div></div>
        <div><div class="field-label">Wi-Fi</div><div class="field-value" id="wifi-state">""" + _html_escape(wifi_text) + """</div></div>
        <div><div class="field-label">IP</div><div class="field-value mono" id="ip">""" + _html_escape(status["wifi"]["ip"] or "-") + """</div></div>
        <div><div class="field-label">Gateway</div><div class="field-value mono" id="gateway">""" + _html_escape(status["wifi"]["gateway"] or "-") + """</div></div>
      </div>
    </div>
    <div class="cardish">
      <h2 class="h5 mb-3">Pico</h2>
      <div class="stack">
        <div><div class="field-label">Temperature</div><div class="field-value mono" id="temperature">""" + _html_escape(temp_text) + """</div></div>
        <div><div class="field-label">CPU</div><div class="field-value mono" id="cpu">""" + _html_escape(cpu_text) + """</div></div>
        <div><div class="field-label">RAM</div><div class="field-value mono" id="ram">""" + _html_escape(ram_text) + """</div></div>
        <div><div class="field-label">Firmware</div><div class="field-value mono" id="firmware">""" + _html_escape(status["pico"]["firmware"]) + """</div></div>
      </div>
    </div>
    <div class="cardish">
      <h2 class="h5 mb-3">Traffic</h2>
      <div class="stack">
        <div><div class="field-label">Requests / 60s</div><div class="field-value mono" id="requests-60s">""" + _html_escape(metrics["requests_60s"]) + """</div></div>
        <div><div class="field-label">Requests total</div><div class="field-value mono" id="requests-total">""" + _html_escape(metrics["requests_total"]) + """</div></div>
        <div><div class="field-label">Last hit</div><div class="field-value mono" id="last-hit">""" + _html_escape(last_hit) + """</div></div>
        <div><div class="field-label">Last client</div><div class="field-value mono" id="last-client">""" + _html_escape(metrics["last_client"] or "-") + """</div></div>
      </div>
    </div>
    <div class="cardish">
      <h2 class="h5 mb-3">Server</h2>
      <div class="stack">
        <div><div class="field-label">Uptime</div><div class="field-value mono" id="server-uptime">""" + _html_escape(str(metrics["server_uptime_s"]) + " s") + """</div></div>
        <div><div class="field-label">Metrics age</div><div class="field-value mono" id="metrics-uptime">""" + _html_escape(str(metrics["metrics_uptime_s"]) + " s") + """</div></div>
        <div><div class="field-label">Active clients</div><div class="field-value mono" id="active-clients">""" + _html_escape(metrics["active_clients"]) + """</div></div>
        <div><div class="field-label">mDNS / hostname</div><div class="field-value mono" id="mdns-mode">""" + _html_escape(mdns_text) + """</div></div>
      </div>
    </div>
  </section>

  <div class="small-muted">Routes: /, /api/status, /api/metrics</div>
</main>

<script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
<script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script>
(function () {
  function setText(id, value) {
    var node = document.getElementById(id);
    if (!node) return;
    node.textContent = value == null || value === "" ? "-" : String(value);
  }

  async function load() {
    try {
      var responses = await Promise.all([
        fetch("/api/status", {cache: "no-store"}),
        fetch("/api/metrics", {cache: "no-store"})
      ]);
      var status = await responses[0].json();
      var metrics = await responses[1].json();
      var errorNode = document.getElementById("load-error");
      if (errorNode) {
        errorNode.style.display = "none";
        errorNode.textContent = "";
      }

      setText("access-url", status.access_url || status.wifi.ip || "No IP yet");
      setText("host-note", status.hostname_ok ? status.hostname + " active" : status.hostname + " unavailable");
      setText("hostname", status.hostname);
      setText("wifi-state", status.wifi.connected ? "Connected to " + (status.wifi.ssid || "network") : "Disconnected");
      setText("ip", status.wifi.ip || "-");
      setText("gateway", status.wifi.gateway || "-");
      setText("temperature", status.pico.temperature_c == null ? "Unavailable" : status.pico.temperature_c.toFixed(1) + " C");
      setText("cpu", status.pico.cpu_mhz ? status.pico.cpu_mhz + " MHz" : "Unknown");
      setText("ram", status.pico.memory_kb_free == null ? "Unknown" : status.pico.memory_kb_free + " KB free");
      setText("firmware", status.pico.firmware || "Unknown");
      setText("requests-60s", metrics.requests_60s || 0);
      setText("requests-total", metrics.requests_total || 0);
      setText("last-hit", metrics.last_method ? metrics.last_method + " " + metrics.last_path : "No requests yet");
      setText("last-client", metrics.last_client || "-");
      setText("server-uptime", (metrics.server_uptime_s || 0) + " s");
      setText("metrics-uptime", (metrics.metrics_uptime_s || 0) + " s");
      setText("active-clients", metrics.active_clients || 0);
      setText("mdns-mode", status.hostname_method || status.hostname_error || "Unavailable");
    } catch (err) {
      var errorNode = document.getElementById("load-error");
      if (errorNode) {
        errorNode.style.display = "block";
        errorNode.textContent = String(err);
      }
    }
  }

  load();
  setInterval(load, 3000);
})();
</script>
</body>
</html>"""

    def _handle_request(self, method, path, query, addr, server):
        if method not in ("GET", "HEAD"):
            return {
                "status": 405,
                "content_type": "text/plain; charset=utf-8",
                "body": "Only GET is supported",
                "headers": {
                    "Cache-Control": "no-store",
                },
            }

        if self.runtime is None:
            return {
                "status": 503,
                "content_type": "text/plain; charset=utf-8",
                "body": "Server app is closing",
                "headers": {
                    "Cache-Control": "no-store",
                },
            }

        if path == "/":
            return {
                "status": 200,
                "content_type": "text/html; charset=utf-8",
                "body": self._dashboard_html(),
                "headers": {
                    "Cache-Control": "no-store",
                },
            }
        if path == "/favicon.ico":
            return {
                "status": 204,
                "content_type": "text/plain; charset=utf-8",
                "body": "",
                "headers": {
                    "Cache-Control": "no-store",
                },
            }
        if path == "/api/status":
            return json_response(self._device_status_payload())
        if path == "/api/metrics":
            return json_response(self._metrics_payload())

        return {
            "status": 404,
            "content_type": "text/plain; charset=utf-8",
            "body": "Not found",
            "headers": {
                "Cache-Control": "no-store",
            },
        }

    def _draw_overview(self, lcd, status, metrics):
        access_text = self._access_url() or "Join Wi-Fi to get an IP"
        draw_field(lcd, WINDOW_CONTENT_X, WINDOW_CONTENT_Y, WINDOW_CONTENT_W, 16, access_text, BLUE)

        y = WINDOW_CONTENT_Y + 22
        state_text = "Ready"
        state_color = GREEN
        if self.server.error:
            state_text = self.server.error
            state_color = RED
        elif not self.server.running():
            state_text = "Stopped"
            state_color = ORANGE
        lines = [
            ("Host   " + self._hostname_text(), BLUE),
            ("Wi-Fi  " + (self.bind_ssid or ("Joining" if status.get("connecting") else "Offline")), BLACK),
            ("Port   " + str(metrics["port"]), BLACK),
            ("Req60  " + str(metrics["requests_60s"]), GREEN),
            ("Total  " + str(metrics["requests_total"]), BLACK),
            ("Last   " + (metrics["last_method"] + " " + metrics["last_path"] if metrics["last_method"] else "No hits"), BLACK),
            ("Client " + (metrics["last_client"] or "-"), GRAY),
            ("State  " + fit_text(state_text, WINDOW_TEXT_CHARS - 7), state_color),
        ]

        for text, color in lines:
            lcd.text(fit_text(text, WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, y, color)
            y += 18

    def _draw_details(self, lcd, metrics):
        mode = self.hostname_method or self.hostname_error or "Unavailable"
        access_text = self.bind_ip or "-"
        state_text = self.server.error or "Ready"
        state_color = RED if self.server.error else GREEN
        lines = [
            ("IP     " + access_text, GREEN),
            ("Host   " + self._hostname_text(), BLUE),
            ("mDNS   " + fit_text(mode, WINDOW_TEXT_CHARS - 7), GRAY),
            ("Port   " + str(metrics["port"]) + " / " + str(metrics["active_clients"]) + " cli", BLACK),
            ("Srv up " + _format_seconds(metrics["server_uptime_s"]), BLACK),
            ("Stats  " + _format_seconds(metrics["metrics_uptime_s"]), BLACK),
            ("Ages   " + ("-" if metrics["last_request_age_s"] is None else str(metrics["last_request_age_s"]) + " sec"), BLACK),
            ("State  " + fit_text(state_text, WINDOW_TEXT_CHARS - 7), state_color),
        ]

        y = WINDOW_CONTENT_Y + 6
        for text, color in lines:
            lcd.text(fit_text(text, WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, y, color)
            y += 18

    def _service_server(self, runtime, force_sample=False):
        self.sensor.sample(force=force_sample)
        self._ensure_server(runtime, force=False)
        if self.server.running():
            self.server.poll()
            if self.server.error:
                self._sync_note("Server error: " + self.server.error, RED)
            elif self.bind_ip:
                self._sync_note(self._serving_note(), BLUE)

    def background_step(self, runtime):
        self.runtime = runtime
        self._service_server(runtime, force_sample=False)

    def step(self, runtime):
        self.runtime = runtime
        buttons = runtime.buttons

        if buttons.pressed("A"):
            self.page = (self.page + 1) % 2
        if buttons.pressed("B"):
            self._ensure_server(runtime, force=True)
        if buttons.pressed("X"):
            self.server.reset_metrics()
            self._sync_note("Metrics reset", BLUE)

        self._service_server(runtime, force_sample=buttons.pressed("B"))

        lcd = runtime.lcd
        draw_window_shell(lcd, "Server", runtime.wifi.status())

        metrics = self.server.snapshot(ticks_ms())
        if self.page == 0:
            self._draw_overview(lcd, runtime.wifi.status(), metrics)
        else:
            self._draw_details(lcd, metrics)

        note_y = WINDOW_CONTENT_BOTTOM - 38
        draw_field(lcd, WINDOW_CONTENT_X, note_y, WINDOW_CONTENT_W, 16, fit_text(self.note, WINDOW_TEXT_CHARS), self.note_color)
        footer = "A page  B restart  X clear"
        draw_window_footer(lcd, fit_text(footer, WINDOW_TEXT_CHARS), GRAY)
        return None
