import network
import json

PROFILES_FILE = "wifi_profiles.txt"
LEGACY_PROFILES_FILE = "wifi_profiles.json"

_STAT_GOT_IP = getattr(network, "STAT_GOT_IP", 3)
_STAT_IDLE = getattr(network, "STAT_IDLE", 0)
_STAT_CONNECTING = getattr(network, "STAT_CONNECTING", 1)
_STAT_WRONG_PASSWORD = getattr(network, "STAT_WRONG_PASSWORD", -3)
_STAT_NO_AP_FOUND = getattr(network, "STAT_NO_AP_FOUND", -2)
_STAT_CONNECT_FAIL = getattr(network, "STAT_CONNECT_FAIL", -1)


def _status_label(status):
    labels = {
        _STAT_IDLE: "idle",
        _STAT_CONNECTING: "connecting",
        _STAT_WRONG_PASSWORD: "wrong_password",
        _STAT_NO_AP_FOUND: "no_ap_found",
        _STAT_CONNECT_FAIL: "connect_fail",
        _STAT_GOT_IP: "got_ip",
    }
    return labels.get(status, str(status))


def _normalize_profiles(profiles):
    out = []
    seen = set()
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        ssid = str(profile.get("ssid", "")).strip()
        if not ssid or ssid in seen:
            continue
        seen.add(ssid)
        out.append({"ssid": ssid, "password": str(profile.get("password", ""))})
    return out


def _ensure_profiles_file():
    try:
        with open(PROFILES_FILE, "r") as f:
            raw = f.read()
        if raw.strip():
            return
    except Exception:
        pass
    profiles = []
    try:
        with open(LEGACY_PROFILES_FILE, "r") as f:
            profiles = json.loads(f.read())
    except Exception:
        profiles = []
    _save_profiles(_normalize_profiles(profiles))


def _load_profiles():
    try:
        _ensure_profiles_file()
        with open(PROFILES_FILE, "r") as f:
            return _normalize_profiles(json.loads(f.read()))
    except Exception:
        return []


def _save_profiles(profiles):
    with open(PROFILES_FILE, "w") as f:
        f.write(json.dumps(_normalize_profiles(profiles)))


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


def set_profile(index, ssid, password):
    ssid = ssid.strip()
    if not ssid:
        return
    profiles = _load_profiles()
    if 0 <= index < len(profiles):
        profiles[index] = {"ssid": ssid, "password": password}
        _save_profiles(profiles)
        return
    add_profile(ssid, password)


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
    profiles = _load_profiles()
    priority = {}
    for i, profile in enumerate(profiles):
        priority[profile["ssid"]] = i
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
        networks.append(
            {
                "ssid": ssid,
                "rssi": rssi,
                "secure": auth != 0,
                "saved": ssid in priority,
            }
        )
    networks.sort(key=lambda n: (0, priority[n["ssid"]]) if n["saved"] else (1, -n["rssi"]))
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
    from utime import sleep_ms, ticks_diff, ticks_ms
    sleep_ms(500)
    if password:
        wlan.connect(ssid, password)
    else:
        wlan.connect(ssid)
    deadline = ticks_ms() + 20000
    last_status = None
    while ticks_diff(deadline, ticks_ms()) > 0:
        status = wlan.status()
        if status != last_status:
            print("WiFi status:", ssid, _status_label(status))
            last_status = status
        if wlan.isconnected() or status == _STAT_GOT_IP:
            add_profile(ssid, password)
            return True
        if status in (_STAT_WRONG_PASSWORD, _STAT_NO_AP_FOUND, _STAT_CONNECT_FAIL):
            return False
        sleep_ms(500)
    return False
