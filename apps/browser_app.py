import time

from core.display import BLACK, WHITE, GRAY, CYAN
from core.controls import A_LABEL, B_LABEL, X_LABEL, Y_LABEL
from core.http import build_url, get_json
from core.ui import (
    WINDOW_CONTENT_X,
    WINDOW_CONTENT_Y,
    WINDOW_CONTENT_W,
    WINDOW_CONTENT_BOTTOM,
    WINDOW_TEXT_CHARS,
    draw_window_shell,
    draw_window_footer_actions,
    fit_text,
)


WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
BOOK_SEARCH_URL = "https://openlibrary.org/search.json"
RATES_URL = "https://api.frankfurter.dev/v1/latest"
BREWERY_URL = "https://api.openbrewerydb.org/v1/breweries"

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
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    80: "Rain shwr",
    81: "Rain shwr",
    82: "Hvy shwr",
    95: "T-storm",
}


def _safe_int(value, fallback=0):
    try:
        return int(round(float(value)))
    except Exception:
        return fallback


def _weather_label(code):
    return WEATHER_LABELS.get(code, "Code " + str(code))


def _upper_words(text):
    return str(text).replace("-", " ").upper()


def _first_text(value, fallback):
    if isinstance(value, list) and value:
        return str(value[0])
    if value:
        return str(value)
    return fallback


def _page(title, url, deck, source, lines):
    return {
        "title": title,
        "url": url,
        "deck": deck,
        "source": source,
        "lines": lines,
        "loaded_ms": time.ticks_ms(),
    }


def _load_weatherwire():
    url = build_url(
        WEATHER_URL,
        {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min",
            "forecast_days": 1,
            "timezone": "auto",
        },
    )
    result = get_json(url, 5)
    if not result["ok"]:
        return {"ok": False, "error": result["error"] or "weather fetch failed"}

    data = result["data"] or {}
    current = data.get("current") or {}
    daily = data.get("daily") or {}
    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    daily_codes = daily.get("weather_code") or []

    if "temperature_2m" not in current:
        return {"ok": False, "error": "weather payload missing current data"}

    current_code = _safe_int(current.get("weather_code"))
    high = _safe_int(highs[0] if highs else 0)
    low = _safe_int(lows[0] if lows else 0)
    daily_code = _safe_int(daily_codes[0] if daily_codes else current_code)

    return {
        "ok": True,
        "error": "",
        "page": _page(
            "WeatherWire",
            "https://weatherwire.pico/new-york",
            "New York forecast desk",
            "Open-Meteo",
            [
                "NEW YORK NOW",
                str(_safe_int(current.get("temperature_2m"))) + "C " + _weather_label(current_code),
                "FEELS " + str(_safe_int(current.get("apparent_temperature"))) + "C",
                "WIND " + str(_safe_int(current.get("wind_speed_10m"))) + " km/h",
                "",
                "TODAY HI " + str(high) + "C",
                "TODAY LO " + str(low) + "C",
                "OUTLOOK " + _weather_label(daily_code),
            ],
        ),
    }


def _load_openshelf():
    url = build_url(
        BOOK_SEARCH_URL,
        {
            "q": "science fiction",
            "fields": "title,author_name,first_publish_year",
            "limit": 3,
            "lang": "en",
        },
    )
    result = get_json(url, 5)
    if not result["ok"]:
        return {"ok": False, "error": result["error"] or "book search failed"}

    data = result["data"] or {}
    docs = data.get("docs") or []
    if not docs:
        return {"ok": False, "error": "no books returned"}

    lines = ["SCI-FI PICKS", ""]
    for index in range(min(3, len(docs))):
        doc = docs[index] or {}
        title = str(doc.get("title") or "Untitled")
        author = _first_text(doc.get("author_name"), "Anon")
        year = doc.get("first_publish_year")
        lines.append(str(index + 1) + ". " + title)
        meta = author
        if year:
            meta += " " + str(year)
        lines.append(meta)

    return {
        "ok": True,
        "error": "",
        "page": _page(
            "Open Shelf",
            "https://openshelf.pico/trending/scifi",
            "Book picks from a public catalog",
            "Open Library",
            lines,
        ),
    }


