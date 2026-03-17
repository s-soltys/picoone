import time

from core.display import BLACK, WHITE, CYAN, YELLOW, GREEN, GRAY, ORANGE, RED, SLATE
from core.controls import A_LABEL, B_LABEL
from core.ui import CONTENT_TOP, SCREEN_W, draw_header, draw_footer_actions, fit_text, HOME_HINT


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
WIFI_LIST_ROWS = 9
WIFI_NAME_X = 16
WIFI_MARKER_X = SCREEN_W - 16
WIFI_NAME_CHARS = 24
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
        card_y = CONTENT_TOP + 116

        lcd.fill(BLACK)
        draw_header(lcd, "Wi-Fi", detail, GREEN)

        if not status["supported"]:
            lcd.text("No network", 4, CONTENT_TOP + 14, ORANGE)
            lcd.text("module here", 4, CONTENT_TOP + 34, WHITE)
            draw_footer_actions(lcd, HOME_HINT)
            return

        if status["connected"]:
            ssid = status["ssid"] or "connected"
            ifconfig = status["ifconfig"] or ("ip ?", "mask ?", "gw ?", "dns ?")
            lcd.text(self._marquee_text(ssid, 26, ("status", ssid)), 4, CONTENT_TOP + 6, CYAN)
            lcd.text(fit_text("IP " + ifconfig[0], 28), 4, CONTENT_TOP + 28, WHITE)
            lcd.text(fit_text("MASK " + ifconfig[1], 28), 4, CONTENT_TOP + 50, WHITE)
            lcd.text(fit_text("GW " + ifconfig[2], 28), 4, CONTENT_TOP + 72, WHITE)
            lcd.text(fit_text("DNS " + ifconfig[3], 28), 4, CONTENT_TOP + 94, GRAY)
            action = "Join another"
        elif status.get("connecting"):
            target = status.get("target") or "saved network"
            lcd.text("Restoring Wi-Fi", 4, CONTENT_TOP + 6, CYAN)
            lcd.text(fit_text(target, 28), 4, CONTENT_TOP + 28, WHITE)
            lcd.text("Saved profile", 4, CONTENT_TOP + 72, WHITE)
            lcd.text("Please wait", 4, CONTENT_TOP + 94, GRAY)
            action = "Join network"
        elif status["active"]:
            lcd.text("Not connected", 4, CONTENT_TOP + 6, ORANGE)
            lcd.text("Radio active", 4, CONTENT_TOP + 28, CYAN)
            lcd.text("Open a scan to", 4, CONTENT_TOP + 72, WHITE)
            lcd.text("pick a network", 4, CONTENT_TOP + 94, GRAY)
            action = "Join network"
        else:
            lcd.text("Not connected", 4, CONTENT_TOP + 6, ORANGE)
            lcd.text("Radio off", 4, CONTENT_TOP + 28, ORANGE)
            lcd.text("Opening scan", 4, CONTENT_TOP + 72, WHITE)
            lcd.text("will wake Wi-Fi", 4, CONTENT_TOP + 94, GRAY)
            action = "Join network"

        lcd.fill_rect(0, card_y, SCREEN_W, 20, SLATE)
        lcd.text(">", 4, card_y + 6, WHITE)
        lcd.text(fit_text(action, WIFI_NAME_CHARS), WIFI_NAME_X, card_y + 6, WHITE)
        draw_footer_actions(lcd, HOME_HINT, B_LABEL + " open", GRAY)

    def _draw_list(self, lcd, runtime):
        status = runtime.wifi.status()
        chosen = self._selected_item()
        detail = ""
        if chosen:
            detail = fit_text(chosen["security"], 6)

        lcd.fill(BLACK)
        draw_header(lcd, "Wi-Fi", detail, GREEN)

        if not status["supported"]:
            lcd.text("No network", 4, CONTENT_TOP + 14, ORANGE)
            lcd.text("module here", 4, CONTENT_TOP + 34, WHITE)
            draw_footer_actions(lcd, HOME_HINT)
            return

        if status["connected"]:
            ssid = status["ssid"] or "connected"
            lcd.text(fit_text(ssid, 28), 4, CONTENT_TOP + 4, CYAN)
            ip = status["ifconfig"][0] if status["ifconfig"] else "ip ?"
            lcd.text(fit_text(ip, 28), 4, CONTENT_TOP + 24, WHITE)
        elif status["active"]:
            lcd.text("Radio active", 4, CONTENT_TOP + 4, CYAN)
            lcd.text("Choose a network", 4, CONTENT_TOP + 24, WHITE)
        else:
            lcd.text("Radio off", 4, CONTENT_TOP + 4, ORANGE)
            lcd.text("Scan woke radio", 4, CONTENT_TOP + 24, WHITE)

        if chosen:
            saved = self._has_saved_profile(chosen)
            if chosen["hidden"]:
                lcd.text("Hidden SSID", 4, CONTENT_TOP + 24, ORANGE)
            elif self._secure_network(chosen):
                lcd.text("Saved pass" if saved else "Need password", 4, CONTENT_TOP + 24, WHITE)
            else:
                lcd.text("Saved open" if saved else "Open network", 4, CONTENT_TOP + 24, WHITE)

        if self.error:
            lcd.text(fit_text(self.error, 28), 4, CONTENT_TOP + 46, ORANGE)
            draw_footer_actions(lcd, A_LABEL + " status")
            return

        if not self.results:
            lcd.text("No SSIDs found", 4, CONTENT_TOP + 46, GRAY)
            draw_footer_actions(lcd, A_LABEL + " status")
            return

        y = CONTENT_TOP + 48
        end = min(len(self.results), self.scroll + WIFI_LIST_ROWS)
        for index in range(self.scroll, end):
            item = self.results[index]
            selected = index == self.selected
            if selected:
                lcd.fill_rect(0, y - 2, SCREEN_W, 14, GRAY)

            prefix = ">" if selected else " "
            text_color = BLACK if selected else WHITE
            lcd.text(prefix, 2, y, text_color)
            lcd.text(self._network_name(item, selected), WIFI_NAME_X, y, text_color)

            marker = "S" if self._has_saved_profile(item) else ("O" if not self._secure_network(item) else "*")
            lcd.text(marker, WIFI_MARKER_X, y, BLACK if selected else CYAN)
            y += 14

        draw_footer_actions(lcd, A_LABEL + " status", B_LABEL + " join", GRAY)

    def _draw_keyboard(self, lcd):
        page_name = KEYBOARD_PAGES[self.keyboard_page][0]
        slot_w = 40
        slot_gap = 6
        slot_x0 = 5
        slot_y = CONTENT_TOP + 116
        lcd.fill(BLACK)
        draw_header(lcd, "Password", page_name, GREEN)

        ssid = self.current_network["ssid"] if self.current_network else "network"
        lcd.text(fit_text(ssid, 28), 4, CONTENT_TOP + 4, CYAN)
        lcd.text("Pass", 4, CONTENT_TOP + 30, WHITE)
        buffer_text = self.password_buffer if self.password_buffer else "_"
        lcd.text(fit_text(buffer_text[-28:], 28), 4, CONTENT_TOP + 52, YELLOW if self.password_buffer else GRAY)
        note_color = GRAY if self.keyboard_note == KEYBOARD_NOTE else ORANGE
        lcd.text(fit_text(self.keyboard_note, 28), 4, CONTENT_TOP + 76, note_color)

        tokens = self._keyboard_tokens()
        for slot in range(5):
            offset = slot - 2
            token_index = (self.keyboard_index + offset) % len(tokens)
            token = tokens[token_index]
            label = KEY_LABELS.get(token, token)
            x = slot_x0 + (slot * (slot_w + slot_gap))
            selected = offset == 0
            fill = SLATE if selected else BLACK
            border = YELLOW if selected else GRAY
            text_color = BLACK if selected else WHITE
            lcd.fill_rect(x, slot_y, slot_w, 22, fill)
            lcd.rect(x, slot_y, slot_w, 22, border)
            tx = x + max(1, (slot_w - (len(label) * 8)) // 2)
            lcd.text(label, tx, slot_y + 7, text_color)

        draw_footer_actions(lcd, A_LABEL + " next", B_LABEL + " pick", GRAY)

    def _draw_connecting(self, lcd):
        dots = "." * ((time.ticks_ms() // 250) % 4)
        lcd.fill(BLACK)
        draw_header(lcd, "Joining", color=GREEN)
        ssid = self.current_network["ssid"] if self.current_network else "network"
        lcd.text(fit_text(ssid, 28), 4, CONTENT_TOP + 16, CYAN)
        lcd.text("Connecting" + dots, 4, CONTENT_TOP + 54, WHITE)
        lcd.text("Please wait", 4, CONTENT_TOP + 80, GRAY)
        draw_footer_actions(lcd, HOME_HINT)

    def _draw_result(self, lcd):
        ok = self.result and self.result["ok"]
        header_color = GREEN if ok else RED
        title = "Joined" if ok else "Failed"
        lcd.fill(BLACK)
        draw_header(lcd, title, color=header_color)

        ssid = self.current_network["ssid"] if self.current_network else "network"
        lcd.text(fit_text(ssid, 28), 4, CONTENT_TOP + 10, CYAN)

        if ok:
            ip = self.result["ifconfig"][0] if self.result["ifconfig"] else "ip ?"
            lcd.text(fit_text(ip, 28), 4, CONTENT_TOP + 42, WHITE)
            if self.connect_remember and self.connect_password:
                lcd.text("Password saved", 4, CONTENT_TOP + 74, GRAY)
            draw_footer_actions(lcd, A_LABEL + " status", B_LABEL + " nets", GREEN)
        else:
            error = self.result["error"] if self.result else "connection failed"
            lcd.text(fit_text(error, 28), 4, CONTENT_TOP + 42, ORANGE)
            if self._secure_network(self.current_network):
                lcd.text(B_LABEL + " edit pass", 4, CONTENT_TOP + 74, GRAY)
                draw_footer_actions(lcd, A_LABEL + " status", B_LABEL + " edit", RED)
            else:
                draw_footer_actions(lcd, A_LABEL + " status", B_LABEL + " retry", RED)

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
