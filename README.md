# Pico Launcher

Colorful Windows 95-inspired desktop launcher for Raspberry Pi Pico 2 W with the Waveshare Pico-LCD-1.3 display.

Hardware reference:
- https://www.waveshare.com/wiki/Pico-LCD-1.3
- https://docs.micropython.org/en/latest/rp2/quickref.html

## What It Does

The device now boots into a monochrome desktop instead of jumping straight into the galaxy explorer.

Included apps:
- `Galaxy`: the original galaxy/system/planet explorer
- `PipBoy`: full-screen retro-futurist terminal with live weather, space, and market feeds
- `Wi-Fi`: status, scan, join flow, saved passwords, and boot-time reconnect to remembered networks
- `Browser`: bookmark-only faux web browser with API-backed pages
- `Server`: on-demand local web dashboard with JSON APIs while the app stays open
- `Weather`: current conditions plus a short forecast for a built-in city list using Open-Meteo
- `Calculator`: four-function on-screen calculator
- `Device Status`: small system monitor with internal sensor and runtime status
- `MTG Life`: four-player Commander life counter
- `Mines`: compact minesweeper
- `Invaders`: arcade shooter
- `Pac-Man`: maze chase
- `Arkanoid`: brick breaker
- `Tetris`: falling-block puzzle
- `Paint`: simple pixel painter

Desktop shell notes:
- the shell now boots through a black Win95-style splash screen before landing on the desktop
- the shell now leans into a tiny Windows 95-style desktop with a teal background, gray taskbar, blue title bars, beveled window chrome, and colorful desktop icons
- apps are shown as compact desktop icons in a `4x4` grid instead of launcher tiles
- the D-pad drives a desktop mouse pointer again, including the taskbar and `Start` menu, and the pointer accelerates while you hold a direction
- `Start` now lives on the bottom taskbar, with `Run...` and `About PicoOS` available from the menu
- the bottom-right tray shows Wi-Fi state and the current `HH:MM` if the device RTC is valid, otherwise it falls back to `Pico`
- utility apps such as `Wi-Fi`, `Browser`, `Server`, `Weather`, `Calc`, `Status`, and `Games` open in a Win95-style window shell with a live taskbar button
- `Y` now opens a contextual help/about dialog on the desktop and inside apps, so most static control footers are gone
- `Games`, `Calculator`, `Status`, and `Wi-Fi` now use more Explorer/control-panel style list and field chrome
- arcade apps such as `Mines`, `Invaders`, `Pac-Man`, `Arkanoid`, and `Tetris` now live inside the desktop `Games` folder
- immersive apps such as `Galaxy`, `PipBoy`, and `Paint` stay full screen

## Controls

Shared controls:
- Desktop D-pad: move the mouse pointer
- In-app D-pad: move selection / scroll / pan
- `Top (A)`: open or close `Start` on the desktop, or act as the app's secondary action
- `Bottom (B)`: primary action, open, select, or confirm depending on the app
- `Y`: open contextual help/about for the current desktop or app view
- `X`: app-specific shortcut on the desktop and in many apps
- `Top + Bottom`: global home shortcut, returns to the launcher from any app

Board notes:
- The launcher now targets the Pico-LCD-1.3 native `240x240` panel.
- The board exposes `X`, `Y`, and joystick press buttons. This repo version now reserves `Y` for contextual help and uses `X` as an app-specific shortcut in the desktop shell, utilities, and games.

