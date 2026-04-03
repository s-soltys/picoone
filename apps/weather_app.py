import time

from core.display import BLACK, WHITE, GRAY, BLUE, ORANGE, GREEN, YELLOW
from core.controls import B_LABEL, X_LABEL
from core.ui import (
    WINDOW_CONTENT_X,
    WINDOW_CONTENT_Y,
    WINDOW_CONTENT_W,
    WINDOW_CONTENT_BOTTOM,
    WINDOW_TEXT_CHARS,
    draw_field,
    draw_window_shell,
    fit_text,
)
from core.http import build_url, get_json

try:
    import ujson as json
except ImportError:
    import json


WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_MS = 15 * 60 * 1000
STATE_PATH = "weather_state.json"
CURRENT_FIELDS = "temperature_2m,apparent_temperature,weather_code,wind_speed_10m"
DAILY_FIELDS = "weather_code,temperature_2m_max,temperature_2m_min"
CITY_OPTIONS = [
    {"name": "Berlin", "short": "Berlin", "latitude": 52.52, "longitude": 13.41},
    {"name": "London", "short": "London", "latitude": 51.5072, "longitude": -0.1276},
    {"name": "New York", "short": "NYC", "latitude": 40.7128, "longitude": -74.006},
    {"name": "Tokyo", "short": "Tokyo", "latitude": 35.6762, "longitude": 139.6503},
    {"name": "Sydney", "short": "Sydney", "latitude": -33.8688, "longitude": 151.2093},
]
WEATHER_LABELS = {
    0: "Clear",
    1: "Fair",
    2: "Partly cld",
    3: "Cloudy",
    45: "Fog",
    48: "Rime fog",
    51: "Light driz",
    53: "Drizzle",
    55: "Heavy driz",
    56: "Frz driz",
    57: "Frz driz",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Frz rain",
    67: "Frz rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grain",
    80: "Rain shwr",
    81: "Rain shwr",
    82: "Hvy shwr",
    85: "Snow shwr",
    86: "Snow shwr",
    95: "T-storm",
    96: "Storm hail",
    99: "Storm hail",
}


def _safe_int(value, fallback=0):
    try:
        return int(round(float(value)))
    except Exception:
        return fallback


def _safe_float(value, fallback=0.0):
    try:
        return float(value)
    except Exception:
        return fallback


def _weather_label(code):
    return WEATHER_LABELS.get(code, "?")


def _temp_text(value):
    return str(_safe_int(value)) + "C"


def _wind_text(value):
    return str(_safe_int(value)) + "km/h"


def _age_text(updated_ms):
    if updated_ms is None:
        return "never"

    delta_ms = max(0, time.ticks_diff(time.ticks_ms(), updated_ms))
    minutes = delta_ms // 60000
    if minutes < 1:
        return "now"
    if minutes < 60:
        return str(minutes) + "m"
    hours = minutes // 60
    return str(hours) + "h"


def _forecast_label(index, iso_date):
    if index == 0:
        return "Today"
    if not iso_date or len(iso_date) < 10:
        return "Day " + str(index + 1)
    return iso_date[5:7] + "/" + iso_date[8:10]


