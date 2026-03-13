from machine import Pin
import time
import math
import random
from lcd import (LCD_0inch96, RED, GREEN, BLUE, WHITE, BLACK,
                 YELLOW, CYAN, GRAY, ORANGE, PINK, DKRED)

# --- States ---
STATE_GALAXYSEL = 0
STATE_GALAXY = 1
STATE_SYSTEM = 2

# --- World size (virtual galaxy map) ---
WORLD_W = 640
WORLD_H = 320

# --- Name generation ---
# Star/system naming: catalog-style scientific designations
_CAT = ["NGC","HD","GJ","HR","TYC","KIC","KOI","PSR","TOI","HIP",
        "SAO","LHS","HAT","XO","WASP","2MASS","V838","UGC","IC","Mrk"]
_GRK = ["Alpha","Beta","Gamma","Delta","Theta","Sigma","Omega","Zeta",
        "Kappa","Lambda","Epsilon","Pi","Upsilon","Xi","Chi"]
_CON = ["Cygni","Lyrae","Draconis","Centauri","Eridani","Pavonis",
        "Aquilae","Tauri","Andromedae","Orionis","Pegasi","Arietis",
        "Virginis","Scorpii","Leonis","Hydrae","Crucis","Velorum"]
_PRE = ["Zan","Kry","Vel","Tor","Neb","Pha","Xen","Ori",
        "Lyr","Dra","Cas","Eri","Pul","Sig","Ald","Rig",
        "Ara","Cep","Vol","Cor","Thr","Hex","Syn","Nym"]
_SUF = ["th","ra","nis","tus","ris","lon","tex","pia",
        "mos","vus","nex","cor","das","kas","ion","eos",
        "ium","ari","ux","oth","ael","yn"]

def gen_name(seed):
    random.seed(seed)
    style = random.randint(0, 7)
    if style == 0:
        return _CAT[random.randint(0, len(_CAT)-1)] + " " + str(random.randint(100, 9999))
    elif style == 1:
        return _GRK[random.randint(0, len(_GRK)-1)] + " " + _CON[random.randint(0, len(_CON)-1)]
    elif style == 2:
        return "J" + str(random.randint(1000, 9999)) + "+" + str(random.randint(10, 99))
    elif style == 3:
        return _PRE[random.randint(0, len(_PRE)-1)] + _SUF[random.randint(0, len(_SUF)-1)] + "-" + str(random.randint(1, 99))
    elif style == 4:
        return _PRE[random.randint(0, len(_PRE)-1)] + _SUF[random.randint(0, len(_SUF)-1)]
    elif style == 5:
        # double catalog: "WASP-12 / HD 4091"
        return _CAT[random.randint(0, len(_CAT)-1)] + "-" + str(random.randint(1, 200))
    elif style == 6:
        # constellation + number: "Orionis V-42"
        return _CON[random.randint(0, len(_CON)-1)] + " V" + str(random.randint(1, 99))
    else:
        # two syllables: "Xendas Korion"
        return _PRE[random.randint(0, len(_PRE)-1)] + _SUF[random.randint(0, len(_SUF)-1)] + " " + _PRE[random.randint(0, len(_PRE)-1)] + _SUF[random.randint(0, len(_SUF)-1)]

# Planet naming: independent from system
_PCAT = ["Kepler","Gliese","Proxima","Trappist","Ross","Wolf",
         "Barnard","Luyten","Teegarden","Lacaille"]
_PSUF = ["prime","major","minor","nova","terra","mara","haven",
         "forge","reach","drift","vale","deep"]
_PPRE = ["Ax","Ze","Io","Mu","Rho","Tau","Nu","Phi","Eta","Psi",
         "Sol","Lux","Vex","Nyx","Arx","Dex"]

