import time

from lcd import BLACK, WHITE, CYAN, YELLOW, GREEN, GRAY, ORANGE, RED, SLATE
from core.ui import draw_header, draw_footer, fit_text, HOME_HINT


KEYBOARD_PAGES = [
    ("abc", list("abcdefghijklmnopqrstuvwxyz") + ["SP", "BK", "123", "ABC", "SYM", "OK", "CAN"]),
    ("ABC", list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + ["SP", "BK", "123", "abc", "SYM", "OK", "CAN"]),
    ("123", list("0123456789") + ["-", "_", ".", "@", "BK", "abc", "SYM", "OK", "CAN"]),
    ("SYM", list("!?#$%&+=:;/") + ["SP", "BK", "123", "abc", "OK", "CAN"]),
]

KEY_LABELS = {
    "SP": "SPC",
    "BK": "BK",
    "OK": "JOIN",
    "CAN": "BACK",
    "abc": "abc",
    "ABC": "ABC",
    "123": "123",
    "SYM": "!?",
}

KEYBOARD_NOTE = "Pick 123/ABC/!?"
WIFI_LIST_ROWS = 4
WIFI_NAME_X = 12
WIFI_MARKER_X = 150
WIFI_NAME_CHARS = 17
MARQUEE_HOLD_STEPS = 4
MARQUEE_STEP_MS = 180


