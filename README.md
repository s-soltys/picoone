# Pico Launcher

Mini smartphone-style launcher for Raspberry Pi Pico 2 W with the Waveshare Pico-LCD-1.3 display.

Hardware reference:
- https://www.waveshare.com/wiki/Pico-LCD-1.3
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
- `Top (A)`: secondary action, back, cycle, or restart depending on the app
- `Bottom (B)`: primary action, open, select, or confirm depending on the app
- `Top + Bottom`: global home shortcut, returns to the launcher from any app

Board notes:
- The launcher now targets the Pico-LCD-1.3 native `240x240` panel.
- The board also exposes `X`, `Y`, and joystick press buttons, but this repo version intentionally does not bind them yet.

App-specific notes:
- `Galaxy`: `Top (A)` jumps to the next galaxy on the overview, `Bottom (B)` enters the current target, and `Top (A)` backs out of deeper views
- `Wi-Fi`: opens on a status page, `Bottom (B)` opens the network list from status, `Top (A)` returns to status from the list/result views, and `Bottom (B)` joins or picks the highlighted item
- `Weather`: `Left/Right` switches between built-in cities, `Up/Down` toggles current conditions vs forecast, and `Bottom (B)` refreshes data
- `Calculator`: `Top (A)` deletes one character, `Bottom (B)` presses the highlighted key
- `Files`: `Top (A)` goes back, `Bottom (B)` opens a folder or file preview
- `Mines`: `Top (A)` toggles a flag while playing and restarts after a win/loss, `Bottom (B)` reveals a tile
- `Rage`: D-pad moves, `Bottom (B)` punches, `Top (A)` uses the spin attack, and `Top (A)` restarts after defeat/clear
- `Invaders`: D-pad moves, `Bottom (B)` fires, `Top (A)` restarts
- `Pac-Man`: D-pad steers, `Bottom (B)` pauses/resumes, `Top (A)` restarts
- `Arkanoid`: D-pad moves, `Bottom (B)` launches, `Top (A)` resets
- `Tetris`: D-pad moves, `Top (A)` rotates, `Bottom (B)` hard-drops
- `Paint`: D-pad moves, `Top (A)` cycles colors, `Bottom (B)` paints, and choosing white acts as erase

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
- `lcd_test.py`
- `waveshare_lcd_demo.py`
- `screentest.py`
- `ping.py`
- `wireless-test.py`

## LCD Validation

If the launcher is not booting cleanly and you want to verify the panel path by itself, run:

```python
import lcd_test
lcd_test.run()
```

What it does:
- steps the backlight through low, medium, and full brightness
- fills the panel with solid `RED`, `GREEN`, `BLUE`, `WHITE`, and `BLACK`
- draws a final `240x240` test card with diagonals, color bars, and a moving square

If you see those screens in sequence, the current [lcd.py](/Users/szymon/picotest/picoone/lcd.py) driver is talking to the Waveshare Pico-LCD-1.3 correctly.

## Direct Driver Demo

If you want an even more isolated check, run:

```python
import waveshare_lcd_demo
waveshare_lcd_demo.run()
```

This file does not import from `core/` or the launcher. It talks to the device's `lcd.py` driver directly and draws a simple Waveshare-style frame with lines, color bars, and a box, then returns immediately.

If you want the longer animated cycle instead, run:

```python
import waveshare_lcd_demo
waveshare_lcd_demo.demo_cycle()
```

## Direct Driver Debug

If the panel still stays blank, run this and copy the REPL output back:

```python
import waveshare_lcd_debug
waveshare_lcd_debug.run()
```

This script still talks directly to the device's `lcd.py` driver, but it prints the detected class name, available methods, backlight path, refresh path, and each fill/draw stage. It also tests both standard and byte-swapped RGB565 fills because some Pico LCD drivers expect swapped color values.

## Raw ST7789 Probe

If `waveshare_lcd_debug.py` logs look healthy but the panel is still blank, run:

```python
import st7789_probe
st7789_probe.run()
```

This script does not import `lcd.py` at all. It drives the Pico-LCD-1.3 pins directly with `machine.SPI`, pushes raw full-screen pixel data, and tries a few likely ST7789 addressing/color-order variants. If any attempt shows a color fill, note which attempt label printed in the REPL.

It now starts with an automatic backlight sweep (`BL MIN`, `BL LOW`, `BL MID`, `BL MAX`) so you can check brightness behavior without typing manual REPL commands.

## Button Seating Probe

If the backlight sweep works but the LCD stays blank, you can verify the board is sitting on the expected GPIO pins with:

```python
import board_button_probe
board_button_probe.run()
```

It watches the Pico-LCD board buttons for 20 seconds and prints presses/releases for `UP`, `DOWN`, `LEFT`, `RIGHT`, `A`, `B`, `CTRL`, `X`, and `Y`. If those all report correctly, the board seating and GPIO alignment are probably fine and the fault is more likely in the LCD section itself.

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

This project is written for MicroPython on Pico 2 W with the Waveshare Pico-LCD-1.3 board.

Typical flow:
1. Flash MicroPython to the board if needed.
2. Copy the project files and folders to the device.
3. Ensure `main.py` is present at the device root.
4. Reboot the board.

If you use the VS Code MicroPico workflow, upload the full repo so `core/` and `apps/` are copied alongside `main.py`.
