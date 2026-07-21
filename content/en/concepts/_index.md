---
title: The four-layer model
weight: 1
bookCollapseSection: false
---

# The four-layer model

Every Sovol in this knowledge base is easiest to reason about as four independent layers. Each one can be replaced without touching the others, each has its own backup and rollback story, and each fails in its own way. Almost every hard lesson here maps to exactly one layer boundary — so the layers are also how the docs are organised.

| Layer | What lives there | Vendor state | Mainline target |
| --- | --- | --- | --- |
| 1. Hardware | Host board, mainboard MCU, toolhead MCU, eMMC module, probe, camera, screen | as shipped | unchanged — you just need to know its quirks |
| 2. MCU firmware | Katapult bootloaders + Klipper apps on the MCUs | vendor fork, mixed versions | one pinned upstream commit everywhere |
| 3. OS | what boots from the eMMC | rebadged CB1 image, old Debian + old kernel | vanilla Armbian + one dtb overlay |
| 4. Application | Klipper host, Moonraker, UI, crowsnest, extras — and the config set | vendor fork + vendor scripts | stock upstream via KIAUH + your config in git |

Three properties are worth internalising before you touch anything.

**Layer 2 survives layer 3.** MCU firmware lives in the MCUs, not on the eMMC. A wiped or replaced OS does not touch it, and the CAN UUIDs derive from hardware IDs, so they stay stable across everything. A machine whose OS died boots a fresh OS and finds its MCUs exactly as they were.

**Layer 4's config is the most volatile artifact in the whole machine.** Calibration blocks, macros, and saved variables change with every tuning session, and they live on the eMMC — the layer most likely to be reflashed. Keep the config set in a git repo and re-snapshot it after every session. It's the only layer where "restore from a month-old backup" visibly hurts.

**Layer 1 is fixed but not silent.** A dead vendor port, an absent-on-late-units sensor, a camera with no hardware flip — hardware facts constrain every layer above. Read the hardware pages before planning around a feature the board may not actually have.

## Which Klipper version

Build from current Klipper `master`, not a release tag. Klipper tags rarely — roughly once a year — and the features you actually want here, eddy-probe **tap** most of all, live on `master` after the last tag. Tracking `master` (Moonraker's `channel: dev`) is normal Klipper practice; pinning an old tag mainly costs you tap and recent fixes. Whatever commit you pick, build the **host and every MCU app from the same commit** so the command dictionaries match.

## Why this approach

The choices across these docs follow from a few principles, in order:

- **Reproducibility** — everything is built from pinned upstream sources, so the exact firmware on the machine can be rebuilt from scratch by anyone. No mystery binaries.
- **Clean upstream** — track mainline Klipper with no vendor code and no carried patches. The target state is "what's running is plain upstream," with nothing to rebase.
- **Supply-chain hygiene** — flash only firmware you built from source you can read. Third-party *prebuilt* binaries — bootloaders especially — are not trusted; they appear only as an emergency rollback, and then with the caveat that you can't know what's inside them.
- **Recoverability** — take your own backups (an SWD dump, a git bundle) before touching anything, so your rollback is something you built, not something you downloaded.

## The backup matrix that makes every path cheap {#the-backup-matrix-that-makes-every-path-cheap}

| Artifact | Layer | Changes | Where to keep it |
| --- | --- | --- | --- |
| Config set (`printer.cfg`, `saved_variables.cfg`, `moonraker.conf`) | 4 | every tuning session | git, committed after every session |
| Klipper commit pin + venv package list | 4 | rarely | one line in your notes |
| Full eMMC image | 3 | rarely | one `dd` before any OS work — not after |
| MCU firmware binaries + the SWD dump | 2 | rarely | with the build artifacts |
| Nothing | 1 | — | hardware facts live in the docs |

The asymmetry is the lesson. Three of the four layers change rarely and back up trivially, while the config changes constantly and is the one people lose. Put it in git first, before any other step in any path.
