from core.display import BLACK, WHITE, GRAY, AMBER
from core.controls import A_LABEL, B_LABEL
from core.ui import (
    WINDOW_CONTENT_X,
    WINDOW_CONTENT_Y,
    WINDOW_CONTENT_W,
    WINDOW_CONTENT_BOTTOM,
    WINDOW_TEXT_CHARS,
    draw_window_shell,
    draw_window_footer_actions,
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
        self.rows = max(1, (WINDOW_CONTENT_BOTTOM - (WINDOW_CONTENT_Y + 22)) // 16)

    def draw_icon(self, lcd, cx, cy, selected, monochrome=False):
        ink = BLACK if monochrome else WHITE
        tab = BLACK if monochrome else WHITE
        lcd.rect(cx - 10, cy - 5, 20, 12, ink)
        lcd.fill_rect(cx - 8, cy - 8, 7, 4, tab)
        lcd.hline(cx - 8, cy + 1, 14, ink)
        lcd.hline(cx - 8, cy + 4, 10, ink)

    def on_open(self, runtime):
        if self.selected >= len(self.games):
            self.selected = 0
        if self.selected < self.scroll:
            self.scroll = self.selected
        if self.selected >= self.scroll + self.rows:
            self.scroll = self.selected - (self.rows - 1)

    def step(self, runtime):
        buttons = runtime.buttons
        lcd = runtime.lcd

        if buttons.pressed("A"):
            return "home"

        if buttons.repeat("UP"):
            self.selected = max(0, self.selected - 1)
        if buttons.repeat("DOWN"):
            self.selected = min(len(self.games) - 1, self.selected + 1)
        if buttons.pressed("B") and self.games:
            runtime.open_app(self.games[self.selected])
            return None

        if self.selected < self.scroll:
            self.scroll = self.selected
        if self.selected >= self.scroll + self.rows:
            self.scroll = self.selected - (self.rows - 1)

        draw_window_shell(lcd, "Games", runtime.wifi.status())
        lcd.text("Arcade folder", WINDOW_CONTENT_X, WINDOW_CONTENT_Y, BLACK)
        lcd.text(fit_text(str(len(self.games)) + " titles", 8), WINDOW_CONTENT_X + WINDOW_CONTENT_W - 64, WINDOW_CONTENT_Y, GRAY)

        y = WINDOW_CONTENT_Y + 20
        end = min(len(self.games), self.scroll + self.rows)
        for index in range(self.scroll, end):
            app = self.games[index]
            selected = index == self.selected
            if selected:
                lcd.fill_rect(WINDOW_CONTENT_X - 2, y - 2, WINDOW_CONTENT_W + 2, 14, BLACK)

            app.draw_icon(lcd, WINDOW_CONTENT_X + 12, y + 4, selected, True)
            text_color = WHITE if selected else BLACK
            lcd.text(fit_text(app.title, WINDOW_TEXT_CHARS - 4), WINDOW_CONTENT_X + 28, y, text_color)
            y += 16

        draw_window_footer_actions(lcd, A_LABEL + " desk", B_LABEL + " open", BLACK)
        return None
