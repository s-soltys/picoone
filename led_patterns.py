from machine import Pin, Timer
from utime import ticks_ms, ticks_diff

pin = Pin("LED", Pin.OUT)

PATTERN_NAMES = [
    "Off",
    "On (solid)",
    "Slow blink",
    "Fast blink",
    "Heartbeat",
    "SOS",
    "Strobe",
    "Breathe",
    "Double flash",
    "Lighthouse",
    "Triple burst",
    "Candle flicker",
    "Pulse train",
    "Disco",
    "Random mix",
]

PERSIST_FILE = "led_mode.txt"


def _steps_off():
    return [(0, 1000)]


def _steps_on():
    return [(1, 1000)]


def _steps_slow_blink():
    return [(1, 500), (0, 500)]


def _steps_fast_blink():
    return [(1, 100), (0, 100)]


def _steps_heartbeat():
    return [
        (1, 100), (0, 100),
        (1, 100), (0, 600),
    ]


def _steps_sos():
    # ... --- ...
    s = []
    for _ in range(3):
        s += [(1, 100), (0, 100)]
    s += [(0, 200)]
    for _ in range(3):
        s += [(1, 300), (0, 100)]
    s += [(0, 200)]
    for _ in range(3):
        s += [(1, 100), (0, 100)]
    s += [(0, 600)]
    return s


def _steps_strobe():
    return [(1, 30), (0, 30)]


def _steps_breathe():
    # Simulate a triangular ramp with short on/off bursts
    steps = []
    # ramp up
    for i in range(1, 11):
        on = i * 10
        off = (11 - i) * 10
        steps.append((1, on))
        steps.append((0, off))
    # ramp down
    for i in range(10, 0, -1):
        on = i * 10
        off = (11 - i) * 10
        steps.append((1, on))
        steps.append((0, off))
    steps.append((0, 200))
    return steps


def _steps_double_flash():
    return [
        (1, 80), (0, 80),
        (1, 80), (0, 400),
    ]


def _steps_lighthouse():
    # Long on, long off — like a rotating beacon
    return [(1, 200), (0, 2000)]


def _steps_triple_burst():
    return [
        (1, 60), (0, 60),
        (1, 60), (0, 60),
        (1, 60), (0, 700),
    ]


def _steps_candle_flicker():
    import urandom
    steps = []
    for _ in range(20):
        on = 10 + urandom.getrandbits(6)   # 10-73 ms
        off = 5 + urandom.getrandbits(5)    # 5-36 ms
        steps.append((1, on))
        steps.append((0, off))
    return steps


def _steps_pulse_train():
    # 5 rapid pulses then a pause
    steps = []
    for _ in range(5):
        steps.append((1, 50))
        steps.append((0, 50))
    steps.append((0, 800))
    return steps


def _steps_disco():
    import urandom
    steps = []
    for _ in range(12):
        on = 20 + urandom.getrandbits(5)    # 20-51 ms
        off = 40 + urandom.getrandbits(7)   # 40-167 ms
        steps.append((1, on))
        steps.append((0, off))
    steps.append((0, 300))
    return steps


def _steps_random_mix():
    import urandom
    builders = [
        _steps_slow_blink, _steps_fast_blink, _steps_heartbeat,
        _steps_sos, _steps_strobe, _steps_breathe, _steps_double_flash,
        _steps_lighthouse, _steps_triple_burst, _steps_candle_flicker,
        _steps_pulse_train, _steps_disco,
    ]
    return builders[urandom.getrandbits(8) % len(builders)]()


BUILDERS = [
    _steps_off,
    _steps_on,
    _steps_slow_blink,
    _steps_fast_blink,
    _steps_heartbeat,
    _steps_sos,
    _steps_strobe,
    _steps_breathe,
    _steps_double_flash,
    _steps_lighthouse,
    _steps_triple_burst,
    _steps_candle_flicker,
    _steps_pulse_train,
    _steps_disco,
    _steps_random_mix,
]


class LEDController:
    def __init__(self):
        self._mode = 0
        self._steps = []
        self._idx = 0
        self._deadline = 0
        self._load_persisted()
        self._reload_steps()

    # -- persistence ---------------------------------------------------------
    def _load_persisted(self):
        try:
            with open(PERSIST_FILE, "r") as f:
                val = int(f.read().strip())
                if 0 <= val < len(BUILDERS):
                    self._mode = val
        except Exception:
            pass

    def _persist(self):
        try:
            with open(PERSIST_FILE, "w") as f:
                f.write(str(self._mode))
        except Exception:
            pass

    # -- pattern playback ----------------------------------------------------
    def _reload_steps(self):
        self._steps = BUILDERS[self._mode]()
        self._idx = 0
        self._apply()

    def _apply(self):
        if self._idx < len(self._steps):
            state, dur = self._steps[self._idx]
            pin.value(state)
            self._deadline = ticks_ms() + dur

    def set_mode(self, mode):
        if 0 <= mode < len(BUILDERS):
            self._mode = mode
            self._persist()
            self._reload_steps()

    @property
    def mode(self):
        return self._mode

    def tick(self):
        if self._idx >= len(self._steps):
            self._reload_steps()
            return
        if ticks_diff(ticks_ms(), self._deadline) >= 0:
            self._idx += 1
            if self._idx >= len(self._steps):
                self._reload_steps()
            else:
                self._apply()
