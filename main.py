import network
from machine import Pin
from utime import sleep_ms
import _thread
import secrets
from led_patterns import LEDController
from web_server import start_server, handle_client
import uptime
import morse
import reaction
import pomodoro

# ---------------------------------------------------------------------------
# Wi-Fi
# ---------------------------------------------------------------------------
pin = Pin("LED", Pin.OUT)

def connect_wifi():
    network.hostname("picoone")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to", secrets.SSID)
        wlan.connect(secrets.SSID, secrets.PASSWORD)
        for _ in range(40):  # wait up to ~20 s
            if wlan.isconnected():
                break
            pin.on(); sleep_ms(50); pin.off(); sleep_ms(50)
    pin.off()
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print("Connected — IP:", ip)
        print("Also reachable at http://picoone.local/")
        # Solid LED for 3 seconds to confirm connection
        pin.on()
        sleep_ms(3000)
        pin.off()
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
uptime.init()
srv = start_server(led)
print("Open http://{}/ in a browser".format(ip))

# ---------------------------------------------------------------------------
# LED animation thread (core 1)
# ---------------------------------------------------------------------------
def led_thread():
    while True:
        # Priority: morse > reaction > pomodoro > LED patterns
        if morse.is_playing():
            morse.tick()
        elif reaction.get_state()["state"] not in ("idle", "done"):
            reaction.tick()
            sleep_ms(20)
        elif reaction.get_state()["state"] == "done":
            reaction.tick()  # play blink feedback
        elif pomodoro.get_status()["state"] != "idle":
            pomodoro.tick()
            sleep_ms(20)
        else:
            led.tick()
            sleep_ms(20)
        # Periodically save uptime
        uptime.save_current()

_thread.start_new_thread(led_thread, ())
print("LED + apps running on second core")

# ---------------------------------------------------------------------------
# Main loop — web server (core 0)
# ---------------------------------------------------------------------------
while True:
    handle_client(srv, led)
    sleep_ms(10)