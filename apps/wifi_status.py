import time

from core.display import BLACK, WHITE, CYAN, YELLOW, GREEN, GRAY, ORANGE, RED
from core.controls import A_LABEL, B_LABEL, HOME_HINT
from core.ui import (
    WINDOW_CONTENT_X,
    WINDOW_CONTENT_Y,
    WINDOW_CONTENT_W,
    WINDOW_CONTENT_BOTTOM,
    WINDOW_TEXT_CHARS,
    draw_button,
    draw_field,
    draw_list_row,
    draw_window_shell,
    draw_window_footer,
    draw_window_footer_actions,
    fit_text,
)


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
WIFI_LIST_ROWS = max(4, (WINDOW_CONTENT_BOTTOM - (WINDOW_CONTENT_Y + 40)) // 14)
WIFI_NAME_X = WINDOW_CONTENT_X + 16
WIFI_MARKER_X = WINDOW_CONTENT_X + WINDOW_CONTENT_W - 10
WIFI_NAME_CHARS = max(10, (WINDOW_CONTENT_W // 8) - 6)
MARQUEE_HOLD_STEPS = 4
MARQUEE_STEP_MS = 180


class WiFiStatusApp:
    app_id = "wifi"
    title = "Wi-Fi"
    accent = GREEN
    launch_mode = "window"

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
        self.requested_view = "status"

    def request_view(self, view):
        self.requested_view = view

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
        requested = self.requested_view
        self.requested_view = "status"
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

        if requested == "list" and runtime.wifi.supported():
            self._open_networks(runtime)

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

    def _draw_status_card(self, lcd, label, detail):
        card_y = WINDOW_CONTENT_BOTTOM - 24
        draw_field(lcd, WINDOW_CONTENT_X, card_y, WINDOW_CONTENT_W, 18, label + (" " + detail if detail else ""), GREEN)

    def _draw_status(self, lcd, runtime):
        status = runtime.wifi.status()
        draw_window_shell(lcd, "Network", status)

        if not status["supported"]:
            lcd.text("No network module", WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 8, ORANGE)
            lcd.text("found on device", WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 28, BLACK)
            draw_window_footer(lcd, A_LABEL + " desk", BLACK)
            return

        y = WINDOW_CONTENT_Y + 6
        if status["connected"]:
            ssid = status["ssid"] or "connected"
            ifconfig = status["ifconfig"] or ("ip ?", "mask ?", "gw ?", "dns ?")
            lcd.text(self._marquee_text(ssid, WINDOW_TEXT_CHARS, ("status", ssid)), WINDOW_CONTENT_X, y, CYAN)
            lcd.text(fit_text("IP   " + ifconfig[0], WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, y + 20, BLACK)
            lcd.text(fit_text("MASK " + ifconfig[1], WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, y + 38, BLACK)
            lcd.text(fit_text("GW   " + ifconfig[2], WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, y + 56, BLACK)
            lcd.text(fit_text("DNS  " + ifconfig[3], WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, y + 74, GRAY)
            self._draw_status_card(lcd, "Networks", "scan")
        elif status.get("connecting"):
            target = status.get("target") or "saved network"
            lcd.text("Restoring Wi-Fi", WINDOW_CONTENT_X, y, CYAN)
            lcd.text(fit_text(target, WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, y + 20, BLACK)
            lcd.text("Saved profile", WINDOW_CONTENT_X, y + 54, BLACK)
            lcd.text("Please wait", WINDOW_CONTENT_X, y + 72, GRAY)
            self._draw_status_card(lcd, "Networks", "scan")
        elif status["active"]:
            lcd.text("Radio ready", WINDOW_CONTENT_X, y, CYAN)
            lcd.text("Not connected", WINDOW_CONTENT_X, y + 20, BLACK)
            lcd.text("Open the network list", WINDOW_CONTENT_X, y + 54, BLACK)
            lcd.text("to join a hotspot", WINDOW_CONTENT_X, y + 72, GRAY)
            self._draw_status_card(lcd, "Networks", "scan")
        else:
            lcd.text("Radio sleeping", WINDOW_CONTENT_X, y, ORANGE)
            lcd.text("No active link", WINDOW_CONTENT_X, y + 20, BLACK)
            lcd.text("Opening Networks", WINDOW_CONTENT_X, y + 54, BLACK)
            lcd.text("will wake Wi-Fi", WINDOW_CONTENT_X, y + 72, GRAY)
            self._draw_status_card(lcd, "Wake + Scan", "")

        draw_window_footer_actions(lcd, A_LABEL + " desk", B_LABEL + " open", BLACK)

    def _draw_list(self, lcd, runtime):
        status = runtime.wifi.status()
        chosen = self._selected_item()
        detail = ""
        if chosen:
            detail = fit_text(chosen["security"], 6)

        draw_window_shell(lcd, "Network", status)

        if not status["supported"]:
            lcd.text("No network module", WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 8, ORANGE)
            lcd.text("found on device", WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 28, BLACK)
            draw_window_footer(lcd, A_LABEL + " status", BLACK)
            return

        summary = "Ready"
        summary_color = BLACK
        if status["connected"]:
            summary = status["ssid"] or "Connected"
            summary_color = CYAN
        elif status.get("connecting"):
            summary = status.get("target") or "Joining"
            summary_color = CYAN
        elif not status["active"]:
            summary = "Radio waking"
            summary_color = ORANGE

        draw_field(lcd, WINDOW_CONTENT_X, WINDOW_CONTENT_Y, WINDOW_CONTENT_W, 16, summary, summary_color)
        if chosen:
            if chosen["hidden"]:
                lcd.text("Hidden SSID", WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 24, ORANGE)
            elif self._secure_network(chosen):
                label = "Saved pass" if self._has_saved_profile(chosen) else "Need password"
                lcd.text(label, WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 24, BLACK)
            else:
                label = "Saved open" if self._has_saved_profile(chosen) else "Open network"
                lcd.text(label, WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 24, BLACK)
        elif detail:
            lcd.text(detail, WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 24, GRAY)

        if self.error:
            lcd.text(fit_text(self.error, WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 48, ORANGE)
            draw_window_footer(lcd, A_LABEL + " status", BLACK)
            return

        if not self.results:
            lcd.text("No SSIDs found", WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 48, GRAY)
            draw_window_footer(lcd, A_LABEL + " status", BLACK)
            return

        y = WINDOW_CONTENT_Y + 48
        end = min(len(self.results), self.scroll + WIFI_LIST_ROWS)
        for index in range(self.scroll, end):
            item = self.results[index]
            marker = "S" if self._has_saved_profile(item) else ("O" if not self._secure_network(item) else "*")
            draw_list_row(
                lcd,
                WINDOW_CONTENT_X,
                y,
                WINDOW_CONTENT_W,
                self._network_name(item, index == self.selected),
                index == self.selected,
                lead=marker,
                detail=item["security"],
                text_color=CYAN if self._has_saved_profile(item) else BLACK,
            )
            y += 14

        draw_window_footer_actions(lcd, A_LABEL + " status", B_LABEL + " join", BLACK)

    def _draw_keyboard(self, lcd, runtime):
        page_name = KEYBOARD_PAGES[self.keyboard_page][0]
        slot_gap = 4
        slot_w = (WINDOW_CONTENT_W - (slot_gap * 4)) // 5
        slot_x0 = WINDOW_CONTENT_X
        slot_y = WINDOW_CONTENT_BOTTOM - 22

        draw_window_shell(lcd, "Password", runtime.wifi.status())

        ssid = self.current_network["ssid"] if self.current_network else "network"
        draw_field(lcd, WINDOW_CONTENT_X, WINDOW_CONTENT_Y, WINDOW_CONTENT_W, 16, ssid, CYAN)
        lcd.text("Page " + page_name, WINDOW_CONTENT_X + 112, WINDOW_CONTENT_Y + 4, GRAY)
        lcd.text("Pass", WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 26, BLACK)
        buffer_text = self.password_buffer if self.password_buffer else "_"
        draw_field(
            lcd,
            WINDOW_CONTENT_X,
            WINDOW_CONTENT_Y + 40,
            WINDOW_CONTENT_W,
            18,
            fit_text(buffer_text[-WINDOW_TEXT_CHARS:], WINDOW_TEXT_CHARS),
            YELLOW if self.password_buffer else GRAY,
            YELLOW if self.password_buffer else GRAY,
        )
        note_color = GRAY if self.keyboard_note == KEYBOARD_NOTE else ORANGE
        lcd.text(fit_text(self.keyboard_note, WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 68, note_color)

        tokens = self._keyboard_tokens()
        for slot in range(5):
            offset = slot - 2
            token_index = (self.keyboard_index + offset) % len(tokens)
            token = tokens[token_index]
            label = KEY_LABELS.get(token, token)
            x = slot_x0 + (slot * (slot_w + slot_gap))
            selected = offset == 0
            draw_button(lcd, x, slot_y, slot_w, 18, label, selected, WHITE)

        draw_window_footer_actions(lcd, A_LABEL + " next", B_LABEL + " pick", BLACK)

    def _draw_connecting(self, lcd, runtime):
        dots = "." * ((time.ticks_ms() // 250) % 4)
        draw_window_shell(lcd, "Joining", runtime.wifi.status())
        ssid = self.current_network["ssid"] if self.current_network else "network"
        draw_field(lcd, WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 8, WINDOW_CONTENT_W, 16, ssid, CYAN)
        lcd.text("Connecting" + dots, WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 52, BLACK)
        lcd.text("Please wait", WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 74, GRAY)
        draw_window_footer(lcd, HOME_HINT, BLACK)

    def _draw_result(self, lcd, runtime):
        ok = self.result and self.result["ok"]
        title = "Joined" if ok else "Failed"
        draw_window_shell(lcd, title, runtime.wifi.status())

        ssid = self.current_network["ssid"] if self.current_network else "network"
        draw_field(lcd, WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 8, WINDOW_CONTENT_W, 16, ssid, CYAN)

        if ok:
            ip = self.result["ifconfig"][0] if self.result["ifconfig"] else "ip ?"
            lcd.text(fit_text("IP " + ip, WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 38, BLACK)
            if self.connect_remember and self.connect_password:
                lcd.text("Password saved", WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 62, GRAY)
            draw_window_footer_actions(lcd, A_LABEL + " status", B_LABEL + " nets", BLACK)
        else:
            error = self.result["error"] if self.result else "connection failed"
            lcd.text(fit_text(error, WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 38, ORANGE)
            if self._secure_network(self.current_network):
                lcd.text(B_LABEL + " edit pass", WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 62, GRAY)
                draw_window_footer_actions(lcd, A_LABEL + " status", B_LABEL + " edit", BLACK)
            else:
                draw_window_footer_actions(lcd, A_LABEL + " status", B_LABEL + " retry", BLACK)

    def _step_status(self, runtime):
        if runtime.buttons.pressed("A"):
            return "home"
        if runtime.buttons.pressed("B") and runtime.wifi.supported():
            self._open_networks(runtime)
        self._draw_status(runtime.lcd, runtime)
        return None

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
        return None

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
        self._draw_keyboard(runtime.lcd, runtime)
        return None

    def _step_connecting(self, runtime):
        if not self.connect_drawn:
            self.connect_drawn = True
            self._draw_connecting(runtime.lcd, runtime)
            return None

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
        self._draw_result(runtime.lcd, runtime)
        return None

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
        self._draw_result(runtime.lcd, runtime)
        return None

    def step(self, runtime):
        if self.state == "status":
            return self._step_status(runtime)
        if self.state == "list":
            return self._step_list(runtime)
        if self.state == "keyboard":
            return self._step_keyboard(runtime)
        if self.state == "connecting":
            return self._step_connecting(runtime)
        return self._step_result(runtime)
