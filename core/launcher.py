from machine import Pin
import time

from core.display import LCD, BLACK, WHITE, GRAY
from core.buttons import ButtonManager
from core.ui import (
    SCREEN_W,
    SCREEN_H,
    DESKTOP_TOP,
    MENU_BAR_H,
    MENU_DROPDOWN_ROW_H,
    MENU_TITLE,
    WINDOW_CONTENT_X,
    WINDOW_CONTENT_Y,
    WINDOW_TEXT_CHARS,
    draw_menu_bar,
    draw_menu_dropdown,
    draw_desktop_background,
    draw_desktop_icon,
    draw_footer_actions,
    draw_mouse_pointer,
    draw_window_shell,
    fit_text,
    menu_bar_regions,
)
from core.wifi import WiFiHelper
from apps import build_apps


class Launcher:
    CURSOR_STEP = 8
    ICON_COLS = 4
    ICON_ROWS = 4
    MENU_FRAME_MS = 12
    APP_FRAME_MS = 30
    WIFI_MENU_W = 132

    def __init__(self):
        self.lcd = LCD()
        self.buttons = ButtonManager()
        self.wifi = WiFiHelper()
        registry = build_apps()
        self.apps = registry["desktop"]
        self.menu_apps = registry.get("menu", {})
        self.selected_index = 0
        self.active_app = None
        self.active_mode = "desktop"
        self.cursor_x = 18
        self.cursor_y = DESKTOP_TOP + 18
        self.menu_open = ""
        self.led = None
        try:
            self.led = Pin("LED", Pin.OUT)
            self.led.on()
        except Exception:
            self.led = None

    def open_app(self, target):
        if isinstance(target, int):
            if target < 0 or target >= len(self.apps):
                return
            self.selected_index = target
            app = self.apps[target]
        else:
            app = target
            for index in range(len(self.apps)):
                if self.apps[index] is app:
                    self.selected_index = index
                    break

        if self.active_app and self.active_app is not app and hasattr(self.active_app, "on_close"):
            self.active_app.on_close(self)

        self.menu_open = ""
        self.active_app = app
        self.active_mode = getattr(self.active_app, "launch_mode", "fullscreen")
        if hasattr(self.active_app, "on_open"):
            self.active_app.on_open(self)

    def go_home(self):
        if self.active_app and hasattr(self.active_app, "on_close"):
            self.active_app.on_close(self)
        self.active_app = None
        self.active_mode = "desktop"
        self.menu_open = ""

    def _desktop_layout(self):
        left = 4
        top = DESKTOP_TOP + 6
        slot_w = (SCREEN_W - (left * 2)) // self.ICON_COLS
        slot_h = max(40, (SCREEN_H - top - 18) // self.ICON_ROWS)
        layout = []
        for index in range(len(self.apps)):
            col = index % self.ICON_COLS
            row = index // self.ICON_COLS
            if row >= self.ICON_ROWS:
                break
            layout.append((left + (col * slot_w), top + (row * slot_h), slot_w, slot_h))
        return layout

    def _hovered_index(self):
        for index, rect in enumerate(self._desktop_layout()):
            x, y, w, h = rect
            if x <= self.cursor_x < x + w and y <= self.cursor_y < y + h:
                return index
        return None

    def _move_cursor(self):
        if self.buttons.down("LEFT"):
            self.cursor_x -= self.CURSOR_STEP
        if self.buttons.down("RIGHT"):
            self.cursor_x += self.CURSOR_STEP
        if self.buttons.down("UP"):
            self.cursor_y -= self.CURSOR_STEP
        if self.buttons.down("DOWN"):
            self.cursor_y += self.CURSOR_STEP

        self.cursor_x = min(SCREEN_W - 6, max(0, self.cursor_x))
        self.cursor_y = min(SCREEN_H - 8, max(0, self.cursor_y))

    def _wifi_menu_items(self):
        status = self.wifi.status()
        label = "Radio off"
        detail = "OFF"
        if not status["supported"]:
            label = "No Wi-Fi module"
            detail = "N/A"
        elif status.get("connected"):
            label = status.get("ssid") or "Wi-Fi linked"
            detail = "ON"
        elif status.get("connecting"):
            label = status.get("target") or "Joining"
            detail = "JOIN"
        elif status.get("active"):
            label = "Radio ready"
            detail = "READY"

        items = [
            {"label": label, "detail": detail, "enabled": False},
            {"label": "Wi-Fi Panel", "detail": "", "enabled": status["supported"], "action": "panel"},
            {"label": "Networks", "detail": "", "enabled": status["supported"], "action": "networks"},
        ]

        if status.get("connected"):
            items.append({"label": "Disconnect", "detail": "", "enabled": True, "action": "disconnect"})
        return items

    def _wifi_dropdown_rect(self):
        regions = menu_bar_regions(MENU_TITLE)
        return (
            max(2, regions["wifi_x"] - 6),
            MENU_BAR_H,
            self.WIFI_MENU_W,
            (len(self._wifi_menu_items()) * MENU_DROPDOWN_ROW_H) + 4,
        )

    def _menu_hover(self):
        regions = menu_bar_regions(MENU_TITLE)
        wx, wy, ww, wh = regions["wifi_rect"]
        if wx <= self.cursor_x < wx + ww and wy <= self.cursor_y < wy + wh:
            return ("wifi", None)

        if self.menu_open == "wifi":
            x, y, w, h = self._wifi_dropdown_rect()
            if x <= self.cursor_x < x + w and y <= self.cursor_y < y + h:
                row = (self.cursor_y - y - 2) // MENU_DROPDOWN_ROW_H
                if 0 <= row < len(self._wifi_menu_items()):
                    return ("wifi_item", row)
        return (None, None)

    def _launch_wifi(self, view):
        wifi_app = self.menu_apps.get("wifi")
        if wifi_app is None:
            return
        if hasattr(wifi_app, "request_view"):
            wifi_app.request_view(view)
        self.open_app(wifi_app)

    def _activate_wifi_item(self, row):
        items = self._wifi_menu_items()
        if row < 0 or row >= len(items):
            return
        item = items[row]
        if not item.get("enabled"):
            return

        action = item.get("action")
        self.menu_open = ""
        if action == "panel":
            self._launch_wifi("status")
        elif action == "networks":
            self._launch_wifi("list")
        elif action == "disconnect":
            self.wifi.disconnect()

    def draw_boot(self):
        draw_window_shell(self.lcd, "Welcome", self.wifi.status())
        self.lcd.text("PicoOS", WINDOW_CONTENT_X + 64, WINDOW_CONTENT_Y + 12, BLACK)
        self.lcd.text("Tiny desktop shell", WINDOW_CONTENT_X + 28, WINDOW_CONTENT_Y + 34, BLACK)
        self.lcd.text("Wi-Fi lives in menu", WINDOW_CONTENT_X + 20, WINDOW_CONTENT_Y + 64, BLACK)
        self.lcd.text("D-pad moves cursor", WINDOW_CONTENT_X + 20, WINDOW_CONTENT_Y + 86, BLACK)
        self.lcd.text("Top (A) select", WINDOW_CONTENT_X + 20, WINDOW_CONTENT_Y + 108, BLACK)
        self.lcd.text("Bottom (B) open", WINDOW_CONTENT_X + 20, WINDOW_CONTENT_Y + 130, BLACK)
        self.lcd.text("Top + Bottom home", WINDOW_CONTENT_X + 20, WINDOW_CONTENT_Y + 154, GRAY)
        self.lcd.display()
        time.sleep(0.75)

    def draw_home(self):
        wifi_status = self.wifi.status()
        hovered = self._hovered_index()
        hovered_menu, hovered_row = self._menu_hover()
        active_index = hovered if hovered is not None else self.selected_index

        draw_desktop_background(self.lcd)
        highlight_menu = "wifi" if self.menu_open == "wifi" or hovered_menu == "wifi" else None
        draw_menu_bar(self.lcd, MENU_TITLE, wifi_status, highlight_menu)

        for index, app in enumerate(self.apps):
            if index >= len(self._desktop_layout()):
                break
            x, y, w, h = self._desktop_layout()[index]
            draw_desktop_icon(self.lcd, x, y, w, h, app.title, index == active_index, app.draw_icon)

        if self.menu_open == "wifi":
            x, y, w, _ = self._wifi_dropdown_rect()
            draw_menu_dropdown(self.lcd, x, y, w, self._wifi_menu_items(), hovered_row)
            status_label = "Wi-Fi menu"
            status_detail = "B open"
        elif hovered_menu == "wifi":
            status_label = "Wi-Fi menu"
            status_detail = "A/B show"
        elif active_index is not None and 0 <= active_index < len(self.apps):
            app = self.apps[active_index]
            status_label = app.title
            if app.app_id == "games-folder":
                status_detail = "folder"
            else:
                mode = getattr(app, "launch_mode", "fullscreen")
                status_detail = "window" if mode == "window" else "full"
        else:
            status_label = "Desktop"
            status_detail = "ready"

        draw_footer_actions(self.lcd, fit_text(status_label, WINDOW_TEXT_CHARS), fit_text(status_detail, 10), BLACK)
        draw_mouse_pointer(self.lcd, self.cursor_x, self.cursor_y)

    def step_home(self):
        if self.buttons.down("A") and self.buttons.down("B"):
            self.draw_home()
            return

        self._move_cursor()
        hovered_menu, hovered_row = self._menu_hover()

        if self.menu_open == "wifi":
            if self.buttons.pressed("B") and hovered_menu == "wifi_item":
                self._activate_wifi_item(hovered_row)
                return
            if self.buttons.pressed("A") or self.buttons.pressed("B"):
                if hovered_menu == "wifi":
                    self.menu_open = ""
                elif hovered_menu != "wifi_item":
                    self.menu_open = ""
            self.draw_home()
            return

        if hovered_menu == "wifi":
            if self.buttons.pressed("A") or self.buttons.pressed("B"):
                self.menu_open = "wifi"
                self.draw_home()
                return
        else:
            hovered = self._hovered_index()
            if hovered is not None and self.buttons.pressed("A"):
                self.selected_index = hovered
            if hovered is not None and self.buttons.pressed("B"):
                self.open_app(hovered)
                return

        self.draw_home()

    def run(self):
        self.wifi.start_auto_connect()
        self.draw_boot()
        while True:
            self.wifi.poll_auto_connect()
            self.buttons.update()
            if self.active_app is None:
                self.step_home()
            else:
                if self.buttons.home_triggered():
                    self.go_home()
                    self.draw_home()
                else:
                    action = self.active_app.step(self)
                    if action == "home":
                        self.go_home()
                        self.draw_home()
            self.lcd.display()
            if self.active_app is None:
                time.sleep_ms(self.MENU_FRAME_MS)
            else:
                time.sleep_ms(self.APP_FRAME_MS)
