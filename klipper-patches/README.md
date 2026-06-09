# Sovol Zero — Klipper vendor patches

These are the substantive (non-version-bump) commits from the Klipper that ships on the Sovol Zero, extracted as `git format-patch` files. Each can be replayed onto a Klipper checkout with `git am < NN-*.patch`, or just read as a diff.

## Provenance

The on-printer Klipper is a Sovol vendor fork served from their internal Gitea (`origin http://<sovol-lan>/root/klipper.git`), at version 1.4.5 (`8a8b5e8`, branch `main`). The upstream history is squashed: there is no `Kevin O'Connor` (upstream maintainer) authorship anywhere in the log — the most recent 200 commits are all Sovol-internal authors (`zcsw`, `focczi`, `Sovol3d`, `root`). So the base upstream version is not recoverable from git, and the tree is an opaque vendor snapshot rather than a clean rebase on upstream.

## The patches

| File | Commit | What it does | Files touched | Upstream relevance |
| --- | --- | --- | --- | --- |
| `01-input-shaper-unlock-503f61d.patch` | `503f61d` | Re-enables all input-shaper types; adds 15 mm Z headroom in the contact-probe Z-offset routine | `extras/shaper_calibrate.py`, `extras/z_offset_calibration.py`, `extras/display/menu.cfg` | None — see below |
| `02-fix-calib-105-z-code-36d4468.patch` | `36d4468` | Reworks the "105" Z prompt-code path during calibration | `config/printer.cfg`, `extras/z_offset_calibration.py`, `extras/display/menu.cfg` | Vendor UI only |
| `03-eddy-calib-z-lift-e88b61c.patch` | `e88b61c` | Adds a Z-axis lift to the eddy-current bed calibration flow | `klippy.py`, `extras/display/menu.cfg` | Vendor flow only |
| `04-refine-prompt-codes-101-103-9366ec4.patch` | `9366ec4` | Refines the proprietary "101"/"103" prompt codes | `extras/homing.py`, `kinematics/corexy.py`, `extras/display/menu.cfg` | Vendor UI only |

## Are these fixes needed upstream? No

Nothing here is a fix that upstream Klipper is missing:

- **The input-shaper "unlock" only restores the upstream default.** The diff comments back in `AUTOTUNE_SHAPERS = ['zv', 'mzv', 'ei', '2hump_ei', '3hump_ei']` — which is exactly the upstream value in `shaper_calibrate.py`. Sovol had replaced it with `['mzv']` (the MZV-only lock the printer reviews complained about) and this commit reverts that self-inflicted restriction. Upstream never had the lock, so there is nothing to merge.
- **The rest wire Sovol's proprietary on-screen "prompt codes" (101/103/105) into the firmware.** They edit the vendor screen menu (`extras/display/menu.cfg`), the machine config (`config/printer.cfg`), the vendor contact-probe add-on (`extras/z_offset_calibration.py`, which is not an upstream file), and — invasively — upstream core files (`klippy.py`, `extras/homing.py`, `kinematics/corexy.py`) to inject those numeric codes into error/homing paths. These are vendor UI instrumentation tied to Sovol's touchscreen, not bug fixes; upstream would not take hardcoded vendor codes.

Practical reading: keep these only as a record of what the vendor changed (useful when deciding what would be lost by flashing stock `Klipper3d/klipper` or a community fork such as `pulponair/sovol-zero-klipper-enhanced`). The actual concern is the reverse of "upstream is missing these" — the squashed fork is likely a stale upstream base carrying vendor cruft, so this printer is more likely missing upstream fixes than holding any.
