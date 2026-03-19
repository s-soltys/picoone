# PicoOne

## Wi-Fi

- The web UI is advertised as `http://pico.local/` after the Pico joins your network.
- `wifi_profiles.txt` is included in the project and is copied to the device filesystem with the rest of the app.
- Replace the example entry in `wifi_profiles.txt` with your real SSID and password before deploying.
- Saved networks are stored in `wifi_profiles.txt` in priority order.
- On boot, PicoOne tries only the saved networks in `wifi_profiles.txt`, top to bottom.
- The default `/wifi` page shows only saved networks, lets you reorder/edit/delete them, and includes a manual add/edit form for SSID and password.
- Nearby network scanning is available separately at `/wifi/scan`.
- Phone hotspots need to offer 2.4 GHz WPA/WPA2 compatibility. Pico W class devices will typically fail against 5 GHz-only or WPA3-only hotspots.
