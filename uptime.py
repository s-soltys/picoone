from utime import ticks_ms

HISTORY_FILE = "uptime_log.txt"
MAX_ENTRIES = 10
_boot_ticks = ticks_ms()
_boot_id = 0


def init():
    """Call once at boot to record a new session."""
    global _boot_id
    entries = load_entries()
    _boot_id = (entries[0]["id"] + 1) if entries else 1
    _save_entries(entries)  # just ensure file exists


def load_entries():
    try:
        with open(HISTORY_FILE, "r") as f:
            lines = f.read().strip().split("\n")
        entries = []
        for line in lines:
            if not line.strip():
                continue
            parts = line.split("|")
            if len(parts) == 2:
                entries.append({"id": int(parts[0]), "seconds": int(parts[1])})
        return entries
    except OSError:
        return []


def _save_entries(entries):
    with open(HISTORY_FILE, "w") as f:
        for e in entries:
            f.write("{}|{}\n".format(e["id"], e["seconds"]))


def save_current():
    """Append/update current session in history."""
    up_s = (ticks_ms() - _boot_ticks) // 1000
    entries = load_entries()
    # Update existing entry for this boot or add new
    found = False
    for e in entries:
        if e["id"] == _boot_id:
            e["seconds"] = up_s
            found = True
            break
    if not found:
        entries.insert(0, {"id": _boot_id, "seconds": up_s})
    # Keep only last N
    entries = entries[:MAX_ENTRIES]
    _save_entries(entries)


def get_current_uptime():
    return (ticks_ms() - _boot_ticks) // 1000


def format_duration(s):
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    if h:
        return "{}h {:02d}m {:02d}s".format(h, m, sec)
    if m:
        return "{}m {:02d}s".format(m, sec)
    return "{}s".format(sec)
