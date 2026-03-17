from machine import Pin
import time
import math
import random
from core.controls import BUTTON_PINS, A_LABEL, B_LABEL
from core.ui import fit_text, center_x, right_x
from core.display import (LCD, SCREEN_W, SCREEN_H, RED, GREEN, BLUE, WHITE, BLACK,
                          YELLOW, CYAN, GRAY, ORANGE, PINK, DKRED,
                          PURPLE, TEAL, RUST, CRIMSON, BROWN, GOLD, SLATE,
                          INDIGO, MARINE, AMBER, OLIVE, MAROON, COPPER, SAND)

# --- States ---
STATE_GALAXYSEL = 0
STATE_GALAXY = 1
STATE_SYSTEM = 2
STATE_PLANET = 3

# --- World sizes ---
VIEW_W = SCREEN_W
VIEW_H = SCREEN_H
UNIV_W = max(VIEW_W + 120, 360)
UNIV_H = max(VIEW_H + 80, 320)
WORLD_W = max(VIEW_W * 4, 960)
WORLD_H = max(VIEW_H * 3, 720)
TITLE_BAR_H = 18
FOOTER_BAR_H = 16
SYSTEM_HUD_H = 78
PLANET_HUD_H = 86
PLANET_RENDER_RADIUS = 62

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
_GCOLORS = [MARINE, GOLD, AMBER, SLATE, PURPLE, TEAL, COPPER]

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
_PLANET_COLORS = [RED, CRIMSON, TEAL, BLUE, RUST, PURPLE, BROWN, GOLD,
                  ORANGE, SLATE, MAROON, DKRED, OLIVE, INDIGO, COPPER, AMBER]

_ATMO = ["None","Thin","Dense","Toxic","H2/He","N2/O2","CO2","CH4"]
_PTYPE = ["Rocky","Gas","Ice","Lava","Ocean","Desert"]

def gen_planets(system):
    sseed = system[2]
    random.seed(sseed + 1000)
    n = random.randint(3, 5)
    planets = []
    for i in range(n):
        orbit_rx = 12 + i * 10  # tighter for left panel
        orbit_ry = 8 + i * 6
        size = random.randint(1, 3)
        color = _PLANET_COLORS[random.randint(0, len(_PLANET_COLORS)-1)]
        pseed = sseed * 100 + i + 7
        pname = gen_planet_name(pseed)
        random.seed(sseed + 1000 + (i + 1) * 31)
        angle = random.randint(0, 628) / 100.0
        speed = 0.08 / (1 + i * 0.5)
        # datapoints
        mass = random.randint(1, 500)  # x Earth mass (0.1-50.0)
        temp = random.randint(-200, 800)  # surface temp C
        radius = random.randint(3, 150)  # x0.1 Earth radii (0.3-15.0)
        atmo = _ATMO[random.randint(0, len(_ATMO)-1)]
        ptype = _PTYPE[random.randint(0, len(_PTYPE)-1)]
        planets.append([orbit_rx, orbit_ry, size, color, pname, angle, speed,
                        mass, temp, radius, atmo, ptype])
    return planets

# --- Galaxy list generation (placed in 2D universe) ---
def gen_galaxy_list(count=8):
    random.seed(time.ticks_ms())
    galaxies = []
    attempts = 0
    while len(galaxies) < count and attempts < 300:
        attempts += 1
        x = random.randint(25, UNIV_W - 25)
        y = random.randint(25, UNIV_H - 25)
        too_close = False
        for g in galaxies:
            dx = x - g[4]
            dy = y - g[5]
            if dx*dx + dy*dy < 1600:  # 40px min
                too_close = True
                break
        if too_close:
            continue
        gseed = (len(galaxies) + 1) * 7741 + attempts
        info = gen_galaxy_info(gseed)
        # append (seed, name, shape, color, wx, wy)
        galaxies.append((info[0], info[1], info[2], info[3], x, y))
    return galaxies

