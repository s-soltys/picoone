from machine import Pin
from utime import sleep
import random

pin = Pin("LED", Pin.OUT)
delay = 0.2

def blink(times):
    global delay
    for _ in range(times):
        pin.on()
        sleep(delay)
        pin.off()
        sleep(delay)
        delay += random.uniform(-0.04, 0.04)
        delay = max(0.01, min(0.5, delay))

print("LED starts flashing...")
while True:
    try:
        for second in range(1, 11):
            blink(second)
            sleep(0.5)
    except KeyboardInterrupt:
        break

pin.off()
print("Finished.")
