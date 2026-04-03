import gc
from machine import Pin
import time

from core.display import LCD, BLACK, GRAY
from core.buttons import ButtonManager
from core.controls import A_LABEL, B_LABEL, HELP_HINT, HOME_HINT, X_LABEL, Y_LABEL
from core.ui import (
    SCREEN_W,
    SCREEN_H,
    DESKTOP_TOP,
    DESKTOP_BOTTOM,
    TASKBAR_Y,
    START_MENU_W,
    START_MENU_ROW_H,
    WINDOW_CONTENT_X,
    WINDOW_CONTENT_Y,
    draw_boot_splash,
    draw_desktop_background,
    draw_desktop_icon,
    draw_dialog,
    draw_help_dialog,
    draw_mouse_pointer,
    draw_start_menu,
    draw_taskbar,
    taskbar_regions,
)
from core.wifi import WiFiHelper
from apps import build_apps


class Launcher:
    CURSOR_STEP = 8
    CURSOR_MEDIUM_STEP = 12
    CURSOR_FAST_STEP = 18
    CURSOR_ACCEL_MEDIUM_MS = 180
    CURSOR_ACCEL_FAST_MS = 520
    ICON_COLS = 4
    ICON_ROWS = 4
    MENU_FRAME_MS = 12
    APP_FRAME_MS = 30
    SPLASH_MS = 3000

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
        self.start_open = False
        self.start_selected = 0
        self.dialog = ""
        self.run_selected = 0
        self.help_open = False
        self.help_title = ""
        self.help_lines = []
        self.led = None
        self.start_items = self._build_start_items()
        self.run_items = self._build_run_items()
        self.cursor_x = 18
        self.cursor_y = DESKTOP_TOP + 18
        self.cursor_axis = {"x": 0, "y": 0}
        self.cursor_axis_since = {"x": 0, "y": 0}
        layout = self._desktop_layout()
        if layout:
            x, y, w, _ = layout[0]
            self.cursor_x = x + (w // 2)
            self.cursor_y = y + 12
        try:
            self.led = Pin("LED", Pin.OUT)
            self.led.on()
        except Exception:
            self.led = None

    def _find_app(self, app_id):
        for app in self.apps:
            if getattr(app, "app_id", "") == app_id:
                return app
        if app_id in self.menu_apps:
            return self.menu_apps[app_id]
        return None

    def _build_start_items(self):
        return [
            {"label": "Device Status", "detail": "stat", "kind": "app", "app": self._find_app("device-status")},
            {"label": "Games", "detail": "games", "kind": "app", "app": self._find_app("games-folder")},
            {"label": "Calculator", "detail": "calc", "kind": "app", "app": self._find_app("calculator")},
            {"label": "Weather", "detail": "wx", "kind": "app", "app": self._find_app("weather")},
            {"label": "Browser", "detail": "web", "kind": "app", "app": self._find_app("browser")},
            {"label": "Server", "detail": "http", "kind": "app", "app": self._find_app("server")},
            {"label": "Wi-Fi", "detail": "net", "kind": "wifi"},
            {"label": "Paint", "detail": "art", "kind": "app", "app": self._find_app("paint")},
            {"label": "Galaxy", "detail": "map", "kind": "app", "app": self._find_app("galaxy")},
            {"label": "Run...", "detail": "cmd", "kind": "run"},
            {"label": "About PicoOS", "detail": "info", "kind": "about"},
        ]

    def _build_run_items(self):
        return [
            {"label": "browser", "kind": "app", "app": self._find_app("browser")},
            {"label": "calc", "kind": "app", "app": self._find_app("calculator")},
            {"label": "galaxy", "kind": "app", "app": self._find_app("galaxy")},
            {"label": "games", "kind": "app", "app": self._find_app("games-folder")},
            {"label": "paint", "kind": "app", "app": self._find_app("paint")},
            {"label": "server", "kind": "app", "app": self._find_app("server")},
            {"label": "status", "kind": "app", "app": self._find_app("device-status")},
            {"label": "weather", "kind": "app", "app": self._find_app("weather")},
            {"label": "wifi", "kind": "wifi"},
        ]

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

        if app is None:
            return

        if self.active_app and self.active_app is not app and hasattr(self.active_app, "on_close"):
            self.active_app.on_close(self)

        self.start_open = False
        self.dialog = ""
        self.help_open = False
        self.active_app = app
        self.active_mode = getattr(self.active_app, "launch_mode", "fullscreen")
        if hasattr(self.active_app, "on_open"):
            self.active_app.on_open(self)

    def go_home(self):
        if self.active_app and hasattr(self.active_app, "on_close"):
            self.active_app.on_close(self)
        self.active_app = None
        self.active_mode = "desktop"
        self.start_open = False
        self.dialog = ""
        self.help_open = False

    def _desktop_layout(self):
        left = 6
        top = DESKTOP_TOP + 8
        available_h = max(1, DESKTOP_BOTTOM - top - 8)
        slot_w = (SCREEN_W - (left * 2)) // self.ICON_COLS
        slot_h = max(44, available_h // self.ICON_ROWS)
        layout = []
        for index in range(len(self.apps)):
            col = index % self.ICON_COLS
            row = index // self.ICON_COLS
            if row >= self.ICON_ROWS:
                break
            layout.append((left + (col * slot_w), top + (row * slot_h), slot_w, slot_h))
        return layout

    def _cursor_in_rect(self, rect):
        x, y, w, h = rect
        return x <= self.cursor_x < x + w and y <= self.cursor_y < y + h

    def _cursor_axis_step(self, axis_name, direction, now_ms):
        if direction != self.cursor_axis[axis_name]:
            self.cursor_axis[axis_name] = direction
            self.cursor_axis_since[axis_name] = now_ms

        if direction == 0:
            return 0

        held_ms = time.ticks_diff(now_ms, self.cursor_axis_since[axis_name])
        step = self.CURSOR_STEP
        if held_ms >= self.CURSOR_ACCEL_FAST_MS:
            step = self.CURSOR_FAST_STEP
        elif held_ms >= self.CURSOR_ACCEL_MEDIUM_MS:
            step = self.CURSOR_MEDIUM_STEP
        return direction * step

    def _move_cursor(self):
        now_ms = time.ticks_ms()
        x_dir = 0
        y_dir = 0
        if self.buttons.down("LEFT") and not self.buttons.down("RIGHT"):
            x_dir = -1
        elif self.buttons.down("RIGHT") and not self.buttons.down("LEFT"):
            x_dir = 1
        if self.buttons.down("UP") and not self.buttons.down("DOWN"):
            y_dir = -1
        elif self.buttons.down("DOWN") and not self.buttons.down("UP"):
            y_dir = 1

        self.cursor_x += self._cursor_axis_step("x", x_dir, now_ms)
        self.cursor_y += self._cursor_axis_step("y", y_dir, now_ms)

        self.cursor_x = min(SCREEN_W - 6, max(0, self.cursor_x))
        self.cursor_y = min(SCREEN_H - 8, max(0, self.cursor_y))

    def _snap_cursor_to_rect(self, rect):
        x, y, w, h = rect
        self.cursor_x = min(SCREEN_W - 6, max(0, x + (w // 2)))
        self.cursor_y = min(SCREEN_H - 8, max(0, y + (h // 2)))

    def _snap_cursor_to_index(self, index):
        layout = self._desktop_layout()
        if 0 <= index < len(layout):
            self._snap_cursor_to_rect(layout[index])

    def _snap_cursor_to_start(self, index):
        x, y, width, _ = self._start_menu_rect()
        row_x = x + 22
        row_y = y + 22 + (index * START_MENU_ROW_H)
        self._snap_cursor_to_rect((row_x, row_y, width - 28, START_MENU_ROW_H))

    def _hovered_index(self):
        for index, rect in enumerate(self._desktop_layout()):
            if self._cursor_in_rect(rect):
                return index
        return None

    def _hovered_taskbar_target(self):
        regions = taskbar_regions("")
        if self._cursor_in_rect(regions["start_rect"]):
            return "start"
        if self._cursor_in_rect(regions["tray_rect"]):
            return "tray"
        return None

    def _start_menu_rect(self):
        width = START_MENU_W
        height = 24 + (len(self.start_items) * START_MENU_ROW_H) + 6
        return (2, TASKBAR_Y - height - 2, width, height)

    def _hovered_start_index(self):
        if not self.start_open:
            return None

        x, y, width, _ = self._start_menu_rect()
        row_x = x + 20
        row_w = width - 24
        row_y = y + 22
        if not (row_x <= self.cursor_x < row_x + row_w):
            return None

        for index in range(len(self.start_items)):
            if row_y <= self.cursor_y < row_y + START_MENU_ROW_H:
                return index
            row_y += START_MENU_ROW_H
        return None

    def _launch_wifi(self, view):
        wifi_app = self.menu_apps.get("wifi")
        if wifi_app is None:
            return
        if hasattr(wifi_app, "request_view"):
            wifi_app.request_view(view)
        self.open_app(wifi_app)

    def _activate_entry(self, entry):
        kind = entry.get("kind")
        self.start_open = False
        self.dialog = ""
        if kind == "app":
            self.open_app(entry.get("app"))
        elif kind == "wifi":
            self._launch_wifi("status")
        elif kind == "run":
            self.dialog = "run"
            self.run_selected = 0
        elif kind == "about":
            self.dialog = "about"

    def _memory_text(self):
        try:
            free = gc.mem_free()
            return str(free) + " bytes free"
        except Exception:
            return "memory unknown"

    def _about_lines(self):
        status = self.wifi.status()
        wifi_text = "Wi-Fi off"
        if status.get("connected"):
            wifi_text = "Wi-Fi " + (status.get("ssid") or "linked")
        elif status.get("connecting"):
            wifi_text = "Wi-Fi joining"
        elif status.get("active"):
            wifi_text = "Wi-Fi ready"
        return [
            "PicoOS shell",
            "Windows 95 mode",
            str(len(self.apps)) + " desktop apps",
            wifi_text,
            self._memory_text(),
        ]

    def _desktop_help_lines(self):
        if self.dialog == "run":
            return [
                "Run dialog",
                "Up/Down pick command",
                A_LABEL + " cancel",
                B_LABEL + " open",
                Y_LABEL + " close help",
            ]
        if self.dialog == "about":
            return [
                "About PicoOS",
                A_LABEL + " close dialog",
                B_LABEL + " close dialog",
                Y_LABEL + " close help",
                HOME_HINT,
            ]
        if self.start_open:
            return [
                "Desktop Start menu",
                "D-pad moves pointer",
                B_LABEL + " open entry",
                A_LABEL + " close Start",
                X_LABEL + " snap to active row",
            ]
        return [
            "Desktop controls",
            "D-pad moves pointer",
            B_LABEL + " click or open",
            A_LABEL + " open Start",
            X_LABEL + " snap to icon",
            HOME_HINT,
        ]

    def _app_help_payload(self):
        if self.active_app is None:
            return ("Desktop Help", self._desktop_help_lines())

        title = getattr(self.active_app, "help_title", getattr(self.active_app, "title", "App")) + " Help"
        if hasattr(self.active_app, "help_lines"):
            try:
                lines = self.active_app.help_lines(self)
            except TypeError:
                lines = self.active_app.help_lines()
        else:
            lines = [
                getattr(self.active_app, "title", "App"),
                "Use the D-pad to move",
                B_LABEL + " primary action",
                A_LABEL + " secondary action",
                HOME_HINT,
            ]
        return (title, lines)

    def _open_help(self):
        self.help_title, self.help_lines = self._app_help_payload()
        self.help_open = True
        if self.active_app is None:
            self.draw_home()
        self._draw_help()

    def _draw_help(self):
        draw_help_dialog(self.lcd, self.help_title, self.help_lines)

    def _step_help(self):
        if self.active_app is not None and self.buttons.home_triggered():
            self.go_home()
            self.draw_home()
            return
        if self.buttons.pressed("Y") or self.buttons.pressed("A") or self.buttons.pressed("B"):
            self.help_open = False
            if self.active_app is None:
                self.draw_home()
            return
        if self.active_app is not None and hasattr(self.active_app, "background_step"):
            self.active_app.background_step(self)
        self._draw_help()

    def show_splash(self):
        started_ms = time.ticks_ms()
        while True:
            self.wifi.poll_auto_connect()
            self.buttons.update()
            elapsed_ms = time.ticks_diff(time.ticks_ms(), started_ms)
            draw_boot_splash(self.lcd, elapsed_ms)
            self.lcd.display()
            if elapsed_ms >= self.SPLASH_MS or self.buttons.any_pressed() or self.buttons.any_down():
                break
            time.sleep_ms(30)

        self.buttons.update()
        while self.buttons.any_down():
            time.sleep_ms(20)
            self.buttons.update()

    def draw_home(self):
        draw_desktop_background(self.lcd)

        hovered_index = None
        hovered_task = None
        hovered_start = None
        if not self.dialog:
            hovered_index = self._hovered_index()
            hovered_task = self._hovered_taskbar_target()
            hovered_start = self._hovered_start_index()

        active_index = hovered_index if hovered_index is not None else self.selected_index
        layout = self._desktop_layout()
        for index, app in enumerate(self.apps):
            if index >= len(layout):
                break
            x, y, w, h = layout[index]
            draw_desktop_icon(self.lcd, x, y, w, h, app.title, index == active_index, app.draw_icon)

        draw_taskbar(self.lcd, self.wifi.status(), focus=hovered_task, start_open=self.start_open)

        if self.start_open:
            menu_index = hovered_start if hovered_start is not None else self.start_selected
            draw_start_menu(self.lcd, self.start_items, menu_index)

        if self.dialog == "run":
            command = self.run_items[self.run_selected]["label"]
            draw_dialog(
                self.lcd,
                "Run",
                [
                    "Open:",
                    command,
                    "Use Up/Down to choose",
                ],
                ["Cancel", "Open"],
                1,
                170,
            )
        elif self.dialog == "about":
            draw_dialog(self.lcd, "About PicoOS", self._about_lines(), ["OK"], 0, 184)

        if not self.dialog:
            draw_mouse_pointer(self.lcd, self.cursor_x, self.cursor_y)

    def _open_start(self):
        self.start_open = True
        self.dialog = ""
        self.start_selected = 0

    def _close_start(self):
        self.start_open = False
        self.dialog = ""

    def _step_dialog(self):
        if self.dialog == "about":
            if self.buttons.pressed("A") or self.buttons.pressed("B"):
                self.dialog = ""
            self.draw_home()
            return

        if self.dialog == "run":
            if self.buttons.repeat("UP", 180, 100):
                self.run_selected = (self.run_selected - 1) % len(self.run_items)
            if self.buttons.repeat("DOWN", 180, 100):
                self.run_selected = (self.run_selected + 1) % len(self.run_items)
            if self.buttons.pressed("A"):
                self.dialog = ""
            elif self.buttons.pressed("B"):
                self._activate_entry(self.run_items[self.run_selected])
                if self.active_app is not None:
                    return
            self.draw_home()

    def _step_start_menu(self):
        hovered_row = self._hovered_start_index()
        if hovered_row is not None:
            self.start_selected = hovered_row

        if self.buttons.pressed("X"):
            self._snap_cursor_to_start(self.start_selected)
            self.draw_home()
            return

        if self.buttons.pressed("A"):
            self._close_start()
            self.draw_home()
            return

        if self.buttons.pressed("B"):
            if hovered_row is not None:
                self._activate_entry(self.start_items[hovered_row])
                if self.active_app is not None:
                    return
            else:
                hovered_task = self._hovered_taskbar_target()
                if hovered_task == "start":
                    self._close_start()
                elif hovered_task == "tray":
                    self._launch_wifi("status")
                    return
                else:
                    self._close_start()

        self.draw_home()

    def _step_desktop(self):
        hovered_index = self._hovered_index()
        if hovered_index is not None:
            self.selected_index = hovered_index

        if self.buttons.pressed("X"):
            if hovered_index is not None:
                self._snap_cursor_to_index(hovered_index)
            else:
                self._snap_cursor_to_index(self.selected_index)
            self.draw_home()
            return

        if self.buttons.pressed("A"):
            if self.start_open:
                self._close_start()
            else:
                self._open_start()
            self.draw_home()
            return

        if self.buttons.pressed("B"):
            hovered_task = self._hovered_taskbar_target()
            if hovered_task == "start":
                self._open_start()
                self.draw_home()
                return
            if hovered_task == "tray":
                self._launch_wifi("status")
                return
            if hovered_index is not None:
                self.open_app(hovered_index)
                return

        self.draw_home()

    def step_home(self):
        if self.buttons.down("A") and self.buttons.down("B"):
            self.draw_home()
            return

        if self.dialog:
            self._step_dialog()
            return

        self._move_cursor()

        if self.start_open:
            self._step_start_menu()
            return

        self._step_desktop()

    def run(self):
        self.wifi.start_auto_connect()
        self.show_splash()
        self.draw_home()
        while True:
            self.wifi.poll_auto_connect()
            self.buttons.update()
            if self.help_open:
                self._step_help()
            elif self.active_app is None:
                if self.buttons.pressed("Y"):
                    self._open_help()
                else:
                    self.step_home()
            else:
                if self.buttons.home_triggered():
                    self.go_home()
                    self.draw_home()
                elif self.buttons.pressed("Y"):
                    self._open_help()
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
