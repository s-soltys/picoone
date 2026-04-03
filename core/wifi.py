import time

try:
    import ujson as json
except ImportError:
    import json

try:
    import network
except ImportError:
    network = None

try:
    from secrets import SSID as DEFAULT_SSID
    from secrets import PASSWORD as DEFAULT_PASSWORD
except ImportError:
    DEFAULT_SSID = ""
    DEFAULT_PASSWORD = ""


AUTH_NAMES = {
    0: "OPEN",
    1: "WEP",
    2: "WPA",
    3: "WPA2",
    4: "WPA/WPA2",
    5: "WPA2",
    6: "WPA3",
}

PROFILE_PATH = "wifi_profiles.txt"
LAST_SSID_PATH = "wifi_last.txt"


def _decode_ssid(raw):
    if isinstance(raw, bytes):
        try:
            return raw.decode("utf-8")
        except Exception:
            return str(raw)
    return str(raw)


def _normalize_profiles(data):
    profiles = {}
    if isinstance(data, dict):
        for ssid in data:
            name = _decode_ssid(ssid).strip()
            if not name:
                continue
            password = data[ssid]
            profiles[name] = "" if password is None else str(password)
        return profiles

    if not isinstance(data, list):
        return profiles

    for entry in data:
        if not isinstance(entry, dict):
            continue
        ssid = _decode_ssid(entry.get("ssid", "")).strip()
        if not ssid:
            continue
        password = entry.get("password", "")
        profiles[ssid] = "" if password is None else str(password)
    return profiles


