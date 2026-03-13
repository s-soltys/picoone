import time

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


def _decode_ssid(raw):
    if isinstance(raw, bytes):
        try:
            return raw.decode("utf-8")
        except Exception:
            return str(raw)
    return str(raw)


class WiFiHelper:
    def __init__(self):
        self._wlan = None

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
                "ssid": "",
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
            "ssid": ssid,
            "ifconfig": info,
        }

    def scan(self):
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
                for raw_line in handle:
                    line = raw_line.strip("\n")
                    if not line or "\t" not in line:
                        continue
                    ssid, password = line.split("\t", 1)
                    profiles[ssid] = password
        except OSError:
            pass

        if DEFAULT_SSID and DEFAULT_SSID not in profiles:
            profiles[DEFAULT_SSID] = DEFAULT_PASSWORD
        return profiles

    def _write_profiles(self, profiles):
        with open(PROFILE_PATH, "w") as handle:
            for ssid in profiles:
                handle.write(ssid)
                handle.write("\t")
                handle.write(profiles[ssid])
                handle.write("\n")

    def get_saved_password(self, ssid):
        profiles = self.load_profiles()
        return profiles.get(ssid, "")

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

    def connect(self, ssid, password=""):
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
                    return {"ok": True, "error": "", "ifconfig": wlan.ifconfig()}
                remaining -= 1
                time.sleep(0.25)
        except Exception as exc:
            return {"ok": False, "error": str(exc), "ifconfig": None}

        return {"ok": False, "error": "connection failed", "ifconfig": None}

    def disconnect(self):
        wlan = self._wlan_if()
        if wlan is None:
            return False
        try:
            wlan.disconnect()
            return True
        except Exception:
            return False
