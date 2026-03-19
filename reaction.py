from machine import Pin
from utime import ticks_ms, ticks_diff, sleep_ms
import urandom

_pin = Pin("LED", Pin.OUT)

BEST_FILE = "reaction_best.txt"

# States: idle -> waiting -> lit -> done
_state = "idle"
_light_at = 0      # ticks when LED should turn on
_lit_at = 0         # ticks when LED turned on
_last_ms = 0        # last reaction time
_blink_queue = []   # LED blinks to play


def get_state():
    return {
        "state": _state,
        "last_ms": _last_ms,
        "best_ms": _load_best(),
    }


def _load_best():
    try:
        with open(BEST_FILE, "r") as f:
            return int(f.read().strip())
    except Exception:
        return 0


def _save_best(ms):
    with open(BEST_FILE, "w") as f:
        f.write(str(ms))


def start():
    """Begin a new round: LED will turn on after a random delay."""
    global _state, _light_at
    _state = "waiting"
    _pin.off()
    delay = 1000 + (urandom.getrandbits(12) % 4000)  # 1-5 seconds
    _light_at = ticks_ms() + delay


def react():
    """User pressed the button. Calculate reaction time."""
    global _state, _last_ms, _blink_queue
    if _state == "waiting":
        # Too early!
        _state = "idle"
        _pin.off()
        _last_ms = -1  # flag for "too early"
        return get_state()
    if _state != "lit":
        return get_state()
    _last_ms = ticks_diff(ticks_ms(), _lit_at)
    _state = "done"
    _pin.off()
    # Save best
    best = _load_best()
    if best == 0 or _last_ms < best:
        _save_best(_last_ms)
    # Blink hundreds-of-ms count (e.g. 350ms -> 3 blinks)
    count = max(1, _last_ms // 100)
    _blink_queue.clear()
    for _ in range(min(count, 20)):  # cap at 20 blinks
        _blink_queue.append((1, 150))
        _blink_queue.append((0, 150))
    _blink_queue.append((0, 500))
    return get_state()


def tick():
    """Called from the LED thread."""
    global _state, _lit_at
    if _state == "waiting":
        if ticks_diff(ticks_ms(), _light_at) >= 0:
            _pin.on()
            _lit_at = ticks_ms()
            _state = "lit"
    elif _state == "done" and _blink_queue:
        state, dur = _blink_queue.pop(0)
        _pin.value(state)
        sleep_ms(dur)
        if not _blink_queue:
            _pin.off()
            _state = "idle"
