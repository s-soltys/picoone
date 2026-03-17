from core.display import BLACK, WHITE, RED, GREEN, BLUE, AMBER, CYAN, SCREEN_W, SCREEN_H
from core.controls import A_LABEL, B_LABEL, X_LABEL, Y_LABEL
from core.ui import draw_footer_actions, draw_header


SEGMENTS = {
    "0": "abcedf",
    "1": "bc",
    "2": "abdeg",
    "3": "abcdg",
    "4": "bcfg",
    "5": "acdfg",
    "6": "acdefg",
    "7": "abc",
    "8": "abcdefg",
    "9": "abcdfg",
    "-": "g",
}

PLAYER_COLORS = (RED, GREEN, BLUE, AMBER)


class MTGLifeCounterApp:
    app_id = "mtg-life"
    title = "MTG Life"
    accent = RED

    def __init__(self):
        self.life = [40, 40, 40, 40]
        self.selected = 0
        self.reset_latched = False

    def draw_icon(self, lcd, cx, cy, selected, monochrome=False):
        ink = BLACK if monochrome and selected else (WHITE if monochrome else RED)
        detail = BLACK if monochrome and selected else (WHITE if monochrome else GREEN)
        lcd.rect(cx - 9, cy - 8, 18, 18, ink)
        lcd.vline(cx, cy - 7, 16, detail)
        lcd.hline(cx - 8, cy + 1, 16, detail)
        lcd.fill_rect(cx - 3, cy - 3, 6, 6, detail)

    def on_open(self, runtime):
        self.reset_latched = False

    def _grid_rect(self, index):
        content_top = 18
        content_bottom = SCREEN_H - 18
        gap = 4
        width = (SCREEN_W - gap) // 2
        height = ((content_bottom - content_top) - gap) // 2
        col = index % 2
        row = index // 2
        x = col * (width + gap)
        y = content_top + (row * (height + gap))
        return x, y, width, height

    def _set_selected(self, row, col):
        row = max(0, min(1, row))
        col = max(0, min(1, col))
        self.selected = (row * 2) + col

    def _move_selected(self, dx=0, dy=0):
        row = self.selected // 2
        col = self.selected % 2
        self._set_selected(row + dy, col + dx)

    def _adjust_selected(self, delta):
        self.life[self.selected] += delta

    def _reset_match(self):
        for index in range(4):
            self.life[index] = 40

    def _draw_segment_char(self, lcd, x, y, scale, char, color):
        width = 12 * scale
        height = 20 * scale
        thick = max(2, scale)
        segments = SEGMENTS.get(char, "")

        if "a" in segments:
            lcd.fill_rect(x + thick, y, width - (thick * 2), thick, color)
        if "b" in segments:
            lcd.fill_rect(x + width - thick, y + thick, thick, (height // 2) - thick, color)
        if "c" in segments:
            lcd.fill_rect(x + width - thick, y + (height // 2), thick, (height // 2) - thick, color)
        if "d" in segments:
            lcd.fill_rect(x + thick, y + height - thick, width - (thick * 2), thick, color)
        if "e" in segments:
            lcd.fill_rect(x, y + (height // 2), thick, (height // 2) - thick, color)
        if "f" in segments:
            lcd.fill_rect(x, y + thick, thick, (height // 2) - thick, color)
        if "g" in segments:
            lcd.fill_rect(x + thick, y + (height // 2) - (thick // 2), width - (thick * 2), thick, color)

    def _draw_total(self, lcd, x, y, width, value, color):
        text = str(value)
        if len(text) > 3:
            text = "999" if value > 0 else "-99"

        scale = 2
        char_w = 14 * scale
        total_w = len(text) * char_w
        start_x = x + max(4, (width - total_w) // 2)
        for index in range(len(text)):
            self._draw_segment_char(lcd, start_x + (index * char_w), y, scale, text[index], color)

    def _draw_player_panel(self, lcd, index):
        x, y, w, h = self._grid_rect(index)
        selected = index == self.selected
        life = self.life[index]
        fill = PLAYER_COLORS[index]
        text_color = WHITE
        accent = CYAN if selected else BLACK

        lcd.fill_rect(x, y, w, h, fill)
        lcd.rect(x, y, w, h, BLACK)
        if selected:
            lcd.rect(x + 2, y + 2, w - 4, h - 4, WHITE)
            lcd.rect(x + 4, y + 4, w - 8, h - 8, WHITE)

        lcd.fill_rect(x + 6, y + 6, 26, 12, BLACK)
        lcd.text("P" + str(index + 1), x + 11, y + 8, WHITE)

        if life <= 0:
            lcd.fill_rect(x + w - 34, y + 6, 28, 12, BLACK)
            lcd.text("OUT", x + w - 31, y + 8, WHITE)

        self._draw_total(lcd, x, y + max(22, (h // 2) - 20), w, life, text_color)

        lcd.fill_rect(x + 8, y + h - 30, w - 16, 22, BLACK)
        if selected:
            lcd.text("A/B +/-1", x + 20, y + h - 28, WHITE)
            lcd.text("X/Y +/-5", x + 20, y + h - 16, WHITE)
        else:
            lcd.text("D-pad select", x + 16, y + h - 18, WHITE)

        lcd.hline(x + 8, y + h - 34, w - 16, accent)

    def step(self, runtime):
        buttons = runtime.buttons
        lcd = runtime.lcd

        if buttons.repeat("LEFT", 180, 100):
            self._move_selected(dx=-1)
        if buttons.repeat("RIGHT", 180, 100):
            self._move_selected(dx=1)
        if buttons.repeat("UP", 180, 100):
            self._move_selected(dy=-1)
        if buttons.repeat("DOWN", 180, 100):
            self._move_selected(dy=1)

        reset_combo = buttons.down("X") and buttons.down("Y")
        if reset_combo:
            if not self.reset_latched:
                self._reset_match()
                self.reset_latched = True
        else:
            self.reset_latched = False
            if buttons.repeat("A", 260, 110):
                self._adjust_selected(-1)
            if buttons.repeat("B", 260, 110):
                self._adjust_selected(1)
            if buttons.repeat("X", 260, 110):
                self._adjust_selected(-5)
            if buttons.repeat("Y", 260, 110):
                self._adjust_selected(5)

        lcd.fill(BLACK)
        draw_header(lcd, "MTG Life", "X+Y rst", CYAN)
        for index in range(4):
            self._draw_player_panel(lcd, index)
        draw_footer_actions(lcd, A_LABEL + " -1", B_LABEL + " +1", CYAN)
        return None