class WiFiStatusApp:
    app_id = "wifi"
    title = "Wi-Fi"
    accent = GREEN

    def __init__(self):
        self.results = []
        self.saved_profiles = {}
        self.selected = 0
        self.scroll = 0
        self.error = ""
        self.state = "status"
        self.current_network = None
        self.password_buffer = ""
        self.keyboard_page = 0
        self.keyboard_index = 0
        self.keyboard_note = ""
        self.connect_password = ""
        self.connect_remember = False
        self.connect_drawn = False
        self.result = None
        self.marquee_key = None
        self.marquee_started_ms = 0

    def draw_icon(self, lcd, cx, cy, selected, monochrome=False):
        ring = BLACK if monochrome and selected else (WHITE if monochrome else YELLOW)
        ink = BLACK if monochrome and selected else (WHITE if monochrome else GREEN)
        lcd.pixel(cx, cy + 7, ink)
        lcd.ellipse(cx, cy + 4, 3, 2, ink, False)
        lcd.ellipse(cx, cy + 1, 6, 4, ink, False)
        lcd.ellipse(cx, cy - 2, 9, 6, ink, False)
        if not monochrome and selected:
            lcd.ellipse(cx, cy + 2, 12, 10, ring, False)

    def on_open(self, runtime):
        self.state = "status"
        self.results = []
        self.saved_profiles = runtime.wifi.load_profiles()
        self.selected = 0
        self.scroll = 0
        self.error = ""
        self.current_network = None
        self.password_buffer = ""
        self.keyboard_page = 0
        self.keyboard_index = 0
        self.keyboard_note = ""
        self.connect_password = ""
        self.connect_remember = False
        self.connect_drawn = False
        self.result = None
        self._reset_marquee()

    def refresh(self, runtime):
        self.saved_profiles = runtime.wifi.load_profiles()
        data = runtime.wifi.scan()
        self.results = data["results"]
        self.error = data["error"]
        self._reset_marquee()
        if self.selected >= len(self.results):
            self.selected = max(0, len(self.results) - 1)
        if self.scroll > self.selected:
            self.scroll = self.selected

    def _open_networks(self, runtime):
        self.selected = 0
        self.scroll = 0
        self.refresh(runtime)
        self.state = "list"

    def _selected_item(self):
        if not self.results:
            return None
        return self.results[self.selected]

    def _secure_network(self, item):
        if item is None:
            return False
        return item["security"] != "OPEN"

    def _saved_password(self, item):
        if item is None:
            return ""
        return self.saved_profiles.get(item["ssid"], "")

    def _has_saved_profile(self, item):
        if item is None:
            return False
        return item["ssid"] in self.saved_profiles

    def _move_selection(self, delta):
        if not self.results:
            return
        count = len(self.results)
        self.selected = (self.selected + delta) % count
        if self.selected < self.scroll:
            self.scroll = self.selected
        if self.selected >= self.scroll + WIFI_LIST_ROWS:
            self.scroll = self.selected - (WIFI_LIST_ROWS - 1)

    def _reset_marquee(self):
        self.marquee_key = None
        self.marquee_started_ms = time.ticks_ms()

    def _marquee_offset(self, text, width_chars, key):
        if len(text) <= width_chars:
            return 0

        if self.marquee_key != key:
            self.marquee_key = key
            self.marquee_started_ms = time.ticks_ms()

        max_offset = len(text) - width_chars
        cycle = (MARQUEE_HOLD_STEPS * 2) + (max_offset * 2)
        if cycle <= 0:
            return 0

        phase = (time.ticks_diff(time.ticks_ms(), self.marquee_started_ms) // MARQUEE_STEP_MS) % cycle
        if phase < MARQUEE_HOLD_STEPS:
            return 0

        phase -= MARQUEE_HOLD_STEPS
        if phase < max_offset:
            return phase + 1

        phase -= max_offset
        if phase < MARQUEE_HOLD_STEPS:
            return max_offset

        phase -= MARQUEE_HOLD_STEPS
        return max(0, max_offset - 1 - phase)

    def _marquee_text(self, text, width_chars, key):
        if len(text) <= width_chars:
            return text

        offset = self._marquee_offset(text, width_chars, key)
        visible = text[offset:offset + width_chars]
        if offset > 0:
            visible = "..." + visible[3:]
        if offset + width_chars < len(text):
            visible = visible[:-3] + "..."
        return visible

    def _network_name(self, item, selected):
        ssid = item["ssid"]
        if not selected:
            return fit_text(ssid, WIFI_NAME_CHARS)
        return self._marquee_text(ssid, WIFI_NAME_CHARS, ("list", self.selected, ssid))

    def _open_keyboard(self, item, password):
        self.current_network = item
        self.password_buffer = password
        self.keyboard_page = 0
        self.keyboard_index = 0
        self.keyboard_note = KEYBOARD_NOTE
        self.state = "keyboard"

    def _start_connect(self, item, password, remember):
        self.current_network = item
        self.connect_password = password
        self.connect_remember = remember
        self.connect_drawn = False
        self.result = None
        self.state = "connecting"

    def _set_result(self, ok, error, ifconfig=None):
        self.result = {
            "ok": ok,
            "error": error,
            "ifconfig": ifconfig,
        }
        self.state = "result"

    def _keyboard_tokens(self):
        return KEYBOARD_PAGES[self.keyboard_page][1]

    def _set_keyboard_page(self, page_index):
        self.keyboard_page = page_index % len(KEYBOARD_PAGES)
        tokens = self._keyboard_tokens()
        self.keyboard_index %= len(tokens)
        self.keyboard_note = KEYBOARD_NOTE

    def _append_password_char(self, token):
        if len(self.password_buffer) >= 32:
            self.keyboard_note = "32 char max"
            return
        if token == "SP":
            self.password_buffer += " "
        else:
            self.password_buffer += token
        self.keyboard_note = KEYBOARD_NOTE

    def _handle_keyboard_token(self):
        token = self._keyboard_tokens()[self.keyboard_index]
        if token == "BK":
            self.password_buffer = self.password_buffer[:-1]
            self.keyboard_note = KEYBOARD_NOTE
        elif token == "OK":
            if not self.password_buffer:
                self.keyboard_note = "Need password"
            else:
                self._start_connect(self.current_network, self.password_buffer, True)
        elif token == "CAN":
            self.state = "list"
        elif token == "123":
            self._set_keyboard_page(2)
        elif token == "ABC":
            self._set_keyboard_page(1)
        elif token == "abc":
            self._set_keyboard_page(0)
        elif token == "SYM":
            self._set_keyboard_page(3)
        else:
            self._append_password_char(token)

    def _draw_status(self, lcd, runtime):
        status = runtime.wifi.status()
        detail = "LINK" if status["connected"] else ("JOIN" if status.get("connecting") else ("READY" if status["active"] else "OFF"))

        lcd.fill(BLACK)
        draw_header(lcd, "Wi-Fi", detail, GREEN)

        if not status["supported"]:
            lcd.text("No network", 4, 18, ORANGE)
            lcd.text("module here", 4, 30, WHITE)
            draw_footer(lcd, HOME_HINT)
            return

        if status["connected"]:
            ssid = status["ssid"] or "connected"
            ifconfig = status["ifconfig"] or ("ip ?", "mask ?", "gw ?", "dns ?")
            lcd.text(self._marquee_text(ssid, 19, ("status", ssid)), 4, 12, CYAN)
            lcd.text(fit_text("IP " + ifconfig[0], 19), 4, 22, WHITE)
            lcd.text(fit_text("MASK " + ifconfig[1], 19), 4, 32, WHITE)
            lcd.text(fit_text("GW " + ifconfig[2], 19), 4, 42, WHITE)
            lcd.text(fit_text("DNS " + ifconfig[3], 19), 4, 52, GRAY)
            action = "Join another"
        elif status.get("connecting"):
            target = status.get("target") or "saved network"
            lcd.text("Restoring Wi-Fi", 4, 12, CYAN)
            lcd.text(fit_text(target, 18), 4, 22, WHITE)
            lcd.text("Saved profile", 4, 42, WHITE)
            lcd.text("Please wait", 4, 52, GRAY)
            action = "Join network"
        elif status["active"]:
            lcd.text("Not connected", 4, 12, ORANGE)
            lcd.text("Radio active", 4, 22, CYAN)
            lcd.text("Open a scan to", 4, 42, WHITE)
            lcd.text("pick a network", 4, 52, GRAY)
            action = "Join network"
        else:
            lcd.text("Not connected", 4, 12, ORANGE)
            lcd.text("Radio off", 4, 22, ORANGE)
            lcd.text("Opening scan", 4, 42, WHITE)
            lcd.text("will wake Wi-Fi", 4, 52, GRAY)
            action = "Join network"

        lcd.fill_rect(0, 60, 160, 10, SLATE)
        lcd.text(">", 2, 61, WHITE)
        lcd.text(fit_text(action, WIFI_NAME_CHARS), WIFI_NAME_X, 61, WHITE)
        draw_footer(lcd, HOME_HINT)
        lcd.text("B open", 110, 71, GRAY)

    def _draw_list(self, lcd, runtime):
        status = runtime.wifi.status()
        chosen = self._selected_item()
        detail = ""
        if chosen:
            detail = fit_text(chosen["security"], 6)

        lcd.fill(BLACK)
        draw_header(lcd, "Wi-Fi", detail, GREEN)

        if not status["supported"]:
            lcd.text("No network", 4, 18, ORANGE)
            lcd.text("module here", 4, 30, WHITE)
            draw_footer(lcd, HOME_HINT)
            return

        if status["connected"]:
            ssid = status["ssid"] or "connected"
            lcd.text(fit_text(ssid, 18), 4, 12, CYAN)
            ip = status["ifconfig"][0] if status["ifconfig"] else "ip ?"
            lcd.text(fit_text(ip, 18), 4, 22, WHITE)
        elif status["active"]:
            lcd.text("Radio active", 4, 12, CYAN)
            lcd.text("Choose a network", 4, 22, WHITE)
        else:
            lcd.text("Radio off", 4, 12, ORANGE)
            lcd.text("Scan woke radio", 4, 22, WHITE)

        if chosen:
            saved = self._has_saved_profile(chosen)
            if chosen["hidden"]:
                lcd.text("Hidden SSID", 4, 22, ORANGE)
            elif self._secure_network(chosen):
                lcd.text("Saved pass" if saved else "Need password", 4, 22, WHITE)
            else:
                lcd.text("Saved open" if saved else "Open network", 4, 22, WHITE)

        if self.error:
            lcd.text(fit_text(self.error, 18), 4, 34, ORANGE)
            draw_footer(lcd, "A status")
            return

        if not self.results:
            lcd.text("No SSIDs found", 4, 34, GRAY)
            draw_footer(lcd, "A status")
            return

        y = 34
        end = min(len(self.results), self.scroll + WIFI_LIST_ROWS)
        for index in range(self.scroll, end):
            item = self.results[index]
            selected = index == self.selected
            if selected:
                lcd.fill_rect(0, y - 1, 160, 10, GRAY)

            prefix = ">" if selected else " "
            text_color = BLACK if selected else WHITE
            lcd.text(prefix, 2, y, text_color)
            lcd.text(self._network_name(item, selected), WIFI_NAME_X, y, text_color)

            marker = "S" if self._has_saved_profile(item) else ("O" if not self._secure_network(item) else "*")
            lcd.text(marker, WIFI_MARKER_X, y, BLACK if selected else CYAN)
            y += 10

        draw_footer(lcd, "A status", GRAY)
        lcd.text("B join", 86, 71, GRAY)

    def _draw_keyboard(self, lcd):
        page_name = KEYBOARD_PAGES[self.keyboard_page][0]
        lcd.fill(BLACK)
        draw_header(lcd, "Password", page_name, GREEN)

        ssid = self.current_network["ssid"] if self.current_network else "network"
        lcd.text(fit_text(ssid, 18), 4, 12, CYAN)
        lcd.text("Pass", 4, 24, WHITE)
        buffer_text = self.password_buffer if self.password_buffer else "_"
        lcd.text(fit_text(buffer_text[-18:], 18), 4, 34, YELLOW if self.password_buffer else GRAY)
        note_color = GRAY if self.keyboard_note == KEYBOARD_NOTE else ORANGE
        lcd.text(fit_text(self.keyboard_note, 18), 4, 44, note_color)

        tokens = self._keyboard_tokens()
        for slot in range(5):
            offset = slot - 2
            token_index = (self.keyboard_index + offset) % len(tokens)
            token = tokens[token_index]
            label = KEY_LABELS.get(token, token)
            x = 4 + (slot * 31)
            selected = offset == 0
            fill = SLATE if selected else BLACK
            border = YELLOW if selected else GRAY
            text_color = BLACK if selected else WHITE
            lcd.fill_rect(x, 50, 28, 14, fill)
            lcd.rect(x, 50, 28, 14, border)
            tx = x + max(1, (28 - (len(label) * 8)) // 2)
            lcd.text(label, tx, 53, text_color)

        draw_footer(lcd, "A next", GRAY)
        lcd.text("B pick", 66, 71, GRAY)

    def _draw_connecting(self, lcd):
        dots = "." * ((time.ticks_ms() // 250) % 4)
        lcd.fill(BLACK)
        draw_header(lcd, "Joining", color=GREEN)
        ssid = self.current_network["ssid"] if self.current_network else "network"
        lcd.text(fit_text(ssid, 18), 4, 18, CYAN)
        lcd.text("Connecting" + dots, 4, 34, WHITE)
        lcd.text("Please wait", 4, 48, GRAY)
        draw_footer(lcd, HOME_HINT)

    def _draw_result(self, lcd):
        ok = self.result and self.result["ok"]
        header_color = GREEN if ok else RED
        title = "Joined" if ok else "Failed"
        lcd.fill(BLACK)
        draw_header(lcd, title, color=header_color)

        ssid = self.current_network["ssid"] if self.current_network else "network"
        lcd.text(fit_text(ssid, 18), 4, 16, CYAN)

        if ok:
            ip = self.result["ifconfig"][0] if self.result["ifconfig"] else "ip ?"
            lcd.text(fit_text(ip, 18), 4, 30, WHITE)
            if self.connect_remember and self.connect_password:
                lcd.text("Password saved", 4, 44, GRAY)
            draw_footer(lcd, "A status", GREEN)
            lcd.text("B nets", 94, 71, GREEN)
        else:
            error = self.result["error"] if self.result else "connection failed"
            lcd.text(fit_text(error, 18), 4, 30, ORANGE)
            if self._secure_network(self.current_network):
                lcd.text("B edit pass", 4, 44, GRAY)
                draw_footer(lcd, "A status", RED)
                lcd.text("B edit", 88, 71, RED)
            else:
                draw_footer(lcd, "A status", RED)
                lcd.text("B retry", 80, 71, RED)

    def _step_status(self, runtime):
        if runtime.buttons.pressed("B") and runtime.wifi.supported():
            self._open_networks(runtime)
            self._draw_list(runtime.lcd, runtime)
            return
        self._draw_status(runtime.lcd, runtime)

    def _step_list(self, runtime):
        buttons = runtime.buttons
        if buttons.repeat("UP", 180, 100):
            self._move_selection(-1)
        if buttons.repeat("DOWN", 180, 100):
            self._move_selection(1)
        if buttons.pressed("A"):
            self.state = "status"
        if buttons.pressed("B"):
            chosen = self._selected_item()
            if chosen is None:
                pass
            elif chosen["hidden"]:
                self.current_network = chosen
                self.result = {"ok": False, "error": "hidden SSID", "ifconfig": None}
                self.state = "result"
            elif not self._secure_network(chosen):
                self._start_connect(chosen, "", False)
            else:
                saved_password = self._saved_password(chosen)
                if saved_password:
                    self._start_connect(chosen, saved_password, True)
                else:
                    self._open_keyboard(chosen, "")
        self._draw_list(runtime.lcd, runtime)

    def _step_keyboard(self, runtime):
        buttons = runtime.buttons
        tokens = self._keyboard_tokens()
        if buttons.repeat("LEFT", 160, 80):
            self.keyboard_index = (self.keyboard_index - 1) % len(tokens)
        if buttons.repeat("RIGHT", 160, 80):
            self.keyboard_index = (self.keyboard_index + 1) % len(tokens)
        if buttons.pressed("A") or buttons.repeat("A", 220, 90):
            self.keyboard_index = (self.keyboard_index + 1) % len(tokens)
        if buttons.repeat("UP", 180, 100):
            self._set_keyboard_page(self.keyboard_page - 1)
        if buttons.repeat("DOWN", 180, 100):
            self._set_keyboard_page(self.keyboard_page + 1)
        if buttons.pressed("B"):
            self._handle_keyboard_token()
        self._draw_keyboard(runtime.lcd)

    def _step_connecting(self, runtime):
        if not self.connect_drawn:
            self.connect_drawn = True
            self._draw_connecting(runtime.lcd)
            return

        result = runtime.wifi.connect(self.current_network["ssid"], self.connect_password)
        if result["ok"]:
            remember_password = None
            if self._secure_network(self.current_network):
                if self.connect_remember:
                    remember_password = self.connect_password
            else:
                remember_password = ""

            runtime.wifi.remember_connection(self.current_network["ssid"], remember_password)
            if remember_password is not None:
                self.saved_profiles[self.current_network["ssid"]] = remember_password
        self._set_result(result["ok"], result["error"], result["ifconfig"])
        self._draw_result(runtime.lcd)

    def _step_result(self, runtime):
        buttons = runtime.buttons
        ok = self.result and self.result["ok"]

        if ok:
            if buttons.pressed("A"):
                self.state = "status"
            if buttons.pressed("B"):
                self._open_networks(runtime)
        else:
            if buttons.pressed("A"):
                self.state = "status"
            if buttons.pressed("B") and self._secure_network(self.current_network):
                self._open_keyboard(self.current_network, self.connect_password)
            elif buttons.pressed("B"):
                self._start_connect(self.current_network, self.connect_password, self.connect_remember)
        self._draw_result(runtime.lcd)

    def step(self, runtime):
        if self.state == "status":
            self._step_status(runtime)
        elif self.state == "list":
            self._step_list(runtime)
        elif self.state == "keyboard":
            self._step_keyboard(runtime)
        elif self.state == "connecting":
            self._step_connecting(runtime)
        else:
            self._step_result(runtime)
        return None
