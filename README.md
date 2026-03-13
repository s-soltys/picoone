# Pico Launcher

Mini smartphone-style launcher for Raspberry Pi Pico 2 W with the Waveshare Pico-LCD-0.96 display.

Hardware reference:
- https://www.waveshare.com/wiki/Pico-LCD-0.96
- https://docs.micropython.org/en/latest/rp2/quickref.html

## What It Does

The device now boots into a launcher instead of jumping straight into the galaxy explorer.

Included apps:
- `Galaxy`: the original galaxy/system/planet explorer
- `Wi-Fi`: status, scan, join flow, and saved passwords
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
- `Wi-Fi`: `A` scans in list/result views and advances the keyboard carousel, `B` joins or picks the highlighted item
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
- show current connection state and IP data
- scan and list nearby SSIDs with signal/security summary
- connect to open networks directly
- connect to secured networks through an on-screen password keyboard
- store successful passwords in `wifi_profiles.txt` on the device
- reuse credentials from `secrets.py` as a fallback for an existing known SSID

Keyboard flow:
- `A` cycles through keys
- `B` picks the highlighted key
- `123`, `ABC`, `abc`, and `!?` keys switch keyboard pages, so the flow works with only `A` and `B`
- D-pad is optional for faster navigation and page changes, but the flow is usable with only `A` and `B`

Current limits:
- hidden SSIDs are not joinable from the UI yet
- there is no WPA Enterprise flow

## Deploying

This project is written for MicroPython on Pico 2 W.

Typical flow:
1. Flash MicroPython to the board if needed.
2. Copy the project files and folders to the device.
3. Ensure `main.py` is present at the device root.
4. Reboot the board.

If you use the VS Code MicroPico workflow, upload the full repo so `core/` and `apps/` are copied alongside `main.py`.
