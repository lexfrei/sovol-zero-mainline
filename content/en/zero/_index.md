---
title: Sovol Zero
weight: 2
bookCollapseSection: false
---

# Sovol Zero

The Sovol Zero ships a forked Klipper — host `klippy/` plus MCU `src/` — on Sovol's all-in-one Zero control board: an Allwinner H616 Linux host plus an STM32H750 mainboard that doubles as the USB-CAN bridge, and a separate STM32F103 CAN toolhead. Everything else in the stack — Moonraker, Mainsail, Katapult, gs_usb, crowsnest, KlipperScreen — is already stock upstream. Only Klipper is forked, so that's the only thing you have to move.

This section takes the machine fully onto upstream Klipper: host plus both MCUs on one pinned commit, app *and* bootloader, with no vendor bytes left in the firmware. The one vendor layer that stays afterward is the OS image, and replacing that is optional.

## The machine, layer by layer

Read [the four-layer model]({{< relref "/concepts" >}}) once for the reasoning; then use these as the component library.

- **[Hardware]({{< relref "/zero/hardware" >}})** — the system map (host + three CAN MCUs), the toolhead pinout and SWD header, and the board's hardware facts: dead ports, absent-on-late-units sensors, camera limits.
- **[MCU firmware]({{< relref "/zero/firmware" >}})** — building both apps and Katapult from one pinned commit, the one-time SWD flash of the toolhead, and the no-SWD mainboard route over USB-Katapult.
- **[OS]({{< relref "/zero/os" >}})** — vanilla Armbian on the stock eMMC, offline preseed, the one device-tree property that separates this board from a real CB1, and recovery.
- **[Application]({{< relref "/zero/application" >}})** — the KIAUH stack, translating the config to mainline eddy/tap, plugins, calibration, and proven add-ons.

## Assemble your path

The [runbooks]({{< relref "/zero/runbooks" >}}) are the entry points. Pick the one that matches your situation and it forwards you through the layers above in the right order:

- **[Over stock firmware]({{< relref "/zero/runbooks/over-stock" >}})** — the printer works and you migrate in place.
- **[With an eMMC reader]({{< relref "/zero/runbooks/emmc-reader" >}})** — clean-slate build from a blank eMMC.
- **[Recovery]({{< relref "/zero/runbooks/recovery" >}})** — a machine that won't boot, or a bad flash to roll back.

## Key facts

- **Mainboard (STM32H750) — build it as an `STM32H743`.** The app lives at `0x8020000`, past the internal flash. Built as `MACH_STM32H743` it reaches that offset from a stock target with no patch, and H743 defaults to the validated 400 MHz clock — the H750 target builds the same offset but defaults to 480 MHz, which this board isn't validated at. Flash over USB-Katapult; the textbook 32 KiB offset bricks the stock bootloader.
- **Toolhead (STM32F103)** — Katapult at the standard 8 KiB offset, Klipper app at `0x8002000`. The vendor Katapult is request-only and can't be recovered over CAN, so the toolhead needs **one SWD flash** to install a CAN-capable mainline Katapult; after that it flashes over CAN — no probe, no opening the head.
- **Mainboard Katapult, no SWD** — replace it with mainline Katapult by building a Katapult **deployer** and flashing it through the stock bootloader over USB. A bootloader from an unknown prebuilt is exactly what you don't want on the one MCU you can't easily recover.
- **Eddy probe (LDC1612)** — use **software I2C** on mainline; the F103 hardware I2C2 throws `START_NACK` without the vendor's STM32F1 errata workarounds. On `master` it does **tap** probing.

## Status

Verified end-to-end on one printer: host and both MCUs entirely on upstream Klipper, no vendor bytes left in the firmware. Corrections and additions — other probes, other board revisions, the H750-native build route — are welcome via a PR.

## Credit

The most complete Zero-specific mainline resource is [asnajder/zero-config](https://github.com/asnajder/zero-config); cross-checking against it shaped several choices here. The sibling [Rappetor/Sovol-SV08-Mainline](https://github.com/Rappetor/Sovol-SV08-Mainline) project (same H616 + CAN family, different mainboard MCU) was the closest existing reference.

## Disclaimer

Reflashing MCU firmware can brick hardware. The mainboard is the USB-CAN bridge — a bad flash takes the whole CAN bus down. As long as Katapult survives you can re-flash over USB; only a corrupted bootloader forces SWD on the buried mainboard. **Take your own SWD dump first — that is your rollback.** Proceed at your own risk.
