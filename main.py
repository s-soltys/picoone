import network
from machine import Pin
from utime import sleep_ms
import _thread
from led_patterns import LEDController
from web_server import start_server, handle_client
import morse
from wifi_manager import get_profiles, add_profile

# ---------------------------------------------------------------------------
# Wi-Fi
# ---------------------------------------------------------------------------
pin = Pin("LED", Pin.OUT)


def _wifi_targets():
    targets = []
    seen = set()
    for profile in get_profiles():
        ssid = profile.get("ssid", "").strip()
        if not ssid or ssid in seen:
            continue
        seen.add(ssid)
        targets.append((ssid, profile.get("password", "")))
    return targets

def connect_wifi():
    network.hostname("picoone")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        targets = _wifi_targets()
        if not targets:
            raise RuntimeError("No WiFi profiles configured in wifi_profiles.txt")
        for ssid, password in targets:
            print("Connecting to", ssid)
            try:
                wlan.disconnect()
            except Exception:
                pass
            sleep_ms(500)
            wlan.connect(ssid, password)
            for _ in range(40):  # wait up to ~20 s
                if wlan.isconnected():
                    add_profile(ssid, password)
                    break
                pin.on(); sleep_ms(50); pin.off(); sleep_ms(50)
            if wlan.isconnected():
                break
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
srv = start_server(led)
print("Open http://{}/ in a browser".format(ip))

# ---------------------------------------------------------------------------
# LED animation thread (core 1)
# ---------------------------------------------------------------------------
def led_thread():
    while True:
        if morse.is_playing():
            morse.tick()
        else:
            led.tick()
            sleep_ms(20)

_thread.start_new_thread(led_thread, ())
print("LED + apps running on second core")

# ---------------------------------------------------------------------------
# Main loop — web server (core 0)
# ---------------------------------------------------------------------------
while True:
    handle_client(srv, led)
