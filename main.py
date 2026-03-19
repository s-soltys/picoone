import network
from machine import Pin
from utime import sleep_ms
import secrets
from led_patterns import LEDController
from web_server import start_server, handle_client

# ---------------------------------------------------------------------------
# Wi-Fi
# ---------------------------------------------------------------------------
pin = Pin("LED", Pin.OUT)

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    network.hostname("picoone")
    if not wlan.isconnected():
        print("Connecting to", secrets.SSID)
        wlan.connect(secrets.SSID, secrets.PASSWORD)
        for _ in range(40):  # wait up to ~20 s
            if wlan.isconnected():
                break
            pin.toggle()
            sleep_ms(500)
    pin.off()
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print("Connected — IP:", ip)
        print("Also reachable at http://picoone.local/")
        return ip
    raise RuntimeError("WiFi connection failed")

# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------
# 3 quick flashes = starting up
for _ in range(3):
    pin.on(); sleep_ms(80); pin.off(); sleep_ms(80)

try:
    ip = connect_wifi()
except Exception as e:
    print("WiFi failed:", e)
    while True:
        for _ in range(3): pin.on(); sleep_ms(100); pin.off(); sleep_ms(100)
        sleep_ms(200)
        for _ in range(3): pin.on(); sleep_ms(300); pin.off(); sleep_ms(100)
        sleep_ms(200)
        for _ in range(3): pin.on(); sleep_ms(100); pin.off(); sleep_ms(100)
        sleep_ms(1000)

led = LEDController()
srv = start_server(led)
print("Open http://{}/ in a browser".format(ip))

# ---------------------------------------------------------------------------
# Main loop — service web requests + animate LED
# ---------------------------------------------------------------------------
while True:
    handle_client(srv, led)
    led.tick()