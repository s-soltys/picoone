import network
import json

PROFILES_FILE = "wifi_profiles.json"


def _load_profiles():
    try:
        with open(PROFILES_FILE, "r") as f:
            return json.loads(f.read())
    except Exception:
        return []


def _save_profiles(profiles):
    with open(PROFILES_FILE, "w") as f:
        f.write(json.dumps(profiles))


def get_profiles():
    return _load_profiles()


def add_profile(ssid, password):
    ssid = ssid.strip()
    if not ssid:
        return
    profiles = _load_profiles()
    # Update existing or append
    for p in profiles:
        if p["ssid"] == ssid:
            p["password"] = password
            _save_profiles(profiles)
            return
    profiles.append({"ssid": ssid, "password": password})
    _save_profiles(profiles)


def delete_profile(index):
    profiles = _load_profiles()
    if 0 <= index < len(profiles):
        profiles.pop(index)
        _save_profiles(profiles)


def move_profile(index, direction):
    """Move profile up (-1) or down (+1) in priority."""
    profiles = _load_profiles()
    new_idx = index + direction
    if 0 <= index < len(profiles) and 0 <= new_idx < len(profiles):
        profiles[index], profiles[new_idx] = profiles[new_idx], profiles[index]
        _save_profiles(profiles)


def scan_networks():
    wlan = network.WLAN(network.STA_IF)
    was_active = wlan.active()
    if not was_active:
        wlan.active(True)
    try:
        results = wlan.scan()
    except Exception:
        results = []
    networks = []
    seen = set()
    for r in results:
        ssid = r[0].decode("utf-8", "ignore").strip()
        if not ssid or ssid in seen:
            continue
        seen.add(ssid)
        rssi = r[3]
        auth = r[4]  # 0=open, others=secured
        networks.append({"ssid": ssid, "rssi": rssi, "secure": auth != 0})
    networks.sort(key=lambda n: n["rssi"], reverse=True)
    return networks


def get_current():
    wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected():
        cfg = wlan.ifconfig()
        try:
            rssi = wlan.status("rssi")
        except Exception:
            rssi = 0
        # Try to get connected SSID via config
        try:
            ssid = wlan.config("essid")
        except Exception:
            ssid = "?"
        return {"connected": True, "ssid": ssid, "ip": cfg[0], "rssi": rssi}
    return {"connected": False, "ssid": "", "ip": "", "rssi": 0}


def connect_to(ssid, password):
    """Attempt to connect to a network. Returns True on success."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.disconnect()
    from utime import sleep_ms
    sleep_ms(500)
    wlan.connect(ssid, password)
    for _ in range(30):  # up to 15s
        if wlan.isconnected():
            add_profile(ssid, password)
            return True
        sleep_ms(500)
    return False
