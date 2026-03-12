import network
import urequests
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
    try:
        print("Making HTTP request to google.com...")
        response = urequests.get("http://www.google.com")
        print("Status:", response.status_code)
        if 200 <= response.status_code < 400:
            print("Success! Blinking 2 times.")
            blink(2)
        else:
            print("Request failed with status", response.status_code)
        response.close()
    except Exception as e:
        print("Request error:", e)
else:
    print("No WiFi, skipping request.")

pin.off()
print("Finished.")
