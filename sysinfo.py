import gc
import network
from machine import ADC, freq
from utime import ticks_ms

_temp_adc = ADC(4)
_boot_ticks = ticks_ms()


def get_info():
    # Temperature
    raw = _temp_adc.read_u16()
    voltage = raw * 3.3 / 65535
    temp_c = 27 - (voltage - 0.706) / 0.001721

    # Memory
    gc.collect()
    free = gc.mem_free()
    alloc = gc.mem_alloc()
    total = free + alloc

    # Uptime
    up_ms = ticks_ms() - _boot_ticks
    up_s = up_ms // 1000
    hours = up_s // 3600
    mins = (up_s % 3600) // 60
    secs = up_s % 60

    # WiFi
    wlan = network.WLAN(network.STA_IF)
    rssi = 0
    ip = "N/A"
    ssid = "N/A"
    try:
        rssi = wlan.status("rssi")
    except Exception:
        pass
    try:
        ip = wlan.ifconfig()[0]
    except Exception:
        pass
    try:
        ssid = wlan.config("essid")
    except Exception:
        pass

    return {
        "temp_c": round(temp_c, 1),
        "cpu_mhz": freq() // 1_000_000,
        "ram_free_kb": free // 1024,
        "ram_total_kb": total // 1024,
        "ram_pct": (alloc * 100) // total if total else 0,
        "uptime": "{}h {:02d}m {:02d}s".format(hours, mins, secs),
        "ssid": ssid,
        "rssi": rssi,
        "ip": ip,
    }