def gen_planet_name(seed):
    random.seed(seed)
    style = random.randint(0, 5)
    if style == 0:
        return _PCAT[random.randint(0, len(_PCAT)-1)] + "-" + str(random.randint(10, 999)) + chr(random.randint(98, 103))
    elif style == 1:
        return _PPRE[random.randint(0, len(_PPRE)-1)] + " " + _PSUF[random.randint(0, len(_PSUF)-1)]
    elif style == 2:
        return "P-" + str(random.randint(1000, 9999))
    elif style == 3:
        return _PPRE[random.randint(0, len(_PPRE)-1)] + " " + _CON[random.randint(0, len(_CON)-1)][:5] + " " + chr(random.randint(98, 102))
    elif style == 4:
        # catalog dash letter: "HAT-274f"
        return _CAT[random.randint(0, len(_CAT)-1)] + "-" + str(random.randint(10, 999)) + chr(random.randint(98, 104))
    else:
        # two-part name: "Nyx Korion"
        return _PPRE[random.randint(0, len(_PPRE)-1)] + " " + _PRE[random.randint(0, len(_PRE)-1)] + _SUF[random.randint(0, len(_SUF)-1)]

# Galaxy naming & shape types
# shape: 0=spiral, 1=barred, 2=elliptical, 3=dwarf, 4=ring, 5=irregular-h, 6=irregular-v
_GTYPE = ["Spiral","Barred","Elliptical","Dwarf","Ring","Irregular","Irregular"]
_GCOLORS = [CYAN, YELLOW, ORANGE, WHITE, PINK, GREEN, CYAN]

def gen_galaxy_info(seed):
    random.seed(seed)
    shape = random.randint(0, 6)
    color = _GCOLORS[shape]
    style = random.randint(0, 3)
    if style == 0:
        name = _GTYPE[shape] + " " + _CAT[random.randint(0, len(_CAT)-1)] + "-" + str(random.randint(10, 999))
    elif style == 1:
        name = _PRE[random.randint(0, len(_PRE)-1)] + _SUF[random.randint(0, len(_SUF)-1)] + " " + _GTYPE[shape]
    elif style == 2:
        name = _CAT[random.randint(0, len(_CAT)-1)] + " " + str(random.randint(100, 9999))
    else:
        name = _GRK[random.randint(0, len(_GRK)-1)] + " " + _GTYPE[shape]
    return (seed, name, shape, color)

# --- Galaxy generation ---
_STAR_COLORS = [YELLOW, ORANGE, WHITE, CYAN, RED]

