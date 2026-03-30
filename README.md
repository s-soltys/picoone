# Pico Launcher

Colorful Windows 95-inspired desktop launcher for Raspberry Pi Pico 2 W with the Waveshare Pico-LCD-1.3 display.

Hardware reference:
- https://www.waveshare.com/wiki/Pico-LCD-1.3
- https://docs.micropython.org/en/latest/rp2/quickref.html

## What It Does

The device now boots into a monochrome desktop instead of jumping straight into the galaxy explorer.

Included apps:
- `Galaxy`: the original galaxy/system/planet explorer
- `Wi-Fi`: status, scan, join flow, saved passwords, and boot-time reconnect to remembered networks
- `Browser`: bookmark-only faux web browser with API-backed pages
- `Weather`: current conditions plus a short forecast for a built-in city list using Open-Meteo
- `Calculator`: four-function on-screen calculator
- `Files`: fake read-only file explorer backed by a static in-memory tree
- `MTG Life`: four-player Commander life counter
- `Mines`: compact minesweeper
- `Invaders`: arcade shooter
- `Pac-Man`: maze chase
- `Arkanoid`: brick breaker
- `Tetris`: falling-block puzzle
- `Paint`: simple pixel painter

Desktop shell notes:
- the shell now leans into a tiny Windows 95-style desktop with a teal background, beveled chrome, and blue title bars
- apps are shown as compact desktop icons in a `4x4` grid instead of launcher tiles
- the D-pad drives a mouse pointer on the desktop, including the top menu bar
- Wi-Fi now lives under the `Wi-Fi` dropdown in the top bar instead of as a desktop icon
- the top-right corner shows the current `HH:MM` if the device RTC is valid, otherwise it falls back to `PicoOS`
- utility apps such as `Wi-Fi`, `Browser`, `Weather`, `Calc`, `Files`, `MTG Life`, and `Games` open in a tighter maximized window shell
- arcade apps such as `Mines`, `Invaders`, `Pac-Man`, `Arkanoid`, and `Tetris` now live inside the desktop `Games` folder
- immersive apps such as `Galaxy` and `Paint` stay full screen

## Controls

Shared controls:
- Desktop D-pad: move the mouse pointer
- In-app D-pad: move selection / scroll / pan
- `Top (A)`: secondary action, back, cycle, or restart depending on the app
- `Bottom (B)`: primary action, open, select, or confirm depending on the app
- `Top + Bottom`: global home shortcut, returns to the launcher from any app

Board notes:
- The launcher now targets the Pico-LCD-1.3 native `240x240` panel.
- The board exposes `X`, `Y`, and joystick press buttons. This repo version now uses `X` and `Y` in the Browser app and the MTG Commander life counter.

App-specific notes:
- `Desktop`: hover an icon with the pointer, `Top (A)` selects it, and `Bottom (B)` opens it
- `Desktop menu bar`: hover `Wi-Fi` and press `Top (A)` or `Bottom (B)` to open the dropdown, then click a menu item with `Bottom (B)`
- `Galaxy`: the galaxy and selector maps now show a center reticle with parallax star motion, while the system and planet views use a floating scanner window in the top-right; `Top (A)` jumps to the next galaxy on the overview, `Bottom (B)` enters the current target, and `Top (A)` backs out of deeper views
- `Wi-Fi`: open it from the top `Wi-Fi` menu. It opens in a maximized window, `Top (A)` closes back to the desktop from status, `Bottom (B)` opens the network list, and `Bottom (B)` joins the highlighted network
- `Browser`: opens on `about:bookmarks`, `Up/Down` or `X/Y` picks a bookmark, `Bottom (B)` opens a site, and once inside a page `Up/Down` chooses links or entries, `Bottom (B)` opens the selected item, `X/Y` switches top-level sites, and `Top (A)` goes back
- `Weather`: `Left/Right` switches between built-in cities, `Up/Down` toggles current conditions vs forecast, and `Bottom (B)` refreshes data
- `Calculator`: `Top (A)` deletes one character, `Bottom (B)` presses the highlighted key
- `Files`: `Top (A)` goes back, `Bottom (B)` opens a folder or file preview
- `MTG Life`: full-screen four-player Commander board with one color per player; D-pad picks a seat, `Top (A)` is `-1`, `Bottom (B)` is `+1`, `X` is `-5`, `Y` is `+5`, and pressing `X + Y` resets the table to `40`
- `Games`: opens the arcade folder window, `Up/Down` chooses a game, `Bottom (B)` launches it, and `Top (A)` returns to the desktop
- `Mines`: `Top (A)` toggles a flag while playing and restarts after a win/loss, `Bottom (B)` reveals a tile
- `Invaders`: D-pad moves, `Bottom (B)` fires, `Top (A)` restarts, and the pacing is faster than before
- `Pac-Man`: D-pad steers, `Bottom (B)` pauses/resumes, `Top (A)` restarts
- `Arkanoid`: D-pad moves, `Bottom (B)` launches, `Top (A)` resets, and the paddle/ball pace is faster than before
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
- [apps/games/](/Users/szymon/picotest/picoone/apps/games): arcade game apps shown inside the `Games` desktop folder

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
3. Optionally set `launch_mode = "window"` if it should open in a maximized desktop window. Omit it for full-screen apps.
4. Register it in [apps/__init__.py](/Users/szymon/picotest/picoone/apps/__init__.py).
5. Keep navigation on the shared button model and do not bypass the global `A + B` home gesture.

If the app is a game-like launcher item, prefer adding it under [apps/games/](/Users/szymon/picotest/picoone/apps/games) and exposing it through the `Games` folder instead of creating another top-level desktop icon.

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

## Deploying

This project is written for MicroPython on Pico 2 W with the Waveshare Pico-LCD-1.3 board.

Typical flow:
1. Flash MicroPython to the board if needed.
2. Copy the project files and folders to the device.
3. Ensure `main.py` is present at the device root.
4. Reboot the board.

If you use the VS Code MicroPico workflow, upload the full repo so `core/` and `apps/` are copied alongside `main.py`.