# --- Background stars (deterministic, no storage) ---
def draw_bg_stars(lcd, vx, vy):
    # draw sparse deterministic dots in 20x20 cells
    cell = 20
    cx0 = vx // cell
    cy0 = vy // cell
    for ci in range((VIEW_W // cell) + 2):
        for cj in range((VIEW_H // cell) + 2):
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
                    if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                        # dim or bright based on hash
                        c = WHITE if hk % 7 == 0 else GRAY
                        lcd.pixel(px, py, c)


def _draw_star_layer(lcd, vx, vy, cell, seed_off, chance_mod, color):
    cx0 = vx // cell
    cy0 = vy // cell
    for ci in range((VIEW_W // cell) + 2):
        for cj in range((VIEW_H // cell) + 2):
            cx = cx0 + ci
            cy = cy0 + cj
            h = ((cx + seed_off) * 4253 + (cy + seed_off) * 7103) & 0xFFFF
            if h % chance_mod != 0:
                continue
            sx = (h >> 3) % cell
            sy = (h >> 9) % cell
            px = (cx * cell + sx) - vx
            py = (cy * cell + sy) - vy
            if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                lcd.pixel(px, py, WHITE if h % 17 == 0 else color)


def draw_parallax_space(lcd, vx, vy):
    _draw_star_layer(lcd, vx // 7, vy // 7, 52, 13, 3, GRAY)
    _draw_star_layer(lcd, vx // 3, vy // 3, 34, 41, 4, GRAY)
    draw_bg_stars(lcd, vx, vy)


def _draw_viewfinder(lcd, cx, cy, color=GRAY):
    lcd.hline(cx - 8, cy, 4, color)
    lcd.hline(cx + 5, cy, 4, color)
    lcd.vline(cx, cy - 8, 4, color)
    lcd.vline(cx, cy + 5, 4, color)
    lcd.pixel(cx, cy, WHITE)


def _draw_footer_bar(lcd, left_text, right_text="", color=GRAY):
    y = VIEW_H - FOOTER_BAR_H
    lcd.fill_rect(0, y, VIEW_W, FOOTER_BAR_H, BLACK)
    lcd.hline(0, y, VIEW_W, color)
    lcd.text(fit_text(left_text, max(1, (VIEW_W // 16) - 1)), 4, y + 4, color)
    if right_text:
        right_text = fit_text(right_text, max(1, (VIEW_W // 16) - 1))
        lcd.text(right_text, right_x(right_text), y + 4, color)


def _draw_overlay_window(lcd, x, y, w, title, lines):
    h = 18 + (len(lines) * 12) + 6
    lcd.fill_rect(x, y, w, h, WHITE)
    lcd.rect(x, y, w, h, BLACK)
    lcd.fill_rect(x + 1, y + 1, w - 2, 12, BLACK)
    lcd.fill_rect(x + 4, y + 4, 4, 4, WHITE)
    lcd.text(fit_text(title, max(1, (w // 8) - 4)), x + 12, y + 3, WHITE)
    max_chars = max(1, (w // 8) - 2)
    line_y = y + 18
    for line in lines:
        text = line
        color = BLACK
        if isinstance(line, tuple):
            text, color = line
        lcd.text(fit_text(text, max_chars), x + 4, line_y, color)
        line_y += 12

# --- Find nearest system to viewport center ---
def find_nearest(systems, vx, vy):
    cx = vx + (VIEW_W // 2)
    cy = vy + (VIEW_H // 2)
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
    draw_parallax_space(lcd, vx, vy)

    # draw systems
    for i in range(len(systems)):
        s = systems[i]
        sx = s[0] - vx
        sy = s[1] - vy
        if -10 <= sx < VIEW_W + 10 and -10 <= sy < VIEW_H + 10:
            lcd.ellipse(sx, sy, s[5], s[5], s[4], True)
            if i == sel_idx:
                # selection ring
                lcd.ellipse(sx, sy, s[5]+3, s[5]+3, WHITE, False)

    _draw_viewfinder(lcd, VIEW_W // 2, VIEW_H // 2)

    if sel_idx >= 0:
        s = systems[sel_idx]
        name = fit_text(s[3], max(1, (VIEW_W // 8) - 2))
        lcd.fill_rect(0, 0, VIEW_W, TITLE_BAR_H, BLACK)
        lcd.text(name, center_x(name, VIEW_W), 5, YELLOW)
        lcd.text(str(sel_idx + 1) + "/" + str(len(systems)), 4, VIEW_H - FOOTER_BAR_H - 14, GRAY)
    _draw_footer_bar(lcd, A_LABEL + " back", B_LABEL + " enter")

# --- Draw solar system view (full scene + floating scanner) ---
INFO_X = 138

def draw_system(lcd, system, planets, sel_planet):
    lcd.fill(BLACK)
    scx = VIEW_W // 2
    scy = (VIEW_H // 2) + 10
    max_rx = planets[-1][0] + 4
    max_ry = planets[-1][1] + 4
    scene_h = VIEW_H - TITLE_BAR_H - FOOTER_BAR_H - 18
    orbit_scale = min((VIEW_W - 30) / float(max_rx * 2), scene_h / float(max_ry * 2))

    draw_parallax_space(lcd, system[2] * 5, system[2] * 7)

    sun_color = system[4]
    sun_r = min(system[5] + 6, 11)

    for p in planets:
        lcd.ellipse(scx, scy, max(10, int(p[0] * orbit_scale)), max(6, int(p[1] * orbit_scale)), GRAY, False)

    lcd.ellipse(scx, scy, sun_r, sun_r, sun_color, True)
    if sun_r > 1:
        lcd.ellipse(scx, scy, sun_r - 1, sun_r - 1, YELLOW, True)

    for i in range(len(planets)):
        p = planets[i]
        px = scx + int((p[0] * orbit_scale) * math.cos(p[5]))
        py = scy + int((p[1] * orbit_scale) * math.sin(p[5]))
        px = max(6, min(VIEW_W - 7, px))
        py = max(TITLE_BAR_H + 6, min(VIEW_H - FOOTER_BAR_H - 8, py))
        lcd.ellipse(px, py, p[2] + 3, p[2] + 3, p[3], True)
        if i == sel_planet:
            lcd.ellipse(px, py, p[2] + 6, p[2] + 6, WHITE, False)

    lcd.fill_rect(0, 0, VIEW_W, TITLE_BAR_H, BLACK)
    title = fit_text(system[3], max(1, (VIEW_W // 8) - 2))
    lcd.text(title, center_x(title, VIEW_W), 5, YELLOW)

    if 0 <= sel_planet < len(planets):
        p = planets[sel_planet]
        m = p[7]
        if m < 10:
            ms = "0." + str(m) + "Me"
        else:
            ms = str(m // 10) + "." + str(m % 10) + "Me"
        r = p[9]
        if r < 10:
            rs = "0." + str(r) + "Re"
        else:
            rs = str(r // 10) + "." + str(r % 10) + "Re"
        _draw_overlay_window(
            lcd,
            VIEW_W - 104,
            TITLE_BAR_H + 8,
            100,
            "Scanner",
            [
                (str(sel_planet + 1) + "/" + str(len(planets)) + " " + p[4], TEAL),
                p[11] + " / " + p[10],
                (ms + "  " + rs, CYAN),
                (str(p[8]) + "C", ORANGE),
            ],
        )

    _draw_footer_bar(lcd, A_LABEL + " back", B_LABEL + " land")

# --- Region generation for a planet surface ---
_RTYPE = ["Mountain","Canyon","Crater","Volcano","Ocean",
          "Forest","Desert","Tundra","City","Ruins",
          "Ice Cap","Swamp","Plains","Rift","Lake"]
_RDET = ["Ancient","Vast","Deep","Frozen","Active",
         "Dense","Barren","Lush","Glowing","Silent",
         "Crystal","Iron","Sulfur","Mossy","Dusty"]
_RCOLORS = [GRAY, DKRED, ORANGE, RED, MARINE,
            OLIVE, SAND, TEAL, SLATE, PURPLE,
            INDIGO, BROWN, AMBER, COPPER, BLUE]

def gen_regions(planet):
    pseed = hash(planet[4]) & 0xFFFF
    random.seed(pseed + 3000)
    n = random.randint(2, 5)
    regions = []
    for i in range(n):
        # place regions ON the planet surface (angle + distance from center as fraction of radius)
        a = random.randint(0, 628) / 100.0
        d_frac = random.randint(10, 85) / 100.0  # 0.1-0.85 of planet radius
        ri = random.randint(0, len(_RTYPE) - 1)
        rtype = _RTYPE[ri]
        rcolor = _RCOLORS[ri]
        det = _RDET[random.randint(0, len(_RDET) - 1)]
        rname = det + " " + rtype
        rsize = random.randint(2, 4)
        elev = random.randint(-5000, 15000)
        rad = random.randint(0, 100)
        bio = random.randint(0, 100)
        regions.append([a, d_frac, rsize, rcolor, rname, rtype, elev, rad, bio])
    return regions

# --- Draw planet surface view (large planet + floating scanner) ---
def draw_planet(lcd, planet, regions, sel_region):
    lcd.fill(BLACK)
    seed = hash(planet[4]) & 0xFFFF
    draw_parallax_space(lcd, seed, seed // 2)
    hud_y = VIEW_H - FOOTER_BAR_H
    pcx = (VIEW_W // 2) - 40
    pcy = (VIEW_H // 2) + 6
    pcolor = planet[3]
    pr = min(PLANET_RENDER_RADIUS, (VIEW_W // 2) - 34, ((VIEW_H - TITLE_BAR_H - FOOTER_BAR_H) // 2) - 20)
    text_chars = max(1, (VIEW_W // 8) - 2)

    # atmosphere glow (outer halo)
    atm = planet[10]
    if atm != "None":
        # faint atmosphere ring
        lcd.ellipse(pcx, pcy, pr + 3, pr + 3, GRAY, False)
        lcd.ellipse(pcx, pcy, pr + 2, pr + 2, pcolor, False)

    # planet base (dark side first for shadow)
    lcd.ellipse(pcx, pcy, pr, pr, BLACK, True)
    # main body color
    lcd.ellipse(pcx, pcy, pr, pr, pcolor, True)

    # surface texture: deterministic surface features
    pseed = hash(planet[4]) & 0xFFFF
    random.seed(pseed + 7000)
    ptype = planet[11]

    # generate surface detail pixels within the planet disc
    if ptype == "Gas":
        # horizontal bands with varied colors
        band_colors = [pcolor, GRAY, ORANGE, YELLOW]
        for band in range(-pr + 2, pr, 4):
            bw = int(math.sqrt(max(0, pr * pr - band * band)))
            if bw > 2:
                c = band_colors[(band // 3) % len(band_colors)]
                lcd.hline(pcx - bw + 1, pcy + band, bw * 2 - 2, c)
        # swirl spots
        for _ in range(4):
            tx = random.randint(-pr // 2, pr // 2)
            bw = int(math.sqrt(max(0, (pr-3)*(pr-3) - tx*tx)))
            if bw > 0:
                ty = random.randint(-bw, bw)
                lcd.ellipse(pcx + tx, pcy + ty, 2, 1, DKRED, True)
    elif ptype == "Ocean":
        # continent-like land patches
        for _ in range(6):
            tx = random.randint(-pr + 5, pr - 5)
            bw = int(math.sqrt(max(0, (pr-3)*(pr-3) - tx*tx)))
            if bw > 0:
                ty = random.randint(-bw, bw)
                sz = random.randint(2, 4)
                lcd.ellipse(pcx + tx, pcy + ty, sz, sz - 1, OLIVE, True)
        # scattered water highlights
        for _ in range(18):
            tx = random.randint(-pr + 3, pr - 3)
            bw = int(math.sqrt(max(0, (pr-2)*(pr-2) - tx*tx)))
            ty = random.randint(-bw, bw)
            c = CYAN if random.randint(0, 2) == 0 else BLUE
            lcd.pixel(pcx + tx, pcy + ty, c)
    elif ptype == "Ice":
        # cracks and varied ice
        for _ in range(20):
            tx = random.randint(-pr + 3, pr - 3)
            bw = int(math.sqrt(max(0, (pr-2)*(pr-2) - tx*tx)))
            ty = random.randint(-bw, bw)
            c = WHITE if random.randint(0, 2) else CYAN
            lcd.pixel(pcx + tx, pcy + ty, c)
        # crack lines
        for _ in range(2):
            cx0 = random.randint(-pr // 2, pr // 2)
            cy0 = random.randint(-pr // 2, pr // 2)
            for j in range(5):
                nx = cx0 + random.randint(-1, 1)
                ny = cy0 + random.randint(-1, 1)
                if nx*nx + ny*ny < (pr-2)*(pr-2):
                    lcd.pixel(pcx + nx, pcy + ny, BLUE)
                    cx0, cy0 = nx, ny
    elif ptype == "Lava":
        # dark crust with lava veins
        for _ in range(18):
            tx = random.randint(-pr + 3, pr - 3)
            bw = int(math.sqrt(max(0, (pr-2)*(pr-2) - tx*tx)))
            if bw > 0:
                ty = random.randint(-bw, bw)
                c = DKRED if random.randint(0, 1) else GRAY
                lcd.pixel(pcx + tx, pcy + ty, c)
        # bright lava flows
        for _ in range(3):
            cx0 = random.randint(-pr // 2, pr // 2)
            cy0 = random.randint(-pr // 2, pr // 2)
            for j in range(6):
                nx = cx0 + random.randint(-1, 1)
                ny = cy0 + random.randint(-1, 1)
                if nx*nx + ny*ny < (pr-2)*(pr-2):
                    lcd.pixel(pcx + nx, pcy + ny, ORANGE)
                    cx0, cy0 = nx, ny
        for _ in range(5):
            tx = random.randint(-pr + 4, pr - 4)
            bw = int(math.sqrt(max(0, (pr-3)*(pr-3) - tx*tx)))
            if bw > 0:
                ty = random.randint(-bw, bw)
                lcd.pixel(pcx + tx, pcy + ty, YELLOW)
    elif ptype == "Desert":
        # dunes and rocky outcrops
        for _ in range(16):
            tx = random.randint(-pr + 3, pr - 3)
            bw = int(math.sqrt(max(0, (pr-2)*(pr-2) - tx*tx)))
            if bw > 0:
                ty = random.randint(-bw, bw)
                c = YELLOW if random.randint(0, 2) else ORANGE
                lcd.pixel(pcx + tx, pcy + ty, c)
        # rocky patches
        for _ in range(3):
            tx = random.randint(-pr + 5, pr - 5)
            bw = int(math.sqrt(max(0, (pr-4)*(pr-4) - tx*tx)))
            if bw > 0:
                ty = random.randint(-bw, bw)
                lcd.ellipse(pcx + tx, pcy + ty, 2, 1, GRAY, True)
    else:
        # Rocky — craters and varied terrain
        for _ in range(18):
            tx = random.randint(-pr + 3, pr - 3)
            bw = int(math.sqrt(max(0, (pr-2)*(pr-2) - tx*tx)))
            if bw > 0:
                ty = random.randint(-bw, bw)
                c = GRAY if random.randint(0, 1) else DKRED
                lcd.pixel(pcx + tx, pcy + ty, c)
        # crater rings
        for _ in range(2):
            tx = random.randint(-pr // 2, pr // 2)
            bw = int(math.sqrt(max(0, (pr-4)*(pr-4) - tx*tx)))
            if bw > 0:
                ty = random.randint(-bw, bw)
                lcd.ellipse(pcx + tx, pcy + ty, 3, 2, GRAY, False)

    # terminator (shadow on right side for 3D effect)
    for sy in range(-pr, pr + 1):
        bw = int(math.sqrt(max(0, pr * pr - sy * sy)))
        shadow_start = pcx + bw // 2
        shadow_end = pcx + bw
        for sx in range(shadow_start, shadow_end + 1):
            if 0 <= sx < VIEW_W and 0 <= pcy + sy < hud_y:
                lcd.pixel(sx, pcy + sy, BLACK)

    # re-draw planet outline for clean edge
    lcd.ellipse(pcx, pcy, pr, pr, pcolor, False)

    # highlight (specular reflection top-left)
    lcd.ellipse(pcx - 7, pcy - 7, 4, 3, WHITE, False)

    # draw regions ON the planet surface
    for i in range(len(regions)):
        r = regions[i]
        d = int(r[1] * pr)
        rx = pcx + int(d * math.cos(r[0]))
        ry = pcy + int(d * math.sin(r[0]))
        # check if within planet disc
        ddx = rx - pcx
        ddy = ry - pcy
        if ddx * ddx + ddy * ddy <= pr * pr:
            rx = max(4, min(VIEW_W - 5, rx))
            ry = max(TITLE_BAR_H + 4, min(hud_y - 4, ry))
            lcd.ellipse(rx, ry, r[2], r[2], r[3], True)
            if i == sel_region:
                lcd.ellipse(rx, ry, r[2] + 2, r[2] + 2, WHITE, False)

    lcd.fill_rect(0, 0, VIEW_W, TITLE_BAR_H, BLACK)
    title = fit_text(planet[4], max(1, (VIEW_W // 8) - 2))
    lcd.text(title, center_x(title, VIEW_W), 5, TEAL)

    if 0 <= sel_region < len(regions):
        rg = regions[sel_region]
        e = rg[6]
        if e >= 0:
            es = "+" + str(e) + "m"
        else:
            es = str(e) + "m"
        overlay_lines = [
            (planet[11] + " / " + planet[10], GRAY),
            (rg[4], rg[3]),
            rg[5],
            (es, CYAN),
            ("Rad " + str(rg[7]) + "%", ORANGE),
            ("Bio " + str(rg[8]) + "%", TEAL),
        ]
        _draw_overlay_window(
            lcd,
            VIEW_W - 104,
            TITLE_BAR_H + 8,
            100,
            "Region",
            overlay_lines,
        )

    _draw_footer_bar(lcd, A_LABEL + " orbit", "L/R region")

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
                if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
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
                if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
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
            if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                lcd.pixel(px, py, color)
    else:  # ring
        lcd.ellipse(cx, cy, 14, 8, color, False)
        lcd.ellipse(cx, cy, 13, 7, c2, False)
        lcd.ellipse(cx, cy, 2, 2, color, True)
    if shape == 5:  # irregular horizontal
        for _ in range(14):
            px = cx + random.randint(-16, 16)
            py = cy + random.randint(-4, 4)
            if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                lcd.pixel(px, py, color)
        for _ in range(5):
            px = cx + random.randint(-12, 12)
            py = cy + random.randint(-6, 6)
            if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                lcd.pixel(px, py, c2)
    elif shape == 6:  # irregular vertical
        for _ in range(14):
            px = cx + random.randint(-5, 5)
            py = cy + random.randint(-12, 12)
            if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                lcd.pixel(px, py, color)
        for _ in range(5):
            px = cx + random.randint(-7, 7)
            py = cy + random.randint(-10, 10)
            if 0 <= px < VIEW_W and 0 <= py < VIEW_H:
                lcd.pixel(px, py, c2)
    if sel:
        lcd.ellipse(cx, cy, 18, 14, WHITE, False)

# --- Find nearest galaxy to viewport center ---
def find_nearest_gal(galaxies, vx, vy):
    cx = vx + (VIEW_W // 2)
    cy = vy + (VIEW_H // 2)
    best = -1
    best_d = 999999
    for i in range(len(galaxies)):
        g = galaxies[i]
        dx = g[4] - cx
        dy = g[5] - cy
        d = dx*dx + dy*dy
        if d < best_d:
            best_d = d
            best = i
    return best

# --- Draw galaxy selector (scrollable 2D view) ---
def draw_galaxy_sel(lcd, galaxies, vx, vy, sel_gal):
    lcd.fill(BLACK)
    draw_parallax_space(lcd, vx + 5000, vy + 5000)  # offset so stars differ from galaxy map

    for i in range(len(galaxies)):
        g = galaxies[i]
        sx = g[4] - vx
        sy = g[5] - vy
        if -20 <= sx < VIEW_W + 20 and -20 <= sy < VIEW_H + 20:
            _draw_mini_galaxy(lcd, sx, sy, g[2], g[3], i == sel_gal)

    _draw_viewfinder(lcd, VIEW_W // 2, VIEW_H // 2)

    if sel_gal >= 0:
        g = galaxies[sel_gal]
        name = fit_text(g[1], max(1, (VIEW_W // 8) - 2))
        lcd.fill_rect(0, 0, VIEW_W, TITLE_BAR_H, BLACK)
        lcd.text(name, center_x(name, VIEW_W), 5, YELLOW)
        lcd.text(_GTYPE[g[2]], 4, VIEW_H - FOOTER_BAR_H - 14, GRAY)
    _draw_footer_bar(lcd, A_LABEL + " next", B_LABEL + " enter")

# --- Main entry point ---
def run():
    lcd = LCD()

    # splash screen
    lcd.fill(BLACK)
    lcd.text("GALAXY", center_x("GALAXY", VIEW_W), 72, CYAN)
    lcd.text("EXPLORER", center_x("EXPLORER", VIEW_W), 100, YELLOW)
    lcd.text("Press any key", center_x("Press any key", VIEW_W), 150, GRAY)
    lcd.display()

    # inputs
    KEY_UP = Pin(BUTTON_PINS["UP"], Pin.IN, Pin.PULL_UP)
    KEY_DOWN = Pin(BUTTON_PINS["DOWN"], Pin.IN, Pin.PULL_UP)
    KEY_LEFT = Pin(BUTTON_PINS["LEFT"], Pin.IN, Pin.PULL_UP)
    KEY_RIGHT = Pin(BUTTON_PINS["RIGHT"], Pin.IN, Pin.PULL_UP)
    KEY_A = Pin(BUTTON_PINS["A"], Pin.IN, Pin.PULL_UP)
    KEY_B = Pin(BUTTON_PINS["B"], Pin.IN, Pin.PULL_UP)

    # wait for any key
    while (KEY_UP.value() and KEY_DOWN.value() and KEY_LEFT.value()
           and KEY_RIGHT.value() and KEY_A.value() and KEY_B.value()):
        time.sleep(0.05)
    time.sleep(0.2)

    # generate galaxy list
    galaxies = gen_galaxy_list(8)
    sel_gal = 0
    state = STATE_GALAXYSEL
    systems = None
    cur_shape = 0
    # universe viewport (galaxy selector)
    uvx = max(0, min(UNIV_W - VIEW_W, galaxies[0][4] - (VIEW_W // 2)))
    uvy = max(0, min(UNIV_H - VIEW_H, galaxies[0][5] - (VIEW_H // 2)))
    # galaxy viewport (star map)
    vx = 0
    vy = 0
    sel_idx = 0
    planets = None
    sel_planet = 0
    regions = None
    sel_region = 0
    scroll_speed = 4

    while True:
        if state == STATE_GALAXYSEL:
            # --- Galaxy selector: d-pad scrolling ---
            if KEY_UP.value() == 0:
                uvy = max(0, uvy - scroll_speed)
            if KEY_DOWN.value() == 0:
                uvy = min(UNIV_H - VIEW_H, uvy + scroll_speed)
            if KEY_LEFT.value() == 0:
                uvx = max(0, uvx - scroll_speed)
            if KEY_RIGHT.value() == 0:
                uvx = min(UNIV_W - VIEW_W, uvx + scroll_speed)

            # A: jump to next galaxy
            if KEY_A.value() == 0:
                sel_gal = (sel_gal + 1) % len(galaxies)
                g = galaxies[sel_gal]
                uvx = max(0, min(UNIV_W - VIEW_W, g[4] - (VIEW_W // 2)))
                uvy = max(0, min(UNIV_H - VIEW_H, g[5] - (VIEW_H // 2)))
                time.sleep(0.2)

            # B: enter selected galaxy
            if KEY_B.value() == 0:
                sel_gal = find_nearest_gal(galaxies, uvx, uvy)
                if sel_gal >= 0:
                    g = galaxies[sel_gal]
                    cur_shape = g[2]
                    systems = gen_galaxy(g[0], cur_shape)
                    vx = max(0, min(WORLD_W - VIEW_W, systems[0][0] - (VIEW_W // 2)))
                    vy = max(0, min(WORLD_H - VIEW_H, systems[0][1] - (VIEW_H // 2)))
                    sel_idx = 0
                    state = STATE_GALAXY
                    time.sleep(0.2)

            sel_gal = find_nearest_gal(galaxies, uvx, uvy)
            draw_galaxy_sel(lcd, galaxies, uvx, uvy, sel_gal)

        elif state == STATE_GALAXY:
            # --- Galaxy map controls ---
            if KEY_UP.value() == 0:
                vy = max(0, vy - scroll_speed)
            if KEY_DOWN.value() == 0:
                vy = min(WORLD_H - VIEW_H, vy + scroll_speed)
            if KEY_LEFT.value() == 0:
                vx = max(0, vx - scroll_speed)
            if KEY_RIGHT.value() == 0:
                vx = min(WORLD_W - VIEW_W, vx + scroll_speed)

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

            # B: zoom into planet
            if KEY_B.value() == 0:
                regions = gen_regions(planets[sel_planet])
                sel_region = 0
                state = STATE_PLANET
                time.sleep(0.2)

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

        elif state == STATE_PLANET:
            # --- Planet surface controls ---
            if KEY_LEFT.value() == 0:
                sel_region = (sel_region - 1) % len(regions)
                time.sleep(0.15)
            if KEY_RIGHT.value() == 0:
                sel_region = (sel_region + 1) % len(regions)
                time.sleep(0.15)

            # A: back to solar system
            if KEY_A.value() == 0:
                state = STATE_SYSTEM
                time.sleep(0.2)

            draw_planet(lcd, planets[sel_planet], regions, sel_region)

        lcd.display()
        time.sleep(0.03)

if __name__ == '__main__':
    run()
