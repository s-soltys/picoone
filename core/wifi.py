import time

try:
    import network
except ImportError:
    network = None


AUTH_NAMES = {
    0: "OPEN",
    1: "WEP",
    2: "WPA",
    3: "WPA2",
    4: "WPA/WPA2",
    5: "WPA2",
    6: "WPA3",
}


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
