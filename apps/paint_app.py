from core.display import BLACK, WHITE, GRAY, YELLOW, RED, GREEN, BLUE, CYAN, ORANGE, PURPLE
from core.controls import A_LABEL, B_LABEL
from core.ui import CONTENT_TOP, SCREEN_W, draw_header, draw_footer_actions


CANVAS_W = 14
CANVAS_H = 6
CELL = 15
PALETTE = [WHITE, BLACK, RED, GREEN, BLUE, CYAN, YELLOW, ORANGE, PURPLE]


class PaintApp:
    app_id = "paint"
    title = "Paint"
    accent = ORANGE

    def __init__(self):
        self.canvas = []
        self.cursor_x = 0
        self.cursor_y = 0
        self.color_index = 1

    def draw_icon(self, lcd, cx, cy, selected, monochrome=False):
        ink = BLACK if monochrome and selected else (WHITE if monochrome else ORANGE)
        tip = BLACK if monochrome and selected else (WHITE if monochrome else CYAN)
        lcd.hline(cx - 8, cy + 6, 9, ink)
        lcd.hline(cx - 6, cy + 4, 9, ink)
        lcd.hline(cx - 4, cy + 2, 9, ink)
        lcd.fill_rect(cx + 4, cy - 4, 4, 4, tip)
        lcd.pixel(cx + 2, cy, ink)

    def on_open(self, runtime):
        self.reset_canvas()

    def reset_canvas(self):
        self.canvas = []
        for _ in range(CANVAS_H):
            self.canvas.append([WHITE] * CANVAS_W)
        self.cursor_x = 0
        self.cursor_y = 0
        self.color_index = 1

    def draw_scene(self, lcd):
        canvas_x = 4
        canvas_y = CONTENT_TOP + 18
        palette_x = SCREEN_W - 22
        palette_h = 18

        lcd.fill(WHITE)
        draw_header(lcd, "Paint", "C" + str(self.color_index + 1), ORANGE)

        for y in range(CANVAS_H):
            for x in range(CANVAS_W):
                px = canvas_x + (x * CELL)
                py = canvas_y + (y * CELL)
                lcd.fill_rect(px, py, CELL, CELL, self.canvas[y][x])
                lcd.rect(px, py, CELL, CELL, GRAY)
                if x == self.cursor_x and y == self.cursor_y:
                    lcd.rect(px + 1, py + 1, CELL - 2, CELL - 2, BLACK)

        for index in range(len(PALETTE)):
            py = CONTENT_TOP + 8 + (index * (palette_h + 3))
            lcd.fill_rect(palette_x, py, 18, palette_h, PALETTE[index])
            lcd.rect(palette_x, py, 18, palette_h, BLACK if index == self.color_index else GRAY)

        draw_footer_actions(lcd, A_LABEL + " color", B_LABEL + " paint", WHITE)

    def step(self, runtime):
        buttons = runtime.buttons
        lcd = runtime.lcd

        if buttons.repeat("LEFT", 140, 70):
            self.cursor_x = max(0, self.cursor_x - 1)
        if buttons.repeat("RIGHT", 140, 70):
            self.cursor_x = min(CANVAS_W - 1, self.cursor_x + 1)
        if buttons.repeat("UP", 140, 70):
            self.cursor_y = max(0, self.cursor_y - 1)
        if buttons.repeat("DOWN", 140, 70):
            self.cursor_y = min(CANVAS_H - 1, self.cursor_y + 1)
        if buttons.pressed("A"):
            self.color_index = (self.color_index + 1) % len(PALETTE)

        if buttons.down("B"):
            self.canvas[self.cursor_y][self.cursor_x] = PALETTE[self.color_index]

        self.draw_scene(lcd)
        return None
