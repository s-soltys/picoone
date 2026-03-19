from machine import Pin
from utime import sleep_ms

_pin = Pin("LED", Pin.OUT)

MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".",
    "F": "..-.", "G": "--.", "H": "....", "I": "..", "J": ".---",
    "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---",
    "P": ".--.", "Q": "--.-", "R": ".-.", "S": "...", "T": "-",
    "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--",
    "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--",
    "4": "....-", "5": ".....", "6": "-....", "7": "--...",
    "8": "---..", "9": "----.",
}

# Shared state so the LED thread can play it
_queue = []
_playing = False


def is_playing():
    return _playing


def enqueue(text, wpm):
    global _queue, _playing
    dot_ms = 1200 // max(wpm, 5)
    steps = []
    for ch in text.upper():
        if ch == " ":
            steps.append((0, dot_ms * 7))
            continue
        code = MORSE.get(ch)
        if not code:
            continue
        for j, sym in enumerate(code):
            if sym == ".":
                steps.append((1, dot_ms))
            else:
                steps.append((1, dot_ms * 3))
            if j < len(code) - 1:
                steps.append((0, dot_ms))
        steps.append((0, dot_ms * 3))  # inter-char gap
    steps.append((0, dot_ms * 4))  # extra gap at end
    _queue.clear()
    _queue.extend(steps)
    _playing = True


def tick():
    """Called from LED thread. Plays one step at a time (blocking per-step)."""
    global _playing
    if not _queue:
        _playing = False
        return
    state, dur = _queue.pop(0)
    _pin.value(state)
    sleep_ms(dur)
    if not _queue:
        _pin.off()
        _playing = False
