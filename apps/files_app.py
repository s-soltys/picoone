from core.display import BLACK, WHITE, CYAN, GRAY, AMBER, TEAL
from core.controls import A_LABEL, B_LABEL, X_LABEL
from core.ui import (
    LIST_ROW_H,
    WINDOW_CONTENT_X,
    WINDOW_CONTENT_Y,
    WINDOW_CONTENT_W,
    WINDOW_CONTENT_BOTTOM,
    WINDOW_TEXT_CHARS,
    draw_field,
    draw_list_row,
    draw_window_shell,
    fit_text,
)


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
    launch_mode = "window"

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
        self.rows = max(1, (WINDOW_CONTENT_BOTTOM - (WINDOW_CONTENT_Y + 54)) // LIST_ROW_H)

    def help_lines(self, runtime):
        return [
            "Explorer controls",
            "Up/Down moves the list",
            B_LABEL + " open folder or file",
            X_LABEL + " quick preview",
            A_LABEL + " go up or close preview",
        ]

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
            if buttons.pressed("X"):
                self.preview = items[self.selected]

            if self.selected < self.scroll:
                self.scroll = self.selected
            if self.selected >= self.scroll + self.rows:
                self.scroll = self.selected - (self.rows - 1)

        draw_window_shell(lcd, "Explorer", runtime.wifi.status())

        if self.preview:
            item = self.preview
            draw_field(lcd, WINDOW_CONTENT_X, WINDOW_CONTENT_Y, WINDOW_CONTENT_W, 16, self.current_path() + "/" + item["name"], TEAL)
            lcd.text(fit_text(item["name"], WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 28, CYAN)
            kind_text = "DIR" if item["kind"] == "dir" else "FILE"
            lcd.text("Type  " + kind_text, WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 52, BLACK)
            if item["kind"] == "dir":
                count = len(item.get("children", []))
                lcd.text("Items " + str(count), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 70, BLACK)
                lcd.text("Folder preview", WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 96, GRAY)
            else:
                lcd.text("Size  " + item["size"], WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 70, BLACK)
                lcd.text(fit_text(item["meta"], WINDOW_TEXT_CHARS), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 96, GRAY)
            draw_field(lcd, WINDOW_CONTENT_X, WINDOW_CONTENT_BOTTOM - 18, WINDOW_CONTENT_W, 16, "1 object selected", AMBER)
            return None

        draw_field(lcd, WINDOW_CONTENT_X, WINDOW_CONTENT_Y, WINDOW_CONTENT_W, 16, self.current_path(), TEAL)
        lcd.text("Name", WINDOW_CONTENT_X + 2, WINDOW_CONTENT_Y + 24, BLACK)
        lcd.text("Type", WINDOW_CONTENT_X + 114, WINDOW_CONTENT_Y + 24, BLACK)
        lcd.text("Size", WINDOW_CONTENT_X + 164, WINDOW_CONTENT_Y + 24, BLACK)

        y = WINDOW_CONTENT_Y + 34
        items = self.current_items()
        end = min(len(items), self.scroll + self.rows)
        for index in range(self.scroll, end):
            item = items[index]
            label = item["name"]
            detail = item["size"] if item["kind"] == "file" else ""
            kind = "DIR" if item["kind"] == "dir" else "FILE"
            draw_list_row(
                lcd,
                WINDOW_CONTENT_X,
                y,
                WINDOW_CONTENT_W,
                label,
                index == self.selected,
                lead="D" if item["kind"] == "dir" else "F",
                detail=detail,
                text_color=AMBER if item["kind"] == "dir" else BLACK,
            )
            lcd.text(kind, WINDOW_CONTENT_X + 112, y + 3, WHITE if index == self.selected else GRAY)
            y += LIST_ROW_H

        status_text = str(len(items)) + " objects"
        if items:
            status_text += "  " + fit_text(items[self.selected]["name"], 10)
        draw_field(lcd, WINDOW_CONTENT_X, WINDOW_CONTENT_BOTTOM - 18, WINDOW_CONTENT_W, 16, status_text, AMBER)
        return None
