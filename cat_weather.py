try:
    import utime as time
except ImportError:
    import time

import framebuf

from core.http import build_url, get_json
from core.ui import fit_text
from core.wifi import WiFiHelper, DEFAULT_SSID, DEFAULT_PASSWORD
from seengreat_eink_demo import (
    SeengreatEPD154,
    WIDTH,
    HEIGHT,
    BLACK,
    WHITE,
    DEFAULT_BAUDRATE,
    PROFILE_V2,
)


WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
CURRENT_FIELDS = "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m"
DEFAULT_LABEL = "Berlin"
DEFAULT_LATITUDE = 52.52
DEFAULT_LONGITUDE = 13.41

REFRESH_MS = 10 * 60 * 1000
RETRY_MS = 60 * 1000
CONNECT_RETRY_MS = 15 * 1000
FRAME_MS = 1000

WEATHER_LABELS = {
    0: "Clear",
    1: "Fair",
    2: "Partly cloudy",
    3: "Cloudy",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    56: "Freezing drizzle",
    57: "Freezing drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Freezing rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Rain showers",
    81: "Rain showers",
    82: "Heavy showers",
    85: "Snow showers",
    86: "Snow showers",
    95: "Thunderstorm",
    96: "Storm hail",
    99: "Storm hail",
}

try:
    from secrets import WEATHER_LABEL as SECRET_WEATHER_LABEL
except ImportError:
    SECRET_WEATHER_LABEL = DEFAULT_LABEL

try:
    from secrets import WEATHER_LATITUDE as SECRET_WEATHER_LATITUDE
except ImportError:
    SECRET_WEATHER_LATITUDE = DEFAULT_LATITUDE

try:
    from secrets import WEATHER_LONGITUDE as SECRET_WEATHER_LONGITUDE
except ImportError:
    SECRET_WEATHER_LONGITUDE = DEFAULT_LONGITUDE

try:
    from secrets import WEATHER_FLIP_X as SECRET_WEATHER_FLIP_X
except ImportError:
    SECRET_WEATHER_FLIP_X = True


def _ticks_ms():
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms()
    return int(time.time() * 1000)


def _ticks_diff(newer, older):
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(newer, older)
    return newer - older


def _sleep_ms(delay_ms):
    if hasattr(time, "sleep_ms"):
        time.sleep_ms(delay_ms)
        return
    time.sleep(delay_ms / 1000.0)


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


def _safe_text(value):
    value = str(value)
    chars = []
    for char in value:
        code = ord(char)
        if 32 <= code <= 126:
            chars.append(char)
        else:
            chars.append("?")
    return "".join(chars)


def _weather_label(code):
    return WEATHER_LABELS.get(code, "Unknown")


