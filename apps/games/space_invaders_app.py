import random

from core.display import BLACK, WHITE, GRAY, YELLOW, GREEN, RED, CYAN
from core.controls import A_LABEL, B_LABEL
from core.ui import CONTENT_TOP, CONTENT_BOTTOM, SCREEN_W, draw_header, draw_footer_actions


PLAY_LEFT = 18
PLAY_RIGHT = SCREEN_W - 18
PLAYER_Y = CONTENT_BOTTOM - 18
PLAYER_BULLET_Y = PLAYER_Y - 10
ALIEN_TOP = CONTENT_TOP + 36
ALIEN_COL_SPACING = 38
ALIEN_ROW_SPACING = 22
ALIEN_LEFT = PLAY_LEFT + 14


class SpaceInvadersApp:
    app_id = "invaders"
    title = "Invaders"
    accent = GREEN

    def __init__(self):
        self.player_x = SCREEN_W // 2
        self.player_lives = 3
        self.aliens = []
        self.alien_dir = 1
        self.frame = 0
        self.player_bullet = None
        self.enemy_bullet = None
        self.score = 0
        self.state = "playing"

    def draw_icon(self, lcd, cx, cy, selected, monochrome=False):
        ink = BLACK if monochrome and selected else (WHITE if monochrome else GREEN)
        eye = BLACK if monochrome and selected else (WHITE if monochrome else RED)
        lcd.rect(cx - 8, cy - 5, 16, 9, ink)
        lcd.fill_rect(cx - 5, cy - 8, 10, 3, ink)
        lcd.pixel(cx - 4, cy - 2, eye)
        lcd.pixel(cx + 3, cy - 2, eye)
        lcd.vline(cx - 6, cy + 4, 4, ink)
        lcd.vline(cx + 5, cy + 4, 4, ink)

    def on_open(self, runtime):
        self.reset_game()

    def reset_game(self):
        self.player_x = SCREEN_W // 2
        self.player_lives = 3
        self.aliens = []
        for row in range(3):
            for col in range(5):
                self.aliens.append({
                    "x": ALIEN_LEFT + (col * ALIEN_COL_SPACING),
                    "y": ALIEN_TOP + (row * ALIEN_ROW_SPACING),
                    "alive": True,
                    "color": GREEN if row < 2 else CYAN,
                })
        self.alien_dir = 1
        self.frame = 0
        self.player_bullet = None
        self.enemy_bullet = None
        self.score = 0
        self.state = "playing"

    def _alive_aliens(self):
        alive = []
        for alien in self.aliens:
            if alien["alive"]:
                alive.append(alien)
        return alive

    def _move_aliens(self):
        alive = self._alive_aliens()
        if not alive:
            self.state = "won"
            return

        edge_hit = False
        for alien in alive:
            next_x = alien["x"] + (self.alien_dir * 7)
            if next_x < PLAY_LEFT or next_x > PLAY_RIGHT:
                edge_hit = True
                break

        if edge_hit:
            self.alien_dir *= -1
            for alien in alive:
                alien["y"] += 10
                if alien["y"] >= PLAYER_Y - 16:
                    self.state = "lost"
        else:
            for alien in alive:
                alien["x"] += self.alien_dir * 7

    def _spawn_enemy_bullet(self):
        if self.enemy_bullet is not None:
            return
        alive = self._alive_aliens()
        if not alive:
            return
        shooter = alive[random.randint(0, len(alive) - 1)]
        self.enemy_bullet = {"x": shooter["x"], "y": shooter["y"] + 4}

    def _check_player_bullet(self):
        if self.player_bullet is None:
            return
        self.player_bullet["y"] -= 8
        if self.player_bullet["y"] < CONTENT_TOP + 4:
            self.player_bullet = None
            return

        for alien in self.aliens:
            if not alien["alive"]:
                continue
            if abs(self.player_bullet["x"] - alien["x"]) <= 7 and abs(self.player_bullet["y"] - alien["y"]) <= 5:
                alien["alive"] = False
                self.player_bullet = None
                self.score += 1
                return

    def _check_enemy_bullet(self):
        if self.enemy_bullet is None:
            return
        self.enemy_bullet["y"] += 6
        if self.enemy_bullet["y"] > CONTENT_BOTTOM + 4:
            self.enemy_bullet = None
            return

        if abs(self.enemy_bullet["x"] - self.player_x) <= 9 and self.enemy_bullet["y"] >= PLAYER_Y - 4:
            self.enemy_bullet = None
            self.player_lives -= 1
            if self.player_lives <= 0:
                self.state = "lost"

    def draw_scene(self, lcd):
        lcd.fill(BLACK)
        draw_header(lcd, "Invaders", "L" + str(self.player_lives), GREEN)

        for alien in self.aliens:
            if not alien["alive"]:
                continue
            x = alien["x"]
            y = alien["y"]
            lcd.rect(x - 6, y - 3, 12, 7, alien["color"])
            lcd.fill_rect(x - 3, y - 5, 6, 2, alien["color"])
            lcd.pixel(x - 3, y - 1, WHITE)
            lcd.pixel(x + 2, y - 1, WHITE)
            lcd.vline(x - 4, y + 4, 3, alien["color"])
            lcd.vline(x + 3, y + 4, 3, alien["color"])

        lcd.fill_rect(self.player_x - 12, PLAYER_Y + 4, 24, 5, WHITE)
        lcd.fill_rect(self.player_x - 5, PLAYER_Y - 1, 10, 5, CYAN)

        if self.player_bullet:
            lcd.vline(self.player_bullet["x"], self.player_bullet["y"], 8, YELLOW)
        if self.enemy_bullet:
            lcd.vline(self.enemy_bullet["x"], self.enemy_bullet["y"], 8, RED)

        lcd.text("S" + str(self.score), SCREEN_W - 44, CONTENT_TOP - 12, WHITE)

        if self.state == "playing":
            draw_footer_actions(lcd, B_LABEL + " fire", A_LABEL + " reset", GRAY)
        elif self.state == "won":
            draw_footer_actions(lcd, "Wave clear", A_LABEL + " restart", CYAN)
        else:
            draw_footer_actions(lcd, "Invaded", A_LABEL + " restart", RED)

    def step(self, runtime):
        buttons = runtime.buttons
        lcd = runtime.lcd

        if buttons.pressed("A"):
            self.reset_game()

        if self.state == "playing":
            if buttons.down("LEFT"):
                self.player_x = max(PLAY_LEFT, self.player_x - 6)
            if buttons.down("RIGHT"):
                self.player_x = min(PLAY_RIGHT, self.player_x + 6)
            if buttons.pressed("B") and self.player_bullet is None:
                self.player_bullet = {"x": self.player_x, "y": PLAYER_BULLET_Y}

            self.frame += 1
            if self.frame % 6 == 0:
                self._move_aliens()
            if self.frame % 14 == 0:
                self._spawn_enemy_bullet()
            self._check_player_bullet()
            self._check_enemy_bullet()

        self.draw_scene(lcd)
        return None
