from machine import Pin, SPI, PWM
import framebuf
import time


SCREEN_W = 240
SCREEN_H = 240

# colors are BGR565 byte-swapped so raw framebuf bytes display correctly
RED = 0x00F8
GREEN = 0xE007
BLUE = 0x1F00
WHITE = 0xFFFF
BLACK = 0x0000
DKRED = 0x0090
PINK = 0x1FFC
DKGRN = 0x4004
YELLOW = 0xE0FF
CYAN = 0xFF07
GRAY = 0x1084
ORANGE = 0x20FD
PURPLE = 0x1660
TEAL = 0x6F04
RUST = 0x80C2
CRIMSON = 0x05B0
BROWN = 0x228A
GOLD = 0x40DD
SLATE = 0x8F52
INDIGO = 0x1E30
MARINE = 0xB903
AMBER = 0x00FE
OLIVE = 0xE063
MAROON = 0x0060
COPPER = 0xA0CA
SAND = 0x4BCD


class PicoLCD13(framebuf.FrameBuffer):
    def __init__(self):
        self.width = SCREEN_W
        self.height = SCREEN_H

        self.cs = Pin(9, Pin.OUT)
        self.rst = Pin(12, Pin.OUT)
        self.dc = Pin(8, Pin.OUT)
        self.cs(1)
        self.dc(1)

        self.spi = SPI(
            1,
            20_000_000,
            polarity=0,
            phase=0,
            sck=Pin(10),
            mosi=Pin(11),
            miso=None,
        )
        self.backlight_pwm = PWM(Pin(13))
        self.backlight_pwm.freq(1000)

        self.buffer = bytearray(self.height * self.width * 2)
        super().__init__(self.buffer, self.width, self.height, framebuf.RGB565)

        self._init_display()
        self.backlight(1000)
        self.fill(BLACK)
        self.display()

    def _reset(self):
        self.rst(1)
        time.sleep(0.12)
        self.rst(0)
        time.sleep(0.12)
        self.rst(1)
        time.sleep(0.12)

    def write_cmd(self, cmd):
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, data):
        self.dc(1)
        self.cs(0)
        if isinstance(data, int):
            self.spi.write(bytearray([data]))
        else:
            self.spi.write(data)
        self.cs(1)

    def backlight(self, value):
        value = max(0, min(1000, value))
        duty = int(value * 65535 / 1000)
        self.backlight_pwm.duty_u16(duty)

    def _init_display(self):
        self._reset()

        self.write_cmd(0x36)
        self.write_data(0x70)

        self.write_cmd(0x3A)
        self.write_data(0x05)

        self.write_cmd(0xB2)
        self.write_data(bytearray([0x0C, 0x0C, 0x00, 0x33, 0x33]))

        self.write_cmd(0xB7)
        self.write_data(0x35)

        self.write_cmd(0xBB)
        self.write_data(0x19)

        self.write_cmd(0xC0)
        self.write_data(0x2C)

        self.write_cmd(0xC2)
        self.write_data(0x01)

        self.write_cmd(0xC3)
        self.write_data(0x12)

        self.write_cmd(0xC4)
        self.write_data(0x20)

        self.write_cmd(0xC6)
        self.write_data(0x0F)

        self.write_cmd(0xD0)
        self.write_data(bytearray([0xA4, 0xA1]))

        self.write_cmd(0xE0)
        self.write_data(
            bytearray(
                [
                    0xD0,
                    0x04,
                    0x0D,
                    0x11,
                    0x13,
                    0x2B,
                    0x3F,
                    0x54,
                    0x4C,
                    0x18,
                    0x0D,
                    0x0B,
                    0x1F,
                    0x23,
                ]
            )
        )

        self.write_cmd(0xE1)
        self.write_data(
            bytearray(
                [
                    0xD0,
                    0x04,
                    0x0C,
                    0x11,
                    0x13,
                    0x2C,
                    0x3F,
                    0x44,
                    0x51,
                    0x2F,
                    0x1F,
                    0x1F,
                    0x20,
                    0x23,
                ]
            )
        )

        self.write_cmd(0x21)
        self.write_cmd(0x11)
        time.sleep(0.12)
        self.write_cmd(0x29)
        time.sleep(0.02)

    def set_window(self, x0, y0, x1, y1):
        self.write_cmd(0x2A)
        self.write_data(bytearray([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF]))
        self.write_cmd(0x2B)
        self.write_data(bytearray([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF]))
        self.write_cmd(0x2C)

    def display(self):
        self.set_window(0, 0, self.width - 1, self.height - 1)
        self.dc(1)
        self.cs(0)
        self.spi.write(self.buffer)
        self.cs(1)


LCD = PicoLCD13
LCD_0inch96 = PicoLCD13
