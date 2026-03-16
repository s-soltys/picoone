# Pico Launcher

Mini smartphone-style launcher for Raspberry Pi Pico 2 W with the Waveshare Pico-LCD-0.96 display.

Hardware reference:
- https://www.waveshare.com/wiki/Pico-LCD-0.96
- https://docs.micropython.org/en/latest/rp2/quickref.html

## What It Does

The device now boots into a launcher instead of jumping straight into the galaxy explorer.

Included apps:
- `Galaxy`: the original galaxy/system/planet explorer
- `Wi-Fi`: status, scan, join flow, saved passwords, and boot-time reconnect to remembered networks
- `Weather`: current conditions plus a short forecast for a built-in city list using Open-Meteo
- `Calculator`: four-function on-screen calculator
- `Files`: fake read-only file explorer backed by a static in-memory tree
- `Mines`: compact minesweeper
- `Rage`: small side-scrolling beat-em-up inspired by Streets of Rage
- `Invaders`: arcade shooter
- `Pac-Man`: maze chase
- `Arkanoid`: brick breaker
- `Tetris`: falling-block puzzle
- `Paint`: simple pixel painter

## Controls

Shared controls:
- D-pad: move selection / scroll / pan
- `A`: secondary action, back, cycle, or restart depending on the app
- `B`: primary action, open, select, or confirm depending on the app
- `A + B`: global home shortcut, returns to the launcher from any app

App-specific notes:
- `Galaxy`: `A` jumps to the next galaxy on the overview, `B` enters the current target, and `A` backs out of deeper views
- `Wi-Fi`: opens on a status page, `B` opens the network list from status, `A` returns to status from the list/result views, and `B` joins or picks the highlighted item
- `Weather`: `Left/Right` switches between built-in cities, `Up/Down` toggles current conditions vs forecast, and `Bottom (B)` refreshes data
- `Calculator`: `A` deletes one character, `B` presses the highlighted key
- `Files`: `A` goes back, `B` opens a folder or file preview
- `Mines`: `A` toggles a flag while playing and restarts after a win/loss, `B` reveals a tile
- `Rage`: D-pad moves, `B` punches, `A` uses the spin attack, and `A` restarts after defeat/clear
- `Invaders`: D-pad moves, `B` fires, `A` restarts
- `Pac-Man`: D-pad steers, `B` pauses/resumes, `A` restarts
- `Arkanoid`: D-pad moves, `B` launches, `A` resets
- `Tetris`: D-pad moves, `A` rotates, `B` hard-drops
- `Paint`: D-pad moves, `A` cycles colors, `B` paints, and choosing white acts as erase

## Project Layout

- [main.py](/Users/szymon/picotest/picoone/main.py): launcher entrypoint
- [lcd.py](/Users/szymon/picotest/picoone/lcd.py): LCD driver
- [galaxy.py](/Users/szymon/picotest/picoone/galaxy.py): galaxy generation and rendering engine
- [core/controls.py](/Users/szymon/picotest/picoone/core/controls.py): canonical pin map and shared control labels
- [core/launcher.py](/Users/szymon/picotest/picoone/core/launcher.py): shared runtime and home screen
- [core/buttons.py](/Users/szymon/picotest/picoone/core/buttons.py): GPIO input handling and `A + B` home-chord detection
- [core/wifi.py](/Users/szymon/picotest/picoone/core/wifi.py): Pico W network helpers
- [core/http.py](/Users/szymon/picotest/picoone/core/http.py): small JSON fetch helper for public API-backed apps
- [core/ui.py](/Users/szymon/picotest/picoone/core/ui.py): shared drawing helpers
- [apps/](/Users/szymon/picotest/picoone/apps): launcher apps

Legacy helper scripts are still present at repo root:
- `screentest.py`
- `ping.py`
- `wireless-test.py`

## Adding Apps

1. Create a new app class under `apps/`.
2. Give it `app_id`, `title`, `accent`, `draw_icon()`, `on_open()`, and `step()` methods.
3. Register it in [apps/__init__.py](/Users/szymon/picotest/picoone/apps/__init__.py).
4. Keep navigation on the shared button model and do not bypass the global `A + B` home gesture.

`step(runtime)` is called once per frame. Use:
- `runtime.lcd` for drawing
- `runtime.buttons` for button state
- `runtime.wifi` for Wi-Fi status/scan helpers

## Wi-Fi App Notes

The Wi-Fi app now supports joining networks from the device itself.

It can:
- open on a status view with the current SSID plus IP, mask, gateway, and DNS details
- open a separate network list when you want to join another network
- scan and list nearby SSIDs with security markers, and horizontally scroll the selected SSID when it is too long
- connect to open networks directly
- connect to secured networks through an on-screen password keyboard
- store successful passwords in `wifi_profiles.txt` on the device
- remember the last successful network and try reconnecting to it on boot
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

## Deploying

This project is written for MicroPython on Pico 2 W.

Typical flow:
1. Flash MicroPython to the board if needed.
2. Copy the project files and folders to the device.
3. Ensure `main.py` is present at the device root.
4. Reboot the board.

If you use the VS Code MicroPico workflow, upload the full repo so `core/` and `apps/` are copied alongside `main.py`.
