# PicoOne

## Wi-Fi

- The web UI is advertised as `http://pico.local/` after the Pico joins your network.
- The Pico now serves a single-page app shell at `/`, with internal views routed by URL hash fragments such as `/#/wifi` and `/#/sysinfo`.
- Legacy paths such as `/wifi` and `/notes` redirect into the SPA so old bookmarks still work.
- The browser must be able to reach the public CDN URLs for Preact, Preact Hooks, and HTM. There is no offline fallback UI.
- `web_app.js` is part of the deployed Pico filesystem and is served locally from `/static/app.js`.
- `wifi_profiles.txt` is included in the project and is copied to the device filesystem with the rest of the app.
- Replace the example entry in `wifi_profiles.txt` with your real SSID and password before deploying.
- Saved networks are stored in `wifi_profiles.txt` in priority order.
- On boot, PicoOne keeps cycling through the saved networks in `wifi_profiles.txt` until one connects.
- While Wi-Fi is disconnected, the onboard LED uses a sustained full-bright blink pattern; the user-selected LED pattern resumes after Wi-Fi comes up.
- The Wi-Fi manager view shows saved networks, lets you reorder/edit/delete them, and includes a manual add/edit form for SSID and password.
- Nearby network scanning remains a separate SPA view at `/#/wifi/scan`.
- Phone hotspots need to offer 2.4 GHz WPA/WPA2 compatibility. Pico W class devices will typically fail against 5 GHz-only or WPA3-only hotspots.
