import time

from core.display import BLACK, WHITE, GRAY, CYAN
from core.controls import A_LABEL, B_LABEL, X_LABEL
from core.http import build_url, get_json
from core.ui import (
    WINDOW_CONTENT_X,
    WINDOW_CONTENT_Y,
    WINDOW_CONTENT_W,
    WINDOW_CONTENT_BOTTOM,
    WINDOW_TEXT_CHARS,
    draw_window_shell,
    fit_text,
)


WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
BOOK_SEARCH_URL = "https://openlibrary.org/search.json"
RATES_URL = "https://api.frankfurter.dev/v1/latest"
BREWERY_URL = "https://api.openbrewerydb.org/v1/breweries"
BOOK_DETAIL_URL = "https://openlibrary.org"

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


def _description_text(value, fallback="No description"):
    if isinstance(value, dict):
        value = value.get("value")
    if value:
        text = str(value)
        return text.replace("\n", " ")
    return fallback


def _page(title, url, deck, source, lines, items=None):
    return {
        "title": title,
        "url": url,
        "deck": deck,
        "source": source,
        "lines": lines,
        "items": items or [],
        "cursor": 0,
        "scroll": 0,
        "loaded_ms": time.ticks_ms(),
        "cache_key": "",
        "root_index": 0,
        "loader": None,
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
                "HI " + str(high) + "C / LO " + str(low) + "C",
                "OUTLOOK " + _weather_label(daily_code),
            ],
        ),
    }


