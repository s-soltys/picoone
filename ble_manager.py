import json

try:
    import bluetooth
except ImportError:
    try:
        import ubluetooth as bluetooth
    except ImportError:
        bluetooth = None

try:
    from micropython import const
except ImportError:
    def const(value):
        return value

try:
    from ubinascii import hexlify
except ImportError:
    from binascii import hexlify


CONFIG_FILE = "ble_config.json"
DEFAULT_NAME = "PicoOne"
DEFAULT_STATUS = "PicoOne ready"
MAX_NAME_LEN = 20
MAX_STATUS_LEN = 120
MAX_SCAN_RESULTS = 24
ADV_INTERVAL_US = 250000
SCAN_DURATION_MS = 5000
SCAN_INTERVAL_US = 30000
SCAN_WINDOW_US = 30000

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)

_FLAG_READ = const(0x0002)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)

SERVICE_UUID_STR = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
TX_UUID_STR = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
RX_UUID_STR = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"

if bluetooth is not None:
    _UART_SERVICE = (
        bluetooth.UUID(SERVICE_UUID_STR),
        (
            (bluetooth.UUID(TX_UUID_STR), _FLAG_READ | _FLAG_NOTIFY),
            (bluetooth.UUID(RX_UUID_STR), _FLAG_WRITE | _FLAG_WRITE_NO_RESPONSE),
        ),
    )
else:
    _UART_SERVICE = None


def _normalize_name(name):
    if not isinstance(name, str):
        name = str(name)
    name = name.strip()
    if not name:
        name = DEFAULT_NAME
    return name[:MAX_NAME_LEN]


def _normalize_status(text):
    if not isinstance(text, str):
        text = str(text)
    text = text.strip()
    if not text:
        text = DEFAULT_STATUS
    return text[:MAX_STATUS_LEN]


def _format_mac(raw):
    return ":".join(["%02X" % part for part in bytes(raw)])


def _hex_string(raw):
    value = hexlify(bytes(raw))
    if not isinstance(value, str):
        value = value.decode("ascii")
    return value.upper()


def _format_uuid128_le(raw):
    if len(raw) != 16:
        return _hex_string(raw)
    value = _hex_string(bytes(raw)[::-1])
    return "%s-%s-%s-%s-%s" % (
        value[0:8],
        value[8:12],
        value[12:16],
        value[16:20],
        value[20:32],
    )


def _decode_name(payload):
    data = bytes(payload or b"")
    i = 0
    while i + 1 < len(data):
        size = data[i]
        if size <= 0 or i + size >= len(data) + 1:
            break
        field_type = data[i + 1]
        field = data[i + 2 : i + 1 + size]
        if field_type in (0x08, 0x09):
            try:
                return field.decode("utf-8", "ignore")
            except Exception:
                return ""
        i += 1 + size
    return ""


def _decode_services(payload):
    services = []
    data = bytes(payload or b"")
    i = 0
    while i + 1 < len(data):
        size = data[i]
        if size <= 0 or i + size >= len(data) + 1:
            break
        field_type = data[i + 1]
        field = data[i + 2 : i + 1 + size]
        if field_type in (0x02, 0x03):
            for j in range(0, len(field), 2):
                chunk = field[j : j + 2]
                if len(chunk) == 2:
                    services.append("0x%04X" % (chunk[0] | (chunk[1] << 8)))
        elif field_type in (0x06, 0x07):
            for j in range(0, len(field), 16):
                chunk = field[j : j + 16]
                if len(chunk) == 16:
                    services.append(_format_uuid128_le(chunk))
        i += 1 + size
    return services


def _build_adv_payload(name):
    name_bytes = _normalize_name(name).encode("utf-8")
    payload = bytearray()
    payload.extend(b"\x02\x01\x06")
    if len(name_bytes) > 26:
        name_bytes = name_bytes[:26]
    payload.append(len(name_bytes) + 1)
    payload.append(0x09)
    payload.extend(name_bytes)
    return bytes(payload)


def _load_config():
    try:
        with open(CONFIG_FILE, "r") as handle:
            data = json.loads(handle.read())
            if isinstance(data, dict):
                return {
                    "name": _normalize_name(data.get("name", DEFAULT_NAME)),
                    "status": _normalize_status(data.get("status", DEFAULT_STATUS)),
                }
    except Exception:
        pass
    return {"name": DEFAULT_NAME, "status": DEFAULT_STATUS}


