# PicoOne

## Wi-Fi

- `wifi_profiles.txt` is included in the project and is copied to the device filesystem with the rest of the app.
- Replace the example entry in `wifi_profiles.txt` with your real SSID and password before deploying.
- Saved networks are stored in `wifi_profiles.txt` in priority order.
- On boot, PicoOne tries only the saved networks in `wifi_profiles.txt`, top to bottom.
- In the web Wi-Fi page, scanned networks that are already saved are listed first and marked as saved.