def _load_openshelf():
    url = build_url(
        BOOK_SEARCH_URL,
        {
            "q": "science fiction",
            "fields": "title,author_name,first_publish_year,key,subject,edition_count",
            "limit": 4,
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

    items = []
    for index in range(min(4, len(docs))):
        doc = docs[index] or {}
        title = str(doc.get("title") or "Untitled")
        author = _first_text(doc.get("author_name"), "Anon")
        year = doc.get("first_publish_year")
        meta = author
        if year:
            meta += " " + str(year)
        work_key = str(doc.get("key") or "")
        subject = _first_text(doc.get("subject"), "science fiction")
        items.append({
            "action": "book-detail",
            "label": title,
            "meta": meta,
            "work_key": work_key,
            "title": title,
            "author": author,
            "year": year,
            "subject": subject,
            "cache_key": "book:" + (work_key or title),
        })

    return {
        "ok": True,
        "error": "",
        "page": _page(
            "Open Shelf",
            "https://openshelf.pico/trending/scifi",
            "Book picks from a public catalog",
            "Open Library",
            [
                "SCI-FI PICKS",
                "Open a title for notes",
            ],
            items,
        ),
    }


def _load_book_detail(item):
    title = item.get("title") or "Untitled"
    author = item.get("author") or "Anon"
    year = item.get("year")
    work_key = item.get("work_key") or ""
    fallback_lines = [
        "AUTHOR " + author,
        "YEAR " + (str(year) if year else "?"),
        "TOPIC " + item.get("subject", "science fiction"),
        "",
        "No extra notes",
    ]

    if not work_key.startswith("/works/"):
        return {
            "ok": True,
            "error": "",
            "page": _page(
                title,
                "https://openlibrary.org/",
                "Open Library work card",
                "Open Library",
                fallback_lines,
            ),
        }

    result = get_json(BOOK_DETAIL_URL + work_key + ".json", 5)
    if not result["ok"]:
        return {"ok": False, "error": result["error"] or "book detail failed"}

    data = result["data"] or {}
    description = _description_text(data.get("description"))
    subjects = data.get("subjects") or []
    subject_text = _first_text(subjects, item.get("subject", "science fiction"))
    lines = [
        "AUTHOR " + author,
        "YEAR " + (str(year) if year else "?"),
        "TOPIC " + subject_text,
        "",
        fit_text(description, 28),
    ]
    if len(description) > 28:
        lines.append(fit_text(description[28:], 28))

    return {
        "ok": True,
        "error": "",
        "page": _page(
            title,
            BOOK_DETAIL_URL + work_key,
            "Open Library work card",
            "Open Library",
            lines,
        ),
    }


def _rate_detail_page(code, rate, date):
    return _page(
        code + " Board",
        "https://rateboard.pico/markets/usd/" + code.lower(),
        "USD rate drill-down",
        "Frankfurter",
        [
            "DATE " + str(date or "?"),
            "1 USD = " + str(rate),
            "10 USD = " + "{:.2f}".format(float(rate) * 10),
            "100 USD = " + "{:.2f}".format(float(rate) * 100),
        ],
    )


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

    date = data.get("date") or "?"
    items = []
    for code in ("EUR", "GBP", "JPY"):
        if code not in rates:
            continue
        items.append({
            "action": "static-page",
            "label": code + " " + str(rates[code]),
            "meta": "Open rate sheet",
            "cache_key": "rate:" + code,
            "page": _rate_detail_page(code, rates[code], date),
        })

    return {
        "ok": True,
        "error": "",
        "page": _page(
            "RateBoard",
            "https://rateboard.pico/markets/usd",
            "Small foreign-exchange blotter",
            "Frankfurter",
            [
                "USD WATCH",
                "DATE " + str(date),
                "Pick a currency board",
            ],
            items,
        ),
    }


def _brewery_detail_page(item):
    lines = [
        fit_text(_upper_words(item.get("brewery_type") or "spot"), 28),
        fit_text((item.get("city") or "Portland") + ", " + (item.get("state") or "OR"), 28),
        fit_text(item.get("street") or "No street listed", 28),
    ]
    website = item.get("website_url") or ""
    if website:
        lines.append(fit_text(website.replace("https://", "").replace("http://", ""), 28))
    phone = item.get("phone") or ""
    if phone:
        lines.append("PHONE " + fit_text(phone, 22))

    return _page(
        item.get("name") or "Brewery",
        "https://taplist.pico/" + str(item.get("city") or "portland").lower(),
        "Brewery detail card",
        "Open Brewery DB",
        lines,
    )


def _load_taplist():
    url = build_url(
        BREWERY_URL,
        {
            "by_city": "portland",
            "by_state": "oregon",
            "by_type": "micro",
            "per_page": 4,
        },
    )
    result = get_json(url, 5)
    if not result["ok"]:
        return {"ok": False, "error": result["error"] or "brewery fetch failed"}

    data = result["data"] or []
    if not data:
        return {"ok": False, "error": "no breweries returned"}

    items = []
    for index in range(min(4, len(data))):
        brewery = data[index] or {}
        items.append({
            "action": "static-page",
            "label": str(brewery.get("name") or "Untitled"),
            "meta": _upper_words(brewery.get("brewery_type") or "spot") + " / " + str(brewery.get("city") or "Portland"),
            "cache_key": "brewery:" + str(brewery.get("id") or brewery.get("name") or index),
            "page": _brewery_detail_page(brewery),
        })

    return {
        "ok": True,
        "error": "",
        "page": _page(
            "TapList",
            "https://taplist.pico/portland",
            "Portland microbrew guide",
            "Open Brewery DB",
            [
                "PORTLAND POURS",
                "Open a place card",
            ],
            items,
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
        self.page_stack = []
        self.pending_request = None

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
        self.page_stack = []
        self.pending_request = None

    def help_lines(self, runtime):
        return [
            "Browser controls",
            "Up/Down picks bookmarks or items",
            "Left/Right switches top sites",
            B_LABEL + " opens or reloads",
            A_LABEL + " goes back",
            X_LABEL + " jumps to the next site",
        ]

    def _bookmark(self, index=None):
        if index is None:
            index = self.selected
        return BOOKMARKS[index]

    def _current_page(self):
        if not self.page_stack:
            return None
        return self.page_stack[-1]

    def _move_selection(self, delta):
        self.selected = (self.selected + delta) % len(BOOKMARKS)

    def _root_cache_key(self, index):
        return "bookmark:" + str(index)

    def _attach_page_meta(self, page, cache_key, root_index, loader):
        page["cache_key"] = cache_key
        page["root_index"] = root_index
        page["loader"] = loader
        if "cursor" not in page:
            page["cursor"] = 0
        if "scroll" not in page:
            page["scroll"] = 0
        return page

    def _show_cached_page(self, cache_key, push=False):
        page = self.cache.get(cache_key)
        if page is None:
            return False
        if push:
            self.page_stack.append(page)
        else:
            self.page_stack = [page]
        self.state = "page"
        self.pending_request = None
        return True

    def _queue_request(self, request):
        self.pending_request = request
        self.page_notice = ""
        self.page_error = ""
        self.state = "loading"
        self.loading_drawn = False

    def _start_root_loading(self, index, force_refresh=False):
        self.page_index = index
        self.selected = index
        cache_key = self._root_cache_key(index)
        if not force_refresh and self._show_cached_page(cache_key, False):
            return

        bookmark = self._bookmark(index)
        self._queue_request({
            "kind": "root",
            "index": index,
            "title": bookmark["title"],
            "url": bookmark["host"] + bookmark["path"],
            "cache_key": cache_key,
            "push": False,
            "loader": {"kind": "bookmark", "index": index},
        })

    def _start_item_loading(self, item, force_refresh=False):
        cache_key = item.get("cache_key", "")
        if cache_key and not force_refresh and self._show_cached_page(cache_key, True):
            return

        self._queue_request({
            "kind": "item",
            "item": item,
            "title": item.get("label", "Page"),
            "url": item.get("url", self._current_page()["url"] if self._current_page() else "about:blank"),
            "cache_key": cache_key,
            "push": True,
            "loader": {"kind": "item", "item": item},
        })

    def _browse_adjacent(self, delta):
        root_index = self.page_index
        current = self._current_page()
        if current is not None:
            root_index = current.get("root_index", root_index)
        next_index = (root_index + delta) % len(BOOKMARKS)
        self.page_stack = []
        self._start_root_loading(next_index)

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

    def _page_item_layout(self, page):
        summary_lines = min(2, len(page.get("lines") or []))
        items_y = WINDOW_CONTENT_Y + 58 + (summary_lines * 12)
        visible_rows = max(1, (WINDOW_CONTENT_BOTTOM - items_y - 18) // 22)
        return items_y, visible_rows

    def _move_page_cursor(self, delta):
        page = self._current_page()
        if page is None or not page.get("items"):
            return

        items = page["items"]
        page["cursor"] = (page.get("cursor", 0) + delta) % len(items)
        items_y, visible_rows = self._page_item_layout(page)
        del items_y
        if page["cursor"] < page.get("scroll", 0):
            page["scroll"] = page["cursor"]
        if page["cursor"] >= page.get("scroll", 0) + visible_rows:
            page["scroll"] = page["cursor"] - (visible_rows - 1)

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

    def _draw_loading(self, lcd, runtime):
        request = self.pending_request or {}
        draw_window_shell(lcd, "Browser", runtime.wifi.status())
        self._address_bar(lcd, request.get("url", "about:blank"))
        lcd.fill_rect(WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 22, WINDOW_CONTENT_W, 14, BLACK)
        lcd.text(fit_text(request.get("title", "Loading"), 16), WINDOW_CONTENT_X + 4, WINDOW_CONTENT_Y + 25, WHITE)
        lcd.text("Fetching page", WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 50, BLACK)
        lcd.text("Please wait", WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 68, BLACK)
        lcd.text("Rendering page", WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 92, GRAY)

    def _draw_page(self, lcd, runtime):
        page = self._current_page()
        if page is None:
            self._draw_bookmarks(lcd, runtime)
            return

        draw_window_shell(lcd, "Browser", runtime.wifi.status())
        self._address_bar(lcd, page["url"])
        lcd.fill_rect(WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 22, WINDOW_CONTENT_W, 14, BLACK)
        lcd.text(fit_text(page["title"], 14), WINDOW_CONTENT_X + 4, WINDOW_CONTENT_Y + 25, WHITE)
        lcd.text(fit_text(page["deck"], WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 42, BLACK)

        y = WINDOW_CONTENT_Y + 56
        lines = page.get("lines") or []
        items = page.get("items") or []
        if items:
            for index in range(min(2, len(lines))):
                line = lines[index]
                lcd.text(fit_text(line, WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, y, GRAY if not line else BLACK)
                y += 12

            items_y, visible_rows = self._page_item_layout(page)
            end = min(len(items), page.get("scroll", 0) + visible_rows)
            for index in range(page.get("scroll", 0), end):
                item = items[index]
                selected = index == page.get("cursor", 0)
                if selected:
                    lcd.fill_rect(WINDOW_CONTENT_X, items_y - 2, WINDOW_CONTENT_W, 20, BLACK)
                label_color = WHITE if selected else BLACK
                meta_color = WHITE if selected else GRAY
                lcd.text(fit_text(item.get("label", "Item"), WINDOW_TEXT_CHARS - 1), WINDOW_CONTENT_X + 2, items_y, label_color)
                lcd.text(fit_text(item.get("meta", ""), WINDOW_TEXT_CHARS - 1), WINDOW_CONTENT_X + 2, items_y + 10, meta_color)
                items_y += 22
        else:
            limit_y = WINDOW_CONTENT_BOTTOM - 18
            for line in lines:
                if y > limit_y:
                    break
                lcd.text(fit_text(line, WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, y, GRAY if not line else BLACK)
                y += 12

        if self.page_notice:
            status_line = self.page_notice
        elif self.page_error:
            status_line = "stale: " + self.page_error
        else:
            status_line = page["source"] + " / " + self._loaded_text(page.get("loaded_ms"))
            if items:
                status_line = str(len(items)) + " items from " + page["source"]
        lcd.text(fit_text(status_line, WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_BOTTOM - 10, GRAY)

    def _draw_error(self, lcd, runtime):
        request = self.pending_request or {}
        draw_window_shell(lcd, "Browser", runtime.wifi.status())
        self._address_bar(lcd, request.get("url", "about:blank"))
        lcd.text("Page unavailable", WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 28, BLACK)
        lcd.text(fit_text(self.page_error or "Browser error", WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 52, BLACK)
        lcd.text("Open Wi-Fi first", WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 76, GRAY)

    def _load_item_request(self, item):
        action = item.get("action")
        if action == "book-detail":
            return _load_book_detail(item)
        if action == "static-page":
            return {"ok": True, "error": "", "page": item.get("page")}
        return {"ok": False, "error": "page action missing"}

    def _use_stale_cache(self, request, notice):
        cache_key = request.get("cache_key", "")
        if not cache_key:
            return False
        if not self._show_cached_page(cache_key, request.get("push", False)):
            return False
        self.page_notice = notice
        self.page_error = ""
        return True

    def _load_request(self, runtime):
        request = self.pending_request
        if request is None:
            return

        status = runtime.wifi.status()
        if not status["supported"]:
            if self._use_stale_cache(request, "offline cache"):
                return
            self.page_error = "No network module"
            self.state = "error"
            return

        if not status["connected"]:
            if self._use_stale_cache(request, "offline cache"):
                return
            self.page_error = "connect Wi-Fi first"
            self.state = "error"
            return

        if request["kind"] == "root":
            result = self._bookmark(request["index"])["loader"]()
        else:
            result = self._load_item_request(request["item"])

        if result["ok"]:
            page = result["page"]
            page = self._attach_page_meta(page, request.get("cache_key", ""), self.page_index, request.get("loader"))
            cache_key = request.get("cache_key", "")
            if cache_key:
                self.cache[cache_key] = page
            if request.get("push"):
                self.page_stack.append(page)
            else:
                self.page_stack = [page]
            self.page_notice = ""
            self.page_error = ""
            self.pending_request = None
            self.state = "page"
            return

        self.page_error = result["error"] or "fetch failed"
        if self._use_stale_cache(request, "stale cache"):
            return
        self.state = "error"

    def _reload_current_page(self):
        page = self._current_page()
        if page is None:
            self._start_root_loading(self.selected, True)
            return

        loader = page.get("loader") or {}
        if loader.get("kind") == "bookmark":
            self.page_stack = []
            self._start_root_loading(loader.get("index", self.page_index), True)
        elif loader.get("kind") == "item":
            self.page_stack.pop()
            self._start_item_loading(loader.get("item") or {}, True)

    def step(self, runtime):
        buttons = runtime.buttons
        lcd = runtime.lcd

        if self.state == "bookmarks":
            if buttons.pressed("A"):
                return "home"
            if buttons.repeat("UP", 180, 100) or buttons.repeat("LEFT", 180, 100):
                self._move_selection(-1)
            if buttons.repeat("DOWN", 180, 100) or buttons.repeat("RIGHT", 180, 100) or buttons.pressed("X"):
                self._move_selection(1)
            if buttons.pressed("B"):
                self._start_root_loading(self.selected)
            self._draw_bookmarks(lcd, runtime)
            return None

        if self.state == "loading":
            if buttons.pressed("LEFT"):
                self.page_stack = []
                self._browse_adjacent(-1)
                self._draw_loading(lcd, runtime)
                return None
            if buttons.pressed("RIGHT") or buttons.pressed("X"):
                self.page_stack = []
                self._browse_adjacent(1)
                self._draw_loading(lcd, runtime)
                return None
            if buttons.pressed("A") or buttons.pressed("B"):
                self.pending_request = None
                if self.page_stack:
                    self.state = "page"
                    self._draw_page(lcd, runtime)
                else:
                    self.state = "bookmarks"
                    self._draw_bookmarks(lcd, runtime)
                return None
            if not self.loading_drawn:
                self.loading_drawn = True
                self._draw_loading(lcd, runtime)
                return None
            self._load_request(runtime)
        elif self.state == "error":
            if buttons.pressed("LEFT"):
                self.page_stack = []
                self._browse_adjacent(-1)
                self._draw_loading(lcd, runtime)
                return None
            if buttons.pressed("RIGHT") or buttons.pressed("X"):
                self.page_stack = []
                self._browse_adjacent(1)
                self._draw_loading(lcd, runtime)
                return None
            if buttons.pressed("A"):
                if self.page_stack:
                    self.state = "page"
                    self.pending_request = None
                    self._draw_page(lcd, runtime)
                else:
                    self.state = "bookmarks"
                    self.pending_request = None
                    self._draw_bookmarks(lcd, runtime)
                return None
            if buttons.pressed("B"):
                self.state = "loading"
                self.loading_drawn = False
                self._draw_loading(lcd, runtime)
                return None
            self._draw_error(lcd, runtime)
            return None
        else:
            page = self._current_page()
            if buttons.pressed("LEFT"):
                self.page_stack = []
                self._browse_adjacent(-1)
                self._draw_loading(lcd, runtime)
                return None
            if buttons.pressed("RIGHT") or buttons.pressed("X"):
                self.page_stack = []
                self._browse_adjacent(1)
                self._draw_loading(lcd, runtime)
                return None
            if buttons.repeat("UP", 180, 100):
                self._move_page_cursor(-1)
            if buttons.repeat("DOWN", 180, 100):
                self._move_page_cursor(1)
            if buttons.pressed("A"):
                self.page_notice = ""
                self.page_error = ""
                if len(self.page_stack) > 1:
                    self.page_stack.pop()
                else:
                    self.state = "bookmarks"
                    self._draw_bookmarks(lcd, runtime)
                    return None
            if buttons.pressed("B"):
                if page and page.get("items"):
                    item = page["items"][page.get("cursor", 0)]
                    self._start_item_loading(item)
                    self._draw_loading(lcd, runtime)
                    return None
                self._reload_current_page()
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
