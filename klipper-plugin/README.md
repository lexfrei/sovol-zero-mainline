# `sovol_codes` — Sovol Zero knob-screen codes as an opt-in Klipper plugin

The Sovol Zero ships a vendor Klipper fork that shows numeric codes on the knob screen (`101`, `103`, the `60+` shutdown range, …). It produces them by **editing upstream core files in place**:

- `klippy/extras/homing.py` — `M117 Tip code: 101` / `103` spliced in next to the existing descriptive errors.
- `klippy/klippy.py` — a growing `message -> shutCode` table.
- `klippy/kinematics/corexy.py` — incidental churn.

That couples product UI to Klipper core and is the reason the printer is stuck on a squashed vendor snapshot instead of tracking upstream.

This plugin reproduces the same screen codes with **zero core edits**, using only Klipper's public extension points.

## How it works

- `gcode.register_output_handler(cb)` — the callback sees every message Klipper emits, so the descriptive text (`No trigger on x after full movement` — upstream already emits the short axis name via `get_name(short=True)`) is mapped to its code (`101 x`) without touching the path that produced it.
- `register_event_handler("klippy:shutdown", …)` — stock upstream calls these handlers directly from `invoke_shutdown` (after `_set_state`), so `printer.get_state_message()` already holds the reason, mapped to the `60+` code. The vendor fork renamed this to `klippy:notify_mcu_shutdown`, so the plugin registers both.
- The match is shown by writing `display_status.message` directly — the same field `M117` sets, but without routing a gcode command through the dispatcher. This matters for the shutdown codes: after a shutdown the printer is not ready and `M117` (registered without `when_not_ready`) is gone from the active handlers, so a routed `M117` would raise in `cmd_default` instead of displaying. Writing the attribute works in both ready and shutdown states and never takes the gcode mutex. If `display_status` is absent, it falls back to a deferred `M117` (reactor-scheduled, so gcode never runs from inside the output callback).

The `message -> code` table is the official **SOVOL ZERO Screen code list** (see `../SOVOL ZERO Screen code list.pdf`). The mapping itself is a pure function, `lookup_code()`, fully unit-tested with no Klipper runtime required.

## Install (on a stock Klipper checkout)

1. Flash / check out upstream `Klipper3d/klipper` (or a community fork such as `pulponair/sovol-zero-klipper-enhanced`).
2. Copy the plugin into the extras directory:

   ```bash
   cp sovol_codes.py ~/klipper/klippy/extras/sovol_codes.py
   ```

3. Enable it in `printer.cfg`:

   ```ini
   [sovol_codes]
   # enable: True   # default; set False to load the module but stay passive
   ```

4. Restart Klipper. On any enumerated condition the knob screen shows `Tip code: N`, exactly like the vendor firmware. `SOVOL_LAST_CODE` reports the most recent match.

## Run the tests

```bash
python3 -m unittest test_sovol_codes -v
```

Pure stdlib `unittest`; runs anywhere with Python 3.

## Scope

This is the **screen-code** behaviour only — the one piece of vendor logic that was wired invasively into core. The other vendor commits are either a revert to an upstream default (the input-shaper unlock) or plain config-level macros (the eddy-calibration Z-lift); neither needs a plugin. See `../klipper-patches/README.md` for the full provenance analysis.

### Fidelity limits versus the vendor screen

The reference PDF describes the **vendor** firmware's screen. Some of its codes come from messages that exist only in Sovol's modified Klipper, and the screen text is not always the literal Klipper message. Every rule was verified against both stock upstream Klipper and the vendor source; the plugin is deliberately honest about the gaps rather than matching invented strings:

- **Stock vs vendor coverage.** Codes whose anchor string exists in stock upstream (most of `101`–`124` plus the `60`–`72` shutdown reasons) fire on a plain `Klipper3d/klipper` checkout. Codes `73`, `109`, `110`, `117`, `123`, `125` come from vendor-only code (custom `fan.py` shutdowns, vendor `probe_eddy_current` strings, the vendor `z_offset_calibration` add-on) and therefore only fire on the vendor / a community fork that carries those messages. They are grouped separately in the source.
- **Code 109 uses the real wording, not the PDF text.** The PDF prints "Pressure probe more than five times", but the vendor add-on actually raises "Toolhead probe more than ten times" — the rule anchors the real string.
- **Codes 104 and 105 are emitted without the axis letter.** The screen list defines them per-axis (`104 x/y/z`, `105 x/y/z`), but upstream forms these as static strings wrapped by `move_error()` with coordinates only (`Must home axis first: <x> <y> <z> [<e>]`). The axis index is lost before the string exists, so the plugin can only surface the bare `104` / `105`.
- **Codes 112 and 113 (LDC1612 I2C bus busy / error) are not matched at all.** No such host-side string exists in stock or vendor Klipper — the LDC1612 reports faults as numeric enumerations from the MCU, not as a stable text reason. (Many other MCU faults *do* arrive as verbatim text, which is how `62`/`69`/`70` work — so this omission is specific to the LDC1612, not a general limitation.)

## Upstreamability

This is **not** a candidate for `Klipper3d/klipper` mainline: the numeric codes are product-specific UI for Sovol's touchscreen, and Klipper deliberately keeps human-readable messages, leaving presentation to the upper layer (Moonraker / the screen). The correct home for this behaviour is exactly what it is here — an opt-in `extras/` plugin layered on unmodified upstream, so the printer can follow mainline Klipper and keep its screen codes at the same time.
