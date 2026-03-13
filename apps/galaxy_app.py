import galaxy

from lcd import CYAN, WHITE, YELLOW


class GalaxyApp:
    app_id = "galaxy"
    title = "Galaxy"
    accent = CYAN

    def __init__(self):
        self.state = galaxy.STATE_GALAXYSEL
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
        self.scroll_speed = 4

    def draw_icon(self, lcd, cx, cy, selected):
        lcd.ellipse(cx, cy, 10, 6, CYAN, False)
        lcd.ellipse(cx, cy, 2, 2, YELLOW, True)
        lcd.pixel(cx - 7, cy, WHITE)
        lcd.pixel(cx + 8, cy - 1, WHITE)
        if selected:
            lcd.ellipse(cx, cy, 13, 9, YELLOW, False)

    def on_open(self, runtime):
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
        self.uvx = max(0, min(galaxy.UNIV_W - 160, g[4] - 80))
        self.uvy = max(0, min(galaxy.UNIV_H - 80, g[5] - 40))

    def step(self, runtime):
        buttons = runtime.buttons
        lcd = runtime.lcd

        if self.state == galaxy.STATE_GALAXYSEL:
            if buttons.down("UP"):
                self.uvy = max(0, self.uvy - self.scroll_speed)
            if buttons.down("DOWN"):
                self.uvy = min(galaxy.UNIV_H - 80, self.uvy + self.scroll_speed)
            if buttons.down("LEFT"):
                self.uvx = max(0, self.uvx - self.scroll_speed)
            if buttons.down("RIGHT"):
                self.uvx = min(galaxy.UNIV_W - 160, self.uvx + self.scroll_speed)
            if buttons.pressed("CTRL"):
                self.sel_gal = (self.sel_gal + 1) % len(self.galaxies)
                entry = self.galaxies[self.sel_gal]
                self.uvx = max(0, min(galaxy.UNIV_W - 160, entry[4] - 80))
                self.uvy = max(0, min(galaxy.UNIV_H - 80, entry[5] - 40))
            if buttons.pressed("B"):
                self.sel_gal = galaxy.find_nearest_gal(self.galaxies, self.uvx, self.uvy)
                if self.sel_gal >= 0:
                    entry = self.galaxies[self.sel_gal]
                    self.cur_shape = entry[2]
                    self.systems = galaxy.gen_galaxy(entry[0], self.cur_shape)
                    self.vx = max(0, min(galaxy.WORLD_W - 160, self.systems[0][0] - 80))
                    self.vy = max(0, min(galaxy.WORLD_H - 80, self.systems[0][1] - 40))
                    self.sel_idx = 0
                    self.state = galaxy.STATE_GALAXY
            self.sel_gal = galaxy.find_nearest_gal(self.galaxies, self.uvx, self.uvy)
            galaxy.draw_galaxy_sel(lcd, self.galaxies, self.uvx, self.uvy, self.sel_gal)
            return None

        if self.state == galaxy.STATE_GALAXY:
            if buttons.down("UP"):
                self.vy = max(0, self.vy - self.scroll_speed)
            if buttons.down("DOWN"):
                self.vy = min(galaxy.WORLD_H - 80, self.vy + self.scroll_speed)
            if buttons.down("LEFT"):
                self.vx = max(0, self.vx - self.scroll_speed)
            if buttons.down("RIGHT"):
                self.vx = min(galaxy.WORLD_W - 160, self.vx + self.scroll_speed)
            if buttons.pressed("CTRL"):
                self.sel_idx = (self.sel_idx + 1) % len(self.systems)
                system = self.systems[self.sel_idx]
                self.vx = max(0, min(galaxy.WORLD_W - 160, system[0] - 80))
                self.vy = max(0, min(galaxy.WORLD_H - 80, system[1] - 40))
            if buttons.pressed("B"):
                self.sel_idx = galaxy.find_nearest(self.systems, self.vx, self.vy)
                if self.sel_idx >= 0:
                    self.planets = galaxy.gen_planets(self.systems[self.sel_idx])
                    self.sel_planet = 0
                    self.state = galaxy.STATE_SYSTEM
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