def _place_spiral(cx, cy, r, angle_off, random):
    a = random.randint(0, 628) / 100.0 + angle_off
    d = random.randint(20, r)
    spread = d * 0.3
    x = int(cx + d * math.cos(a) + random.randint(-int(spread), int(spread)))
    y = int(cy + (d * math.sin(a)) // 2 + random.randint(-int(spread)//2, int(spread)//2))
    return x, y

def gen_galaxy(seed, shape=0):
    random.seed(seed)
    systems = []
    attempts = 0
    count = random.randint(16, 22)
    cx = WORLD_W // 2
    cy = WORLD_H // 2
    while len(systems) < count and attempts < 400:
        attempts += 1
        if shape == 0:  # spiral
            arm = attempts % 2
            x, y = _place_spiral(cx, cy, 140, arm * 3.14, random)
        elif shape == 1:  # barred spiral
            if random.randint(0, 2) == 0:
                x = cx + random.randint(-80, 80)
                y = cy + random.randint(-10, 10)
            else:
                x, y = _place_spiral(cx, cy, 130, (attempts % 2) * 3.14, random)
        elif shape == 2:  # elliptical
            a = random.randint(0, 628) / 100.0
            d = random.randint(15, 120)
            x = int(cx + d * math.cos(a))
            y = int(cy + (d * math.sin(a)) // 2)
        elif shape == 3:  # dwarf (compact cluster)
            a = random.randint(0, 628) / 100.0
            d = random.randint(10, 70)
            x = int(cx + d * math.cos(a))
            y = int(cy + d * math.sin(a) // 2)
        elif shape == 4:  # ring
            a = random.randint(0, 628) / 100.0
            d = random.randint(80, 130)
            x = int(cx + d * math.cos(a))
            y = int(cy + (d * math.sin(a)) // 2)
        elif shape == 5:  # irregular horizontal
            x = cx + random.randint(-200, 200)
            y = cy + random.randint(-40, 40)
            x += random.randint(-30, 30)
            y += random.randint(-20, 20)
        else:  # irregular vertical
            x = cx + random.randint(-60, 60)
            y = cy + random.randint(-130, 130)
            x += random.randint(-25, 25)
            y += random.randint(-20, 20)
        x = max(20, min(WORLD_W - 20, x))
        y = max(20, min(WORLD_H - 20, y))
        too_close = False
        for s in systems:
            dx = x - s[0]
            dy = y - s[1]
            if dx*dx + dy*dy < 1600:  # 40px min distance (denser)
                too_close = True
                break
        if too_close:
            continue
        sseed = random.randint(0, 65535)
        name = gen_name(sseed)
        color = _STAR_COLORS[random.randint(0, len(_STAR_COLORS)-1)]
        size = random.randint(2, 4)
        systems.append((x, y, sseed, name, color, size))
    return systems

# --- Planet generation for a solar system ---
_PLANET_COLORS = [RED, GREEN, BLUE, CYAN, ORANGE, PINK, WHITE, YELLOW]

def gen_planets(system):
    sseed = system[2]
    random.seed(sseed + 1000)
    n = random.randint(3, 5)
    planets = []
    for i in range(n):
        orbit_rx = 18 + i * 14
        orbit_ry = 9 + i * 7
        size = random.randint(1, 3)
        color = _PLANET_COLORS[random.randint(0, len(_PLANET_COLORS)-1)]
        pseed = sseed * 100 + i + 7
        pname = gen_planet_name(pseed)
        random.seed(sseed + 1000 + (i + 1) * 31)  # restore sequence
        angle = random.randint(0, 628) / 100.0
        speed = 0.08 / (1 + i * 0.5)
        planets.append([orbit_rx, orbit_ry, size, color, pname, angle, speed])
    return planets

# --- Galaxy list generation ---
def gen_galaxy_list(count=6):
    galaxies = []
    for i in range(count):
        gseed = (i + 1) * 7741
        galaxies.append(gen_galaxy_info(gseed))
    return galaxies

# --- Background stars (deterministic, no storage) ---
def draw_bg_stars(lcd, vx, vy):
    # draw sparse deterministic dots in 20x20 cells
    cell = 20
    cx0 = vx // cell
    cy0 = vy // cell
    for ci in range(9):  # 160/20 + 1
        for cj in range(5):  # 80/20 + 1
            cx = cx0 + ci
            cy = cy0 + cj
            h = (cx * 7919 + cy * 6271) & 0xFFFF
            # 2-3 stars per cell
            for k in range(2):
                hk = (h * (k + 1) + 3571) & 0xFFFF
                if hk % 5 == 0:  # ~20% chance
                    sx = (hk >> 3) % cell
                    sy = (hk >> 8) % cell
                    wx = cx * cell + sx
                    wy = cy * cell + sy
                    px = wx - vx
                    py = wy - vy
                    if 0 <= px < 160 and 0 <= py < 80:
                        # dim or bright based on hash
                        c = WHITE if hk % 7 == 0 else GRAY
                        lcd.pixel(px, py, c)

# --- Find nearest system to viewport center ---
def find_nearest(systems, vx, vy):
    cx = vx + 80
    cy = vy + 40
    best = -1
    best_d = 999999
    for i in range(len(systems)):
        s = systems[i]
        dx = s[0] - cx
        dy = s[1] - cy
        d = dx*dx + dy*dy
        if d < best_d:
            best_d = d
            best = i
    return best

# --- Draw galaxy map ---
def draw_galaxy(lcd, systems, vx, vy, sel_idx):
    lcd.fill(BLACK)
    draw_bg_stars(lcd, vx, vy)

    # draw systems
    for i in range(len(systems)):
        s = systems[i]
        sx = s[0] - vx
        sy = s[1] - vy
        if -10 <= sx < 170 and -10 <= sy < 90:
            lcd.ellipse(sx, sy, s[5], s[5], s[4], True)
            if i == sel_idx:
                # selection ring
                lcd.ellipse(sx, sy, s[5]+3, s[5]+3, WHITE, False)

    # show selected system name at top
    if sel_idx >= 0:
        s = systems[sel_idx]
        name = s[3]
        if len(name) > 19:
            name = name[:19]
        tx = (160 - len(name) * 8) // 2
        if tx < 1:
            tx = 1
        lcd.fill_rect(0, 0, 160, 10, BLACK)
        lcd.text(name, tx, 1, YELLOW)

# --- Draw solar system view ---
def draw_system(lcd, system, planets, sel_planet):
    lcd.fill(BLACK)

    # background stars (static, use system seed)
    random.seed(system[2] + 5000)
    for _ in range(30):
        px = random.randint(0, 159)
        py = random.randint(0, 79)
        lcd.pixel(px, py, GRAY)

    sun_color = system[4]
    sun_r = system[5] + 3

    # draw orbits
    for p in planets:
        lcd.ellipse(80, 40, p[0], p[1], GRAY, False)

    # draw sun
    lcd.ellipse(80, 40, sun_r, sun_r, sun_color, True)
    lcd.ellipse(80, 40, sun_r - 1, sun_r - 1, YELLOW, True)

    # draw planets
    for i in range(len(planets)):
        p = planets[i]
        px = 80 + int(p[0] * math.cos(p[5]))
        py = 40 + int(p[1] * math.sin(p[5]))
        px = max(0, min(159, px))
        py = max(0, min(79, py))
        lcd.ellipse(px, py, p[2], p[2], p[3], True)
        if i == sel_planet:
            lcd.ellipse(px, py, p[2]+2, p[2]+2, WHITE, False)

    # system name at top
    name = system[3]
    if len(name) > 19:
        name = name[:19]
    tx = (160 - len(name) * 8) // 2
    if tx < 1:
        tx = 1
    lcd.fill_rect(0, 0, 160, 10, BLACK)
    lcd.text(name, tx, 1, YELLOW)

    # planet name at bottom
    if 0 <= sel_planet < len(planets):
        pname = planets[sel_planet][4]
        if len(pname) > 19:
            pname = pname[:19]
        ptx = (160 - len(pname) * 8) // 2
        if ptx < 1:
            ptx = 1
        lcd.fill_rect(0, 69, 160, 11, BLACK)
        lcd.text(pname, ptx, 70, GREEN)

# --- Draw a mini galaxy shape at given center ---
def _draw_mini_galaxy(lcd, cx, cy, shape, color, sel):
    random.seed(shape * 1000 + cx + cy)
    c2 = GRAY
    if shape == 0:  # spiral
        for arm in range(2):
            for j in range(8):
                a = arm * 3.14 + j * 0.5
                d = 4 + j * 2.5
                px = int(cx + d * math.cos(a))
                py = int(cy + d * math.sin(a) * 0.5)
                if 0 <= px < 160 and 0 <= py < 80:
                    lcd.pixel(px, py, color)
                    if j > 2:
                        lcd.pixel(px+1, py, c2)
    elif shape == 1:  # barred
        lcd.hline(cx - 8, cy, 17, c2)
        for arm in range(2):
            for j in range(5):
                a = arm * 3.14 + j * 0.6
                d = 8 + j * 2.5
                px = int(cx + d * math.cos(a))
                py = int(cy + d * math.sin(a) * 0.5)
                if 0 <= px < 160 and 0 <= py < 80:
                    lcd.pixel(px, py, color)
    elif shape == 2:  # elliptical
        lcd.ellipse(cx, cy, 14, 8, c2, False)
        lcd.ellipse(cx, cy, 8, 5, color, False)
        lcd.ellipse(cx, cy, 3, 2, color, True)
    elif shape == 3:  # dwarf
        lcd.ellipse(cx, cy, 6, 6, c2, False)
        for _ in range(10):
            px = cx + random.randint(-5, 5)
            py = cy + random.randint(-5, 5)
            if 0 <= px < 160 and 0 <= py < 80:
                lcd.pixel(px, py, color)
    else:  # ring
        lcd.ellipse(cx, cy, 14, 8, color, False)
        lcd.ellipse(cx, cy, 13, 7, c2, False)
        lcd.ellipse(cx, cy, 2, 2, color, True)
    if shape == 5:  # irregular horizontal
        for _ in range(14):
            px = cx + random.randint(-16, 16)
            py = cy + random.randint(-4, 4)
            if 0 <= px < 160 and 0 <= py < 80:
                lcd.pixel(px, py, color)
        for _ in range(5):
            px = cx + random.randint(-12, 12)
            py = cy + random.randint(-6, 6)
            if 0 <= px < 160 and 0 <= py < 80:
                lcd.pixel(px, py, c2)
    elif shape == 6:  # irregular vertical
        for _ in range(14):
            px = cx + random.randint(-5, 5)
            py = cy + random.randint(-12, 12)
            if 0 <= px < 160 and 0 <= py < 80:
                lcd.pixel(px, py, color)
        for _ in range(5):
            px = cx + random.randint(-7, 7)
            py = cy + random.randint(-10, 10)
            if 0 <= px < 160 and 0 <= py < 80:
                lcd.pixel(px, py, c2)
    if sel:
        lcd.ellipse(cx, cy, 18, 14, WHITE, False)

# --- Draw galaxy selector ---
def draw_galaxy_sel(lcd, galaxies, sel_gal):
    lcd.fill(BLACK)
    # background stars
    random.seed(999)
    for _ in range(25):
        lcd.pixel(random.randint(0, 159), random.randint(0, 79), GRAY)

    g = galaxies[sel_gal]
    # draw selected galaxy large in center
    _draw_mini_galaxy(lcd, 80, 38, g[2], g[3], True)

    # draw prev/next small on sides
    if len(galaxies) > 1:
        pi = (sel_gal - 1) % len(galaxies)
        ni = (sel_gal + 1) % len(galaxies)
        _draw_mini_galaxy(lcd, 22, 38, galaxies[pi][2], GRAY, False)
        _draw_mini_galaxy(lcd, 138, 38, galaxies[ni][2], GRAY, False)

    # name at top
    name = g[1]
    if len(name) > 19:
        name = name[:19]
    tx = (160 - len(name) * 8) // 2
    if tx < 1:
        tx = 1
    lcd.fill_rect(0, 0, 160, 10, BLACK)
    lcd.text(name, tx, 1, YELLOW)

# --- Main entry point ---
def run():
    lcd = LCD_0inch96()

    # splash screen
    lcd.fill(BLACK)
    lcd.text("GALAXY", 48, 20, CYAN)
    lcd.text("EXPLORER", 40, 36, YELLOW)
    lcd.text("Press any key", 20, 60, GRAY)
    lcd.display()

    # inputs
    KEY_UP = Pin(2, Pin.IN, Pin.PULL_UP)
    KEY_DOWN = Pin(18, Pin.IN, Pin.PULL_UP)
    KEY_LEFT = Pin(16, Pin.IN, Pin.PULL_UP)
    KEY_RIGHT = Pin(20, Pin.IN, Pin.PULL_UP)
    KEY_CTRL = Pin(3, Pin.IN, Pin.PULL_UP)
    KEY_A = Pin(15, Pin.IN, Pin.PULL_UP)
    KEY_B = Pin(17, Pin.IN, Pin.PULL_UP)

    # wait for any key
    while (KEY_UP.value() and KEY_DOWN.value() and KEY_LEFT.value()
           and KEY_RIGHT.value() and KEY_CTRL.value()
           and KEY_A.value() and KEY_B.value()):
        time.sleep(0.05)
    time.sleep(0.2)

    # generate galaxy list
    galaxies = gen_galaxy_list(6)
    sel_gal = 0
    state = STATE_GALAXYSEL
    systems = None
    cur_shape = 0
    vx = 0
    vy = 0
    sel_idx = 0
    planets = None
    sel_planet = 0
    scroll_speed = 4

    while True:
        if state == STATE_GALAXYSEL:
            # --- Galaxy selector controls (L/R to browse) ---
            if KEY_LEFT.value() == 0:
                sel_gal = (sel_gal - 1) % len(galaxies)
                time.sleep(0.15)
            if KEY_RIGHT.value() == 0:
                sel_gal = (sel_gal + 1) % len(galaxies)
                time.sleep(0.15)

            # CTRL: regenerate galaxy list with new seed
            if KEY_CTRL.value() == 0:
                new_base = random.randint(0, 65535)
                galaxies = []
                for i in range(6):
                    gseed = new_base + (i + 1) * 7741
                    galaxies.append(gen_galaxy_info(gseed))
                sel_gal = 0
                time.sleep(0.2)

            # B: enter selected galaxy
            if KEY_B.value() == 0:
                g = galaxies[sel_gal]
                cur_shape = g[2]
                systems = gen_galaxy(g[0], cur_shape)
                vx = max(0, min(WORLD_W - 160, systems[0][0] - 80))
                vy = max(0, min(WORLD_H - 80, systems[0][1] - 40))
                sel_idx = 0
                state = STATE_GALAXY
                time.sleep(0.2)

            draw_galaxy_sel(lcd, galaxies, sel_gal)

        elif state == STATE_GALAXY:
            # --- Galaxy map controls ---
            if KEY_UP.value() == 0:
                vy = max(0, vy - scroll_speed)
            if KEY_DOWN.value() == 0:
                vy = min(WORLD_H - 80, vy + scroll_speed)
            if KEY_LEFT.value() == 0:
                vx = max(0, vx - scroll_speed)
            if KEY_RIGHT.value() == 0:
                vx = min(WORLD_W - 160, vx + scroll_speed)

            # CTRL: jump to next system
            if KEY_CTRL.value() == 0:
                sel_idx = (sel_idx + 1) % len(systems)
                s = systems[sel_idx]
                vx = max(0, min(WORLD_W - 160, s[0] - 80))
                vy = max(0, min(WORLD_H - 80, s[1] - 40))
                time.sleep(0.2)

            # B: zoom into selected system
            if KEY_B.value() == 0:
                sel_idx = find_nearest(systems, vx, vy)
                if sel_idx >= 0:
                    planets = gen_planets(systems[sel_idx])
                    sel_planet = 0
                    state = STATE_SYSTEM
                    time.sleep(0.2)

            # A: back to galaxy selector
            if KEY_A.value() == 0:
                state = STATE_GALAXYSEL
                time.sleep(0.2)

            sel_idx = find_nearest(systems, vx, vy)
            draw_galaxy(lcd, systems, vx, vy, sel_idx)

        elif state == STATE_SYSTEM:
            # --- Solar system controls ---
            if KEY_LEFT.value() == 0:
                sel_planet = (sel_planet - 1) % len(planets)
                time.sleep(0.15)
            if KEY_RIGHT.value() == 0:
                sel_planet = (sel_planet + 1) % len(planets)
                time.sleep(0.15)

            # A: back to galaxy
            if KEY_A.value() == 0:
                state = STATE_GALAXY
                time.sleep(0.2)

            # animate planets
            for p in planets:
                p[5] += p[6]
                if p[5] > 6.283:
                    p[5] -= 6.283

            draw_system(lcd, systems[sel_idx], planets, sel_planet)

        lcd.display()
        time.sleep(0.03)

if __name__ == '__main__':
    run()
