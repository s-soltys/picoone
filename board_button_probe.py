import time

from machine import Pin


BUTTON_PINS = {
    "UP": 2,
    "DOWN": 18,
    "LEFT": 16,
    "RIGHT": 20,
    "A": 15,
    "B": 17,
    "CTRL": 3,
    "X": 19,
    "Y": 21,
}


def _log(message):
    print("[button-probe]", message)


def run(duration_s=20):
    led = None
    try:
        led = Pin("LED", Pin.OUT)
    except Exception:
        led = None

    pins = {}
    last = {}
    for name, gpio in BUTTON_PINS.items():
        pins[name] = Pin(gpio, Pin.IN, Pin.PULL_UP)
        last[name] = pins[name].value()

    _log("watching buttons for %ds" % duration_s)
    _log("press board buttons now: UP DOWN LEFT RIGHT A B CTRL X Y")

    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < duration_s * 1000:
        any_pressed = False
        for name, pin in pins.items():
            value = pin.value()
            if value == 0:
                any_pressed = True
            if value != last[name]:
                state = "pressed" if value == 0 else "released"
                _log("%s on GP%d %s" % (name, BUTTON_PINS[name], state))
                last[name] = value
        if led is not None:
            led.value(1 if any_pressed else 0)
        time.sleep(0.03)

    if led is not None:
        led.value(0)
    _log("done")


if __name__ == "__main__":
    run()
