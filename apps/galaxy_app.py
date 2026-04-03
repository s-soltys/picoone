import time
try:
    import galaxy
except ImportError:
    galaxy = None

from core.display import CYAN, WHITE, YELLOW, BLACK, GRAY, GOLD
from core.controls import A_LABEL, B_LABEL, X_LABEL
from core.ui import center_x, draw_empty_state


class GalaxyApp:
    app_id = "galaxy"
    title = "Galaxy"
    accent = CYAN

    def __init__(self):
        self.state = galaxy.STATE_GALAXYSEL if galaxy is not None else 0
        self.galaxies = None
        self.sel_gal = 0
        self.systems = None
        self.cur_shape = 0
        self.uvx = 0
        self.uvy = 0
        self.vx = 0
        self.vy = 0
        self.sel_idx = 0
        self.planets = None
        self.sel_planet = 0
        self.regions = None
        self.sel_region = 0
        self.scroll_speed = 8
        self.show_splash = False
        self.splash_until = 0
        self.splash_phase = 0

    def draw_icon(self, lcd, cx, cy, selected, monochrome=False):
        if monochrome:
            ink = BLACK if selected else WHITE
            lcd.ellipse(cx, cy, 10, 6, ink, False)
            lcd.ellipse(cx, cy, 2, 2, ink, True)
            lcd.pixel(cx - 7, cy, ink)
            lcd.pixel(cx + 8, cy - 1, ink)
            return
        lcd.ellipse(cx, cy, 10, 6, CYAN, False)
        lcd.ellipse(cx, cy, 2, 2, YELLOW, True)
        lcd.pixel(cx - 7, cy, WHITE)
        lcd.pixel(cx + 8, cy - 1, WHITE)
        if selected:
            lcd.ellipse(cx, cy, 13, 9, YELLOW, False)

    def on_open(self, runtime):
        if galaxy is None:
            return
        self.show_splash = True
        self.splash_phase = time.ticks_ms()
        self.splash_until = time.ticks_add(self.splash_phase, 1100)
        self._init_world()

    def help_lines(self, runtime):
        if galaxy is None:
            return [
                "Galaxy engine missing",
                "galaxy.py is not present",
                "Restore the engine file",
                "Then reopen Galaxy",
                "Desktop and other apps still work",
            ]
        if self.state == galaxy.STATE_GALAXYSEL:
            return [
                "Galaxy selector",
                "D-pad pans the wide map",
                A_LABEL + " jumps to the next galaxy",
                B_LABEL + " enters the centered target",
                X_LABEL + " recenters the current galaxy",
            ]
        if self.state == galaxy.STATE_GALAXY:
            return [
                "Galaxy map",
                "D-pad pans between star systems",
                B_LABEL + " opens the focused system",
                A_LABEL + " returns to galaxy select",
                X_LABEL + " recenters the focused system",
            ]
        if self.state == galaxy.STATE_SYSTEM:
            return [
                "System view",
                "Left/Right picks a planet",
                B_LABEL + " lands on the planet",
                A_LABEL + " returns to the galaxy map",
                X_LABEL + " snaps back to the first planet",
            ]
        return [
            "Planet view",
            "Left/Right picks a region",
            A_LABEL + " returns to orbit",
            "Scanner details stay in the top-right",
            "Y opens contextual help",
        ]

    def _init_world(self):
        self.galaxies = galaxy.gen_galaxy_list(8)
        self.sel_gal = 0
        self.state = galaxy.STATE_GALAXYSEL
        self.systems = None
        self.cur_shape = 0
        self.vx = 0
        self.vy = 0
        self.sel_idx = 0
        self.planets = None
        self.sel_planet = 0
        self.regions = None
        self.sel_region = 0
        g = self.galaxies[0]
        self.uvx = max(0, min(galaxy.UNIV_W - galaxy.VIEW_W, g[4] - (galaxy.VIEW_W // 2)))
        self.uvy = max(0, min(galaxy.UNIV_H - galaxy.VIEW_H, g[5] - (galaxy.VIEW_H // 2)))

    def _draw_splash(self, lcd):
        tick = time.ticks_ms()
        lcd.fill(BLACK)
        galaxy.draw_parallax_space(lcd, (tick // 5) % 900, (tick // 8) % 700)
        galaxy._draw_mini_galaxy(lcd, 56, 116, 0, CYAN, False)
        galaxy._draw_mini_galaxy(lcd, 120, 86, 1, GOLD, False)
        galaxy._draw_mini_galaxy(lcd, 184, 126, 4, YELLOW, False)
        lcd.text("GALAXY", center_x("GALAXY", galaxy.VIEW_W), 40, CYAN)
        lcd.text("EXPLORER", center_x("EXPLORER", galaxy.VIEW_W), 64, WHITE)
        lcd.text("Wide-scan mode", center_x("Wide-scan mode", galaxy.VIEW_W), 166, GRAY)
        hint = "Press any button"
        lcd.text(hint, center_x(hint, galaxy.VIEW_W), 188, YELLOW)

    def step(self, runtime):
        buttons = runtime.buttons
        lcd = runtime.lcd

        if galaxy is None:
            draw_empty_state(
                lcd,
                "Galaxy",
                [
                    "Galaxy engine missing",
                    "Restore galaxy.py",
                    "Then reopen this app",
                ],
                accent=CYAN,
                footer="",
            )
            return None

        if self.show_splash:
            self._draw_splash(lcd)
            if (buttons.any_pressed() or buttons.any_down()
                    or time.ticks_diff(time.ticks_ms(), self.splash_until) >= 0):
                self.show_splash = False
            return None

        if self.state == galaxy.STATE_GALAXYSEL:
            if buttons.down("UP"):
                self.uvy = max(0, self.uvy - self.scroll_speed)
            if buttons.down("DOWN"):
                self.uvy = min(galaxy.UNIV_H - galaxy.VIEW_H, self.uvy + self.scroll_speed)
            if buttons.down("LEFT"):
                self.uvx = max(0, self.uvx - self.scroll_speed)
            if buttons.down("RIGHT"):
                self.uvx = min(galaxy.UNIV_W - galaxy.VIEW_W, self.uvx + self.scroll_speed)
            if buttons.pressed("A"):
                self.sel_gal = (self.sel_gal + 1) % len(self.galaxies)
                entry = self.galaxies[self.sel_gal]
                self.uvx = max(0, min(galaxy.UNIV_W - galaxy.VIEW_W, entry[4] - (galaxy.VIEW_W // 2)))
                self.uvy = max(0, min(galaxy.UNIV_H - galaxy.VIEW_H, entry[5] - (galaxy.VIEW_H // 2)))
            if buttons.pressed("X") and self.sel_gal >= 0:
                entry = self.galaxies[self.sel_gal]
                self.uvx = max(0, min(galaxy.UNIV_W - galaxy.VIEW_W, entry[4] - (galaxy.VIEW_W // 2)))
                self.uvy = max(0, min(galaxy.UNIV_H - galaxy.VIEW_H, entry[5] - (galaxy.VIEW_H // 2)))
            if buttons.pressed("B"):
                self.sel_gal = galaxy.find_nearest_gal(self.galaxies, self.uvx, self.uvy)
                if self.sel_gal >= 0:
                    entry = self.galaxies[self.sel_gal]
                    self.cur_shape = entry[2]
                    self.systems = galaxy.gen_galaxy(entry[0], self.cur_shape)
                    self.vx = max(0, min(galaxy.WORLD_W - galaxy.VIEW_W, self.systems[0][0] - (galaxy.VIEW_W // 2)))
                    self.vy = max(0, min(galaxy.WORLD_H - galaxy.VIEW_H, self.systems[0][1] - (galaxy.VIEW_H // 2)))
                    self.sel_idx = 0
                    self.state = galaxy.STATE_GALAXY
            self.sel_gal = galaxy.find_nearest_gal(self.galaxies, self.uvx, self.uvy)
            galaxy.draw_galaxy_sel(lcd, self.galaxies, self.uvx, self.uvy, self.sel_gal)
            return None

        if self.state == galaxy.STATE_GALAXY:
            if buttons.down("UP"):
                self.vy = max(0, self.vy - self.scroll_speed)
            if buttons.down("DOWN"):
                self.vy = min(galaxy.WORLD_H - galaxy.VIEW_H, self.vy + self.scroll_speed)
            if buttons.down("LEFT"):
                self.vx = max(0, self.vx - self.scroll_speed)
            if buttons.down("RIGHT"):
                self.vx = min(galaxy.WORLD_W - galaxy.VIEW_W, self.vx + self.scroll_speed)
            if buttons.pressed("B"):
                self.sel_idx = galaxy.find_nearest(self.systems, self.vx, self.vy)
                if self.sel_idx >= 0:
                    self.planets = galaxy.gen_planets(self.systems[self.sel_idx])
                    self.sel_planet = 0
                    self.state = galaxy.STATE_SYSTEM
            if buttons.pressed("X") and self.sel_idx >= 0:
                system = self.systems[self.sel_idx]
                self.vx = max(0, min(galaxy.WORLD_W - galaxy.VIEW_W, system[0] - (galaxy.VIEW_W // 2)))
                self.vy = max(0, min(galaxy.WORLD_H - galaxy.VIEW_H, system[1] - (galaxy.VIEW_H // 2)))
            if buttons.pressed("A"):
                self.state = galaxy.STATE_GALAXYSEL
            self.sel_idx = galaxy.find_nearest(self.systems, self.vx, self.vy)
            galaxy.draw_galaxy(lcd, self.systems, self.vx, self.vy, self.sel_idx)
            return None

        if self.state == galaxy.STATE_SYSTEM:
            if buttons.repeat("LEFT", 180, 120):
                self.sel_planet = (self.sel_planet - 1) % len(self.planets)
            if buttons.repeat("RIGHT", 180, 120):
                self.sel_planet = (self.sel_planet + 1) % len(self.planets)
            if buttons.pressed("B"):
                self.regions = galaxy.gen_regions(self.planets[self.sel_planet])
                self.sel_region = 0
                self.state = galaxy.STATE_PLANET
            if buttons.pressed("X"):
                self.sel_planet = 0
            if buttons.pressed("A"):
                self.state = galaxy.STATE_GALAXY

            for planet in self.planets:
                planet[5] += planet[6]
                if planet[5] > 6.283:
                    planet[5] -= 6.283

            galaxy.draw_system(lcd, self.systems[self.sel_idx], self.planets, self.sel_planet)
            return None

        if buttons.repeat("LEFT", 180, 120):
            self.sel_region = (self.sel_region - 1) % len(self.regions)
        if buttons.repeat("RIGHT", 180, 120):
            self.sel_region = (self.sel_region + 1) % len(self.regions)
        if buttons.pressed("A"):
            self.state = galaxy.STATE_SYSTEM

        galaxy.draw_planet(lcd, self.planets[self.sel_planet], self.regions, self.sel_region)
        return None