App-specific notes:
- `Desktop`: D-pad moves the pointer, `Top (A)` opens or closes `Start`, `Bottom (B)` clicks the icon or taskbar item under the pointer, `X` snaps back to the current icon, and `Y` opens desktop help
- `Taskbar`: move the pointer onto `Start` or the tray, then press `Bottom (B)` to open them
- `Galaxy`: the galaxy and selector maps now show a center reticle with parallax star motion, while the system and planet views use a floating scanner window in the top-right; `Top (A)` backs out, `Bottom (B)` enters, and `X` recenters the current target or snaps the system view back to the first planet
- `PipBoy`: opens full screen with `STAT`, `DATA`, `RADIO`, and `MAP` tabs. `Left/Right` changes tabs, `Up/Down` changes the focused panel or item, `Bottom (B)` activates or refreshes the current section, `Top (A)` toggles the section mode, and `X` runs a tab-specific quick action such as full refresh, tuned-feed refresh, or map recenter
- `Wi-Fi`: open it from the tray or `Start`. It opens in a maximized network window, `Top (A)` backs out, `Bottom (B)` opens or joins, `X` rescans network lists, and `X` also cycles password keyboard pages
- `Browser`: opens on `about:bookmarks`; `Up/Down` picks bookmarks or links, `Left/Right` switches top-level sites, `Bottom (B)` opens or reloads, `Top (A)` goes back, and `X` jumps ahead to the next site
- `Server`: hosts a local web dashboard only while the app is open; `Top (A)` switches overview vs detail pages, `Bottom (B)` restarts the listener, and `X` clears request metrics
- `Weather`: `Left/Right` switches between built-in cities, `Up/Down` toggles current conditions vs forecast, `Bottom (B)` refreshes data, and `X` jumps to the next city
- `Calculator`: `Top (A)` deletes one character, `Bottom (B)` presses the highlighted key, and `X` clears the expression
- `Device Status`: shows approximate internal temperature, CPU clock, free RAM, uptime, firmware, and Wi-Fi state; `Top (A)` toggles `C/F`, `Bottom (B)` forces a fresh sample, and `X` switches between overview and extended details. If the current Pico firmware does not expose the internal ADC temp channel, it will show the sensor as unavailable instead of crashing
- `MTG Life`: full-screen four-player Commander board with one color per player; `Left/Right` picks a player, `Top (A)` is `-1`, `Bottom (B)` is `+1`, `Up/Down` changes by the active step, `X` toggles `x1` vs `x5`, and `X` + `Bottom (B)` resets the table to `40`
- `Games`: opens the arcade folder window, `Up/Down` chooses a game, `Bottom (B)` launches it, `X` jumps one page, and `Top (A)` returns to the desktop
- `Mines`: D-pad moves, `Top (A)` toggles a flag, `Bottom (B)` reveals a tile, and `X` starts a new board
- `Invaders`: D-pad moves, `Bottom (B)` fires, `Top (A)` restarts, and `X` restarts instantly
- `Pac-Man`: D-pad steers, `Bottom (B)` pauses/resumes, `Top (A)` restarts, and `X` restarts instantly
- `Arkanoid`: D-pad moves, `Bottom (B)` launches, `Top (A)` resets, and `X` restarts instantly
- `Tetris`: D-pad moves, `Down` soft-drops, `Top (A)` rotates, `Bottom (B)` hard-drops, and `X` restarts the board
- `Paint`: D-pad moves, `Top (A)` cycles colors forward, `X` cycles backward, `Bottom (B)` paints, and choosing white acts as erase

## Project Layout

- [main.py](/Users/szymon/picotest/picoone/main.py): launcher entrypoint
- [lcd.py](/Users/szymon/picotest/picoone/lcd.py): LCD driver
- [galaxy.py](/Users/szymon/picotest/picoone/galaxy.py): galaxy generation and rendering engine
- [core/controls.py](/Users/szymon/picotest/picoone/core/controls.py): canonical pin map and shared control labels
- [core/launcher.py](/Users/szymon/picotest/picoone/core/launcher.py): shared runtime and home screen
- [core/buttons.py](/Users/szymon/picotest/picoone/core/buttons.py): GPIO input handling and `A + B` home-chord detection
- [core/wifi.py](/Users/szymon/picotest/picoone/core/wifi.py): Pico W network helpers
- [core/http.py](/Users/szymon/picotest/picoone/core/http.py): small JSON fetch helper for public API-backed apps
- [core/server.py](/Users/szymon/picotest/picoone/core/server.py): tiny non-blocking local HTTP server used by the `Server` app
- [core/temperature.py](/Users/szymon/picotest/picoone/core/temperature.py): shared Pico internal temperature sampling helper
- [core/ui.py](/Users/szymon/picotest/picoone/core/ui.py): shared drawing helpers
- [apps/](/Users/szymon/picotest/picoone/apps): launcher apps
- [apps/games/](/Users/szymon/picotest/picoone/apps/games): arcade game apps shown inside the `Games` desktop folder

## Adding Apps

1. Create a new app class under `apps/`.
2. Give it `app_id`, `title`, `accent`, `draw_icon()`, `on_open()`, and `step()` methods. Add `help_lines(runtime)` when the app needs contextual control text for the shared `Y` help dialog.
3. Optionally set `launch_mode = "window"` if it should open in the shared desktop window shell above the taskbar. Omit it for full-screen apps.
4. Register it in [apps/__init__.py](/Users/szymon/picotest/picoone/apps/__init__.py).
5. Keep navigation on the shared button model, expose app-specific help through `Y`, and do not bypass the global `A + B` home gesture.

If the app is a game-like launcher item, prefer adding it under [apps/games/](/Users/szymon/picotest/picoone/apps/games) and exposing it through the `Games` folder instead of creating another top-level desktop icon.