class WiFiHelper:
    AUTO_CONNECT_TIMEOUT_MS = 6000

    def __init__(self):
        self._wlan = None
        self._auto_candidates = []
        self._auto_deadline_ms = None
        self._auto_target = ""

    def supported(self):
        return network is not None

    def _wlan_if(self):
        if network is None:
            return None
        if self._wlan is None:
            self._wlan = network.WLAN(network.STA_IF)
        return self._wlan

    def status(self):
        wlan = self._wlan_if()
        if wlan is None:
            return {
                "supported": False,
                "active": False,
                "connected": False,
                "connecting": False,
                "ssid": "",
                "target": "",
                "ifconfig": None,
            }

        active = wlan.active()
        connected = active and wlan.isconnected()
        ssid = ""
        if connected:
            try:
                ssid = _decode_ssid(wlan.config("ssid"))
            except Exception:
                ssid = ""

        info = None
        if connected:
            try:
                info = wlan.ifconfig()
            except Exception:
                info = None

        return {
            "supported": True,
            "active": active,
            "connected": connected,
            "connecting": bool(self._auto_target) and active and not connected,
            "ssid": ssid,
            "target": self._auto_target,
            "ifconfig": info,
        }

    def scan(self):
        self.cancel_auto_connect()
        wlan = self._wlan_if()
        if wlan is None:
            return {"ok": False, "error": "network module unavailable", "results": []}

        try:
            if not wlan.active():
                wlan.active(True)
                time.sleep(0.15)
            raw_results = wlan.scan()
        except Exception as exc:
            return {"ok": False, "error": str(exc), "results": []}

        results = []
        for entry in raw_results:
            try:
                ssid = _decode_ssid(entry[0])
                channel = entry[2]
                rssi = entry[3]
                security = AUTH_NAMES.get(entry[4], str(entry[4]))
                hidden = bool(entry[5])
            except Exception:
                continue

            if not ssid:
                ssid = "<hidden>"

            results.append({
                "ssid": ssid,
                "channel": channel,
                "rssi": rssi,
                "security": security,
                "hidden": hidden,
            })

        results.sort(key=lambda item: item["rssi"], reverse=True)
        return {"ok": True, "error": "", "results": results}

    def load_profiles(self):
        profiles = {}
        try:
            with open(PROFILE_PATH, "r") as handle:
                raw = handle.read()
        except OSError:
            raw = ""

        raw = raw.strip()
        if raw:
            if raw[:1] in ("[", "{"):
                try:
                    profiles.update(_normalize_profiles(json.loads(raw)))
                except Exception:
                    profiles = {}
            else:
                for raw_line in raw.splitlines():
                    line = raw_line.strip("\n")
                    if not line or "\t" not in line:
                        continue
                    ssid, password = line.split("\t", 1)
                    profiles[ssid] = password

        if DEFAULT_SSID and DEFAULT_SSID not in profiles:
            profiles[DEFAULT_SSID] = DEFAULT_PASSWORD
        return profiles

    def _write_profiles(self, profiles):
        with open(PROFILE_PATH, "w") as handle:
            rows = []
            for ssid in profiles:
                rows.append({"ssid": ssid, "password": profiles[ssid]})
            handle.write(json.dumps(rows))

    def get_saved_password(self, ssid):
        profiles = self.load_profiles()
        return profiles.get(ssid, "")

    def _read_last_ssid(self):
        try:
            with open(LAST_SSID_PATH, "r") as handle:
                return handle.read().strip()
        except OSError:
            return ""

    def _write_last_ssid(self, ssid):
        if not ssid:
            return
        try:
            with open(LAST_SSID_PATH, "w") as handle:
                handle.write(ssid)
        except OSError:
            pass

    def save_profile(self, ssid, password):
        if not ssid:
            return
        profiles = self.load_profiles()
        profiles[ssid] = password
        self._write_profiles(profiles)

    def forget_profile(self, ssid):
        profiles = self.load_profiles()
        if ssid in profiles:
            del profiles[ssid]
            self._write_profiles(profiles)

    def remember_connection(self, ssid, password=None):
        if password is not None:
            self.save_profile(ssid, password)
        self._write_last_ssid(ssid)

    def _auto_connect_list(self):
        profiles = self.load_profiles()
        if not profiles:
            return []

        ordered = []
        last_ssid = self._read_last_ssid()
        if last_ssid and last_ssid in profiles:
            ordered.append((last_ssid, profiles[last_ssid]))

        for ssid in profiles:
            if ssid != last_ssid:
                ordered.append((ssid, profiles[ssid]))
        return ordered

    def cancel_auto_connect(self):
        self._auto_candidates = []
        self._auto_deadline_ms = None
        self._auto_target = ""

    def _start_next_auto_connect(self):
        wlan = self._wlan_if()
        if wlan is None:
            self.cancel_auto_connect()
            return False

        if not self._auto_candidates:
            self.cancel_auto_connect()
            return False

        ssid, password = self._auto_candidates.pop(0)
        self._auto_target = ssid
        try:
            if not wlan.active():
                wlan.active(True)
                time.sleep(0.15)
            try:
                wlan.disconnect()
                time.sleep(0.1)
            except Exception:
                pass

            if password:
                wlan.connect(ssid, password)
            else:
                try:
                    wlan.connect(ssid)
                except TypeError:
                    wlan.connect(ssid, "")
        except Exception:
            return self._start_next_auto_connect()

        self._auto_deadline_ms = time.ticks_add(time.ticks_ms(), self.AUTO_CONNECT_TIMEOUT_MS)
        return True

    def start_auto_connect(self):
        if not self.supported():
            return False
        status = self.status()
        if status["connected"] or status["connecting"]:
            return False

        self._auto_candidates = self._auto_connect_list()
        return self._start_next_auto_connect()

    def poll_auto_connect(self):
        wlan = self._wlan_if()
        if wlan is None or not self._auto_target:
            return False

        if wlan.isconnected():
            self._write_last_ssid(self._auto_target)
            self.cancel_auto_connect()
            return True

        if self._auto_deadline_ms is None:
            return False

        if time.ticks_diff(time.ticks_ms(), self._auto_deadline_ms) >= 0:
            return self._start_next_auto_connect()
        return False

    def connect(self, ssid, password=""):
        self.cancel_auto_connect()
        wlan = self._wlan_if()
        if wlan is None:
            return {"ok": False, "error": "network module unavailable", "ifconfig": None}

        try:
            if not wlan.active():
                wlan.active(True)
                time.sleep(0.15)
            try:
                wlan.disconnect()
                time.sleep(0.1)
            except Exception:
                pass

            if password:
                wlan.connect(ssid, password)
            else:
                try:
                    wlan.connect(ssid)
                except TypeError:
                    wlan.connect(ssid, "")

            remaining = 48
            while remaining > 0:
                if wlan.isconnected():
                    self._write_last_ssid(ssid)
                    return {"ok": True, "error": "", "ifconfig": wlan.ifconfig()}
                remaining -= 1
                time.sleep(0.25)
        except Exception as exc:
            return {"ok": False, "error": str(exc), "ifconfig": None}

        return {"ok": False, "error": "connection failed", "ifconfig": None}

    def disconnect(self):
        self.cancel_auto_connect()
        wlan = self._wlan_if()
        if wlan is None:
            return False
        try:
            wlan.disconnect()
            return True
        except Exception:
            return False
