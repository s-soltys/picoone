from core.display import BLACK, WHITE, GRAY, YELLOW, CYAN, RED, ORANGE, GREEN, BLUE
from core.controls import A_LABEL, B_LABEL
from core.ui import CONTENT_TOP, CONTENT_BOTTOM, SCREEN_W, draw_header, draw_footer_actions


BRICK_ROWS = 4
BRICK_COLS = 5
BRICK_GAP = 4
BRICK_W = (SCREEN_W - 20 - ((BRICK_COLS - 1) * BRICK_GAP)) // BRICK_COLS
BRICK_H = 12
BRICK_X = 10
BRICK_Y = CONTENT_TOP + 18
PADDLE_W = 38
PADDLE_Y = CONTENT_BOTTOM - 18


class ArkanoidApp:
    app_id = "arkanoid"
    title = "Arkanoid"
    accent = CYAN

    def __init__(self):
        self.paddle_x = (SCREEN_W - PADDLE_W) // 2
        self.ball_x = SCREEN_W // 2
        self.ball_y = PADDLE_Y - 8
        self.ball_vx = 3
        self.ball_vy = -3
        self.launched = False
        self.lives = 3
        self.state = "playing"
        self.bricks = []
        self.score = 0

    def draw_icon(self, lcd, cx, cy, selected, monochrome=False):
        ink = BLACK if monochrome and selected else (WHITE if monochrome else CYAN)
        brick = BLACK if monochrome and selected else (WHITE if monochrome else ORANGE)
        lcd.fill_rect(cx - 8, cy + 5, 16, 3, ink)
        lcd.ellipse(cx, cy + 1, 2, 2, WHITE if monochrome else YELLOW, True)
        lcd.rect(cx - 10, cy - 8, 7, 4, brick)
        lcd.rect(cx - 1, cy - 8, 7, 4, brick)
        lcd.rect(cx - 5, cy - 2, 7, 4, brick)

    def on_open(self, runtime):
        self.reset_game()

    def reset_game(self):
        self.paddle_x = (SCREEN_W - PADDLE_W) // 2
        self.ball_x = SCREEN_W // 2
        self.ball_y = PADDLE_Y - 8
        self.ball_vx = 3
        self.ball_vy = -3
        self.launched = False
        self.lives = 3
        self.state = "playing"
        self.score = 0
        self.bricks = []
        row_colors = [RED, ORANGE, GREEN, BLUE]
        for row in range(BRICK_ROWS):
            for col in range(BRICK_COLS):
                self.bricks.append({
                    "x": BRICK_X + (col * (BRICK_W + BRICK_GAP)),
                    "y": BRICK_Y + (row * (BRICK_H + BRICK_GAP)),
                    "alive": True,
                    "color": row_colors[row],
                })

    def _reset_ball(self):
        self.ball_x = self.paddle_x + (PADDLE_W // 2)
        self.ball_y = PADDLE_Y - 8
        self.ball_vx = 3
        self.ball_vy = -3
        self.launched = False

    def _update_ball(self):
        if not self.launched:
            self.ball_x = self.paddle_x + (PADDLE_W // 2)
            return

        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy

        if self.ball_x <= 4 or self.ball_x >= SCREEN_W - 4:
            self.ball_vx *= -1
            self.ball_x += self.ball_vx
        if self.ball_y <= CONTENT_TOP + 4:
            self.ball_vy *= -1
            self.ball_y += self.ball_vy

        if self.ball_y >= PADDLE_Y - 4 and self.paddle_x - 2 <= self.ball_x <= self.paddle_x + PADDLE_W + 2:
            self.ball_vy = -abs(self.ball_vy)
            hit = self.ball_x - (self.paddle_x + (PADDLE_W // 2))
            if hit < -4:
                self.ball_vx = -4
            elif hit > 4:
                self.ball_vx = 4
            elif hit < 0:
                self.ball_vx = -3
            elif hit > 0:
                self.ball_vx = 3

        for brick in self.bricks:
            if not brick["alive"]:
                continue
            if brick["x"] <= self.ball_x <= brick["x"] + BRICK_W and brick["y"] <= self.ball_y <= brick["y"] + BRICK_H:
                brick["alive"] = False
                self.ball_vy *= -1
                self.score += 1
                break

        alive = False
        for brick in self.bricks:
            if brick["alive"]:
                alive = True
                break
        if not alive:
            self.state = "won"

        if self.ball_y > CONTENT_BOTTOM + 4:
            self.lives -= 1
            if self.lives <= 0:
                self.state = "lost"
            else:
                self._reset_ball()

    def draw_scene(self, lcd):
        lcd.fill(BLACK)
        draw_header(lcd, "Arkanoid", "L" + str(self.lives), CYAN)

        for brick in self.bricks:
            if brick["alive"]:
                lcd.fill_rect(brick["x"], brick["y"], BRICK_W, BRICK_H, brick["color"])
                lcd.rect(brick["x"], brick["y"], BRICK_W, BRICK_H, WHITE)

        lcd.fill_rect(self.paddle_x, PADDLE_Y, PADDLE_W, 5, WHITE)
        lcd.ellipse(self.ball_x, self.ball_y, 4, 4, YELLOW, True)
        lcd.text("S" + str(self.score), SCREEN_W - 44, CONTENT_TOP - 12, WHITE)

        if self.state == "playing":
            if self.launched:
                draw_footer_actions(lcd, A_LABEL + " reset", "", GRAY)
            else:
                draw_footer_actions(lcd, B_LABEL + " launch", A_LABEL + " reset", GRAY)
        elif self.state == "won":
            draw_footer_actions(lcd, "Wall clear", A_LABEL + " restart", GREEN)
        else:
            draw_footer_actions(lcd, "No lives", A_LABEL + " restart", RED)

    def step(self, runtime):
        buttons = runtime.buttons
        lcd = runtime.lcd

        if buttons.pressed("A"):
            self.reset_game()

        if self.state == "playing":
            if buttons.down("LEFT"):
                self.paddle_x = max(4, self.paddle_x - 6)
            if buttons.down("RIGHT"):
                self.paddle_x = min(SCREEN_W - PADDLE_W - 4, self.paddle_x + 6)
            if buttons.pressed("B") and not self.launched:
                self.launched = True
            self._update_ball()

        self.draw_scene(lcd)
        return None