class WeatherApp:
    app_id = "weather"
    title = "Weather"
    accent = BLUE
    launch_mode = "window"

    def __init__(self):
        self.city_index = 0
        self.view = "current"
        self.loading = False
        self.loading_drawn = False
        self.payload = None
        self.payload_city_index = None
        self.last_refresh_ms = None
        self.persisted_cache = False
        self.error = ""
        self._load_state()

    def draw_icon(self, lcd, cx, cy, selected, monochrome=False):
        if monochrome:
            sun = BLACK if selected else WHITE
            cloud = BLACK if selected else WHITE
        else:
            sun = YELLOW
            cloud = WHITE

        lcd.fill_rect(cx - 5, cy - 2, 14, 7, cloud)
        lcd.ellipse(cx - 3, cy, 5, 4, cloud, True)
        lcd.ellipse(cx + 4, cy - 1, 6, 5, cloud, True)
        lcd.ellipse(cx + 10, cy + 1, 4, 3, cloud, True)
        lcd.fill_rect(cx - 10, cy - 9, 6, 6, sun)
        lcd.hline(cx - 10, cy - 12, 6, sun)
        lcd.hline(cx - 10, cy - 2, 6, sun)
        lcd.vline(cx - 13, cy - 9, 6, sun)
        lcd.vline(cx - 1, cy - 9, 6, sun)

    def on_open(self, runtime):
        self.view = "current"
        self.error = ""
        if self.payload_city_index != self.city_index:
            self.payload = None
            self.last_refresh_ms = None
            self.persisted_cache = False
        if self._refresh_due():
            self._queue_refresh()

    def help_lines(self, runtime):
        return [
            "Weather controls",
            "Left/Right changes city",
            "Up/Down switches view",
            B_LABEL + " refresh now",
            X_LABEL + " next city",
        ]

    def _city(self):
        return CITY_OPTIONS[self.city_index]

    def _refresh_due(self):
        if self.payload is None:
            return True
        if self.payload_city_index != self.city_index:
            return True
        if self.last_refresh_ms is None:
            return True
        return time.ticks_diff(time.ticks_ms(), self.last_refresh_ms) >= CACHE_MS

    def _queue_refresh(self):
        self.loading = True
        self.loading_drawn = False
        self.error = ""

    def _change_city(self, delta):
        self.city_index = (self.city_index + delta) % len(CITY_OPTIONS)
        self.payload = None
        self.payload_city_index = None
        self.last_refresh_ms = None
        self.persisted_cache = False
        self.error = ""
        self._save_state()
        self._queue_refresh()

    def _load_state(self):
        try:
            with open(STATE_PATH, "r") as handle:
                state = json.loads(handle.read())
        except OSError:
            return
        except Exception:
            return

        city_index = state.get("city_index")
        if isinstance(city_index, int) and 0 <= city_index < len(CITY_OPTIONS):
            self.city_index = city_index

        payload_city_index = state.get("payload_city_index")
        payload = state.get("payload")
        if not isinstance(payload_city_index, int) or payload_city_index < 0 or payload_city_index >= len(CITY_OPTIONS):
            payload_city_index = None
        if payload is not None and payload_city_index is not None:
            self.payload = payload
            self.payload_city_index = payload_city_index
            self.last_refresh_ms = None
            self.persisted_cache = True

    def _save_state(self):
        state = {
            "city_index": self.city_index,
            "payload_city_index": self.payload_city_index,
            "payload": self.payload,
        }
        try:
            with open(STATE_PATH, "w") as handle:
                handle.write(json.dumps(state))
        except OSError:
            pass

    def _request_url(self):
        city = self._city()
        return build_url(
            WEATHER_URL,
            {
                "latitude": city["latitude"],
                "longitude": city["longitude"],
                "current": CURRENT_FIELDS,
                "daily": DAILY_FIELDS,
                "forecast_days": 3,
                "timezone": "auto",
            },
        )

    def _compact_payload(self, data):
        current = data.get("current") or {}
        daily = data.get("daily") or {}
        dates = daily.get("time") or []
        codes = daily.get("weather_code") or []
        highs = daily.get("temperature_2m_max") or []
        lows = daily.get("temperature_2m_min") or []

        if "temperature_2m" not in current or "weather_code" not in current:
            return None

        count = min(3, len(dates), len(codes), len(highs), len(lows))
        forecast = []
        for index in range(count):
            forecast.append(
                {
                    "label": _forecast_label(index, dates[index]),
                    "code": _safe_int(codes[index]),
                    "high": _safe_float(highs[index]),
                    "low": _safe_float(lows[index]),
                }
            )

        if not forecast:
            return None

        return {
            "current": {
                "temperature": _safe_float(current.get("temperature_2m")),
                "feels_like": _safe_float(current.get("apparent_temperature")),
                "weather_code": _safe_int(current.get("weather_code")),
                "wind_speed": _safe_float(current.get("wind_speed_10m")),
            },
            "forecast": forecast,
        }

    def _perform_refresh(self, runtime):
        status = runtime.wifi.status()
        if not status["supported"]:
            self.error = "no network module"
            self.loading = False
            return
        if not status["connected"]:
            self.error = "connect Wi-Fi first"
            self.loading = False
            return

        result = get_json(self._request_url(), 5)
        self.loading = False
        if not result["ok"]:
            self.error = result["error"] or "fetch failed"
            return

        payload = self._compact_payload(result["data"] or {})
        if payload is None:
            self.error = "bad weather data"
            return

        self.payload = payload
        self.payload_city_index = self.city_index
        self.last_refresh_ms = time.ticks_ms()
        self.persisted_cache = False
        self.error = ""
        self._save_state()

    def _draw_loading(self, lcd, runtime):
        draw_window_shell(lcd, "Weather", runtime.wifi.status())
        lcd.text(fit_text(self._city()["name"], WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 8, BLUE)
        lcd.text("Fetching forecast", WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 40, BLACK)
        lcd.text("Please wait", WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 66, GRAY)
        draw_field(lcd, WINDOW_CONTENT_X, WINDOW_CONTENT_BOTTOM - 18, WINDOW_CONTENT_W, 16, "Loading weather", BLUE)

    def _draw_empty(self, lcd, runtime):
        draw_window_shell(lcd, "Weather", runtime.wifi.status())
        lcd.text(fit_text(self._city()["name"], WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 8, BLUE)
        lcd.text(fit_text(self.error or "No weather data", WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 40, BLACK)
        lcd.text("Cached data unavailable", WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 66, GRAY)
        draw_field(lcd, WINDOW_CONTENT_X, WINDOW_CONTENT_BOTTOM - 18, WINDOW_CONTENT_W, 16, "No cached forecast", ORANGE)

    def _draw_status_note(self, lcd):
        if self.error:
            note = "stale: " + self.error
            accent = ORANGE
        elif self.persisted_cache:
            note = "Saved cache"
            accent = GRAY
        else:
            note = "Updated " + _age_text(self.last_refresh_ms)
            accent = GRAY
        draw_field(lcd, WINDOW_CONTENT_X, WINDOW_CONTENT_BOTTOM - 18, WINDOW_CONTENT_W, 16, fit_text(note, WINDOW_TEXT_CHARS), accent)

    def _draw_current(self, lcd, runtime):
        city = self._city()
        current = self.payload["current"]
        code = current["weather_code"]

        draw_window_shell(lcd, "Weather", runtime.wifi.status())
        lcd.text(fit_text(city["name"], WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 6, BLUE)
        lcd.text(fit_text(_weather_label(code), WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 30, ORANGE if code == 0 else BLACK)
        lcd.text(
            fit_text("T " + _temp_text(current["temperature"]) + " F " + _temp_text(current["feels_like"]), WINDOW_TEXT_CHARS),
            WINDOW_CONTENT_X,
            WINDOW_CONTENT_Y + 58,
            BLACK,
        )
        lcd.text(fit_text("Wind " + _wind_text(current["wind_speed"]), WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 86, BLUE)
        self._draw_status_note(lcd)

    def _draw_forecast(self, lcd, runtime):
        city = self._city()

        draw_window_shell(lcd, "Weather", runtime.wifi.status())
        lcd.text(fit_text(city["name"], WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 6, BLUE)

        y = WINDOW_CONTENT_Y + 36
        for period in self.payload["forecast"]:
            line = period["label"] + " " + _temp_text(period["high"]) + "/" + _temp_text(period["low"])
            line += " " + _weather_label(period["code"])
            lcd.text(fit_text(line, WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, y, BLACK)
            y += 22

        self._draw_status_note(lcd)

    def _step_loading(self, runtime):
        if not self.loading_drawn:
            self.loading_drawn = True
            self._draw_loading(runtime.lcd, runtime)
            return
        self._perform_refresh(runtime)

    def step(self, runtime):
        buttons = runtime.buttons

        if self.loading:
            self._step_loading(runtime)
            return None

        if buttons.repeat("LEFT", 180, 120):
            self._change_city(-1)
            self._draw_loading(runtime.lcd, runtime)
            return None
        if buttons.repeat("RIGHT", 180, 120):
            self._change_city(1)
            self._draw_loading(runtime.lcd, runtime)
            return None
        if buttons.pressed("X"):
            self._change_city(1)
            self._draw_loading(runtime.lcd, runtime)
            return None
        if buttons.pressed("UP") or buttons.pressed("DOWN"):
            if self.view == "current":
                self.view = "forecast"
            else:
                self.view = "current"
        if buttons.pressed("B"):
            self._queue_refresh()
            self._draw_loading(runtime.lcd, runtime)
            return None

        if self.payload is None:
            self._draw_empty(runtime.lcd, runtime)
        elif self.view == "forecast":
            self._draw_forecast(runtime.lcd, runtime)
        else:
            self._draw_current(runtime.lcd, runtime)
        return None