def _age_text(updated_ms):
    if updated_ms is None:
        return "never"

    minutes = max(0, _ticks_diff(_ticks_ms(), updated_ms) // 60000)
    if minutes < 1:
        return "now"
    if minutes < 60:
        return str(minutes) + "m"
    return str(minutes // 60) + "h"


def _expression_for_bucket(bucket):
    if ((bucket * 1103515245) + 12345) & 0x2000:
        return "smile"
    return "sad"


class MirroredEPD:
    def __init__(self, epd, flip_x=True):
        self._epd = epd
        self._flip_x = bool(flip_x)

    def _map_x(self, x):
        if not self._flip_x:
            return x
        return (WIDTH - 1) - x

    def init(self):
        return self._epd.init()

    def display(self):
        return self._epd.display()

    def clear(self, color=WHITE):
        return self._epd.clear(color)

    def sleep(self):
        return self._epd.sleep()

    def set_pixel(self, x, y, color=BLACK):
        return self._epd.set_pixel(self._map_x(x), y, color)

    def draw_line(self, x0, y0, x1, y1, color=BLACK):
        return self._epd.draw_line(self._map_x(x0), y0, self._map_x(x1), y1, color)

    def draw_rect(self, x0, y0, x1, y1, color=BLACK, thickness=1):
        return self._epd.draw_rect(self._map_x(x0), y0, self._map_x(x1), y1, color, thickness=thickness)

    def fill_rect(self, x0, y0, x1, y1, color=BLACK):
        return self._epd.fill_rect(self._map_x(x0), y0, self._map_x(x1), y1, color)

    def draw_circle(self, cx, cy, radius, color=BLACK):
        return self._epd.draw_circle(self._map_x(cx), cy, radius, color)


def _fill_disc(epd, cx, cy, radius, color=BLACK):
    radius_sq = radius * radius
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if (dx * dx) + (dy * dy) <= radius_sq:
                epd.set_pixel(cx + dx, cy + dy, color)


def _draw_thick_line(epd, x0, y0, x1, y1, color=BLACK, width=3):
    dx = x1 - x0
    dy = y1 - y0
    steps = max(abs(dx), abs(dy), 1)
    radius = max(1, width // 2)
    for step in range(steps + 1):
        x = x0 + ((dx * step) // steps)
        y = y0 + ((dy * step) // steps)
        _fill_disc(epd, x, y, radius, color)


def _draw_curve(epd, p0, p1, p2, color=BLACK, width=3, steps=20):
    last_x = int(p0[0])
    last_y = int(p0[1])
    for step in range(1, steps + 1):
        t = step / steps
        inv = 1.0 - t
        x = (inv * inv * p0[0]) + (2 * inv * t * p1[0]) + (t * t * p2[0])
        y = (inv * inv * p0[1]) + (2 * inv * t * p1[1]) + (t * t * p2[1])
        next_x = int(round(x))
        next_y = int(round(y))
        _draw_thick_line(epd, last_x, last_y, next_x, next_y, color, width)
        last_x = next_x
        last_y = next_y


def _draw_text(epd, x, y, text, color=BLACK):
    text = _safe_text(text)
    if not text:
        return

    width = len(text) * 8
    buf = bytearray(width)
    glyph = framebuf.FrameBuffer(buf, width, 8, framebuf.MONO_HMSB)

    if color == BLACK:
        glyph.fill(1)
        glyph.text(text, 0, 0, 0)
        target = 0
    else:
        glyph.fill(0)
        glyph.text(text, 0, 0, 1)
        target = 1

    for yy in range(8):
        py = y + yy
        if py < 0 or py >= HEIGHT:
            continue
        for xx in range(width):
            if glyph.pixel(xx, yy) == target:
                px = x + xx
                if 0 <= px < WIDTH:
                    epd.set_pixel(px, py, color)


def _draw_center_text(epd, y, text, color=BLACK):
    text = _safe_text(text)
    x = max(0, (WIDTH - (len(text) * 8)) // 2)
    _draw_text(epd, x, y, text, color)


def _draw_weather_glyph(epd, x, y, code):
    if code in (0, 1):
        for radius in range(10, 13):
            epd.draw_circle(x + 16, y + 16, radius, BLACK)
        _draw_thick_line(epd, x + 16, y - 2, x + 16, y + 4, BLACK, 2)
        _draw_thick_line(epd, x + 16, y + 28, x + 16, y + 34, BLACK, 2)
        _draw_thick_line(epd, x - 2, y + 16, x + 4, y + 16, BLACK, 2)
        _draw_thick_line(epd, x + 28, y + 16, x + 34, y + 16, BLACK, 2)
        _draw_thick_line(epd, x + 4, y + 4, x + 8, y + 8, BLACK, 2)
        _draw_thick_line(epd, x + 24, y + 24, x + 28, y + 28, BLACK, 2)
        _draw_thick_line(epd, x + 4, y + 28, x + 8, y + 24, BLACK, 2)
        _draw_thick_line(epd, x + 24, y + 8, x + 28, y + 4, BLACK, 2)
        return

    for radius in range(8, 10):
        epd.draw_circle(x + 12, y + 18, radius, BLACK)
        epd.draw_circle(x + 22, y + 14, radius, BLACK)
        epd.draw_circle(x + 31, y + 18, radius, BLACK)
    epd.fill_rect(x + 8, y + 18, x + 34, y + 27, WHITE)
    epd.draw_line(x + 7, y + 27, x + 36, y + 27, BLACK)
    epd.draw_line(x + 8, y + 28, x + 34, y + 28, BLACK)

    if code >= 61:
        _draw_thick_line(epd, x + 12, y + 33, x + 9, y + 39, BLACK, 2)
        _draw_thick_line(epd, x + 21, y + 33, x + 18, y + 39, BLACK, 2)
        _draw_thick_line(epd, x + 30, y + 33, x + 27, y + 39, BLACK, 2)


def _draw_sparkle(epd, cx, cy, size=4):
    epd.draw_line(cx - size, cy, cx + size, cy, BLACK)
    epd.draw_line(cx, cy - size, cx, cy + size, BLACK)
    epd.draw_line(cx - (size - 1), cy - (size - 1), cx + (size - 1), cy + (size - 1), BLACK)
    epd.draw_line(cx - (size - 1), cy + (size - 1), cx + (size - 1), cy - (size - 1), BLACK)


def _draw_dotted_line(epd, x0, y, x1, step=7):
    if x1 < x0:
        x0, x1 = x1, x0
    for x in range(x0, x1 + 1, step):
        _fill_disc(epd, x, y, 1, BLACK)


def _draw_wavy_line(epd, x0, y, x1, amplitude=3, segment=18):
    x = x0
    while x < x1:
        end = min(x1, x + segment)
        _draw_curve(
            epd,
            (x, y),
            (x + ((end - x) // 2), y - amplitude),
            (end, y),
            BLACK,
            1,
            10,
        )
        x = end


def _draw_cat(epd, x, y, mood):
    cx = x + 36
    cy = y + 42

    for radius in range(28, 30):
        epd.draw_circle(cx, cy, radius, BLACK)

    _draw_curve(epd, (cx - 18, cy - 22), (cx - 30, cy - 56), (cx - 9, cy - 40), BLACK, 3, 16)
    _draw_curve(epd, (cx - 9, cy - 40), (cx - 5, cy - 30), (cx - 15, cy - 18), BLACK, 3, 10)
    _draw_curve(epd, (cx + 18, cy - 22), (cx + 30, cy - 56), (cx + 9, cy - 40), BLACK, 3, 16)
    _draw_curve(epd, (cx + 9, cy - 40), (cx + 5, cy - 30), (cx + 15, cy - 18), BLACK, 3, 10)

    _fill_disc(epd, cx - 11, cy - 4, 3, BLACK)
    _fill_disc(epd, cx + 11, cy - 4, 3, BLACK)

    _draw_thick_line(epd, cx - 3, cy + 8, cx + 3, cy + 8, BLACK, 2)
    _draw_thick_line(epd, cx - 3, cy + 8, cx, cy + 12, BLACK, 2)
    _draw_thick_line(epd, cx + 3, cy + 8, cx, cy + 12, BLACK, 2)

    if mood == "smile":
        _draw_curve(epd, (cx - 11, cy + 16), (cx - 8, cy + 22), (cx - 1, cy + 19), BLACK, 2, 10)
        _draw_curve(epd, (cx + 11, cy + 16), (cx + 8, cy + 22), (cx + 1, cy + 19), BLACK, 2, 10)
    else:
        _draw_curve(epd, (cx - 11, cy + 22), (cx - 8, cy + 16), (cx - 1, cy + 18), BLACK, 2, 10)
        _draw_curve(epd, (cx + 11, cy + 22), (cx + 8, cy + 16), (cx + 1, cy + 18), BLACK, 2, 10)

    for whisker_y in (8, 14):
        _draw_thick_line(epd, cx - 5, cy + whisker_y, cx - 24, cy + whisker_y - 3, BLACK, 1)
        _draw_thick_line(epd, cx + 5, cy + whisker_y, cx + 24, cy + whisker_y - 3, BLACK, 1)


class CatWeatherScreen:
    def __init__(self, label=None, latitude=None, longitude=None, baudrate=DEFAULT_BAUDRATE, profile=PROFILE_V2):
        self.label = str(label if label is not None else SECRET_WEATHER_LABEL or DEFAULT_LABEL)
        self.latitude = _safe_float(latitude if latitude is not None else SECRET_WEATHER_LATITUDE, DEFAULT_LATITUDE)
        self.longitude = _safe_float(longitude if longitude is not None else SECRET_WEATHER_LONGITUDE, DEFAULT_LONGITUDE)
        self.epd = MirroredEPD(
            SeengreatEPD154(baudrate=baudrate, profile=profile),
            flip_x=SECRET_WEATHER_FLIP_X,
        )
        self.wifi = WiFiHelper()
        self.weather = None
        self.error = ""
        self.last_refresh_ms = None
        self.last_attempt_ms = None
        self.last_connect_attempt_ms = None
        self.last_ssid = ""
        self.expression_bucket = None
        self.expression = "smile"
        self.pending_action = None
        self.render_key = None
        self.epd.init()

    def _request_url(self):
        return build_url(
            WEATHER_URL,
            {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "current": CURRENT_FIELDS,
                "timezone": "auto",
            },
        )

    def _set_expression(self, now_ms):
        bucket = now_ms // 60000
        if bucket != self.expression_bucket:
            self.expression_bucket = bucket
            self.expression = _expression_for_bucket(bucket)

    def _connect_due(self, now_ms):
        if self.last_connect_attempt_ms is None:
            return True
        return _ticks_diff(now_ms, self.last_connect_attempt_ms) >= CONNECT_RETRY_MS

    def _refresh_due(self, now_ms):
        if self.weather is None or self.last_refresh_ms is None:
            if self.last_attempt_ms is None:
                return True
            return _ticks_diff(now_ms, self.last_attempt_ms) >= RETRY_MS
        return _ticks_diff(now_ms, self.last_refresh_ms) >= REFRESH_MS

    def _schedule_actions(self, now_ms):
        if self.pending_action:
            return

        status = self.wifi.status()
        if status["connected"]:
            self.last_ssid = status["ssid"]
            if self._refresh_due(now_ms):
                self.pending_action = "weather"
            return

        self.last_ssid = ""
        if not status["supported"]:
            self.error = "NO NETWORK MODULE"
            return

        if not DEFAULT_SSID:
            self.error = "ADD SSID/PASSWORD IN SECRETS.PY"
            return

        if self._connect_due(now_ms):
            self.pending_action = "connect"

    def _perform_connect(self, now_ms):
        self.pending_action = None
        self.last_connect_attempt_ms = now_ms
        result = self.wifi.connect(DEFAULT_SSID, DEFAULT_PASSWORD)
        if result["ok"]:
            self.last_ssid = DEFAULT_SSID
            self.error = ""
            return
        self.error = "WIFI " + fit_text(_safe_text(result["error"] or "connect failed"), 17)

    def _perform_refresh(self, now_ms):
        self.pending_action = None
        self.last_attempt_ms = now_ms
        result = get_json(self._request_url(), 5)
        if not result["ok"]:
            self.error = "WEATHER " + fit_text(_safe_text(result["error"] or "fetch failed"), 14)
            return

        current = (result["data"] or {}).get("current") or {}
        if "temperature_2m" not in current or "weather_code" not in current:
            self.error = "WEATHER BAD RESPONSE"
            return

        self.weather = {
            "temperature": _safe_float(current.get("temperature_2m")),
            "feels_like": _safe_float(current.get("apparent_temperature")),
            "humidity": _safe_int(current.get("relative_humidity_2m")),
            "wind": _safe_float(current.get("wind_speed_10m")),
            "weather_code": _safe_int(current.get("weather_code")),
        }
        self.last_refresh_ms = now_ms
        self.error = ""

    def _weather_signature(self):
        if self.weather is None:
            return None
        return (
            _safe_int(self.weather["temperature"]),
            _safe_int(self.weather["feels_like"]),
            _safe_int(self.weather["humidity"]),
            _safe_int(self.weather["wind"]),
            _safe_int(self.weather["weather_code"]),
        )

    def _status_lines(self):
        if self.pending_action == "connect":
            return ("CONNECTING WIFI", fit_text(_safe_text(DEFAULT_SSID), 23))
        if self.pending_action == "weather":
            return ("FETCHING WEATHER", fit_text(_safe_text(self.label), 23))
        if self.error:
            if self.weather is not None:
                return (fit_text(_safe_text(self.error), 23), "USING LAST WEATHER")
            return (fit_text(_safe_text(self.error), 23), "WAITING")
        if self.last_ssid:
            return (
                "WIFI " + fit_text(_safe_text(self.last_ssid), 18),
                "UPDATED " + _safe_text(_age_text(self.last_refresh_ms)).upper(),
            )
        return ("BOOTING", "WAITING")

    def _render_signature(self):
        line1, line2 = self._status_lines()
        return (
            self.expression,
            self._weather_signature(),
            line1,
            line2,
            fit_text(_safe_text(self.label), 11),
        )

    def _draw_header(self):
        _draw_text(self.epd, 10, 8, "CAT WEATHER")
        _draw_dotted_line(self.epd, 10, 22, 86)
        _draw_wavy_line(self.epd, 98, 18, 190, amplitude=3, segment=18)
        _draw_sparkle(self.epd, 160, 10, 3)
        _draw_sparkle(self.epd, 182, 22, 2)

    def _draw_weather_panel(self):
        x0 = 104
        y0 = 40
        city = fit_text(_safe_text(self.label), 11)
        _draw_text(self.epd, x0, y0, city)
        _draw_dotted_line(self.epd, x0, y0 + 12, 190, step=6)

        if self.weather is None:
            _draw_text(self.epd, x0, y0 + 34, "WAITING")
            _draw_text(self.epd, x0, y0 + 48, "FOR WEATHER")
            return

        code = self.weather["weather_code"]
        _draw_weather_glyph(self.epd, x0, y0 + 18, code)
        _draw_text(self.epd, x0 + 46, y0 + 24, "%sC" % _safe_int(self.weather["temperature"]))
        _draw_text(self.epd, x0, y0 + 58, fit_text(_weather_label(code), 11))
        _draw_text(self.epd, x0, y0 + 76, "FEELS %sC" % _safe_int(self.weather["feels_like"]))
        _draw_text(self.epd, x0, y0 + 90, "WIND %sKM" % _safe_int(self.weather["wind"]))
        _draw_text(self.epd, x0, y0 + 104, "HUM  %s%%" % _safe_int(self.weather["humidity"]))

    def _draw_footer(self):
        line1, line2 = self._status_lines()
        _draw_wavy_line(self.epd, 6, 160, 194, amplitude=3, segment=22)
        _draw_text(self.epd, 10, 170, fit_text(_safe_text(line1), 23))
        _draw_text(self.epd, 10, 182, fit_text(_safe_text(line2), 23))
        _draw_sparkle(self.epd, 184, 172, 2)

    def draw(self):
        self.epd.clear(WHITE)
        self._draw_header()
        _draw_cat(self.epd, 12, 64, self.expression)
        self.epd.draw_line(94, 36, 94, 150, BLACK)
        self._draw_weather_panel()
        self._draw_footer()
        self.epd.display()

    def step(self):
        now_ms = _ticks_ms()
        self._set_expression(now_ms)
        self._schedule_actions(now_ms)

        render_key = self._render_signature()
        if render_key != self.render_key:
            self.draw()
            self.render_key = render_key

        if self.pending_action == "connect":
            self._perform_connect(now_ms)
        elif self.pending_action == "weather":
            self._perform_refresh(now_ms)

    def run(self):
        while True:
            self.step()
            _sleep_ms(FRAME_MS)

    def sleep(self):
        self.epd.sleep()


def run(label=None, latitude=None, longitude=None, baudrate=DEFAULT_BAUDRATE, profile=PROFILE_V2):
    screen = CatWeatherScreen(
        label=label,
        latitude=latitude,
        longitude=longitude,
        baudrate=baudrate,
        profile=profile,
    )
    try:
        screen.run()
    finally:
        screen.sleep()
    return screen


def run_once(label=None, latitude=None, longitude=None, baudrate=DEFAULT_BAUDRATE, profile=PROFILE_V2):
    screen = CatWeatherScreen(
        label=label,
        latitude=latitude,
        longitude=longitude,
        baudrate=baudrate,
        profile=profile,
    )
    screen.step()
    return screen


if __name__ == "__main__":
    run()
