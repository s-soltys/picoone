from core.display import BLACK, WHITE, CYAN, GRAY, AMBER, TEAL
from core.controls import A_LABEL, B_LABEL
from core.ui import CONTENT_TOP, CONTENT_BOTTOM, SCREEN_W, draw_header, draw_footer_actions, fit_text


FAKE_TREE = {
    "name": "home",
    "kind": "dir",
    "children": [
        {
            "name": "photos",
            "kind": "dir",
            "children": [
                {"name": "nebula.jpg", "kind": "file", "size": "1.4MB", "meta": "galaxy snap"},
                {"name": "launch.png", "kind": "file", "size": "560KB", "meta": "boot art"},
            ],
        },
        {
            "name": "music",
            "kind": "dir",
            "children": [
                {"name": "starlight.mod", "kind": "file", "size": "4.8MB", "meta": "tracker tune"},
                {"name": "rain.wav", "kind": "file", "size": "2.1MB", "meta": "field clip"},
            ],
        },
        {
            "name": "notes",
            "kind": "dir",
            "children": [
                {"name": "todo.txt", "kind": "file", "size": "2KB", "meta": "launcher ideas"},
                {"name": "wifi.txt", "kind": "file", "size": "1KB", "meta": "saved scan"},
            ],
        },
        {
            "name": "system",
            "kind": "dir",
            "children": [
                {"name": "apps.cfg", "kind": "file", "size": "3KB", "meta": "app order"},
                {"name": "theme.ini", "kind": "file", "size": "1KB", "meta": "accent colors"},
            ],
        },
        {
            "name": "downloads",
            "kind": "dir",
            "children": [
                {"name": "map.bin", "kind": "file", "size": "8MB", "meta": "sector data"},
                {"name": "calc.log", "kind": "file", "size": "12KB", "meta": "history"},
            ],
        },
    ],
}


class FilesApp:
    app_id = "files"
    title = "Files"
    accent = AMBER

    def __init__(self):
        self.stack = [FAKE_TREE]
        self.selected = 0
        self.scroll = 0
        self.preview = None
        self.rows = 0

    def draw_icon(self, lcd, cx, cy, selected, monochrome=False):
        ink = BLACK if monochrome and selected else (WHITE if monochrome else AMBER)
        detail = BLACK if monochrome and selected else WHITE
        lcd.rect(cx - 10, cy - 6, 20, 12, ink)
        lcd.fill_rect(cx - 8, cy - 8, 7, 4, ink)
        lcd.hline(cx - 9, cy - 1, 18, detail)

    def on_open(self, runtime):
        self.stack = [FAKE_TREE]
        self.selected = 0
        self.scroll = 0
        self.preview = None
        self.rows = max(1, (CONTENT_BOTTOM - (CONTENT_TOP + 28)) // 14)

    def current_dir(self):
        return self.stack[-1]

    def current_items(self):
        return self.current_dir()["children"]

    def current_path(self):
        names = []
        for node in self.stack[1:]:
            names.append(node["name"])
        if not names:
            return "/"
        return "/" + "/".join(names)

    def step(self, runtime):
        buttons = runtime.buttons
        lcd = runtime.lcd

        if self.preview:
            if buttons.pressed("A"):
                self.preview = None
        else:
            items = self.current_items()
            if buttons.repeat("UP"):
                self.selected = max(0, self.selected - 1)
            if buttons.repeat("DOWN"):
                self.selected = min(len(items) - 1, self.selected + 1)
            if buttons.pressed("A"):
                if len(self.stack) > 1:
                    self.stack.pop()
                    self.selected = 0
                    self.scroll = 0
            if buttons.pressed("B"):
                choice = items[self.selected]
                if choice["kind"] == "dir":
                    self.stack.append(choice)
                    self.selected = 0
                    self.scroll = 0
                else:
                    self.preview = choice

            if self.selected < self.scroll:
                self.scroll = self.selected
            if self.selected >= self.scroll + self.rows:
                self.scroll = self.selected - (self.rows - 1)

        lcd.fill(BLACK)
        draw_header(lcd, "Files", color=AMBER)

        if self.preview:
            item = self.preview
            lcd.text(fit_text(item["name"], 28), 4, CONTENT_TOP + 12, CYAN)
            lcd.text("file", 4, CONTENT_TOP + 38, WHITE)
            lcd.text(item["size"], 4, CONTENT_TOP + 56, WHITE)
            lcd.text(fit_text(item["meta"], 28), 4, CONTENT_TOP + 82, GRAY)
            draw_footer_actions(lcd, A_LABEL + " back")
            return None

        lcd.text(fit_text(self.current_path(), 28), 4, CONTENT_TOP + 2, TEAL)

        y = CONTENT_TOP + 24
        items = self.current_items()
        end = min(len(items), self.scroll + self.rows)
        for index in range(self.scroll, end):
            item = items[index]
            selected = index == self.selected
            if selected:
                lcd.fill_rect(0, y - 2, SCREEN_W, 14, GRAY)
            icon = "D" if item["kind"] == "dir" else "F"
            color = BLACK if selected else (AMBER if item["kind"] == "dir" else WHITE)
            lcd.text(icon, 2, y, color)
            lcd.text(fit_text(item["name"], 25), 16, y, BLACK if selected else WHITE)
            y += 14

        draw_footer_actions(lcd, B_LABEL + " open", A_LABEL + " up", GRAY)
        return None