def _load_rateboard():
    url = build_url(
        RATES_URL,
        {
            "base": "USD",
            "symbols": "EUR,GBP,JPY",
        },
    )
    result = get_json(url, 5)
    if not result["ok"]:
        return {"ok": False, "error": result["error"] or "rates fetch failed"}

    data = result["data"] or {}
    rates = data.get("rates") or {}
    if not rates:
        return {"ok": False, "error": "rates payload missing values"}

    lines = [
        "USD WATCH",
        "DATE " + str(data.get("date") or "?"),
        "",
        "EUR " + str(rates.get("EUR", "?")),
        "GBP " + str(rates.get("GBP", "?")),
        "JPY " + str(rates.get("JPY", "?")),
        "",
    ]

    eur = rates.get("EUR")
    if eur is not None:
        lines.append("100 USD = " + "{:.2f}".format(float(eur) * 100) + " EUR")

    return {
        "ok": True,
        "error": "",
        "page": _page(
            "RateBoard",
            "https://rateboard.pico/markets/usd",
            "Small foreign-exchange blotter",
            "Frankfurter",
            lines,
        ),
    }


def _load_taplist():
    url = build_url(
        BREWERY_URL,
        {
            "by_city": "portland",
            "by_state": "oregon",
            "by_type": "micro",
            "per_page": 3,
        },
    )
    result = get_json(url, 5)
    if not result["ok"]:
        return {"ok": False, "error": result["error"] or "brewery fetch failed"}

    data = result["data"] or []
    if not data:
        return {"ok": False, "error": "no breweries returned"}

    lines = ["PORTLAND POURS", ""]
    for index in range(min(3, len(data))):
        brewery = data[index] or {}
        name = str(brewery.get("name") or "Untitled")
        brew_type = _upper_words(brewery.get("brewery_type") or "spot")
        city = str(brewery.get("city") or "Portland")
        lines.append(str(index + 1) + ". " + name)
        lines.append(brew_type + " / " + city)

    return {
        "ok": True,
        "error": "",
        "page": _page(
            "TapList",
            "https://taplist.pico/portland",
            "Portland microbrew guide",
            "Open Brewery DB",
            lines,
        ),
    }


BOOKMARKS = [
    {
        "title": "WeatherWire",
        "host": "weatherwire.pico",
        "path": "/new-york",
        "caption": "New York weather desk",
        "source": "Open-Meteo",
        "loader": _load_weatherwire,
    },
    {
        "title": "Open Shelf",
        "host": "openshelf.pico",
        "path": "/trending/scifi",
        "caption": "Science fiction picks",
        "source": "Open Library",
        "loader": _load_openshelf,
    },
    {
        "title": "RateBoard",
        "host": "rateboard.pico",
        "path": "/markets/usd",
        "caption": "Live USD rates",
        "source": "Frankfurter",
        "loader": _load_rateboard,
    },
    {
        "title": "TapList",
        "host": "taplist.pico",
        "path": "/portland",
        "caption": "Portland brewery guide",
        "source": "Open Brewery DB",
        "loader": _load_taplist,
    },
]


