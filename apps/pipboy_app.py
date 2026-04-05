import gc
import time

try:
    import ujson as json
except ImportError:
    import json

from machine import freq

from core.controls import A_LABEL, B_LABEL, X_LABEL, HOME_HINT
from core.display import BLACK, WHITE, GREEN, ORANGE, CYAN, YELLOW, rgb565, SCREEN_W, SCREEN_H
from core.http import build_url, get_json
from core.temperature import CoreTemperatureSensor, ticks_diff, ticks_ms
from core.ui import fit_text


STATE_PATH = "pipboy_state.json"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
RATES_URL = "https://api.frankfurter.dev/v1/latest"
SPACE_URL = "https://api.nasa.gov/planetary/apod"
NASA_API_KEY = "DEMO_KEY"

TAB_NAMES = ("STAT", "DATA", "RADIO", "MAP")
FEED_KEYS = ("weather", "space", "rates")
CACHE_MS = {
    "weather": 15 * 60 * 1000,
    "space": 6 * 60 * 60 * 1000,
    "rates": 6 * 60 * 60 * 1000,
}

MOJAVE = {
    "name": "Mojave",
    "latitude": 36.1699,
    "longitude": -115.1398,
}

WEATHER_CODES = {
    0: "Clear",
    1: "Fair",
    2: "Partly",
    3: "Cloudy",
    45: "Fog",
    48: "Rime fog",
    51: "Drizzle",
    53: "Drizzle",
    55: "Heavy driz",
    61: "Rain",
    63: "Rain",
    65: "Hard rain",
    71: "Snow",
    73: "Snow",
    75: "Heavy snow",
    80: "Shower",
    81: "Shower",
    82: "Storm rain",
    95: "Storm",
    96: "Storm hail",
    99: "Storm hail",
}

DATA_ITEMS = (
    {"name": "SESSION", "feed": None},
    {"name": "WEATHER", "feed": "weather"},
    {"name": "ORBITAL", "feed": "space"},
    {"name": "MARKET", "feed": "rates"},
)

RADIO_STATIONS = (
    {
        "name": "DUST-13",
        "deck": "Mojave relay",
        "feed": None,
        "lines": (
            "Relay traffic alive.",
            "Caravans clear the ridge.",
            "Static level: tolerable.",
            "Stay off the bright roads.",
        ),
    },
    {
        "name": "WX-88",
        "deck": "Weather front",
        "feed": "weather",
        "lines": (),
    },
    {
        "name": "ORBIT-6",
        "deck": "Deep sky desk",
        "feed": "space",
        "lines": (),
    },
    {
        "name": "CAPS-3",
        "deck": "Trade wire",
        "feed": "rates",
        "lines": (),
    },
    {
        "name": "ENCL-404",
        "deck": "Ghost channel",
        "feed": None,
        "lines": (
            "Old command burst.",
            "No source lock.",
            "Carrier drifts each hour.",
            "Message key unavailable.",
        ),
    },
)

MAP_POINTS = (
    {"name": "Shelter 12", "x": 2, "y": 7, "status": "sealed"},
    {"name": "Dustown", "x": 5, "y": 5, "status": "trade"},
    {"name": "Crater Yard", "x": 8, "y": 8, "status": "salvage"},
    {"name": "North Relay", "x": 9, "y": 3, "status": "signal"},
    {"name": "Dry Wells", "x": 3, "y": 2, "status": "hazard"},
)

MAP_GRID_W = 11
MAP_GRID_H = 11

PHOS_BG = rgb565(5, 12, 6)
PHOS_SHADOW = rgb565(10, 24, 10)
PHOS_PANEL = rgb565(15, 32, 14)
PHOS_DIM = rgb565(34, 82, 38)
PHOS_MID = rgb565(70, 154, 76)
PHOS_LIGHT = rgb565(156, 255, 164)
PHOS_GLOW = rgb565(108, 245, 122)
PHOS_ALERT = rgb565(255, 182, 74)
PHOS_DANGER = rgb565(255, 92, 68)


def _ticks_add(value, delta):
    if hasattr(time, "ticks_add"):
        return time.ticks_add(value, delta)
    return value + delta


def _safe_float(value, fallback=0.0):
    try:
        return float(value)
    except Exception:
        return fallback


def _safe_int(value, fallback=0):
    try:
        return int(round(float(value)))
    except Exception:
        return fallback


