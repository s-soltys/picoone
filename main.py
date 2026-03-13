from machine import Pin
from utime import sleep

pin = Pin("LED", Pin.OUT)
pin.on()

import galaxy
galaxy.run()