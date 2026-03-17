import time

from machine import Pin, SPI


WIDTH = 200
HEIGHT = 200
BYTE_WIDTH = WIDTH // 8
BUFFER_SIZE = BYTE_WIDTH * HEIGHT

# Default Pico wiring for the current bench setup.
# Update these constants if your wiring differs.
SPI_ID = 0
PIN_SCK = 18
PIN_MOSI = 19
PIN_CS = 17
PIN_DC = 20
PIN_RST = 21
PIN_BUSY = 22

WHITE = 1
BLACK = 0
DEFAULT_BAUDRATE = 1000000
PROFILE_V1 = "v1"
PROFILE_V2 = "v2"
CAT_MOODS = ("smile", "wink", "angry")

# Full-update waveform from the vendor 1.54-inch mono reference driver.
FULL_UPDATE_LUT = bytearray(
    b"\x02\x02\x01\x11\x12\x12\x22\x22\x66\x69\x69\x59\x58\x99\x99\x88"
    b"\x00\x00\x00\x00\xF8\xB4\x13\x51\x35\x51\x51\x19\x01\x00"
)


class SeengreatEPD154:
    def __init__(self, baudrate=DEFAULT_BAUDRATE, profile=PROFILE_V2):
        if profile not in (PROFILE_V1, PROFILE_V2):
            raise ValueError("profile must be 'v1' or 'v2'")

        self.width = WIDTH
        self.height = HEIGHT
        self.profile = profile

        self.cs = Pin(PIN_CS, Pin.OUT)
        self.dc = Pin(PIN_DC, Pin.OUT)
        self.rst = Pin(PIN_RST, Pin.OUT)
        self.busy = Pin(PIN_BUSY, Pin.IN)

        self.cs(1)
        self.dc(1)
        self.rst(1)

        self.spi = SPI(
            SPI_ID,
            baudrate=baudrate,
            polarity=0,
            phase=0,
            sck=Pin(PIN_SCK),
            mosi=Pin(PIN_MOSI),
            miso=None,
        )

        self.buffer = bytearray([0xFF] * BUFFER_SIZE)

    def write_cmd(self, value):
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([value]))
        self.cs(1)

    def write_data(self, value):
        self.dc(1)
        self.cs(0)
        if isinstance(value, int):
            self.spi.write(bytearray([value]))
        else:
            self.spi.write(value)
        self.cs(1)

    def wait_ready(self, timeout_ms=10000):
        start = time.ticks_ms()
        while self.busy.value():
            if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
                raise RuntimeError("E-paper busy timeout")
            time.sleep_ms(10)

    def reset(self):
        if self.profile == PROFILE_V2:
            self.rst(1)
            time.sleep_ms(200)
            self.rst(0)
            time.sleep_ms(2)
            self.rst(1)
            time.sleep_ms(200)
            return

        self.rst(0)
        time.sleep_ms(200)
        self.rst(1)
        time.sleep_ms(200)

    def set_lut(self, lut=FULL_UPDATE_LUT):
        self.write_cmd(0x32)
        self.write_data(lut)

    def set_memory_area(self, x_start, y_start, x_end, y_end):
        self.write_cmd(0x44)
        self.write_data(bytearray([(x_start >> 3) & 0xFF, (x_end >> 3) & 0xFF]))

        self.write_cmd(0x45)
        self.write_data(
            bytearray(
                [
                    y_start & 0xFF,
                    (y_start >> 8) & 0xFF,
                    y_end & 0xFF,
                    (y_end >> 8) & 0xFF,
                ]
            )
        )

    def set_memory_pointer(self, x, y):
        self.write_cmd(0x4E)
        self.write_data((x >> 3) & 0xFF)

        self.write_cmd(0x4F)
        self.write_data(bytearray([y & 0xFF, (y >> 8) & 0xFF]))
        self.wait_ready()

    def init(self):
        if self.profile == PROFILE_V2:
            self._init_v2()
            return

        # Older 200x200 mono panels need the external waveform/timing setup.
        self._init_v1()

    def _init_v1(self):
        self.reset()

        self.write_cmd(0x01)  # Driver output control
        self.write_data(bytearray([(HEIGHT - 1) & 0xFF, ((HEIGHT - 1) >> 8) & 0xFF, 0x00]))

        self.write_cmd(0x0C)  # Booster soft start
        self.write_data(bytearray([0xD7, 0xD6, 0x9D]))

        self.write_cmd(0x2C)  # VCOM
        self.write_data(0xA8)

        self.write_cmd(0x3A)  # Dummy line period
        self.write_data(0x1A)

        self.write_cmd(0x3B)  # Gate time
        self.write_data(0x08)

        self.write_cmd(0x11)  # Data entry mode
        self.write_data(0x03)

        self.set_lut()
        self.set_memory_area(0, 0, WIDTH - 1, HEIGHT - 1)
        self.set_memory_pointer(0, 0)

    def _init_v2(self):
        # Current 1.54-inch 200x200 mono modules generally match the V2
        # controller flow used by Waveshare's current demo set.
        self.reset()
        self.wait_ready()

        self.write_cmd(0x12)  # SWRESET
        self.wait_ready()

        self.write_cmd(0x01)  # Driver output control
        self.write_data(bytearray([0xC7, 0x00, 0x01]))

        self.write_cmd(0x11)  # Data entry mode
        self.write_data(0x01)

        self.set_memory_area(0, HEIGHT - 1, WIDTH - 1, 0)
        self.set_memory_pointer(0, HEIGHT - 1)

        self.write_cmd(0x3C)  # Border waveform
        self.write_data(0x01)

        self.write_cmd(0x18)  # Built-in temperature sensor
        self.write_data(0x80)

        self.write_cmd(0x22)  # Display update control
        self.write_data(0xB1)
        self.write_cmd(0x20)
        self.wait_ready()

    def update(self):
        if self.profile == PROFILE_V2:
            self.write_cmd(0x22)
            self.write_data(0xC7)
            self.write_cmd(0x20)
            self.wait_ready()
            return

        self.write_cmd(0x22)
        self.write_data(0xC4)
        self.write_cmd(0x20)
        self.write_cmd(0xFF)
        self.wait_ready()

    def sleep(self):
        self.write_cmd(0x10)
        self.write_data(0x01)
        time.sleep_ms(10)

    def busy_state(self):
        return self.busy.value()

    def clear(self, color=WHITE):
        fill = 0xFF if color == WHITE else 0x00
        for index in range(BUFFER_SIZE):
            self.buffer[index] = fill

    def set_pixel(self, x, y, color=BLACK):
        if x < 0 or x >= WIDTH or y < 0 or y >= HEIGHT:
            return

        if self.profile == PROFILE_V2:
            y = HEIGHT - 1 - y
            addr = (x // 8) + (y * BYTE_WIDTH)
            mask = 0x80 >> (x % 8)
            if color == BLACK:
                self.buffer[addr] &= ~mask
            else:
                self.buffer[addr] |= mask
            return

        # Match the vendor GUI orientation so drawing appears upright.
        xx = y
        yy = HEIGHT - x - 1
        addr = (xx // 8) + (yy * BYTE_WIDTH)
        mask = 0x80 >> (xx % 8)

        if color == BLACK:
            self.buffer[addr] &= ~mask
        else:
            self.buffer[addr] |= mask

    def draw_line(self, x0, y0, x1, y1, color=BLACK):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy

        while True:
            self.set_pixel(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = err + err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def draw_rect(self, x0, y0, x1, y1, color=BLACK, thickness=1):
        for offset in range(thickness):
            self.draw_line(x0 + offset, y0 + offset, x1 - offset, y0 + offset, color)
            self.draw_line(x0 + offset, y1 - offset, x1 - offset, y1 - offset, color)
            self.draw_line(x0 + offset, y0 + offset, x0 + offset, y1 - offset, color)
            self.draw_line(x1 - offset, y0 + offset, x1 - offset, y1 - offset, color)

    def fill_rect(self, x0, y0, x1, y1, color=BLACK):
        left = max(0, min(x0, x1))
        right = min(WIDTH - 1, max(x0, x1))
        top = max(0, min(y0, y1))
        bottom = min(HEIGHT - 1, max(y0, y1))

        for y in range(top, bottom + 1):
            for x in range(left, right + 1):
                self.set_pixel(x, y, color)

    def draw_circle(self, cx, cy, radius, color=BLACK):
        if radius < 0:
            raise ValueError("radius must be >= 0")

        x = radius
        y = 0
        err = 1 - radius

        while x >= y:
            self.set_pixel(cx + x, cy + y, color)
            self.set_pixel(cx + y, cy + x, color)
            self.set_pixel(cx - y, cy + x, color)
            self.set_pixel(cx - x, cy + y, color)
            self.set_pixel(cx - x, cy - y, color)
            self.set_pixel(cx - y, cy - x, color)
            self.set_pixel(cx + y, cy - x, color)
            self.set_pixel(cx + x, cy - y, color)
            y += 1
            if err < 0:
                err += (2 * y) + 1
            else:
                x -= 1
                err += 2 * (y - x) + 1

    def display(self):
        if self.profile == PROFILE_V2:
            self.set_memory_area(0, HEIGHT - 1, WIDTH - 1, 0)
            self.set_memory_pointer(0, HEIGHT - 1)
        else:
            self.set_memory_area(0, 0, WIDTH - 1, HEIGHT - 1)
            self.set_memory_pointer(0, 0)
        self.write_cmd(0x24)
        self.write_data(self.buffer)
        self.update()


def _draw_cat_face(epd, mood="smile"):
    if mood not in CAT_MOODS:
        raise ValueError("unsupported cat mood")

    stroke = 3

    def line(x0, y0, x1, y1, width=stroke):
        radius = max(0, (width - 1) // 2)
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                epd.draw_line(x0 + dx, y0 + dy, x1 + dx, y1 + dy, BLACK)

    def circle(cx, cy, radius, width=stroke):
        inner = max(0, radius - ((width - 1) // 2))
        outer = radius + (width // 2)
        for rr in range(inner, outer + 1):
            epd.draw_circle(cx, cy, rr, BLACK)

    epd.clear(WHITE)
    epd.draw_rect(8, 8, 191, 191, BLACK, thickness=2)

    # Head and ears.
    circle(100, 103, 46)

    line(67, 69, 52, 35)
    line(52, 35, 82, 59)
    line(82, 59, 71, 79)

    line(133, 69, 148, 35)
    line(148, 35, 118, 59)
    line(118, 59, 129, 79)

    line(65, 62, 59, 46)
    line(59, 46, 76, 58)
    line(135, 62, 141, 46)
    line(141, 46, 124, 58)

    # Nose and whiskers.
    line(97, 106, 103, 106, width=2)
    line(97, 106, 100, 110, width=2)
    line(103, 106, 100, 110, width=2)

    line(54, 94, 79, 99, width=2)
    line(51, 104, 79, 104, width=2)
    line(54, 114, 79, 109, width=2)
    line(146, 94, 121, 99, width=2)
    line(149, 104, 121, 104, width=2)
    line(146, 114, 121, 109, width=2)

    if mood == "smile":
        line(72, 95, 80, 87)
        line(80, 87, 88, 95)
        line(112, 95, 120, 87)
        line(120, 87, 128, 95)

        line(100, 111, 93, 119)
        line(100, 111, 107, 119)
        line(93, 119, 98, 123)
        line(102, 123, 107, 119)

        line(59, 123, 65, 129, width=2)
        line(67, 120, 73, 126, width=2)
        line(141, 123, 135, 129, width=2)
        line(133, 120, 127, 126, width=2)
    elif mood == "wink":
        line(72, 95, 80, 87)
        line(80, 87, 88, 95)
        epd.draw_rect(113, 86, 126, 96, BLACK, thickness=2)
        epd.fill_rect(118, 90, 121, 93, BLACK)

        line(100, 111, 94, 118)
        line(100, 111, 106, 118)
        line(94, 118, 100, 122)
        line(100, 122, 106, 118)

        line(151, 51, 160, 60)
        line(160, 51, 151, 60)
        line(155, 47, 155, 64)
        line(147, 56, 163, 56)
    else:
        line(67, 87, 88, 80)
        line(112, 80, 133, 87)
        line(73, 96, 88, 92)
        line(112, 92, 127, 96)

        line(94, 121, 100, 116)
        line(100, 116, 106, 121)

        line(35, 35, 44, 44)
        line(44, 35, 35, 44)
        line(30, 39, 49, 39)
        line(39, 30, 39, 49)

    line(92, 150, 108, 150, width=2)
    line(86, 157, 114, 157, width=2)


def _draw_demo_card(epd):
    _draw_cat_face(epd, mood="smile")


def _show_solid(epd, color):
    epd.clear(color)
    epd.display()


def _draw_checkerboard(epd, cells=8):
    if cells <= 0:
        raise ValueError("cells must be > 0")

    epd.clear(WHITE)

    for row in range(cells):
        top = (row * HEIGHT) // cells
        bottom = ((row + 1) * HEIGHT) // cells - 1
        for col in range(cells):
            if (row + col) % 2 == 0:
                left = (col * WIDTH) // cells
                right = ((col + 1) * WIDTH) // cells - 1
                epd.fill_rect(left, top, right, bottom, BLACK)


def _show_checkerboard(epd, cells=8):
    _draw_checkerboard(epd, cells=cells)
    epd.display()


def _show_cat(epd, mood="smile"):
    _draw_cat_face(epd, mood=mood)
    epd.display()


def _resolve_checker_sizes(checker_sizes, min_cells, max_cells):
    if checker_sizes is None:
        if min_cells <= 0:
            raise ValueError("min_cells must be > 0")
        if max_cells < min_cells:
            raise ValueError("max_cells must be >= min_cells")
        return tuple(range(min_cells, max_cells + 1))

    sizes = tuple(checker_sizes)
    if not sizes:
        raise ValueError("checker_sizes must not be empty")
    for cells in sizes:
        if cells <= 0:
            raise ValueError("checker sizes must be > 0")
    return sizes


def run_demo_card(baudrate=DEFAULT_BAUDRATE, profile=PROFILE_V2):
    epd = SeengreatEPD154(baudrate=baudrate, profile=profile)
    print("e-paper init")
    print("profile =", profile)
    epd.init()
    print("drawing test card")
    _draw_demo_card(epd)
    print("refresh")
    epd.display()
    print("sleep")
    epd.sleep()
    print("done")
    return epd


def run(
    hold_ms=800,
    checker_sizes=None,
    min_cells=2,
    max_cells=32,
    baudrate=DEFAULT_BAUDRATE,
    profile=PROFILE_V2,
    cat_moods=CAT_MOODS,
    loop_forever=True,
):
    if hold_ms < 0:
        raise ValueError("hold_ms must be >= 0")

    checker_sizes = _resolve_checker_sizes(checker_sizes, min_cells, max_cells)

    epd = SeengreatEPD154(baudrate=baudrate, profile=profile)
    print("e-paper init")
    print("profile =", profile)
    epd.init()

    while True:
        for mood in cat_moods:
            print("cat %s" % mood)
            _show_cat(epd, mood=mood)
            if hold_ms:
                time.sleep_ms(hold_ms)
        for cells in checker_sizes:
            print("%dx%d checkerboard" % (cells, cells))
            _show_checkerboard(epd, cells=cells)
            if hold_ms:
                time.sleep_ms(hold_ms)
        if not loop_forever:
            break

    print("sleep")
    epd.sleep()
    print("done")
    return epd


def probe(baudrate=DEFAULT_BAUDRATE, profile=PROFILE_V2):
    epd = SeengreatEPD154(baudrate=baudrate, profile=profile)

    print("probe: profile =", profile)
    print("probe: busy before reset =", epd.busy_state())
    epd.reset()
    print("probe: busy after reset =", epd.busy_state())

    print("probe: init")
    epd.init()
    print("probe: busy after init =", epd.busy_state())

    print("probe: white frame")
    epd.clear(WHITE)
    epd.display()
    print("probe: busy after white refresh =", epd.busy_state())

    print("probe: black frame")
    epd.clear(BLACK)
    epd.display()
    print("probe: busy after black refresh =", epd.busy_state())

    print("probe: sleep")
    epd.sleep()
    print("probe: busy after sleep =", epd.busy_state())
    return epd


if __name__ == "__main__":
    run()
