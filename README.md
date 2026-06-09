# Sovol Zero → mainline Klipper

> **Special thanks to [asnajder/zero-config](https://github.com/asnajder/zero-config)** — the most complete Sovol-Zero-specific mainline resource out there. Cross-checking against it contributed several corrections folded into this guide: the H743 build framing for the mainboard, the no-SWD *deployer* path for mainline Katapult, published ST-LINK recovery firmware, and a full Armbian-Trixie OS recipe. If you want one turnkey walkthrough, read that repo; this guide is a from-the-machine reference that complements it.

A practical guide for migrating a Sovol Zero off its vendor Klipper fork onto upstream [Klipper](https://github.com/Klipper3d/klipper) — host plus both CAN MCUs, with zero version skew.

The printer ships a forked Klipper (host `klippy/` + MCU `src/`) on Sovol's all-in-one Zero control board — an Allwinner H616 Linux host plus an STM32H750 that doubles as the USB-CAN bridge — and a separate STM32F103 toolhead. Everything else in the stack — Moonraker, Mainsail, Katapult, gs_usb, crowsnest, KlipperScreen — is already stock upstream.

## Contents

- **[MIGRATION.md](MIGRATION.md)** — the step-by-step procedure (host + both MCUs).
- **[BUILD.md](BUILD.md)** — building the firmware on the printer host or on a Mac (toolchain + the macOS CPP quirk).
- **[PINOUT.md](PINOUT.md)** — toolhead pinout and the SWD header.
- **[FLASHING.md](FLASHING.md)** — flashing over SWD with a Flipper Zero / DAP Link (verified on the F103 toolhead).
- **[OS.md](OS.md)** — replacing Sovol's stock OS with Armbian Trixie (the last vendor layer, eMMC-level).
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — the system map: host + three CAN MCUs, pin maps, what is forked vs stock.
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** — what bites on mainline and how to clear it: eddy NACK / power-cycle, the resonance-test host overrun, accelerometer noise, version-specific eddy options, fan quirks.
- **[klipper-plugin/](klipper-plugin/)** — `sovol_codes.py`, an opt-in plugin reproducing the vendor's numeric knob-screen codes on mainline.
- **[klipper-patches/](klipper-patches/)** — the vendor's Klipper modifications extracted as patches, with a provenance analysis.

## Key facts

- **F103 toolhead** — Katapult at the standard 8 KiB offset → Klipper app at `0x8002000`. Flash via SWD (the vendor Katapult is request-only and cannot be recovered over CAN once an app is broken). See [PINOUT.md](PINOUT.md).
- **H750 mainboard** — the app lives at `0x8020000`, past the 128 KiB of internal flash. The board carries extra flash (believed QSPI, per the discussion on [Klipper3d/klipper#7219](https://github.com/Klipper3d/klipper/pull/7219)); the stock Katapult runs the app there at a 128 KiB offset. Build with `STM32_FLASH_START_20000` and flash over USB-Katapult — the textbook 32 KiB offset bricks the stock bootloader. Upstream support is landing in [Klipper3d/klipper#7219](https://github.com/Klipper3d/klipper/pull/7219) + [Arksine/katapult#177](https://github.com/Arksine/katapult/pull/177).
- **Eddy probe (LDC1612)** — use **software I2C** on mainline; the F103 hardware I2C2 throws `START_NACK` without the vendor's STM32F1 errata workarounds.

## Status

Host + both MCUs run mainline Klipper with zero version skew. Two vendor layers remain for a fully clean-room mainline, and neither is a dead end:

- **The H750's Katapult bootloader** (the Klipper app on it is already mainline). Mainline Katapult can replace it **over USB, no SWD** — a Katapult *deployer* flashed through the stock bootloader installs it in place (see [MIGRATION.md](MIGRATION.md); upstream support in [Arksine/katapult#177](https://github.com/Arksine/katapult/pull/177)).
- **The OS/eMMC image** — replaceable with Armbian Trixie; see [OS.md](OS.md).

Exact vendor rollback of the H750 is also possible now: ST-LINK-flashable vendor recovery firmware is published in [asnajder/zero-config](https://github.com/asnajder/zero-config).

## Credit

The sibling [Rappetor/Sovol-SV08-Mainline](https://github.com/Rappetor/Sovol-SV08-Mainline) project (same H616 + CAN family, different 512 KiB mainboard MCU) was the closest existing reference.

## Contributing

Verified on one printer. Corrections and additions — other probes, the H750 over SWD, other board revisions — are welcome; open a PR.

## License

[GPLv3](LICENSE). The `klipper-plugin/` and `klipper-patches/` derive from Klipper (itself GPLv3), so the whole repository is under GPLv3 for consistency.

## Disclaimer

Reflashing MCU firmware can brick hardware. The H750 is the USB-CAN bridge — a bad flash takes the whole CAN bus down. As long as Katapult survives you can re-flash over USB; only a corrupted bootloader forces SWD on the buried mainboard (ST-LINK-flashable vendor recovery firmware exists — see [asnajder/zero-config](https://github.com/asnajder/zero-config)). Keep a rollback and proceed at your own risk.