def _save_config(name, status):
    try:
        with open(CONFIG_FILE, "w") as handle:
            handle.write(json.dumps({"name": _normalize_name(name), "status": _normalize_status(status)}))
    except Exception:
        pass


class BLEManager:
    def __init__(self):
        config = _load_config()
        self._name = config["name"]
        self._status_text = config["status"]
        self._last_rx_text = ""
        self._ble = None
        self._tx_handle = None
        self._rx_handle = None
        self._address = ""
        self._address_type = -1
        self._advertise_requested = False
        self._advertising = False
        self._scan_active = False
        self._scan_results = []
        self._scan_index = {}
        self._resume_advertising_after_scan = False
        self._connections = {}
        self._last_error = "" if bluetooth is not None else "Bluetooth LE is unavailable in this MicroPython build."

    def _ensure_ready(self):
        if bluetooth is None:
            return False
        try:
            if self._ble is None:
                self._ble = bluetooth.BLE()
                self._ble.active(True)
                self._ble.irq(self._irq)
                try:
                    # Scanning can produce a burst of events; keep a larger buffer.
                    self._ble.config(rxbuf=2048)
                except Exception:
                    pass
                try:
                    self._ble.config(gap_name=self._name)
                except Exception:
                    pass
                ((self._tx_handle, self._rx_handle),) = self._ble.gatts_register_services((_UART_SERVICE,))
                set_buffer = getattr(self._ble, "gatts_set_buffer", None)
                if set_buffer is not None:
                    try:
                        set_buffer(self._rx_handle, MAX_STATUS_LEN, True)
                    except Exception:
                        pass
                self._write_status_value(self._status_text, notify=False)
            self._refresh_address()
            if not self._last_error.startswith("BLE scan failed:"):
                self._last_error = ""
            return True
        except Exception as exc:
            self._last_error = "Bluetooth init failed: %s" % exc
            return False

    def _refresh_address(self):
        if self._ble is None:
            return
        try:
            addr_type, addr = self._ble.config("mac")
            self._address_type = addr_type
            self._address = _format_mac(addr)
        except Exception:
            pass

    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, addr_type, addr = data
            self._connections[conn_handle] = {
                "addr_type": addr_type,
                "address": _format_mac(addr),
            }
            self._advertising = False
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            if conn_handle in self._connections:
                del self._connections[conn_handle]
            if self._advertise_requested:
                self._start_advertising()
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, attr_handle = data
            if attr_handle == self._rx_handle:
                try:
                    raw = self._ble.gatts_read(self._rx_handle)
                except Exception:
                    raw = b""
                try:
                    text = bytes(raw).decode("utf-8", "ignore").strip()
                except Exception:
                    text = ""
                self._last_rx_text = text[:MAX_STATUS_LEN]
        elif event == _IRQ_SCAN_RESULT:
            addr_type, addr, adv_type, rssi, adv_data = data
            self._record_scan_result(addr_type, addr, adv_type, rssi, adv_data)
        elif event == _IRQ_SCAN_DONE:
            self._scan_active = False
            if self._resume_advertising_after_scan and not self._connections:
                self._resume_advertising_after_scan = False
                self._start_advertising()
            else:
                self._resume_advertising_after_scan = False

    def _record_scan_result(self, addr_type, addr, adv_type, rssi, adv_data):
        address = _format_mac(addr)
        key = "%s|%s" % (addr_type, address)
        name = _decode_name(adv_data)
        services = _decode_services(adv_data)
        adv_label = {
            0: "ADV_IND",
            1: "ADV_DIRECT_IND",
            2: "ADV_SCAN_IND",
            3: "ADV_NONCONN_IND",
            4: "SCAN_RSP",
        }.get(adv_type, str(adv_type))
        item = self._scan_index.get(key)
        if item is None:
            if len(self._scan_results) >= MAX_SCAN_RESULTS:
                lowest = self._scan_results[-1]
                if lowest["rssi"] >= rssi:
                    return
                del self._scan_index[lowest["key"]]
                self._scan_results.pop()
            item = {
                "key": key,
                "address": address,
                "addr_type": addr_type,
                "rssi": rssi,
                "name": name,
                "adv_type": adv_label,
                "connectable": adv_type in (0, 1),
                "services": services,
            }
            self._scan_index[key] = item
            self._scan_results.append(item)
        else:
            item["rssi"] = max(item["rssi"], rssi)
            if name:
                item["name"] = name
            if services:
                item["services"] = services
            item["adv_type"] = adv_label
            item["connectable"] = adv_type in (0, 1)
        self._scan_results.sort(key=lambda entry: entry["rssi"], reverse=True)

    def _write_status_value(self, text, notify=True):
        self._status_text = _normalize_status(text)
        if self._ble is None or self._tx_handle is None:
            return
        payload = self._status_text.encode("utf-8")
        self._ble.gatts_write(self._tx_handle, payload)
        if notify:
            for conn_handle in list(self._connections):
                try:
                    self._ble.gatts_notify(conn_handle, self._tx_handle, payload)
                except Exception:
                    pass

    def _start_advertising(self):
        if self._ble is None:
            return False
        try:
            self._ble.gap_advertise(None)
        except Exception:
            pass
        try:
            self._ble.gap_advertise(ADV_INTERVAL_US, adv_data=_build_adv_payload(self._name))
            self._advertising = True
            self._last_error = ""
            return True
        except Exception as exc:
            self._advertising = False
            self._last_error = "Advertising failed: %s" % exc
            return False

    def configure(self, name, status_text):
        self._name = _normalize_name(name)
        _save_config(self._name, status_text)
        if self._ensure_ready():
            try:
                self._ble.config(gap_name=self._name)
            except Exception:
                pass
            self._write_status_value(status_text, notify=True)
            if self._advertise_requested:
                self._start_advertising()
        else:
            self._status_text = _normalize_status(status_text)
        return self.get_state(include_scan=True)

    def set_advertising(self, active):
        if not self._ensure_ready():
            return self.get_state(include_scan=True)
        self._advertise_requested = bool(active)
        if self._advertise_requested:
            self._start_advertising()
        else:
            try:
                self._ble.gap_advertise(None)
            except Exception:
                pass
            self._advertising = False
        return self.get_state(include_scan=True)

    def start_scan(self, duration_ms=SCAN_DURATION_MS):
        if not self._ensure_ready():
            return {"ok": False, "busy": False, "state": self.get_state(include_scan=True)}
        if self._scan_active:
            return {"ok": False, "busy": True, "state": self.get_state(include_scan=True)}
        self._scan_results = []
        self._scan_index = {}
        self._scan_active = True
        self._last_error = ""
        self._resume_advertising_after_scan = bool(self._advertise_requested and not self._connections)
        try:
            if self._resume_advertising_after_scan:
                try:
                    self._ble.gap_advertise(None)
                except Exception:
                    pass
                self._advertising = False
            # Use a passive 100% duty-cycle scan to reduce radio contention
            # while still surfacing nearby devices on Pico W class hardware.
            self._ble.gap_scan(duration_ms or SCAN_DURATION_MS, SCAN_INTERVAL_US, SCAN_WINDOW_US, False)
            return {"ok": True, "busy": False, "state": self.get_state(include_scan=True)}
        except Exception as exc:
            self._scan_active = False
            self._resume_advertising_after_scan = False
            self._last_error = "BLE scan failed: %s" % exc
            return {"ok": False, "busy": False, "state": self.get_state(include_scan=True)}

    def get_state(self, include_scan=False):
        supported = bluetooth is not None
        if supported:
            self._ensure_ready()
        connections = []
        for conn_handle in self._connections:
            info = self._connections[conn_handle]
            connections.append(
                {
                    "conn_handle": conn_handle,
                    "address": info["address"],
                    "addr_type": info["addr_type"],
                }
            )
        data = {
            "supported": supported,
            "error": self._last_error,
            "name": self._name,
            "status_text": self._status_text,
            "last_rx_text": self._last_rx_text,
            "advertising": self._advertising,
            "advertise_requested": self._advertise_requested,
            "address": self._address,
            "address_type": self._address_type,
            "connected_count": len(connections),
            "connections": connections,
            "scan_active": self._scan_active,
            "service_uuid": SERVICE_UUID_STR,
            "tx_uuid": TX_UUID_STR,
            "rx_uuid": RX_UUID_STR,
        }
        if include_scan:
            data["scan_results"] = [
                {
                    "address": entry["address"],
                    "addr_type": entry["addr_type"],
                    "rssi": entry["rssi"],
                    "name": entry["name"],
                    "adv_type": entry["adv_type"],
                    "connectable": entry["connectable"],
                    "services": entry["services"],
                }
                for entry in self._scan_results
            ]
        return data


ble_manager = BLEManager()
