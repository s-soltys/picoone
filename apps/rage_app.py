import random

from lcd import BLACK, WHITE, GRAY, YELLOW, ORANGE, RED, CYAN, GREEN, BLUE, SLATE, BROWN, DKRED
from core.ui import draw_header, draw_footer


PLAY_TOP = 10
PLAY_BOTTOM = 69
PLAYER_HP = 6
MAX_WAVES = 3


def _sgn(value):
    if value < 0:
        return -1
    if value > 0:
        return 1
    return 0


class RageApp:
    app_id = "rage"
    title = "Rage"
    accent = ORANGE

    def __init__(self):
        self.player_x = 28
        self.player_y = 52
        self.player_hp = PLAYER_HP
        self.facing = 1
        self.attack_timer = 0
        self.special_timer = 0
        self.special_cooldown = 0
        self.invincible_timer = 0
        self.wave = 1
        self.state = "playing"
        self.enemies = []
        self.score = 0
        self.scroll = 0
        self.message_timer = 0
        self.message = ""

    def draw_icon(self, lcd, cx, cy, selected, monochrome=False):
        head = BLACK if monochrome and selected else (WHITE if monochrome else ORANGE)
        body = BLACK if monochrome and selected else (WHITE if monochrome else CYAN)
        limb = BLACK if monochrome and selected else (WHITE if monochrome else YELLOW)
        lcd.ellipse(cx, cy - 3, 4, 4, head, True)
        lcd.rect(cx - 4, cy + 1, 8, 7, body)
        lcd.hline(cx - 8, cy + 4, 5, limb)
        lcd.hline(cx + 4, cy + 4, 5, limb)
        lcd.vline(cx, cy + 8, 5, head)

    def on_open(self, runtime):
        self.reset_game()

    def reset_game(self):
        self.player_x = 28
        self.player_y = 52
        self.player_hp = PLAYER_HP
        self.facing = 1
        self.attack_timer = 0
        self.special_timer = 0
        self.special_cooldown = 0
        self.invincible_timer = 0
        self.wave = 1
        self.state = "playing"
        self.enemies = []
        self.score = 0
        self.scroll = 0
        self.message_timer = 18
        self.message = "STAGE 1"
        self.spawn_wave()

    def spawn_wave(self):
        self.enemies = []
        count = self.wave
        base_x = 94
        lanes = [38, 44, 50, 56]
        for index in range(count):
            self.enemies.append({
                "x": base_x + (index * 18),
                "y": lanes[(index + self.wave) % len(lanes)],
                "hp": 2 + (self.wave // 2),
                "flash": 0,
                "stun": 0,
                "cooldown": 15 + (index * 4),
                "color": RED if index % 2 == 0 else DKRED,
            })

    def _attack_hits(self, special):
        hits = []
        for enemy in self.enemies:
            dx = enemy["x"] - self.player_x
            dy = abs(enemy["y"] - self.player_y)
            if special:
                if abs(dx) <= 30 and dy <= 14:
                    hits.append(enemy)
                continue
            if self.facing == 1 and 0 <= dx <= 22 and dy <= 9:
                hits.append(enemy)
            if self.facing == -1 and -22 <= dx <= 0 and dy <= 9:
                hits.append(enemy)
        if special:
            return hits
        if not hits:
            return []
        hits.sort(key=lambda enemy: abs(enemy["x"] - self.player_x))
        return [hits[0]]

    def do_attack(self, special):
        targets = self._attack_hits(special)
        damage = 2 if special else 1
        knock = 8 if special else 5
        for enemy in targets:
            enemy["hp"] -= damage
            enemy["flash"] = 5
            enemy["stun"] = 10 if special else 7
            enemy["x"] += self.facing * knock
            if enemy["hp"] <= 0:
                self.score += 1
        alive = []
        for enemy in self.enemies:
            if enemy["hp"] > 0:
                alive.append(enemy)
        self.enemies = alive

    def update_enemies(self):
        for enemy in self.enemies:
            if enemy["flash"] > 0:
                enemy["flash"] -= 1
            if enemy["cooldown"] > 0:
                enemy["cooldown"] -= 1
            if enemy["stun"] > 0:
                enemy["stun"] -= 1
                continue

            dy = self.player_y - enemy["y"]
            if abs(dy) > 2:
                enemy["y"] += _sgn(dy)

            dx = self.player_x - enemy["x"]
            if abs(dx) > 13 or abs(dy) > 6:
                enemy["x"] += _sgn(dx)
            elif enemy["cooldown"] == 0:
                enemy["cooldown"] = 20
                if self.invincible_timer == 0:
                    self.player_hp -= 1
                    self.invincible_timer = 18
                    self.message_timer = 6
                    self.message = "OUCH"
                    if self.player_hp <= 0:
                        self.state = "lost"
                        self.message = "KNOCK OUT"
                        self.message_timer = 40

    def update_game(self, buttons):
        move_x = 0
        if buttons.down("LEFT"):
            move_x -= 2
            self.facing = -1
        if buttons.down("RIGHT"):
            move_x += 2
            self.facing = 1
        if buttons.down("UP"):
            self.player_y = max(28, self.player_y - 2)
        if buttons.down("DOWN"):
            self.player_y = min(60, self.player_y + 2)

        self.player_x = min(142, max(18, self.player_x + move_x))
        self.scroll = (self.scroll + move_x) % 32

        if buttons.pressed("B") and self.attack_timer == 0:
            self.attack_timer = 7
            self.do_attack(False)
        if buttons.pressed("A") and self.special_cooldown == 0:
            self.special_timer = 10
            self.special_cooldown = 45
            self.do_attack(True)

        if self.attack_timer > 0:
            self.attack_timer -= 1
        if self.special_timer > 0:
            self.special_timer -= 1
        if self.special_cooldown > 0:
            self.special_cooldown -= 1
        if self.invincible_timer > 0:
            self.invincible_timer -= 1
        if self.message_timer > 0:
            self.message_timer -= 1

        self.update_enemies()
        if self.state != "playing":
            return

        if not self.enemies:
            if self.wave >= MAX_WAVES:
                self.state = "won"
                self.message = "STREET CLEAR"
                self.message_timer = 50
            else:
                self.wave += 1
                self.message = "WAVE " + str(self.wave)
                self.message_timer = 20
                self.spawn_wave()

    def draw_background(self, lcd):
        lcd.fill_rect(0, PLAY_TOP, 160, 14, SLATE)
        for base in range(-16, 176, 24):
            bx = base - (self.scroll // 2)
            while bx < -16:
                bx += 192
            lcd.rect(bx, PLAY_TOP + 2, 14, 10, GRAY)
            lcd.fill_rect(bx + 3, PLAY_TOP + 4, 2, 2, YELLOW)
            lcd.fill_rect(bx + 8, PLAY_TOP + 4, 2, 2, YELLOW)

        lcd.fill_rect(0, PLAY_TOP + 14, 160, 18, BLUE)
        lcd.hline(0, PLAY_TOP + 14, 160, CYAN)
        lcd.hline(0, PLAY_TOP + 31, 160, WHITE)
        lcd.fill_rect(0, PLAY_TOP + 32, 160, 27, BROWN)
        for stripe in range(-20, 190, 28):
            sx = stripe - self.scroll
            while sx < -20:
                sx += 224
            lcd.fill_rect(sx, PLAY_TOP + 45, 10, 2, YELLOW)

    def draw_fighter(self, lcd, x, y, body, accent, attacking, hit, facing):
        shade = WHITE if hit else accent
        lcd.hline(x - 4, y + 2, 9, BLACK)
        lcd.ellipse(x, y - 8, 4, 4, shade, True)
        lcd.rect(x - 3, y - 2, 6, 10, body)
        lcd.vline(x - 1, y + 8, 6, shade)
        lcd.vline(x + 1, y + 8, 6, shade)
        arm_y = y + 1
        if attacking:
            if facing == 1:
                lcd.hline(x + 3, arm_y, 7, shade)
            else:
                lcd.hline(x - 9, arm_y, 7, shade)
        else:
            if facing == 1:
                lcd.hline(x - 7, arm_y, 4, shade)
                lcd.hline(x + 3, arm_y, 6, shade)
            else:
                lcd.hline(x - 8, arm_y, 6, shade)
                lcd.hline(x + 4, arm_y, 4, shade)

    def draw_scene(self, lcd):
        lcd.fill(BLACK)
        draw_header(lcd, "Rage", "W" + str(self.wave), ORANGE)
        self.draw_background(lcd)

        actors = []
        for enemy in self.enemies:
            actors.append((enemy["y"], "enemy", enemy))
        actors.append((self.player_y, "player", None))
        actors.sort(key=lambda item: item[0])

        for _, kind, payload in actors:
            if kind == "player":
                flash = self.invincible_timer > 0 and (self.invincible_timer % 4) < 2
                attacking = self.attack_timer > 0 or self.special_timer > 0
                self.draw_fighter(lcd, self.player_x, self.player_y, CYAN, WHITE, attacking, flash, self.facing)
            else:
                enemy = payload
                enemy_facing = -1 if enemy["x"] > self.player_x else 1
                self.draw_fighter(
                    lcd,
                    enemy["x"],
                    enemy["y"],
                    enemy["color"],
                    WHITE,
                    False,
                    enemy["flash"] > 0,
                    enemy_facing
                )

        for hp in range(PLAYER_HP):
            color = RED if hp < self.player_hp else GRAY
            lcd.fill_rect(4 + (hp * 8), 12, 6, 4, color)

        lcd.text("E" + str(len(self.enemies)), 118, 12, WHITE)
        lcd.text("K" + str(self.score), 138, 12, WHITE)

        if self.message_timer > 0 or self.state != "playing":
            text = self.message
            x = max(2, (160 - len(text) * 8) // 2)
            lcd.fill_rect(0, 30, 160, 12, BLACK)
            lcd.text(text, x, 32, YELLOW)

        if self.state == "playing":
            footer = "B punch"
        else:
            footer = "A restart"
        draw_footer(lcd, footer, GRAY)
        if self.state == "playing":
            lcd.text("A spin", 88, 71, GRAY)

    def step(self, runtime):
        buttons = runtime.buttons
        lcd = runtime.lcd

        if self.state == "playing":
            self.update_game(buttons)
        elif buttons.pressed("A"):
            self.reset_game()

        self.draw_scene(lcd)
        return None