def _fit_box(text, width):
    return fit_text(text, max(1, (width - 8) // 8))


def _clock_tuple():
    try:
        now = time.localtime()
    except Exception:
        return None
    if not now or len(now) < 5 or now[0] < 2024:
        return None
    return now


def _clock_stamp():
    now = _clock_tuple()
    if not now:
        return ""
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}".format(now[0], now[1], now[2], now[3], now[4])


def _clock_label():
    now = _clock_tuple()
    if not now:
        return "RTC --:--"
    return "{:02d}:{:02d} {:02d}/{:02d}".format(now[3], now[4], now[1], now[2])


def _age_text(updated_ms, persisted=False, stamp=""):
    if updated_ms is not None:
        delta_ms = max(0, ticks_diff(ticks_ms(), updated_ms))
        minutes = delta_ms // 60000
        if minutes < 1:
            return "live now"
        if minutes < 60:
            return "live " + str(minutes) + "m"
        return "live " + str(minutes // 60) + "h"
    if persisted and stamp:
        return "saved " + fit_text(stamp, 11)
    if persisted:
        return "saved cache"
    return "no cache"


def _wrap_text(text, max_chars, max_lines):
    clean = str(text or "").replace("\n", " ").replace("\r", " ").strip()
    if not clean:
        return [""]

    words = clean.split()
    lines = []
    line = ""
    for word in words:
        trial = word if not line else line + " " + word
        if len(trial) <= max_chars:
            line = trial
            continue

        if line:
            lines.append(line)
            if len(lines) >= max_lines:
                return lines
            line = ""

        while len(word) > max_chars:
            lines.append(word[:max_chars])
            if len(lines) >= max_lines:
                return lines
            word = word[max_chars:]
        line = word

    if line and len(lines) < max_lines:
        lines.append(line)

    if not lines:
        lines.append(fit_text(clean, max_chars))
    return lines


def _weather_label(code):
    return WEATHER_CODES.get(code, "Code " + str(code))


class PipBoyApp:
    app_id = "pipboy"
    title = "PipBoy"
    accent = GREEN
    launch_mode = "fullscreen"

    def __init__(self):
        self.sensor = CoreTemperatureSensor(1200)
        self.tab_index = 0
        self.stat_selected = 0
        self.stat_alt_panel = False
        self.data_selected = 0
        self.data_archive = False
        self.radio_selected = 0
        self.tuned_station = 1
        self.radio_detail = False
        self.map_selected = 1
        self.map_cursor_mode = False
        self.map_cursor_x = MAP_POINTS[1]["x"]
        self.map_cursor_y = MAP_POINTS[1]["y"]
        self.frame = 0
        self.open_count = 0
        self.boot_ms = ticks_ms()
        self.notice = "LINK READY"
        self.notice_until_ms = 0
        self.loading = False
        self.loading_drawn = False
        self.loading_reason = ""
        self.loading_current = ""
        self.fetch_queue = []
        self.fetch_total = 0
        self.payloads = {}
        self.feed_runtime_ms = {}
        self.feed_persisted = {}
        self.feed_stamps = {}
        self.feed_errors = {}
        self.event_log = []
        for key in FEED_KEYS:
            self.payloads[key] = None
            self.feed_runtime_ms[key] = None
            self.feed_persisted[key] = False
            self.feed_stamps[key] = ""
            self.feed_errors[key] = ""
        self._load_state()

    def draw_icon(self, lcd, cx, cy, selected, monochrome=False):
        ink = BLACK if monochrome and selected else (WHITE if monochrome else PHOS_LIGHT)
        detail = BLACK if monochrome and selected else (WHITE if monochrome else PHOS_MID)
        lcd.rect(cx - 10, cy - 8, 20, 16, ink)
        lcd.rect(cx - 7, cy - 5, 14, 10, ink)
        lcd.fill_rect(cx - 3, cy - 2, 6, 4, detail)
        lcd.fill_rect(cx - 13, cy - 2, 3, 4, ink)
        lcd.fill_rect(cx + 10, cy - 2, 3, 4, ink)
        lcd.hline(cx - 4, cy + 8, 8, ink)

    def on_open(self, runtime):
        self.open_count += 1
        self.frame = 0
        self.tab_index = 0
        self.map_cursor_mode = False
        self.sensor.sample(force=True)
        self._log_event("SESSION " + str(self.open_count))

        due = []
        for key in FEED_KEYS:
            if self.payloads[key] is None or self.feed_persisted[key] or self._feed_due(key):
                due.append(key)
        if due:
            self._queue_refresh(due, "startup")

    def help_lines(self, runtime):
        if self.loading:
            return [
                "PipBoy sync",
                "Wait for feed pull",
                X_LABEL + " refresh queued later",
                "Tabs resume after sync",
                HOME_HINT,
            ]

        if TAB_NAMES[self.tab_index] == "STAT":
            return [
                "PipBoy STAT",
                "Up/Down picks a panel",
                B_LABEL + " refresh panel feed",
                A_LABEL + " swaps orbit/market panel",
                X_LABEL + " refresh all feeds",
            ]

        if TAB_NAMES[self.tab_index] == "DATA":
            return [
                "PipBoy DATA",
                "Up/Down picks report",
                B_LABEL + " refresh selected report",
                A_LABEL + " toggles report/meta view",
                X_LABEL + " refresh all feeds",
            ]

        if TAB_NAMES[self.tab_index] == "RADIO":
            return [
                "PipBoy RADIO",
                "Up/Down picks station",
                B_LABEL + " tunes selected station",
                A_LABEL + " toggles detail scope",
                X_LABEL + " refreshes tuned live feed",
            ]

        if self.map_cursor_mode:
            return [
                "PipBoy MAP",
                "D-pad moves the cursor",
                B_LABEL + " locks the current tile",
                A_LABEL + " exits cursor mode",
                X_LABEL + " centers on selected point",
            ]

        return [
            "PipBoy MAP",
            "Up/Down picks a point",
            B_LABEL + " enters cursor mode",
            A_LABEL + " leaves cursor mode",
            X_LABEL + " center on selected point",
        ]

    def _log_event(self, text):
        stamp = _clock_stamp()
        if stamp:
            label = stamp[11:16] + " " + text
        else:
            label = "T+" + str(max(0, ticks_diff(ticks_ms(), self.boot_ms) // 1000)) + " " + text
        self.event_log.insert(0, fit_text(label, 28))
        if len(self.event_log) > 8:
            self.event_log = self.event_log[:8]

    def _set_notice(self, text, duration_ms=2600):
        self.notice = fit_text(text, 26)
        self.notice_until_ms = _ticks_add(ticks_ms(), duration_ms)

    def _active_notice(self):
        if self.notice and ticks_diff(self.notice_until_ms, ticks_ms()) > 0:
            return self.notice
        return ""

    def _load_state(self):
        try:
            with open(STATE_PATH, "r") as handle:
                state = json.loads(handle.read())
        except OSError:
            return
        except Exception:
            return

        for key in FEED_KEYS:
            record = state.get(key) or {}
            payload = record.get("payload")
            if payload is not None:
                self.payloads[key] = payload
                self.feed_persisted[key] = True
                self.feed_stamps[key] = str(record.get("stamp") or "")

        tab_index = state.get("tab_index")
        if isinstance(tab_index, int) and 0 <= tab_index < len(TAB_NAMES):
            self.tab_index = tab_index

        tuned = state.get("tuned_station")
        if isinstance(tuned, int) and 0 <= tuned < len(RADIO_STATIONS):
            self.tuned_station = tuned

    def _save_state(self):
        state = {
            "tab_index": self.tab_index,
            "tuned_station": self.tuned_station,
        }
        for key in FEED_KEYS:
            if self.payloads[key] is not None:
                state[key] = {
                    "payload": self.payloads[key],
                    "stamp": self.feed_stamps[key],
                }
        try:
            with open(STATE_PATH, "w") as handle:
                handle.write(json.dumps(state))
        except OSError:
            pass

    def _feed_due(self, key):
        if self.payloads[key] is None:
            return True
        updated_ms = self.feed_runtime_ms[key]
        if updated_ms is None:
            return self.feed_persisted[key]
        return ticks_diff(ticks_ms(), updated_ms) >= CACHE_MS[key]

    def _queue_refresh(self, keys=None, reason="manual"):
        queue = []
        wanted = keys or FEED_KEYS
        for key in wanted:
            if key in FEED_KEYS and key not in queue:
                queue.append(key)
        if not queue:
            return
        self.fetch_queue = queue
        self.fetch_total = len(queue)
        self.loading = True
        self.loading_drawn = False
        self.loading_reason = reason
        self.loading_current = queue[0]
        self._set_notice("Sync " + reason)

    def _wifi_label(self, runtime):
        status = runtime.wifi.status()
        if not status.get("supported"):
            return "NO RADIO"
        if status.get("connected"):
            return "LINK " + fit_text(status.get("ssid") or "ACTIVE", 10)
        if status.get("connecting"):
            return "LINK SEEK"
        if status.get("active"):
            return "RADIO READY"
        return "LINK DOWN"

    def _wifi_strength(self, runtime):
        status = runtime.wifi.status()
        if status.get("connected"):
            return 92
        if status.get("connecting"):
            return 48
        if status.get("active"):
            return 22
        return 8

    def _status_color(self, runtime):
        status = runtime.wifi.status()
        if status.get("connected"):
            return PHOS_LIGHT
        if status.get("active"):
            return PHOS_ALERT
        return PHOS_DANGER

    def _memory_free(self):
        try:
            return gc.mem_free()
        except Exception:
            return 0

    def _uptime_text(self):
        total_seconds = max(0, ticks_diff(ticks_ms(), self.boot_ms) // 1000)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)

    def _weather_url(self):
        return build_url(
            WEATHER_URL,
            {
                "latitude": MOJAVE["latitude"],
                "longitude": MOJAVE["longitude"],
                "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,relative_humidity_2m",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min",
                "forecast_days": 1,
                "timezone": "auto",
            },
        )

    def _fetch_weather(self):
        result = get_json(self._weather_url(), 5)
        if not result["ok"]:
            return None, result["error"] or "weather fetch failed"

        data = result["data"] or {}
        current = data.get("current") or {}
        daily = data.get("daily") or {}
        if "temperature_2m" not in current or "weather_code" not in current:
            return None, "weather payload missing values"

        highs = daily.get("temperature_2m_max") or []
        lows = daily.get("temperature_2m_min") or []
        daily_codes = daily.get("weather_code") or []
        code = _safe_int(current.get("weather_code"))
        payload = {
            "zone": MOJAVE["name"],
            "temp": _safe_float(current.get("temperature_2m")),
            "feels": _safe_float(current.get("apparent_temperature")),
            "wind": _safe_float(current.get("wind_speed_10m")),
            "humidity": _safe_int(current.get("relative_humidity_2m")),
            "code": code,
            "label": _weather_label(code),
            "high": _safe_float(highs[0] if highs else current.get("temperature_2m")),
            "low": _safe_float(lows[0] if lows else current.get("temperature_2m")),
            "forecast_code": _safe_int(daily_codes[0] if daily_codes else code),
        }
        return payload, ""

    def _fetch_space(self):
        url = build_url(
            SPACE_URL,
            {
                "api_key": NASA_API_KEY,
                "thumbs": "true",
            },
        )
        result = get_json(url, 6)
        if not result["ok"]:
            return None, result["error"] or "space feed failed"

        data = result["data"] or {}
        title = str(data.get("title") or "").strip()
        explanation = str(data.get("explanation") or "").strip()
        if not title or not explanation:
            return None, "space payload missing title"

        payload = {
            "title": fit_text(title, 48),
            "date": str(data.get("date") or "?"),
            "media": str(data.get("media_type") or "image"),
            "summary": explanation[:260],
        }
        return payload, ""

    def _fetch_rates(self):
        url = build_url(
            RATES_URL,
            {
                "base": "USD",
                "symbols": "EUR,GBP,JPY",
            },
        )
        result = get_json(url, 5)
        if not result["ok"]:
            return None, result["error"] or "rate feed failed"

        data = result["data"] or {}
        rates = data.get("rates") or {}
        if not rates:
            return None, "rate payload missing values"

        payload = {
            "date": str(data.get("date") or "?"),
            "EUR": _safe_float(rates.get("EUR")),
            "GBP": _safe_float(rates.get("GBP")),
            "JPY": _safe_float(rates.get("JPY")),
        }
        return payload, ""

    def _fetch_feed(self, runtime, key):
        status = runtime.wifi.status()
        if not status.get("supported"):
            self.feed_errors[key] = "no network module"
            self._log_event(key.upper() + " NO HW")
            self._set_notice(key.upper() + " no radio")
            return
        if not status.get("connected"):
            self.feed_errors[key] = "connect Wi-Fi first"
            self._log_event(key.upper() + " LINK DOWN")
            self._set_notice("Wi-Fi required")
            return

        if key == "weather":
            payload, error = self._fetch_weather()
        elif key == "space":
            payload, error = self._fetch_space()
        else:
            payload, error = self._fetch_rates()

        if error:
            self.feed_errors[key] = error
            self._log_event(key.upper() + " FAIL")
            self._set_notice(key.upper() + " stale")
            return

        self.payloads[key] = payload
        self.feed_runtime_ms[key] = ticks_ms()
        self.feed_persisted[key] = False
        self.feed_stamps[key] = _clock_stamp()
        self.feed_errors[key] = ""
        self._save_state()
        self._log_event(key.upper() + " OK")
        self._set_notice(key.upper() + " updated")

    def _feed_status(self, key):
        if self.feed_errors[key]:
            base = _age_text(self.feed_runtime_ms[key], self.feed_persisted[key], self.feed_stamps[key])
            return fit_text(base + " / " + self.feed_errors[key], 26)
        return _age_text(self.feed_runtime_ms[key], self.feed_persisted[key], self.feed_stamps[key])

    def _step_loading(self, runtime):
        if not self.loading_drawn:
            self.loading_drawn = True
            self._draw_loading(runtime.lcd, runtime)
            return

        if not self.fetch_queue:
            self.loading = False
            return

        key = self.fetch_queue.pop(0)
        self.loading_current = key
        self._fetch_feed(runtime, key)

        if self.fetch_queue:
            self._draw_loading(runtime.lcd, runtime)
        else:
            self.loading = False

    def _draw_box(self, lcd, x, y, w, h, title="", active=False):
        fill = PHOS_PANEL if active else PHOS_SHADOW
        edge = PHOS_LIGHT if active else PHOS_DIM
        lcd.fill_rect(x, y, w, h, fill)
        lcd.rect(x, y, w, h, edge)
        if w > 2 and h > 2:
            lcd.rect(x + 1, y + 1, w - 2, h - 2, PHOS_BG)
        if title:
            tag_w = min(w - 8, len(title) * 8 + 8)
            lcd.fill_rect(x + 5, y - 1, tag_w, 10, PHOS_BG)
            lcd.text(fit_text(title, max(1, (tag_w - 4) // 8)), x + 7, y + 1, edge)

    def _draw_meter(self, lcd, x, y, w, label, value, accent):
        amount = max(0, min(100, value))
        lcd.text(label, x, y, PHOS_LIGHT)
        lcd.rect(x + 34, y + 1, w, 6, PHOS_DIM)
        inner = max(1, w - 2)
        fill_w = max(1, (inner * amount) // 100)
        lcd.fill_rect(x + 35, y + 2, fill_w, 4, accent)

    def _draw_signal(self, lcd, x, y, strength):
        bars = max(0, min(4, strength // 25))
        for index in range(4):
            bar_h = 3 + (index * 3)
            bx = x + (index * 5)
            by = y + 10 - bar_h
            color = PHOS_LIGHT if index < bars else PHOS_DIM
            lcd.fill_rect(bx, by, 3, bar_h, color)

    def _draw_header(self, lcd, runtime):
        self._draw_box(lcd, 8, 8, SCREEN_W - 16, 18, "", True)
        lcd.text("PIP-BOY 2000", 16, 13, PHOS_GLOW)
        tab = TAB_NAMES[self.tab_index]
        lcd.text(tab, 120 - (len(tab) * 4), 13, PHOS_ALERT)
        clock = _clock_label()
        lcd.text(fit_text(clock, 11), SCREEN_W - 96, 13, PHOS_LIGHT)

        link = self._wifi_label(runtime)
        color = self._status_color(runtime)
        lcd.hline(12, 35, SCREEN_W - 24, PHOS_DIM)
        lcd.text(fit_text(link, 14), 16, 30, color)
        self._draw_signal(lcd, SCREEN_W - 40, 27, self._wifi_strength(runtime))

    def _draw_tabs(self, lcd):
        x = 12
        y = 44
        widths = (46, 46, 58, 46)
        for index, name in enumerate(TAB_NAMES):
            active = index == self.tab_index
            width = widths[index]
            self._draw_box(lcd, x, y, width, 16, "", active)
            lcd.text(name, x + ((width - len(name) * 8) // 2), y + 4, PHOS_LIGHT if active else PHOS_MID)
            x += width + 6

    def _draw_footer(self, lcd, hint):
        self._draw_box(lcd, 8, 214, SCREEN_W - 16, 16, "", False)
        note = self._active_notice() or hint
        lcd.text(fit_text(note, 22), 14, 218, PHOS_LIGHT if self._active_notice() else PHOS_MID)
        lcd.text("A/B/X", SCREEN_W - 48, 218, PHOS_DIM)

    def _draw_scanlines(self, lcd):
        for y in range(24, SCREEN_H, 4):
            lcd.hline(0, y, SCREEN_W, PHOS_BG)

    def _draw_loading(self, lcd, runtime):
        lcd.fill(PHOS_BG)
        self._draw_scanlines(lcd)
        self._draw_header(lcd, runtime)
        self._draw_tabs(lcd)
        self._draw_box(lcd, 18, 78, SCREEN_W - 36, 104, "SYNC", True)
        total = max(1, self.fetch_total)
        done = total - len(self.fetch_queue)
        lcd.text("Establishing uplink", 36, 100, PHOS_GLOW)
        lcd.text("Reason " + fit_text(self.loading_reason.upper(), 10), 36, 122, PHOS_LIGHT)
        lcd.text("Feed   " + fit_text(self.loading_current.upper(), 10), 36, 142, PHOS_ALERT)
        lcd.text("Stage  " + str(done) + "/" + str(total), 36, 162, PHOS_LIGHT)
        self._draw_footer(lcd, self._wifi_label(runtime))

    def _temp_value(self):
        self.sensor.sample()
        if self.sensor.last_temp_c is None:
            return None
        return self.sensor.last_temp_c

    def _stat_hint(self):
        if self.stat_selected == 0:
            return "Vitals local / " + self._feed_status("weather")
        if self.stat_selected == 1:
            return "Weather / " + self._feed_status("weather")
        if self.stat_alt_panel:
            return "Market / " + self._feed_status("rates")
        return "Orbit / " + self._feed_status("space")

    def _draw_silhouette(self, lcd, x, y):
        head_x = x + 38
        head_y = y + 22
        lcd.ellipse(head_x, head_y, 10, 10, PHOS_LIGHT, False)
        lcd.line(head_x, head_y + 10, head_x, head_y + 54, PHOS_LIGHT)
        lcd.line(head_x - 16, head_y + 24, head_x + 16, head_y + 24, PHOS_LIGHT)
        lcd.line(head_x - 18, head_y + 18, head_x - 6, head_y + 42, PHOS_LIGHT)
        lcd.line(head_x + 18, head_y + 18, head_x + 6, head_y + 42, PHOS_LIGHT)
        lcd.line(head_x, head_y + 54, head_x - 13, head_y + 82, PHOS_LIGHT)
        lcd.line(head_x, head_y + 54, head_x + 13, head_y + 82, PHOS_LIGHT)
        lcd.fill_rect(head_x - 7, head_y + 10, 14, 20, PHOS_DIM)
        lcd.fill_rect(head_x - 5, head_y + 32, 10, 16, PHOS_DIM)
        lcd.fill_rect(head_x - 2, head_y + 11, 4, 37, PHOS_GLOW)

    def _draw_stat_tab(self, lcd, runtime):
        self._draw_box(lcd, 10, 66, 84, 138, "BODY", self.stat_selected == 0)
        self._draw_silhouette(lcd, 10, 68)
        temp_c = self._temp_value()
        mem_value = self._memory_free()
        mem_pct = min(100, max(10, mem_value // 1800))
        temp_pct = 10 if temp_c is None else max(0, min(100, int((temp_c - 10) * 2)))
        self._draw_meter(lcd, 18, 170, 36, "PWR", mem_pct, PHOS_GLOW)
        self._draw_meter(lcd, 18, 184, 36, "HEAT", temp_pct, PHOS_ALERT if temp_c and temp_c >= 55 else PHOS_GLOW)
        self._draw_meter(lcd, 18, 198, 36, "LINK", self._wifi_strength(runtime), self._status_color(runtime))

        self._draw_box(lcd, 106, 66, 124, 44, "VITALS", self.stat_selected == 0)
        lcd.text("UP  " + self._uptime_text(), 114, 80, PHOS_LIGHT)
        lcd.text("CPU " + str(_safe_int(freq() / 1000000)) + "MHz", 114, 94, PHOS_MID)
        lcd.text("RAM " + str(mem_value // 1024) + "KB", 114, 108, PHOS_MID)

        weather = self.payloads["weather"]
        self._draw_box(lcd, 106, 118, 124, 38, "WEATHER", self.stat_selected == 1)
        if weather:
            lcd.text(fit_text(weather["zone"] + " " + weather["label"], 14), 114, 132, PHOS_GLOW)
            lcd.text("T " + str(_safe_int(weather["temp"])) + "C  W " + str(_safe_int(weather["wind"])) + "km", 114, 146, PHOS_LIGHT)
        else:
            lcd.text("No weather cache", 114, 132, PHOS_ALERT)
            lcd.text(fit_text(self.feed_errors["weather"] or "Connect Wi-Fi first", 14), 114, 146, PHOS_MID)

        third_title = "MARKET" if self.stat_alt_panel else "ORBIT"
        self._draw_box(lcd, 106, 164, 124, 40, third_title, self.stat_selected == 2)
        if self.stat_alt_panel:
            rates = self.payloads["rates"]
            if rates:
                lcd.text("USD " + fit_text(rates.get("date", "?"), 10), 114, 178, PHOS_GLOW)
                lcd.text("EUR " + "{:.3f}".format(_safe_float(rates.get("EUR"))), 114, 192, PHOS_LIGHT)
                lcd.text("GBP " + "{:.3f}".format(_safe_float(rates.get("GBP"))), 170, 192, PHOS_MID)
            else:
                lcd.text("No market cache", 114, 178, PHOS_ALERT)
                lcd.text(fit_text(self.feed_errors["rates"] or "Link required", 14), 114, 192, PHOS_MID)
        else:
            space = self.payloads["space"]
            if space:
                lcd.text(fit_text(space["date"], 14), 114, 178, PHOS_GLOW)
                lcd.text(fit_text(space["title"], 14), 114, 192, PHOS_LIGHT)
            else:
                lcd.text("No orbit cache", 114, 178, PHOS_ALERT)
                lcd.text(fit_text(self.feed_errors["space"] or "Link required", 14), 114, 192, PHOS_MID)

        self._draw_footer(lcd, self._stat_hint())

    def _data_report(self):
        item = DATA_ITEMS[self.data_selected]
        feed = item["feed"]
        if feed is None:
            lines = [
                "OPEN COUNT " + str(self.open_count),
                "UPTIME " + self._uptime_text(),
                "CLOCK " + _clock_label(),
                "LINK  " + self.notice,
            ]
            lines.extend(self.event_log[:3] or ["NO EVENTS YET"])
            return item["name"], "LOCAL", lines[:7]

        if feed == "weather":
            weather = self.payloads["weather"]
            if weather is None:
                return "WEATHER", "OPEN-METEO", ["No cache.", self.feed_errors["weather"] or "Refresh with Wi-Fi."]
            lines = [
                weather["zone"] + " " + weather["label"],
                "TEMP  " + str(_safe_int(weather["temp"])) + "C",
                "FEELS " + str(_safe_int(weather["feels"])) + "C",
                "WIND  " + str(_safe_int(weather["wind"])) + " km/h",
                "HIGH  " + str(_safe_int(weather["high"])) + "C",
                "LOW   " + str(_safe_int(weather["low"])) + "C",
            ]
            return "WEATHER", "OPEN-METEO", lines

        if feed == "space":
            space = self.payloads["space"]
            if space is None:
                return "ORBITAL", "NASA APOD", ["No cache.", self.feed_errors["space"] or "Refresh with Wi-Fi."]
            lines = [space["date"], space["title"]]
            lines.extend(_wrap_text(space["summary"], 16, 4))
            return "ORBITAL", "NASA APOD", lines[:6]

        rates = self.payloads["rates"]
        if rates is None:
            return "MARKET", "FRANKFURTER", ["No cache.", self.feed_errors["rates"] or "Refresh with Wi-Fi."]
        lines = [
            "DATE  " + str(rates.get("date") or "?"),
            "EUR   " + "{:.3f}".format(_safe_float(rates.get("EUR"))),
            "GBP   " + "{:.3f}".format(_safe_float(rates.get("GBP"))),
            "JPY   " + "{:.1f}".format(_safe_float(rates.get("JPY"))),
            "100USD " + "{:.1f}".format(_safe_float(rates.get("JPY")) * 100),
        ]
        return "MARKET", "FRANKFURTER", lines

    def _data_meta_lines(self):
        item = DATA_ITEMS[self.data_selected]
        feed = item["feed"]
        if feed is None:
            lines = self.event_log[:6]
            if not lines:
                lines = ["No local log yet."]
            return lines
        return [
            "SOURCE " + item["name"],
            "STATE  " + self._feed_status(feed),
            "STAMP  " + fit_text(self.feed_stamps[feed] or "--", 16),
            "ERROR  " + fit_text(self.feed_errors[feed] or "clear", 16),
        ]

    def _draw_data_tab(self, lcd):
        self._draw_box(lcd, 10, 66, 72, 138, "FILES", True)
        row_y = 84
        for index, item in enumerate(DATA_ITEMS):
            active = index == self.data_selected
            if active:
                lcd.fill_rect(16, row_y - 3, 58, 13, PHOS_DIM)
            lcd.text(item["name"], 18, row_y, PHOS_LIGHT if active else PHOS_MID)
            row_y += 22
        lcd.text("VIEW", 18, 178, PHOS_LIGHT)
        lcd.text("META" if self.data_archive else "REPORT", 18, 192, PHOS_ALERT)

        self._draw_box(lcd, 92, 66, 138, 138, "REPORT", True)
        title, source, lines = self._data_report()
        lcd.text(_fit_box(title, 132), 100, 82, PHOS_GLOW)
        lcd.text(_fit_box(source, 132), 100, 98, PHOS_ALERT)
        lcd.hline(100, 114, 122, PHOS_DIM)

        body = self._data_meta_lines() if self.data_archive else lines
        line_y = 126
        for line in body[:5]:
            lcd.text(_fit_box(line, 132), 100, line_y, PHOS_LIGHT if line_y < 142 else PHOS_MID)
            line_y += 16

        feed = DATA_ITEMS[self.data_selected]["feed"]
        status_text = "local archive" if feed is None else self._feed_status(feed)
        lcd.text(_fit_box(status_text, 132), 100, 188, PHOS_ALERT)

        hint = "Meta view" if self.data_archive else "Report view"
        hint += " / " + status_text
        self._draw_footer(lcd, hint)

    def _station_lines(self, station):
        feed = station["feed"]
        if feed is None:
            return list(station["lines"])
        if feed == "weather":
            weather = self.payloads["weather"]
            if weather is None:
                return ["No live front.", self.feed_errors["weather"] or "Signal lost."]
            return [
                weather["zone"] + " " + weather["label"],
                "Temp " + str(_safe_int(weather["temp"])) + "C",
                "Wind " + str(_safe_int(weather["wind"])) + " km/h",
                "Humidity " + str(weather["humidity"]) + "%",
            ]
        if feed == "space":
            space = self.payloads["space"]
            if space is None:
                return ["No sky brief.", self.feed_errors["space"] or "Signal lost."]
            lines = [space["date"], space["title"]]
            lines.extend(_wrap_text(space["summary"], 18, 3))
            return lines[:5]
        rates = self.payloads["rates"]
        if rates is None:
            return ["No market tape.", self.feed_errors["rates"] or "Signal lost."]
        return [
            "Date " + str(rates.get("date") or "?"),
            "EUR " + "{:.3f}".format(_safe_float(rates.get("EUR"))),
            "GBP " + "{:.3f}".format(_safe_float(rates.get("GBP"))),
            "JPY " + "{:.1f}".format(_safe_float(rates.get("JPY"))),
        ]

    def _station_strength(self, station):
        feed = station["feed"]
        wobble = (self.frame * 3 + self.tuned_station * 11) % 14
        if feed is None:
            return 58 + wobble
        if self.payloads[feed] is not None and not self.feed_errors[feed]:
            return 76 + (wobble // 2)
        if self.payloads[feed] is not None:
            return 42 + (wobble // 2)
        return 16 + (wobble // 2)

    def _draw_wave(self, lcd, x, y, w, h, strength):
        lcd.rect(x, y, w, h, PHOS_DIM)
        bars = max(8, w // 8)
        for index in range(bars):
            phase = (index * 7 + self.frame * 3 + self.tuned_station * 5) % max(8, h - 6)
            bar_h = max(3, 3 + phase)
            if strength < 30 and index % 3 == 0:
                bar_h = 2
            bx = x + 2 + (index * 6)
            by = y + h - 2 - bar_h
            lcd.fill_rect(bx, by, 3, bar_h, PHOS_GLOW if index % 2 == 0 else PHOS_MID)

    def _draw_radio_tab(self, lcd):
        self._draw_box(lcd, 10, 66, 74, 138, "BAND", True)
        row_y = 84
        for index, station in enumerate(RADIO_STATIONS):
            active = index == self.radio_selected
            tuned = index == self.tuned_station
            if active:
                lcd.fill_rect(16, row_y - 3, 60, 13, PHOS_DIM)
            label = station["name"] + ("*" if tuned else "")
            lcd.text(fit_text(label, 8), 16, row_y, PHOS_LIGHT if active else PHOS_MID)
            row_y += 22

        station = RADIO_STATIONS[self.tuned_station]
        strength = self._station_strength(station)
        self._draw_box(lcd, 92, 66, 138, 138, "RECEIVER", True)
        lcd.text(_fit_box(station["name"], 132), 100, 82, PHOS_GLOW)
        lcd.text(_fit_box(station["deck"], 132), 100, 98, PHOS_ALERT)
        lcd.text("SIG " + str(strength) + "%", 100, 116, PHOS_LIGHT)
        self._draw_signal(lcd, 192, 112, strength)
        lcd.hline(100, 126, 122, PHOS_DIM)
        lines = self._station_lines(station)
        line_y = 138
        max_lines = 4 if self.radio_detail else 2
        for line in lines[:max_lines]:
            lcd.text(_fit_box(line, 132), 100, line_y, PHOS_LIGHT if line_y < 154 else PHOS_MID)
            line_y += 16
        self._draw_wave(lcd, 100, 170, 122, 24, strength)
        scope = "Detail" if self.radio_detail else "Scan"
        self._draw_footer(lcd, scope + " / tuned " + station["name"])

    def _point_at_cursor(self):
        for index, point in enumerate(MAP_POINTS):
            if point["x"] == self.map_cursor_x and point["y"] == self.map_cursor_y:
                return index
        return None

    def _selected_point(self):
        return MAP_POINTS[self.map_selected]

    def _snap_cursor_to_selected(self):
        point = self._selected_point()
        self.map_cursor_x = point["x"]
        self.map_cursor_y = point["y"]

    def _draw_map_tab(self, lcd):
        map_x = 18
        map_y = 76
        cell = 11
        grid_w = MAP_GRID_W * cell
        grid_h = MAP_GRID_H * cell
        self._draw_box(lcd, 10, 66, 136, 138, "SECTOR MAP", True)
        for gx in range(MAP_GRID_W + 1):
            x = map_x + (gx * cell)
            lcd.vline(x, map_y, grid_h, PHOS_DIM)
        for gy in range(MAP_GRID_H + 1):
            y = map_y + (gy * cell)
            lcd.hline(map_x, y, grid_w, PHOS_DIM)

        for index, point in enumerate(MAP_POINTS):
            px = map_x + (point["x"] * cell) + 3
            py = map_y + (point["y"] * cell) + 3
            color = PHOS_ALERT if index == self.map_selected else PHOS_GLOW
            lcd.fill_rect(px, py, 6, 6, color)

        cursor_px = map_x + (self.map_cursor_x * cell) + (cell // 2)
        cursor_py = map_y + (self.map_cursor_y * cell) + (cell // 2)
        lcd.hline(cursor_px - 5, cursor_py, 11, PHOS_LIGHT)
        lcd.vline(cursor_px, cursor_py - 5, 11, PHOS_LIGHT)

        hovered = self._point_at_cursor()
        if hovered is not None:
            self.map_selected = hovered
        point = self._selected_point()

        self._draw_box(lcd, 156, 66, 74, 138, "INFO", True)
        lcd.text(fit_text(point["name"], 8), 162, 82, PHOS_GLOW)
        lcd.text("MODE", 162, 102, PHOS_LIGHT)
        lcd.text("CURSOR" if self.map_cursor_mode else "TRACK", 162, 116, PHOS_ALERT)
        lcd.text("STATE", 162, 136, PHOS_LIGHT)
        lcd.text(fit_text(point["status"].upper(), 8), 162, 150, PHOS_MID)

        weather = self.payloads["weather"]
        if weather:
            lcd.text("WX", 162, 164, PHOS_LIGHT)
            lcd.text(fit_text(str(_safe_int(weather["temp"])) + "C " + weather["label"], 8), 162, 178, PHOS_MID)
        else:
            lcd.text("WX", 162, 164, PHOS_LIGHT)
            lcd.text("NO FEED", 162, 178, PHOS_MID)

        space = self.payloads["space"]
        if space:
            lcd.text("SKY", 162, 188, PHOS_LIGHT)
            lcd.text(fit_text(space["date"], 8), 162, 200, PHOS_MID)
        else:
            lcd.text("SKY", 162, 188, PHOS_LIGHT)
            lcd.text("NO FEED", 162, 200, PHOS_MID)

        hint = "Cursor live" if self.map_cursor_mode else "Track point"
        hint += " / " + point["name"]
        self._draw_footer(lcd, hint)

    def _draw_scene(self, lcd, runtime):
        lcd.fill(PHOS_BG)
        self._draw_scanlines(lcd)
        self._draw_header(lcd, runtime)
        self._draw_tabs(lcd)

        if TAB_NAMES[self.tab_index] == "STAT":
            self._draw_stat_tab(lcd, runtime)
        elif TAB_NAMES[self.tab_index] == "DATA":
            self._draw_data_tab(lcd)
        elif TAB_NAMES[self.tab_index] == "RADIO":
            self._draw_radio_tab(lcd)
        else:
            self._draw_map_tab(lcd)

    def _change_tab(self, delta):
        self.tab_index = (self.tab_index + delta) % len(TAB_NAMES)
        self.map_cursor_mode = False
        self._save_state()

    def _refresh_selected_data(self):
        feed = DATA_ITEMS[self.data_selected]["feed"]
        if feed is None:
            self._set_notice("Local logs only")
            return
        self._queue_refresh([feed], "data")

    def _refresh_selected_stat(self):
        if self.stat_selected == 0:
            self._queue_refresh(FEED_KEYS, "stat")
            return
        if self.stat_selected == 1:
            self._queue_refresh(["weather"], "weather")
            return
        self._queue_refresh(["rates"] if self.stat_alt_panel else ["space"], "stat")

    def _refresh_tuned_station(self):
        feed = RADIO_STATIONS[self.tuned_station]["feed"]
        if feed is None:
            self._set_notice("Carrier is static")
            return
        self._queue_refresh([feed], "radio")

    def step(self, runtime):
        buttons = runtime.buttons

        if self.loading:
            self._step_loading(runtime)
            return None

        self.frame = (self.frame + 1) % 1000

        if TAB_NAMES[self.tab_index] == "MAP" and self.map_cursor_mode:
            if buttons.repeat("LEFT", 150, 90):
                self.map_cursor_x = max(0, self.map_cursor_x - 1)
            if buttons.repeat("RIGHT", 150, 90):
                self.map_cursor_x = min(MAP_GRID_W - 1, self.map_cursor_x + 1)
            if buttons.repeat("UP", 150, 90):
                self.map_cursor_y = max(0, self.map_cursor_y - 1)
            if buttons.repeat("DOWN", 150, 90):
                self.map_cursor_y = min(MAP_GRID_H - 1, self.map_cursor_y + 1)
            if buttons.pressed("A"):
                self.map_cursor_mode = False
            if buttons.pressed("B"):
                hovered = self._point_at_cursor()
                if hovered is not None:
                    self.map_selected = hovered
                    self._set_notice("Locked " + MAP_POINTS[hovered]["name"])
                else:
                    self._set_notice("Cursor moved")
            if buttons.pressed("X"):
                self._snap_cursor_to_selected()
                self._set_notice("Center on " + self._selected_point()["name"])
            self._draw_scene(runtime.lcd, runtime)
            return None

        if buttons.pressed("LEFT"):
            self._change_tab(-1)
        elif buttons.pressed("RIGHT"):
            self._change_tab(1)
        else:
            tab = TAB_NAMES[self.tab_index]
            if tab == "STAT":
                if buttons.repeat("UP", 180, 120):
                    self.stat_selected = (self.stat_selected - 1) % 3
                if buttons.repeat("DOWN", 180, 120):
                    self.stat_selected = (self.stat_selected + 1) % 3
                if buttons.pressed("A"):
                    self.stat_alt_panel = not self.stat_alt_panel
                if buttons.pressed("B"):
                    self._refresh_selected_stat()
                    self._draw_loading(runtime.lcd, runtime)
                    return None
                if buttons.pressed("X"):
                    self._queue_refresh(FEED_KEYS, "full")
                    self._draw_loading(runtime.lcd, runtime)
                    return None
            elif tab == "DATA":
                if buttons.repeat("UP", 180, 120):
                    self.data_selected = (self.data_selected - 1) % len(DATA_ITEMS)
                if buttons.repeat("DOWN", 180, 120):
                    self.data_selected = (self.data_selected + 1) % len(DATA_ITEMS)
                if buttons.pressed("A"):
                    self.data_archive = not self.data_archive
                if buttons.pressed("B"):
                    self._refresh_selected_data()
                    if self.loading:
                        self._draw_loading(runtime.lcd, runtime)
                        return None
                if buttons.pressed("X"):
                    self._queue_refresh(FEED_KEYS, "full")
                    self._draw_loading(runtime.lcd, runtime)
                    return None
            elif tab == "RADIO":
                if buttons.repeat("UP", 180, 120):
                    self.radio_selected = (self.radio_selected - 1) % len(RADIO_STATIONS)
                if buttons.repeat("DOWN", 180, 120):
                    self.radio_selected = (self.radio_selected + 1) % len(RADIO_STATIONS)
                if buttons.pressed("A"):
                    self.radio_detail = not self.radio_detail
                if buttons.pressed("B"):
                    self.tuned_station = self.radio_selected
                    self._save_state()
                    self._log_event("TUNE " + RADIO_STATIONS[self.tuned_station]["name"])
                    self._set_notice("Tuned " + RADIO_STATIONS[self.tuned_station]["name"])
                if buttons.pressed("X"):
                    self._refresh_tuned_station()
                    if self.loading:
                        self._draw_loading(runtime.lcd, runtime)
                        return None
            else:
                if buttons.repeat("UP", 180, 120):
                    self.map_selected = (self.map_selected - 1) % len(MAP_POINTS)
                if buttons.repeat("DOWN", 180, 120):
                    self.map_selected = (self.map_selected + 1) % len(MAP_POINTS)
                if buttons.pressed("A"):
                    self.map_cursor_mode = False
                    self._set_notice("Tracking " + self._selected_point()["name"])
                if buttons.pressed("B"):
                    self.map_cursor_mode = True
                    self._snap_cursor_to_selected()
                    self._set_notice("Cursor engaged")
                if buttons.pressed("X"):
                    self._snap_cursor_to_selected()
                    self._set_notice("Center on " + self._selected_point()["name"])

        self._draw_scene(runtime.lcd, runtime)
        return None
