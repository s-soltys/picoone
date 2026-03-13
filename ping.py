import network
import socket
from machine import Pin
from utime import sleep
from secrets import SSID, PASSWORD

pin = Pin("LED", Pin.OUT)

def blink(times, delay=0.2):
    for _ in range(times):
        pin.on()
        sleep(delay)
        pin.off()
        sleep(delay)

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    max_wait = 10
    while max_wait > 0:
        if wlan.isconnected():
            break
        max_wait -= 1
        print("Waiting for connection...")
        sleep(1)
    if wlan.isconnected():
        print("Connected:", wlan.ifconfig())
        return True
    else:
        print("Failed to connect to WiFi")
        return False

if connect_wifi():
    while True:
        try:
            print("Pinging 192.168.0.146...")
            s = socket.socket()
            s.settimeout(3)
            s.connect(("192.168.0.146", 22))
            s.close()
            print("OK! Host is up.")
            pin.on()
            sleep(1)
            pin.off()
        except Exception as e:
            print("Ping failed:", e)
            blink(5, 0.1)
        sleep(1)
else:
    print("No WiFi, skipping request.")

pin.off()
print("Finished.")
