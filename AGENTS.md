# Agent Notes

## Overview

This repo is a MicroPython launcher shell for Raspberry Pi Pico 2 W plus the Waveshare Pico-LCD-0.96 screen.

The runtime is intentionally small:
- `main.py` boots the launcher
- `core/` contains reusable platform and UI code
- `apps/` contains user-facing launcher apps
- `galaxy.py` remains the content engine for the Galaxy app

## Architecture Rules

- Keep `main.py` thin. Startup and frame-loop logic belongs in [core/launcher.py](/Users/szymon/picotest/picoone/core/launcher.py).
- Keep GPIO button setup centralized in [core/buttons.py](/Users/szymon/picotest/picoone/core/buttons.py). Do not create raw `Pin` readers inside individual apps.
- Preserve the physical naming convention: top action button = `A`, bottom action button = `B`.
- Preserve the global `A + B` home shortcut. App code must not block or rebind it.
- Reuse [core/ui.py](/Users/szymon/picotest/picoone/core/ui.py) helpers for headers, footers, and tile styling instead of inventing per-app chrome.
- Keep memory use conservative. Prefer drawn icons and static in-memory data over large assets.
- Favor small in-code game state and drawn sprites over external assets for launcher mini-games.

## App Contract

Each app should expose:
- `app_id`
- `title`
- `accent`
- `draw_icon(lcd, cx, cy, selected)`
- `on_open(runtime)`
- `step(runtime)`

Apps are registered in [apps/__init__.py](/Users/szymon/picotest/picoone/apps/__init__.py).

`runtime` provides:
- `lcd`
- `buttons`
- `wifi`

`step(runtime)` is expected to:
- read button state
- draw one frame
- return `None` for normal operation or `"home"` if it wants to exit back to the launcher

## Input Conventions

- Use `buttons.pressed(name)` for one-shot actions.
- Use `buttons.repeat(name)` for menu/list movement.
- Use `buttons.down(name)` for continuous panning or movement.
- Let the launcher own the home gesture handling. App code should assume the launcher may interrupt any frame and return home.

## Wi-Fi Scope

The Wi-Fi app is read-only by design in this repo version.

Allowed:
- activate STA mode
- read current status
- perform scans
- render SSID/security/RSSI summaries

Not allowed unless explicitly requested:
- join networks
- store credentials
- build a password-entry UI

## Validation

When making changes:
- run a syntax-only check such as `env PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile main.py galaxy.py lcd.py core/*.py apps/*.py`
- prefer hardware-safe changes that keep the app usable even if Wi-Fi is unavailable
- document any new app controls or runtime conventions in `README.md`
