from machine import Pin
from utime import ticks_ms, ticks_diff, sleep_ms

_pin = Pin("LED", Pin.OUT)

# States: idle, work, break_, alert
_state = "idle"
_work_min = 25
_break_min = 5
_end_at = 0        # ticks when current phase ends
_started_at = 0


def get_status():
    if _state == "idle":
        return {"state": "idle", "remaining": 0, "work": _work_min, "brk": _break_min}
    remaining = max(0, ticks_diff(_end_at, ticks_ms()) // 1000)
    return {"state": _state, "remaining": remaining, "work": _work_min, "brk": _break_min}


def configure(work, brk):
    global _work_min, _break_min
    _work_min = max(1, min(work, 120))
    _break_min = max(1, min(brk, 60))


def start():
    global _state, _end_at, _started_at
    _state = "work"
    _started_at = ticks_ms()
    _end_at = _started_at + _work_min * 60_000


def stop():
    global _state
    _state = "idle"
    _pin.off()


def tick():
    """Called from LED thread."""
    global _state, _end_at, _started_at
    if _state == "idle":
        return

    now = ticks_ms()

    if _state == "alert":
        # Flash rapidly for 3 seconds then transition
        if ticks_diff(now, _started_at) < 3000:
            _pin.on(); sleep_ms(50); _pin.off(); sleep_ms(50)
        else:
            _state = "idle"
            _pin.off()
        return

    if ticks_diff(now, _end_at) >= 0:
        # Phase ended
        if _state == "work":
            _state = "alert"
            _started_at = now
            _end_at = now + _break_min * 60_000
            # after alert, will switch to break
            return
        elif _state == "break_":
            _state = "alert"
            _started_at = now
            return

    # LED patterns during phases
    if _state == "work":
        # Slow pulse: 1s on, 1s off
        phase = ticks_diff(now, _started_at) % 2000
        _pin.value(1 if phase < 1000 else 0)
    elif _state == "break_":
        # Fast pulse: 200ms on, 200ms off
        phase = ticks_diff(now, _started_at) % 400
        _pin.value(1 if phase < 200 else 0)


def _after_alert():
    """Called when alert finishes to transition."""
    global _state, _started_at, _end_at
    now = ticks_ms()
    # Check what comes next
    if _end_at > now:
        _state = "break_"
        _started_at = now
    else:
        _state = "idle"
        _pin.off()
