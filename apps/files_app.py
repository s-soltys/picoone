from lcd import BLACK, WHITE, CYAN, YELLOW, GRAY, AMBER, TEAL
from core.ui import draw_header, draw_footer, fit_text


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

    def draw_icon(self, lcd, cx, cy, selected):
        lcd.rect(cx - 10, cy - 6, 20, 12, AMBER)
        lcd.fill_rect(cx - 8, cy - 8, 7, 4, AMBER)
        lcd.hline(cx - 9, cy - 1, 18, WHITE)
        if selected:
            lcd.ellipse(cx, cy, 13, 9, YELLOW, False)

    def on_open(self, runtime):
        self.stack = [FAKE_TREE]
        self.selected = 0
        self.scroll = 0
        self.preview = None

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
            if buttons.pressed("A") or buttons.pressed("B"):
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
            if self.selected >= self.scroll + 5:
                self.scroll = self.selected - 4

        lcd.fill(BLACK)
        draw_header(lcd, "Files", color=AMBER)

        if self.preview:
            item = self.preview
            lcd.text(fit_text(item["name"], 18), 4, 18, CYAN)
            lcd.text("file", 4, 32, WHITE)
            lcd.text(item["size"], 4, 44, WHITE)
            lcd.text(fit_text(item["meta"], 18), 4, 58, GRAY)
            draw_footer(lcd, "A/B close")
            return None

        lcd.text(fit_text(self.current_path(), 18), 4, 12, TEAL)

        y = 24
        items = self.current_items()
        end = min(len(items), self.scroll + 5)
        for index in range(self.scroll, end):
            item = items[index]
            selected = index == self.selected
            if selected:
                lcd.fill_rect(0, y - 1, 160, 10, GRAY)
            icon = "D" if item["kind"] == "dir" else "F"
            color = BLACK if selected else (AMBER if item["kind"] == "dir" else WHITE)
            lcd.text(icon, 2, y, color)
            lcd.text(fit_text(item["name"], 15), 14, y, BLACK if selected else WHITE)
            y += 10

        draw_footer(lcd, "B open  A up")
        return None