class BrowserApp:
    app_id = "browser"
    title = "Browser"
    accent = CYAN
    launch_mode = "window"

    def __init__(self):
        self.selected = 0
        self.state = "bookmarks"
        self.page_index = 0
        self.loading_drawn = False
        self.cache = {}
        self.page_notice = ""
        self.page_error = ""

    def draw_icon(self, lcd, cx, cy, selected, monochrome=False):
        ink = BLACK if monochrome and selected else (WHITE if monochrome else CYAN)
        paper = BLACK if monochrome and selected else WHITE
        lcd.rect(cx - 11, cy - 8, 22, 17, ink)
        lcd.fill_rect(cx - 9, cy - 5, 18, 11, paper)
        lcd.hline(cx - 7, cy - 2, 10, ink)
        lcd.hline(cx - 7, cy + 1, 12, ink)
        lcd.fill_rect(cx + 4, cy - 8, 4, 5, ink)

    def on_open(self, runtime):
        if self.selected >= len(BOOKMARKS):
            self.selected = 0
        self.state = "bookmarks"
        self.page_index = self.selected
        self.loading_drawn = False
        self.page_notice = ""
        self.page_error = ""

    def _bookmark(self, index=None):
        if index is None:
            index = self.selected
        return BOOKMARKS[index]

    def _move_selection(self, delta):
        self.selected = (self.selected + delta) % len(BOOKMARKS)

    def _browse_adjacent(self, delta):
        next_index = (self.page_index + delta) % len(BOOKMARKS)
        self.selected = next_index
        self._start_loading(next_index)

    def _loaded_text(self, loaded_ms):
        if loaded_ms is None:
            return "cache unknown"
        minutes = max(0, time.ticks_diff(time.ticks_ms(), loaded_ms) // 60000)
        if minutes < 1:
            return "updated now"
        if minutes < 60:
            return "updated " + str(minutes) + "m ago"
        return "updated " + str(minutes // 60) + "h ago"

    def _address_bar(self, lcd, address):
        lcd.rect(WINDOW_CONTENT_X, WINDOW_CONTENT_Y, WINDOW_CONTENT_W, 14, BLACK)
        lcd.text(fit_text(address, WINDOW_TEXT_CHARS - 1), WINDOW_CONTENT_X + 4, WINDOW_CONTENT_Y + 3, BLACK)

    def _draw_bookmarks(self, lcd, runtime):
        draw_window_shell(lcd, "Browser", runtime.wifi.status())
        self._address_bar(lcd, "about:bookmarks")
        lcd.text("Bookmarks", WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 22, BLACK)

        row_y = WINDOW_CONTENT_Y + 40
        row_h = 26
        for index in range(len(BOOKMARKS)):
            site = BOOKMARKS[index]
            selected = index == self.selected
            if selected:
                lcd.fill_rect(WINDOW_CONTENT_X, row_y - 2, WINDOW_CONTENT_W, row_h, BLACK)
            title_color = WHITE if selected else BLACK
            meta_color = WHITE if selected else GRAY
            lcd.text(fit_text(site["title"], 14), WINDOW_CONTENT_X + 2, row_y, title_color)
            lcd.text(fit_text(site["host"] + site["path"], WINDOW_TEXT_CHARS - 2), WINDOW_CONTENT_X + 2, row_y + 11, meta_color)
            row_y += row_h

        draw_window_footer_actions(lcd, X_LABEL + "/" + Y_LABEL + " pick", B_LABEL + " open", BLACK)

    def _draw_loading(self, lcd, runtime):
        bookmark = self._bookmark(self.page_index)
        draw_window_shell(lcd, "Browser", runtime.wifi.status())
        self._address_bar(lcd, bookmark["host"] + bookmark["path"])
        lcd.fill_rect(WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 22, WINDOW_CONTENT_W, 14, BLACK)
        lcd.text(fit_text(bookmark["title"], 16), WINDOW_CONTENT_X + 4, WINDOW_CONTENT_Y + 25, WHITE)
        lcd.text(fit_text(bookmark["caption"], WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 50, BLACK)
        lcd.text("Fetching live page", WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 76, BLACK)
        lcd.text("Source " + bookmark["source"], WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 94, GRAY)
        draw_window_footer_actions(lcd, X_LABEL + "/" + Y_LABEL + " site", B_LABEL + " stop", BLACK)

    def _draw_page(self, lcd, runtime):
        page = self.cache[self.page_index]

        draw_window_shell(lcd, "Browser", runtime.wifi.status())
        self._address_bar(lcd, page["url"])
        lcd.fill_rect(WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 22, WINDOW_CONTENT_W, 14, BLACK)
        lcd.text(fit_text(page["title"], 14), WINDOW_CONTENT_X + 4, WINDOW_CONTENT_Y + 25, WHITE)
        lcd.text(fit_text(page["deck"], WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 42, BLACK)

        y = WINDOW_CONTENT_Y + 60
        limit_y = WINDOW_CONTENT_BOTTOM - 18
        for line in page["lines"]:
            if y > limit_y:
                break
            color = GRAY if not line else BLACK
            lcd.text(fit_text(line, WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, y, color)
            y += 12

        status_line = page["source"] + " / " + self._loaded_text(page.get("loaded_ms"))
        if self.page_notice:
            status_line = self.page_notice
        elif self.page_error:
            status_line = "stale: " + self.page_error
        lcd.text(fit_text(status_line, WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_BOTTOM - 10, GRAY)
        draw_window_footer_actions(lcd, X_LABEL + "/" + Y_LABEL + " site", B_LABEL + " reload", BLACK)

    def _draw_error(self, lcd, runtime):
        bookmark = self._bookmark(self.page_index)
        draw_window_shell(lcd, "Browser", runtime.wifi.status())
        self._address_bar(lcd, bookmark["host"] + bookmark["path"])
        lcd.text("Page unavailable", WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 28, BLACK)
        lcd.text(fit_text(self.page_error or "Browser error", WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 52, BLACK)
        lcd.text("Open Wi-Fi first", WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 76, GRAY)
        draw_window_footer_actions(lcd, X_LABEL + "/" + Y_LABEL + " site", B_LABEL + " retry", BLACK)

    def _start_loading(self, index, force_refresh=False):
        self.page_index = index
        self.page_notice = ""
        self.page_error = ""
        if not force_refresh and index in self.cache:
            self.state = "page"
            return
        self.state = "loading"
        self.loading_drawn = False

    def _load_page(self, runtime):
        status = runtime.wifi.status()
        if not status["supported"]:
            self.page_error = "No network module"
            if self.page_index in self.cache:
                self.page_notice = "offline cache"
                self.state = "page"
            else:
                self.state = "error"
            return

        if not status["connected"]:
            self.page_error = "connect Wi-Fi first"
            if self.page_index in self.cache:
                self.page_notice = "offline cache"
                self.state = "page"
            else:
                self.state = "error"
            return

        result = self._bookmark(self.page_index)["loader"]()
        if result["ok"]:
            self.cache[self.page_index] = result["page"]
            self.page_notice = ""
            self.page_error = ""
            self.state = "page"
            return

        self.page_error = result["error"] or "fetch failed"
        if self.page_index in self.cache:
            self.page_notice = "stale cache"
            self.state = "page"
        else:
            self.state = "error"

    def step(self, runtime):
        buttons = runtime.buttons
        lcd = runtime.lcd

        if self.state == "bookmarks":
            if buttons.pressed("A"):
                return "home"
            if buttons.repeat("UP", 180, 100):
                self._move_selection(-1)
            if buttons.repeat("DOWN", 180, 100):
                self._move_selection(1)
            if buttons.pressed("X"):
                self._move_selection(-1)
            if buttons.pressed("Y"):
                self._move_selection(1)
            if buttons.pressed("B"):
                self._start_loading(self.selected)
            self._draw_bookmarks(lcd, runtime)
            return None

        if self.state == "loading":
            if buttons.pressed("X"):
                self._browse_adjacent(-1)
                self._draw_loading(lcd, runtime)
                return None
            if buttons.pressed("Y"):
                self._browse_adjacent(1)
                self._draw_loading(lcd, runtime)
                return None
            if buttons.pressed("A"):
                self.state = "bookmarks"
                self.selected = self.page_index
                self._draw_bookmarks(lcd, runtime)
                return None
            if buttons.pressed("B"):
                if self.page_index in self.cache:
                    self.state = "page"
                    self.page_notice = "cached page"
                    self._draw_page(lcd, runtime)
                else:
                    self.state = "bookmarks"
                    self.selected = self.page_index
                    self._draw_bookmarks(lcd, runtime)
                return None
            if not self.loading_drawn:
                self.loading_drawn = True
                self._draw_loading(lcd, runtime)
                return None
            self._load_page(runtime)
        elif self.state == "error":
            if buttons.pressed("X"):
                self._browse_adjacent(-1)
                self._draw_loading(lcd, runtime)
                return None
            if buttons.pressed("Y"):
                self._browse_adjacent(1)
                self._draw_loading(lcd, runtime)
                return None
            if buttons.pressed("A"):
                self.state = "bookmarks"
                self.selected = self.page_index
                self._draw_bookmarks(lcd, runtime)
                return None
            elif buttons.pressed("B"):
                self._start_loading(self.page_index, True)
                self._draw_loading(lcd, runtime)
                return None
            self._draw_error(lcd, runtime)
            return None
        else:
            if buttons.pressed("X"):
                self._browse_adjacent(-1)
                self._draw_loading(lcd, runtime)
                return None
            if buttons.pressed("Y"):
                self._browse_adjacent(1)
                self._draw_loading(lcd, runtime)
                return None
            if buttons.pressed("A"):
                self.state = "bookmarks"
                self.selected = self.page_index
                self.page_notice = ""
                self.page_error = ""
                self._draw_bookmarks(lcd, runtime)
                return None
            if buttons.pressed("B"):
                self._start_loading(self.page_index, True)
                self._draw_loading(lcd, runtime)
                return None
            self._draw_page(lcd, runtime)
            return None

        if self.state == "page":
            self._draw_page(lcd, runtime)
        elif self.state == "error":
            self._draw_error(lcd, runtime)
        else:
            self._draw_loading(lcd, runtime)
        return None
