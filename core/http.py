try:
    import urequests as requests
except ImportError:
    try:
        import requests
    except ImportError:
        requests = None

try:
    import ujson as json
except ImportError:
    try:
        import json
    except ImportError:
        json = None

try:
    import gc
except ImportError:
    gc = None


DEFAULT_TIMEOUT = 5
_UNRESERVED = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~"


def _percent_encode(text):
    value = str(text)
    pieces = []
    for char in value:
        if char in _UNRESERVED:
            pieces.append(char)
        else:
            code = ord(char)
            if code < 0x80:
                pieces.append("%{:02X}".format(code))
            else:
                for byte in char.encode("utf-8"):
                    pieces.append("%{:02X}".format(byte))
    return "".join(pieces)


def build_url(base_url, params):
    if not params:
        return base_url

    pieces = []
    for key in params:
        value = params[key]
        if value is None:
            continue
        pieces.append(_percent_encode(key) + "=" + _percent_encode(value))

    if not pieces:
        return base_url
    return base_url + "?" + "&".join(pieces)


def get_json(url, timeout=DEFAULT_TIMEOUT):
    if requests is None:
        return {
            "ok": False,
            "status": None,
            "data": None,
            "error": "HTTP client unavailable",
        }

    response = None
    try:
        try:
            response = requests.get(url, timeout=timeout)
        except TypeError:
            response = requests.get(url)
    except Exception as exc:
        return {
            "ok": False,
            "status": None,
            "data": None,
            "error": str(exc),
        }

    try:
        status = getattr(response, "status_code", None)
        if status is not None and status >= 400:
            return {
                "ok": False,
                "status": status,
                "data": None,
                "error": "HTTP " + str(status),
            }

        try:
            data = response.json()
        except Exception:
            if json is None:
                return {
                    "ok": False,
                    "status": status,
                    "data": None,
                    "error": "JSON parser unavailable",
                }
            try:
                data = json.loads(response.text)
            except Exception as exc:
                return {
                    "ok": False,
                    "status": status,
                    "data": None,
                    "error": str(exc),
                }

        return {
            "ok": True,
            "status": status if status is not None else 200,
            "data": data,
            "error": "",
        }
    finally:
        try:
            response.close()
        except Exception:
            pass
        if gc is not None:
            gc.collect()