`step(runtime)` is called once per frame. Use:
- `runtime.lcd` for drawing
- `runtime.buttons` for button state
- `runtime.wifi` for Wi-Fi status/scan helpers

## Wi-Fi App Notes

The Wi-Fi app now supports joining networks from the device itself.

It can:
- open from the taskbar tray or `Start`
- open on a status view with the current SSID plus IP, mask, gateway, and DNS details
- open a separate network list when you want to join another network
- scan and list nearby SSIDs with security markers, and horizontally scroll the selected SSID when it is too long
- connect to open networks directly
- connect to secured networks through an on-screen password keyboard
- store successful passwords in `wifi_profiles.txt` on the device
- remember the last successful network and try reconnecting to it on boot, while also accepting JSON profile entries from `wifi_profiles.txt`
- reuse credentials from `secrets.py` as a fallback for an existing known SSID

Keyboard flow:
- `A` cycles through keys
- `B` picks the highlighted key
- `123`, `ABC`, `abc`, and `!?` keys switch keyboard pages, so the flow works with only `A` and `B`
- D-pad is optional for faster navigation and page changes, but the flow is usable with only `A` and `B`

Current limits:
- hidden SSIDs are not joinable from the UI yet
- there is no WPA Enterprise flow

## Weather App Notes

The Weather app uses the public Open-Meteo API and does not require an API key.

It can:
- show current temperature, feels-like temperature, wind, and a short condition label
- show a compact 3-period forecast for the selected city
- cycle through a small built-in city list without text entry
- keep the last successful weather payload on-screen if a later refresh fails
- restore the last saved weather payload after power-off or reboot

Current limits:
- it depends on Wi-Fi connectivity and a working `urequests` client on the device
- the built-in city list is static in this repo version

## PipBoy App Notes

The PipBoy app is a full-screen Fallout-style terminal view with live data and offline fallback.

It uses:
- `Open-Meteo` for Mojave weather conditions
- NASA `APOD` for the orbital bulletin feed
- `Frankfurter` for the market tape / caps exchange panel

It can:
- show live or cached data across `STAT`, `DATA`, `RADIO`, and `MAP`
- cache the last successful weather, space, and market payloads in `pipboy_state.json`
- stay usable when Wi-Fi is down by showing stale cached content and local faux data
- tune themed radio stations, including live weather, space, and market channels
- show a faux wasteland map with live telemetry sidebars

Current limits:
- all internet-backed sections depend on Wi-Fi connectivity plus a working JSON HTTP client on the device
- the map is stylized and offline, not a real geographic tile map
- the NASA feed uses the public `DEMO_KEY`, so heavy repeated polling is not a goal for this app

## Browser App Notes

The Browser app is intentionally not a general-purpose browser. It renders a small bookmark list and turns each bookmark into a faux site built from live public API data.

Current bookmarks:
- `WeatherWire`: a weather front page built from Open-Meteo forecast data
- `Open Shelf`: a book-picks page built from Open Library search results
- `RateBoard`: a small market page built from Frankfurter exchange-rate data
- `TapList`: a city brewery guide built from Open Brewery DB

Behavior notes:
- pages are cached in memory after a successful load so a later failed refresh can still show the stale page
- the Browser app depends on Wi-Fi and the same HTTP client support as the Weather app
- this is a bookmark viewer with fake sites, not an arbitrary URL loader

## Server App Notes

The Server app exposes a small local dashboard served by the Pico itself.

It can:
- listen on port `80` only while the `Server` app is open
- serve `/` with a Bootstrap + React dashboard loaded from public CDNs
- serve `/api/status` with Wi-Fi, Pico, and server state
- serve `/api/metrics` with total requests, rolling `60s` traffic, and last-hit details
- show the preferred host as `pico.local` and always show the direct IP fallback on the device screen
- show the direct `http://<ip>/` access URL on the device screen even when `pico.local` is unavailable
- keep running request stats visible on the Pico screen while the app stays active
- keep the Pico LCD focused on server access and traffic details instead of generic device stats

Current limits:
- `pico.local` is best-effort and depends on the deployed firmware/network exposing hostname or mDNS support
- if the client browser has no internet access, the dashboard HTML still loads but the React/Bootstrap CDN assets may not

## Deploying

This project is written for MicroPython on Pico 2 W with the Waveshare Pico-LCD-1.3 board.

Typical flow:
1. Flash MicroPython to the board if needed.
2. Copy the project files and folders to the device.
3. Ensure `main.py` is present at the device root.
4. Reboot the board.

If you use the VS Code MicroPico workflow, upload the full repo so `core/` and `apps/` are copied alongside `main.py`.
