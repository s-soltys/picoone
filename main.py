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

_DISCONNECTED_ON_MS = 240
_DISCONNECTED_OFF_MS = 60
_CONNECT_TIMEOUT_MS = 20000
_STAT_GOT_IP = getattr(network, "STAT_GOT_IP", 3)
_STAT_WRONG_PASSWORD = getattr(network, "STAT_WRONG_PASSWORD", -3)
_STAT_NO_AP_FOUND = getattr(network, "STAT_NO_AP_FOUND", -2)
_STAT_CONNECT_FAIL = getattr(network, "STAT_CONNECT_FAIL", -1)
_TERMINAL_WIFI_STATUSES = (
    _STAT_WRONG_PASSWORD,
    _STAT_NO_AP_FOUND,
    _STAT_CONNECT_FAIL,
)


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


def _blink_disconnected(cycles=1):
    for _ in range(cycles):
        pin.on()
        sleep_ms(_DISCONNECTED_ON_MS)
        pin.off()
        sleep_ms(_DISCONNECTED_OFF_MS)


def _wait_for_wifi(wlan, timeout_ms=_CONNECT_TIMEOUT_MS):
    waited = 0
    interval_ms = _DISCONNECTED_ON_MS + _DISCONNECTED_OFF_MS
    last_status = None
    while waited < timeout_ms:
        status = wlan.status()
        if status != last_status:
            print("WiFi status:", status)
            last_status = status
        if wlan.isconnected() or status == _STAT_GOT_IP:
            return True
        if status in _TERMINAL_WIFI_STATUSES:
            return False
        _blink_disconnected()
        waited += interval_ms
    return wlan.isconnected()


def connect_wifi():
    network.hostname("pico")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    round_num = 0
    while not wlan.isconnected():
        wlan.active(True)
        targets = _wifi_targets()
        if not targets:
            print("WiFi: no profiles configured in wifi_profiles.txt; waiting")
            _blink_disconnected(4)
            continue
        round_num += 1
        print("WiFi retry round", round_num)
        for ssid, password in targets:
            if wlan.isconnected():
                break
            print("Connecting to", ssid)
            try:
                wlan.disconnect()
            except Exception:
                pass
            sleep_ms(300)
            try:
                if password:
                    wlan.connect(ssid, password)
                else:
                    wlan.connect(ssid)
            except Exception as e:
                print("WiFi connect error for", ssid, ":", e)
                _blink_disconnected(2)
                continue
            if _wait_for_wifi(wlan):
                add_profile(ssid, password)
                break
            print("WiFi still offline after", ssid)
        if not wlan.isconnected():
            print("WiFi offline; retrying saved networks")
            _blink_disconnected(3)
    pin.off()
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print("Connected — IP:", ip)
        print("Also reachable at http://pico.local/")
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
        _blink_disconnected(6)

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
