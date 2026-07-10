# Bring-up — the machine as four layers, and the full path to a mainline Zero

The Sovol Zero is easiest to reason about as four independent layers. Each one can be replaced without touching the others, each has its own backup/rollback story, and each fails in its own way. Every hard lesson in this repo maps to exactly one layer boundary.

| Layer | What lives there | Vendor state | Mainline target | Detail docs |
| --- | --- | --- | --- | --- |
| 1. Hardware | H616 host board, STM32H750 mainboard MCU, STM32F103 toolhead, eMMC module, eddy coil, camera, screen | as shipped | unchanged (know its quirks) | [ARCHITECTURE.md](ARCHITECTURE.md), [PINOUT.md](PINOUT.md) |
| 2. MCU firmware | Katapult bootloaders + Klipper apps on both MCUs | vendor fork, mixed versions | one pinned upstream commit everywhere | [BUILD.md](BUILD.md), [FLASHING.md](FLASHING.md), [MIGRATION.md](MIGRATION.md) |
| 3. OS | what boots from the eMMC | rebadged CB1 image, Debian 11, kernel 5.16 | vanilla Armbian + one dtb overlay | [OS.md](OS.md) |
| 4. Application | Klipper host, Moonraker, UI, crowsnest, extras — and the config set | vendor fork + vendor scripts | stock upstream via KIAUH + your config in git | [MIGRATION.md](MIGRATION.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md) |

Three properties of the layer model worth internalizing before touching anything:

- **Layer 2 survives layer 3.** MCU firmware lives in the MCUs, not on the eMMC — a wiped or replaced OS does not touch it, and the CAN UUIDs are derived from hardware IDs, so they stay stable across everything. A machine whose OS died boots a fresh OS and finds its MCUs exactly as they were.
- **Layer 4's config is the most volatile artifact in the whole machine.** Calibration blocks, macros, and saved variables change with every tuning session, and they live on the eMMC — the layer most likely to be reflashed. Keep the config set in a git repo and re-snapshot it after every tuning session; it is the only layer where "restore from a month-old backup" visibly hurts.
- **Layer 1 is fixed but not silent.** The dead vendor part-fan port, the absent-on-late-units load cell, the camera with no hardware flip — hardware facts constrain every layer above. Read [ARCHITECTURE.md](ARCHITECTURE.md) before planning around a feature the board may not actually have.

## Path A — incremental de-vendoring (the printer works, you migrate in place)

This is the original migration path: the vendor OS stays, layers 4 and 2 move to upstream, layer 3 is optional at the end. Follow [MIGRATION.md](MIGRATION.md) — in brief:

1. **Back up everything first** (MIGRATION.md Stage 0): vendor stack rsync, SWD dump of the toolhead, and ideally a full eMMC image. The backups are what make every later step reversible.
2. **Application layer** on the vendor OS: stock Klipper/Moonraker beside the vendor stack, translate the config.
3. **MCU firmware**: build both apps + Katapult from one pinned commit ([BUILD.md](BUILD.md)), flash the toolhead once over SWD ([FLASHING.md](FLASHING.md)), the mainboard over USB-Katapult.
4. **OS** (optional, destructive, needs the eMMC pulled): [OS.md](OS.md).

## Path B — clean-slate build or recovery (fresh eMMC, dead OS, or "make it all vanilla now")

This is the path a recovery actually takes, verified end-to-end on this machine. The order inverts: OS first, application on top, MCUs usually last — and often untouched, because layer 2 survived whatever killed layer 3.

1. **Inventory your backups.** Minimum viable: the config set (git repo or any copy) and the MCU state (already-mainline MCUs need nothing; vendor MCUs need Path A steps 3). A full eMMC image makes this a restore instead of a rebuild.
2. **OS**: flash vanilla Armbian to the eMMC per [OS.md](OS.md) — CB1 board profile, the 40 MHz eMMC overlay, headless WiFi preseed. Verify before proceeding: boots, joins WiFi, `mmc DDR52` at 37.5 MHz effective in `/sys/kernel/debug/mmc*/ios`.
3. **Application stack**: KIAUH — Klipper (master), Moonraker, Mainsail + config, Crowsnest; then the extras you actually use (timelapse, Shake&Tune, Spoolman section, Obico agent). Gotchas for every one of these live in [TROUBLESHOOTING.md](TROUBLESHOOTING.md). Enable CAN (`systemd-networkd` link at 1 Mbit + `can_raw` in modules-load) and install `scipy` in the Klipper venv for the eddy probe.
4. **Config**: restore your config set — `printer.cfg` with its SAVE_CONFIG block (the eddy freq table and tap threshold live there), `saved_variables.cfg`, `moonraker.conf`. Fix absolute paths if the OS user changed. If klippy reports a missing section, that section's plugin (screen codes, Shake&Tune) hasn't been reinstalled yet — install the plugin, don't delete the section.
5. **MCUs**: if they ran mainline before, they still do — klippy connecting to both CAN UUIDs is the proof. If they're on vendor firmware, do Path A steps 3.
6. **Verify layer by layer, bottom up**: eMMC clock (layer 3), both MCUs respond (layer 2), klippy `ready` (layer 4), then a supervised first print — watch the first layer; the tap reference recovers from a config restore, but only a real print proves it.

## The backup matrix that makes both paths cheap

| Artifact | Layer | Changes | Where to keep it |
| --- | --- | --- | --- |
| Config set (`printer.cfg`, `saved_variables.cfg`, `moonraker.conf`) | 4 | every tuning session | git, committed after every session |
| Klipper commit pin + venv package list | 4 | rarely | one line in your notes |
| Full eMMC image | 3 | rarely | one `dd` before any OS work — not after |
| MCU firmware binaries + the SWD dump | 2 | rarely | with the build artifacts from [BUILD.md](BUILD.md) |
| Nothing | 1 | — | hardware facts live in [ARCHITECTURE.md](ARCHITECTURE.md) |

The asymmetry is the lesson: three of the four layers change rarely and back up trivially, while the config changes constantly and is the one people lose. Put it in git first, before any other step in either path.
