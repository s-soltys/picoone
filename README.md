# Pico Launcher

Mini smartphone-style launcher for Raspberry Pi Pico 2 W with the Waveshare Pico-LCD-0.96 display.

Hardware reference:
- https://www.waveshare.com/wiki/Pico-LCD-0.96
- https://docs.micropython.org/en/latest/rp2/quickref.html

## What It Does

The device now boots into a launcher instead of jumping straight into the galaxy explorer.

Included apps:
- `Galaxy`: the original galaxy/system/planet explorer
- `Wi-Fi`: current radio status plus real Pico W SSID scanning
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
- `Top (A)`: top action button
- `Bottom (B)`: bottom action button, open app or activate highlighted item
- `CTRL`: app-specific secondary action
- `Top + Bottom`: global home shortcut, returns to the launcher from any app

App-specific notes:
- `Galaxy`: opens with a splash screen, `CTRL` jumps to next galaxy/system, `Top` backs out one level
- `Wi-Fi`: `CTRL` rescans nearby SSIDs
- `Calculator`: `Top` deletes one character, `CTRL` clears all
- `Files`: `Top` goes up one level, `Bottom` opens folder or file preview
- `Mines`: `Bottom` reveals a tile, `CTRL` toggles flag, `Top` restarts
- `Rage`: D-pad moves, `Bottom` punches, `CTRL` uses a spin attack, `Top` restarts after defeat/clear
- `Invaders`: D-pad moves, `Bottom` fires, `Top` restarts
- `Pac-Man`: D-pad steers, `Bottom` pauses, `Top` restarts
- `Arkanoid`: D-pad moves, `Bottom` launches, `Top` restarts
- `Tetris`: D-pad moves, `Top` rotates, `Bottom` hard-drops
- `Paint`: D-pad moves, `Bottom` paints, `Top` erases, `CTRL` changes color

## Project Layout

- [main.py](/Users/szymon/picotest/picoone/main.py): launcher entrypoint
- [lcd.py](/Users/szymon/picotest/picoone/lcd.py): LCD driver
- [galaxy.py](/Users/szymon/picotest/picoone/galaxy.py): galaxy generation and rendering engine
- [core/launcher.py](/Users/szymon/picotest/picoone/core/launcher.py): shared runtime and home screen
- [core/buttons.py](/Users/szymon/picotest/picoone/core/buttons.py): GPIO input handling and `Top + Bottom` home-chord detection
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
4. Keep navigation on the shared button model and do not bypass the global `Top + Bottom` home gesture.

`step(runtime)` is called once per frame. Use:
- `runtime.lcd` for drawing
- `runtime.buttons` for button state
- `runtime.wifi` for Wi-Fi status/scan helpers

## Wi-Fi App Notes

The Wi-Fi app is intentionally status-only in v1.

It can:
- show whether station mode is active
- show IP data when already connected
- scan and list nearby SSIDs with channel, RSSI, and security summary

It does not:
- connect to networks
- store passwords
- edit `secrets.py`

## Deploying

This project is written for MicroPython on Pico 2 W.

Typical flow:
1. Flash MicroPython to the board if needed.
2. Copy the project files and folders to the device.
3. Ensure `main.py` is present at the device root.
4. Reboot the board.

If you use the VS Code MicroPico workflow, upload the full repo so `core/` and `apps/` are copied alongside `main.py`.
