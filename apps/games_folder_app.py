from core.display import BLACK, WHITE, GRAY, AMBER
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


class GamesFolderApp:
    app_id = "games-folder"
    title = "Games"
    accent = AMBER
    launch_mode = "window"

    def __init__(self, games):
        self.games = games
        self.selected = 0
        self.scroll = 0
        self.rows = max(1, (WINDOW_CONTENT_BOTTOM - (WINDOW_CONTENT_Y + 44)) // LIST_ROW_H)

    def draw_icon(self, lcd, cx, cy, selected, monochrome=False):
        ink = BLACK if monochrome and selected else (WHITE if monochrome else AMBER)
        tab = BLACK if monochrome and selected else (WHITE if monochrome else WHITE)
        lcd.rect(cx - 10, cy - 5, 20, 12, ink)
        lcd.fill_rect(cx - 8, cy - 8, 7, 4, tab)
        lcd.hline(cx - 8, cy + 1, 14, ink)
        lcd.hline(cx - 8, cy + 4, 10, BLACK if monochrome and selected else WHITE)

    def on_open(self, runtime):
        if self.selected >= len(self.games):
            self.selected = 0
        if self.selected < self.scroll:
            self.scroll = self.selected
        if self.selected >= self.scroll + self.rows:
            self.scroll = self.selected - (self.rows - 1)

    def help_lines(self, runtime):
        return [
            "Games folder controls",
            "Up/Down moves the list",
            B_LABEL + " launch game",
            X_LABEL + " jump one page",
            A_LABEL + " return home",
        ]

    def step(self, runtime):
        buttons = runtime.buttons
        lcd = runtime.lcd

        if buttons.pressed("A"):
            return "home"

        if buttons.repeat("UP"):
            self.selected = max(0, self.selected - 1)
        if buttons.repeat("DOWN"):
            self.selected = min(len(self.games) - 1, self.selected + 1)
        if buttons.pressed("X") and self.games:
            self.selected = min(len(self.games) - 1, self.selected + self.rows)
        if buttons.pressed("B") and self.games:
            runtime.open_app(self.games[self.selected])
            return None

        if self.selected < self.scroll:
            self.scroll = self.selected
        if self.selected >= self.scroll + self.rows:
            self.scroll = self.selected - (self.rows - 1)

        draw_window_shell(lcd, "Programs", runtime.wifi.status())
        draw_field(lcd, WINDOW_CONTENT_X, WINDOW_CONTENT_Y, WINDOW_CONTENT_W, 16, "Arcade Games", AMBER)
        lcd.text(fit_text(str(len(self.games)) + " titles", 10), WINDOW_CONTENT_X, WINDOW_CONTENT_Y + 24, GRAY)

        y = WINDOW_CONTENT_Y + 34
        end = min(len(self.games), self.scroll + self.rows)
        for index in range(self.scroll, end):
            app = self.games[index]
            draw_list_row(
                lcd,
                WINDOW_CONTENT_X,
                y,
                WINDOW_CONTENT_W,
                app.title,
                index == self.selected,
                lead=">",
                detail="play",
            )
            y += LIST_ROW_H

        draw_field(
            lcd,
            WINDOW_CONTENT_X,
            WINDOW_CONTENT_BOTTOM - 18,
            WINDOW_CONTENT_W,
            16,
            fit_text("Selected: " + self.games[self.selected].title, WINDOW_TEXT_CHARS),
            AMBER,
        )
        return None
