from lcd import BLACK, WHITE, CYAN, YELLOW, GRAY, GREEN, ORANGE, SLATE
from core.ui import draw_header, fit_text


OPS = "+-*/"
KEYPAD = [
    ["7", "8", "9", "/"],
    ["4", "5", "6", "*"],
    ["1", "2", "3", "-"],
    ["0", ".", "=", "+"],
]


class CalculatorApp:
    app_id = "calculator"
    title = "Calc"
    accent = ORANGE

    def __init__(self):
        self.cursor_x = 0
        self.cursor_y = 0
        self.expression = ""
        self.result = ""
        self.error = ""
        self.just_evaluated = False

    def draw_icon(self, lcd, cx, cy, selected, monochrome=False):
        frame = BLACK if monochrome and selected else (WHITE if monochrome else ORANGE)
        screen = BLACK if monochrome and selected else (WHITE if monochrome else GREEN)
        mark = BLACK if monochrome and selected else WHITE
        lcd.rect(cx - 10, cy - 9, 20, 18, frame)
        lcd.fill_rect(cx - 8, cy - 7, 16, 5, screen)
        lcd.hline(cx - 6, cy + 1, 4, mark)
        lcd.vline(cx - 4, cy - 1, 4, mark)
        lcd.hline(cx + 2, cy, 4, mark)
        lcd.hline(cx + 2, cy + 3, 4, mark)

    def on_open(self, runtime):
        self.cursor_x = 0
        self.cursor_y = 0
        self.expression = ""
        self.result = ""
        self.error = ""
        self.just_evaluated = False

    def clear(self):
        self.expression = ""
        self.result = ""
        self.error = ""
        self.just_evaluated = False

    def backspace(self):
        self.error = ""
        if self.just_evaluated:
            self.expression = self.result
            self.just_evaluated = False
        self.expression = self.expression[:-1]
        if not self.expression:
            self.result = ""

    def press_key(self, key):
        if key == "=":
            self.evaluate()
            return

        self.error = ""
        if key in OPS:
            if self.just_evaluated:
                self.expression = self.result or "0"
                self.just_evaluated = False
            if not self.expression:
                self.expression = "0"
            if self.expression[-1] in OPS:
                self.expression = self.expression[:-1] + key
            else:
                self.expression += key
            return

        if self.just_evaluated:
            self.expression = ""
            self.result = ""
            self.just_evaluated = False

        if key == ".":
            tail = self.expression
            for op in OPS:
                pos = tail.rfind(op)
                if pos >= 0:
                    tail = tail[pos + 1:]
            if "." in tail:
                return
            if not tail:
                self.expression += "0"

        self.expression += key

    def evaluate(self):
        if not self.expression:
            return
        if self.expression[-1] in OPS:
            self.error = "finish expr"
            return

        for char in self.expression:
            if char not in "0123456789.+-*/":
                self.error = "bad input"
                return

        try:
            value = eval(self.expression)
        except ZeroDivisionError:
            self.error = "div by 0"
            return
        except Exception:
            self.error = "bad expr"
            return

        if isinstance(value, float):
            text = "{:.4f}".format(value)
            while "." in text and text[-1] == "0":
                text = text[:-1]
            if text.endswith("."):
                text = text[:-1]
        else:
            text = str(value)

        self.result = text
        self.just_evaluated = True

    def step(self, runtime):
        buttons = runtime.buttons
        lcd = runtime.lcd

        if buttons.repeat("LEFT"):
            self.cursor_x = max(0, self.cursor_x - 1)
        if buttons.repeat("RIGHT"):
            self.cursor_x = min(3, self.cursor_x + 1)
        if buttons.repeat("UP"):
            self.cursor_y = max(0, self.cursor_y - 1)
        if buttons.repeat("DOWN"):
            self.cursor_y = min(3, self.cursor_y + 1)
        if buttons.pressed("A"):
            self.backspace()
        if buttons.pressed("CTRL"):
            self.clear()
        if buttons.pressed("B"):
            self.press_key(KEYPAD[self.cursor_y][self.cursor_x])

        lcd.fill(BLACK)
        draw_header(lcd, "Calculator", color=ORANGE)

        display_expr = self.expression or "0"
        lcd.text(fit_text(display_expr, 19), 4, 14, WHITE)
        if self.error:
            lcd.text(fit_text(self.error, 19), 4, 24, YELLOW)
        else:
            result = self.result if self.result else "Bottom = eval"
            lcd.text(fit_text(result, 19), 4, 24, CYAN)

        for row in range(4):
            for col in range(4):
                x = 1 + (col * 40)
                y = 36 + (row * 11)
                key = KEYPAD[row][col]
                selected = row == self.cursor_y and col == self.cursor_x
                lcd.fill_rect(x, y, 38, 10, SLATE if selected else BLACK)
                lcd.rect(x, y, 38, 10, YELLOW if selected else GRAY)
                lcd.text(key, x + 15, y + 1, ORANGE if selected else GREEN)

        lcd.text("Top del", 2, 70, GRAY)
        lcd.text("CTRL clr", 56, 70, GRAY)
        return None
