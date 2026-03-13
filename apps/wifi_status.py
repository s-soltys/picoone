from lcd import BLACK, WHITE, CYAN, YELLOW, GREEN, GRAY, ORANGE
from core.ui import draw_header, draw_footer, fit_text


class WiFiStatusApp:
    app_id = "wifi"
    title = "Wi-Fi"
    accent = GREEN

    def __init__(self):
        self.results = []
        self.selected = 0
        self.scroll = 0
        self.error = ""

    def draw_icon(self, lcd, cx, cy, selected):
        lcd.pixel(cx, cy + 7, WHITE)
        lcd.ellipse(cx, cy + 4, 3, 2, GREEN, False)
        lcd.ellipse(cx, cy + 1, 6, 4, GREEN, False)
        lcd.ellipse(cx, cy - 2, 9, 6, GREEN, False)
        if selected:
            lcd.ellipse(cx, cy + 2, 12, 10, YELLOW, False)

    def on_open(self, runtime):
        self.selected = 0
        self.scroll = 0
        self.refresh(runtime)

    def refresh(self, runtime):
        data = runtime.wifi.scan()
        self.results = data["results"]
        self.error = data["error"]
        if self.selected >= len(self.results):
            self.selected = max(0, len(self.results) - 1)
        if self.scroll > self.selected:
            self.scroll = self.selected

    def _selected_item(self):
        if not self.results:
            return None
        return self.results[self.selected]

    def step(self, runtime):
        buttons = runtime.buttons
        lcd = runtime.lcd

        if buttons.repeat("UP"):
            self.selected = max(0, self.selected - 1)
        if buttons.repeat("DOWN"):
            self.selected = min(max(0, len(self.results) - 1), self.selected + 1)
        if buttons.pressed("CTRL"):
            self.refresh(runtime)

        if self.selected < self.scroll:
            self.scroll = self.selected
        if self.selected >= self.scroll + 4:
            self.scroll = self.selected - 3

        status = runtime.wifi.status()
        lcd.fill(BLACK)
        draw_header(lcd, "Wi-Fi", color=GREEN)

        if not status["supported"]:
            lcd.text("No network", 4, 18, ORANGE)
            lcd.text("module here", 4, 30, WHITE)
            draw_footer(lcd, "A+B home")
            return None

        if status["connected"]:
            ssid = status["ssid"] or "connected"
            lcd.text(fit_text(ssid, 18), 4, 12, CYAN)
            ip = status["ifconfig"][0] if status["ifconfig"] else "ip ?"
            lcd.text(fit_text(ip, 18), 4, 22, WHITE)
        elif status["active"]:
            lcd.text("Radio active", 4, 12, CYAN)
            lcd.text("not linked", 4, 22, WHITE)
        else:
            lcd.text("Radio off", 4, 12, ORANGE)
            lcd.text("scan to wake", 4, 22, WHITE)

        if self.error:
            lcd.text(fit_text(self.error, 18), 4, 34, ORANGE)
            draw_footer(lcd, "CTRL scan")
            return None

        if not self.results:
            lcd.text("No SSIDs found", 4, 34, GRAY)
            draw_footer(lcd, "CTRL scan")
            return None

        y = 34
        end = min(len(self.results), self.scroll + 4)
        for index in range(self.scroll, end):
            item = self.results[index]
            selected = index == self.selected
            if selected:
                lcd.fill_rect(0, y - 1, 160, 10, GRAY)
            prefix = ">" if selected else " "
            name = fit_text(item["ssid"], 11)
            lcd.text(prefix + name, 2, y, BLACK if selected else WHITE)
            rssi = str(item["rssi"])
            lcd.text(rssi, 132, y, BLACK if selected else CYAN)
            y += 10

        chosen = self._selected_item()
        footer = "CTRL scan"
        if chosen:
            footer = "C" + str(chosen["channel"]) + " " + fit_text(chosen["security"], 10)
        draw_footer(lcd, footer)
        return None
