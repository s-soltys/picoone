from machine import Pin
import time

from core.display import LCD, BLACK, CYAN, WHITE, YELLOW, GRAY
from core.controls import A_LABEL, B_LABEL
from core.buttons import ButtonManager
from core.ui import (
    SCREEN_W,
    SCREEN_H,
    CONTENT_TOP,
    CONTENT_H,
    draw_header,
    draw_footer_actions,
    draw_tile,
    center_x,
    HOME_HINT,
)
from core.wifi import WiFiHelper
from apps import build_apps


class Launcher:
    def __init__(self):
        self.lcd = LCD()
        self.buttons = ButtonManager()
        self.wifi = WiFiHelper()
        self.apps = build_apps()
        self.selected_index = 0
        self.active_app = None
        self.led = None
        try:
            self.led = Pin("LED", Pin.OUT)
            self.led.on()
        except Exception:
            self.led = None

    def app_count(self):
        return len(self.apps)

    def page_count(self):
        return (self.app_count() + 3) // 4

    def current_page(self):
        return self.selected_index // 4

    def open_app(self, index):
        if index < 0 or index >= len(self.apps):
            return
        self.active_app = self.apps[index]
        if hasattr(self.active_app, "on_open"):
            self.active_app.on_open(self)

    def go_home(self):
        if self.active_app and hasattr(self.active_app, "on_close"):
            self.active_app.on_close(self)
        self.active_app = None

    def move_selection(self, delta):
        new_index = self.selected_index + delta
        if 0 <= new_index < len(self.apps):
            self.selected_index = new_index

    def next_page(self):
        if self.page_count() <= 1:
            return
        page = (self.current_page() + 1) % self.page_count()
        self.selected_index = min(len(self.apps) - 1, page * 4)

    def draw_boot(self):
        self.lcd.fill(BLACK)
        self.lcd.text("PICO", center_x("PICO"), 54, CYAN)
        self.lcd.text("LAUNCHER", center_x("LAUNCHER"), 82, WHITE)
        self.lcd.text("Pico 2 W", center_x("Pico 2 W"), 110, YELLOW)
        self.lcd.text("Waveshare Pico-LCD-1.3", center_x("Waveshare Pico-LCD-1.3"), 136, GRAY)
        self.lcd.text(A_LABEL + " page", center_x(A_LABEL + " page"), 176, WHITE)
        self.lcd.text(B_LABEL + " open", center_x(B_LABEL + " open"), 192, WHITE)
        self.lcd.text(HOME_HINT, center_x(HOME_HINT), 208, GRAY)
        self.lcd.display()
        time.sleep(0.7)

    def _tile_layout(self):
        gap = 10
        tile_w = (SCREEN_W - 24 - gap) // 2
        tile_h = (CONTENT_H - 10) // 2
        left = 8
        top = CONTENT_TOP + 4
        return [
            (left, top, tile_w, tile_h),
            (left + tile_w + gap, top, tile_w, tile_h),
            (left, top + tile_h + 10, tile_w, tile_h),
            (left + tile_w + gap, top + tile_h + 10, tile_w, tile_h),
        ]

    def draw_home(self):
        self.lcd.fill(BLACK)
        detail = str(self.current_page() + 1) + "/" + str(self.page_count())
        draw_header(self.lcd, "Launcher", detail, WHITE)

        start = self.current_page() * 4
        layout = self._tile_layout()

        for offset, app in enumerate(self.apps[start : start + 4]):
            x, y, w, h = layout[offset]
            is_selected = (start + offset) == self.selected_index
            draw_tile(self.lcd, x, y, w, h, app.title, is_selected, app.accent, app.draw_icon, True)

        draw_footer_actions(self.lcd, A_LABEL + " page", B_LABEL + " open", WHITE)

    def step_home(self):
        if self.buttons.down("A") and self.buttons.down("B"):
            self.draw_home()
            return
        if self.buttons.repeat("LEFT"):
            self.move_selection(-1)
        if self.buttons.repeat("RIGHT"):
            self.move_selection(1)
        if self.buttons.repeat("UP"):
            self.move_selection(-2)
        if self.buttons.repeat("DOWN"):
            self.move_selection(2)
        if self.buttons.pressed("A"):
            self.next_page()
        if self.buttons.pressed("B"):
            self.open_app(self.selected_index)
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
            time.sleep(0.03)
