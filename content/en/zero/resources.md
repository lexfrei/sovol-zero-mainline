---
title: Resources
weight: 7
---

# Plugin & patches

Two artifacts live as source in the repository, version-controlled and downloadable, and are documented here. They stay as code — the site describes them, the repo holds them.

## `sovol_codes` — the knob-screen codes plugin

The vendor Klipper fork shows numeric codes on the knob screen (`101`, `103`, the `60+` shutdown range) by **editing upstream core files in place** — `klippy/extras/homing.py`, `klippy/klippy.py`, `klippy/kinematics/corexy.py`. That couples product UI to Klipper core and is the reason the printer is stuck on a squashed vendor snapshot instead of tracking upstream.

The [`sovol_codes.py` plugin](https://github.com/lexfrei/sovol-zero-mainline/tree/main/klipper-plugin) reproduces the same screen codes with **zero core edits**, using only Klipper's public extension points:

- `gcode.register_output_handler(cb)` sees every message Klipper emits, so the descriptive text is mapped to its code (`101 x`) without touching the path that produced it.
- `register_event_handler("klippy:shutdown", …)` catches the shutdown reason for the `60+` codes (the plugin registers the vendor's renamed event too).
- The match is written to `display_status.message` directly — the same field `M117` sets, but without routing a gcode command through the dispatcher, so it works in both ready and shutdown states.

The `message → code` table is the official SOVOL ZERO screen-code list, implemented as a pure `lookup_code()` function that is fully unit-tested with no Klipper runtime required (`python3 -m unittest test_sovol_codes -v`). Install and enable are on [the plugins page]({{< relref "/zero/application/plugins" >}}).

### Fidelity limits versus the vendor screen

The reference list describes the *vendor* firmware's screen; some codes come from messages that exist only in Sovol's modified Klipper, and the screen text is not always the literal Klipper message. The plugin is deliberately honest about the gaps rather than matching invented strings:

- **Stock vs vendor coverage.** Codes whose anchor string exists in stock upstream (most of `101`–`124` plus the `60`–`72` shutdown reasons) fire on a plain `Klipper3d/klipper` checkout. Codes `73`, `109`, `110`, `117`, `123`, `125` come from vendor-only code and only fire on the vendor / a community fork that carries those messages.
- **Code 109 uses the real wording, not the list text** — the add-on raises "Toolhead probe more than ten times", so the rule anchors that string.
- **Codes 104 and 105 are emitted without the axis letter** — upstream forms them as static strings with coordinates only, so the axis index is lost before the string exists.
- **Codes 112 and 113 (LDC1612 I2C bus busy / error) are not matched at all** — no such host-side string exists; the LDC1612 reports faults as numeric enumerations from the MCU, not stable text.

This is **not** a candidate for mainline Klipper: the numeric codes are product-specific UI for Sovol's touchscreen, and Klipper deliberately keeps human-readable messages and leaves presentation to the upper layer. An opt-in `extras/` plugin on unmodified upstream is exactly the right home — the printer can follow mainline and keep its screen codes at the same time.

## Vendor patch provenance

The [`klipper-patches/`](https://github.com/lexfrei/sovol-zero-mainline/tree/main/klipper-patches) directory holds the substantive (non-version-bump) vendor commits, extracted as `git format-patch` files. They exist as a record of what the vendor changed — useful when deciding what would be lost by flashing stock Klipper or a community fork.

The on-printer Klipper is a Sovol vendor fork at 1.4.5 (`8a8b5e8`) with a **squashed** upstream history: no `Kevin O'Connor` authorship survives, so the base upstream version isn't recoverable from git. It's an opaque snapshot, not a clean rebase.

| Commit | What it does | Upstream relevance |
| --- | --- | --- |
| `503f61d` | Re-enables all input-shaper types; adds 15 mm Z headroom in the contact-probe routine | None — restores the upstream default |
| `36d4468` | Reworks the "105" Z prompt-code path during calibration | Vendor UI only |
| `e88b61c` | Adds a Z-axis lift to the eddy-current bed calibration flow | Vendor flow only |
| `9366ec4` | Refines the proprietary "101"/"103" prompt codes | Vendor UI only |

Nothing here is a fix upstream is missing. The input-shaper "unlock" only comments back in the upstream default `AUTOTUNE_SHAPERS` list that Sovol had replaced with `['mzv']` (the MZV-only lock the reviews complained about). The rest wire Sovol's proprietary on-screen prompt codes into the firmware — vendor UI instrumentation tied to the touchscreen, not bug fixes. The real concern is the reverse: the squashed fork is likely a stale upstream base carrying vendor cruft, so this printer is more likely *missing* upstream fixes than holding any.
