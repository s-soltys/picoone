from machine import Pin
import time

from core.display import LCD, BLACK, WHITE, GRAY
from core.buttons import ButtonManager
from core.ui import (
    SCREEN_W,
    SCREEN_H,
    DESKTOP_TOP,
    WINDOW_CONTENT_X,
    WINDOW_CONTENT_Y,
    WINDOW_TEXT_CHARS,
    draw_menu_bar,
    draw_desktop_background,
    draw_desktop_icon,
    draw_mouse_pointer,
    draw_window_shell,
    fit_text,
)
from core.wifi import WiFiHelper
from apps import build_apps


class Launcher:
    CURSOR_STEP = 8
    ICON_COLS = 3
    ICON_ROWS = 4
    MENU_FRAME_MS = 12
    APP_FRAME_MS = 30

    def __init__(self):
        self.lcd = LCD()
        self.buttons = ButtonManager()
        self.wifi = WiFiHelper()
        self.apps = build_apps()
        self.selected_index = 0
        self.active_app = None
        self.active_mode = "desktop"
        self.cursor_x = 18
        self.cursor_y = DESKTOP_TOP + 18
        self.led = None
        try:
            self.led = Pin("LED", Pin.OUT)
            self.led.on()
        except Exception:
            self.led = None

    def open_app(self, index):
        if index < 0 or index >= len(self.apps):
            return
        self.selected_index = index
        self.active_app = self.apps[index]
        self.active_mode = getattr(self.active_app, "launch_mode", "fullscreen")
        if hasattr(self.active_app, "on_open"):
            self.active_app.on_open(self)

    def go_home(self):
        if self.active_app and hasattr(self.active_app, "on_close"):
            self.active_app.on_close(self)
        self.active_app = None
        self.active_mode = "desktop"

    def _desktop_layout(self):
        slot_w = (SCREEN_W - 20) // self.ICON_COLS
        slot_h = 50
        left = 8
        top = DESKTOP_TOP + 8
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
        self.cursor_y = min(SCREEN_H - 8, max(DESKTOP_TOP, self.cursor_y))

    def draw_boot(self):
        draw_window_shell(self.lcd, "Welcome", self.wifi.status())
        self.lcd.text("Pico Finder", WINDOW_CONTENT_X + 40, WINDOW_CONTENT_Y + 18, BLACK)
        self.lcd.text("Desktop launcher", WINDOW_CONTENT_X + 12, WINDOW_CONTENT_Y + 44, BLACK)
        self.lcd.text("D-pad moves mouse", WINDOW_CONTENT_X + 12, WINDOW_CONTENT_Y + 72, BLACK)
        self.lcd.text("Top (A) select", WINDOW_CONTENT_X + 12, WINDOW_CONTENT_Y + 98, BLACK)
        self.lcd.text("Bottom (B) open", WINDOW_CONTENT_X + 12, WINDOW_CONTENT_Y + 124, BLACK)
        self.lcd.text("Top + Bottom home", WINDOW_CONTENT_X + 12, WINDOW_CONTENT_Y + 150, GRAY)
        self.lcd.display()
        time.sleep(0.75)

    def draw_home(self):
        wifi_status = self.wifi.status()
        hovered = self._hovered_index()
        active_index = hovered if hovered is not None else self.selected_index

        draw_desktop_background(self.lcd)
        draw_menu_bar(self.lcd, "Pico Finder", wifi_status)

        for index, app in enumerate(self.apps):
            if index >= len(self._desktop_layout()):
                break
            x, y, w, h = self._desktop_layout()[index]
            draw_desktop_icon(self.lcd, x, y, w, h, app.title, index == active_index, app.draw_icon)

        if active_index is not None and 0 <= active_index < len(self.apps):
            label = self.apps[active_index].title
            mode = getattr(self.apps[active_index], "launch_mode", "fullscreen")
            detail = "window" if mode == "window" else "full screen"
            self.lcd.fill_rect(0, SCREEN_H - 14, SCREEN_W, 14, WHITE)
            self.lcd.hline(0, SCREEN_H - 14, SCREEN_W, BLACK)
            self.lcd.text(fit_text(label, WINDOW_TEXT_CHARS), 4, SCREEN_H - 11, BLACK)
            self.lcd.text(fit_text(detail, 11), SCREEN_W - 92, SCREEN_H - 11, GRAY)

        draw_mouse_pointer(self.lcd, self.cursor_x, self.cursor_y)

    def step_home(self):
        if self.buttons.down("A") and self.buttons.down("B"):
            self.draw_home()
            return

        self._move_cursor()
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
