# Sovol Zero → mainline Klipper

> **Special thanks to [asnajder/zero-config](https://github.com/asnajder/zero-config)** — the most complete Sovol-Zero-specific mainline resource out there. Cross-checking against it shaped several choices in this guide: the H743 build framing for the mainboard, the no-SWD *deployer* path for mainline Katapult, published ST-LINK recovery firmware, and a full Armbian-Trixie OS recipe. If you want one turnkey walkthrough, read that repo; this guide is a from-the-machine reference that complements it.

A practical guide to running a Sovol Zero on upstream [Klipper](https://github.com/Klipper3d/klipper) instead of Sovol's vendor fork — host plus both CAN MCUs on one upstream version, no skew. It aims at **the clean way to do it**, not at recording any one person's migration.

The printer ships a forked Klipper (host `klippy/` + MCU `src/`) on Sovol's all-in-one Zero control board — an Allwinner H616 Linux host plus an STM32H750 mainboard that doubles as the USB-CAN bridge — and a separate STM32F103 toolhead. Everything else in the stack — Moonraker, Mainsail, Katapult, gs_usb, crowsnest, KlipperScreen — is already stock upstream.

## Goals

The choices in this guide follow from a few principles, in order:

- **Reproducibility** — everything is built from pinned upstream sources, so the exact firmware on the machine can be rebuilt from scratch by anyone. No mystery binaries.
- **Clean upstream** — track mainline Klipper with no vendor code and no carried patches; everything is built from stock upstream targets (the mainboard as a stock `STM32H743`, the toolhead as a stock `STM32F103`). The target state is "what's running is plain upstream," with nothing to rebase.
- **Supply-chain hygiene** — flash only firmware you built from source you can read. Third-party *prebuilt* binaries — bootloaders especially — are not trusted: they appear here only as an emergency rollback for someone who took no backup, and then with the caveat that you can't know what's inside them.
- **Recoverability** — take your own backups (an SWD dump, a git bundle) before touching anything, so your rollback is something you built, not something you downloaded.

## Which Klipper version

**Build from current Klipper `master`, not a release tag.** Klipper tags rarely (roughly once a year), and the features you actually want here — most importantly eddy-probe **tap** ([PR #7220](https://github.com/Klipper3d/klipper/pull/7220), merged after the last tag) — live on `master`. Tracking `master` (Moonraker's `channel: dev`) is normal Klipper practice; pinning an old tag mainly costs you tap and recent fixes. Whatever commit you pick, build the **host and both MCU apps from the same commit** so the command dictionaries match.

## Contents

- **[MIGRATION.md](MIGRATION.md)** — the step-by-step procedure (host + both MCUs, from `master`).
- **[BUILD.md](BUILD.md)** — building the firmware on the printer host or on a Mac (toolchain + the macOS CPP quirk).
- **[PINOUT.md](PINOUT.md)** — toolhead pinout and the SWD header.
- **[FLASHING.md](FLASHING.md)** — the one-time SWD flash of the toolhead with a Flipper Zero / DAP Link.
- **[OS.md](OS.md)** — replacing Sovol's stock OS with Armbian Trixie (the last vendor layer, eMMC-level).
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — the system map: host + three CAN MCUs, pin maps, what is forked vs stock.
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** — what bites on mainline and how to clear it: eddy NACK / power-cycle, version-specific eddy options, the resonance-test host overrun, accelerometer noise, flashing all three for tap, fan quirks.
- **[klipper-plugin/](klipper-plugin/)** — `sovol_codes.py`, an opt-in plugin reproducing the vendor's numeric knob-screen codes on mainline.
- **[klipper-patches/](klipper-patches/)** — the vendor's Klipper modifications extracted as patches, with a provenance analysis.

## Key facts

- **Mainboard (STM32H750) — build it as an `STM32H743`.** The app lives at `0x8020000`, past the 128 KiB of internal flash (the board carries extra flash; the mechanism is discussed on [#7219](https://github.com/Klipper3d/klipper/pull/7219)). Build it as **`MACH_STM32H743`**: on current master that offset is a stock menu option (no patch), and H743 defaults to the **validated 400 MHz** clock — the `H750` target builds the same offset but defaults to 480 MHz, which this board isn't validated at. Flash over **USB-Katapult** (it's the bridge); the textbook 32 KiB offset bricks the stock bootloader. See [BUILD.md](BUILD.md).
- **Toolhead (STM32F103)** — Katapult at the standard 8 KiB offset → Klipper app at `0x8002000`. The vendor Katapult is request-only and can't be recovered over CAN, so the toolhead needs **one SWD flash** to install a CAN-capable mainline Katapult; after that it flashes over CAN — no probe, no opening the head. See [FLASHING.md](FLASHING.md).
- **Mainboard Katapult, no SWD** — replace it with mainline Katapult by **building a Katapult deployer** ([BUILD.md](BUILD.md)) and flashing it through the stock bootloader over USB. Build it from source — a bootloader from an unknown prebuilt binary is exactly what you don't want on the one MCU you can't easily recover.
- **Eddy probe (LDC1612)** — use **software I2C** on mainline; the F103 hardware I2C2 throws `START_NACK` without the vendor's STM32F1 errata workarounds. On `master` it does **tap** probing.

## Status

Done in full, this guide puts the host and both MCUs entirely on upstream Klipper — app *and* bootloader, no vendor bytes left in the firmware (the mainboard's bootloader is replaced via the USB deployer in [MIGRATION.md](MIGRATION.md) Stage 3, no SWD). This was verified end-to-end on one printer (see [Contributing](#contributing)); the only vendor layer then left is the OS image, optional to replace — see [OS.md](OS.md) for the Armbian-Trixie path.

## Credit

The sibling [Rappetor/Sovol-SV08-Mainline](https://github.com/Rappetor/Sovol-SV08-Mainline) project (same H616 + CAN family, different 512 KiB mainboard MCU) was the closest existing reference.

## Contributing

Verified on one printer. Corrections and additions — other probes, other board revisions, the H750-native build route — are welcome; open a PR.

## License

[GPLv3](LICENSE). The `klipper-plugin/` and `klipper-patches/` derive from Klipper (itself GPLv3), so the whole repository is under GPLv3 for consistency.

## Disclaimer

Reflashing MCU firmware can brick hardware. The mainboard is the USB-CAN bridge — a bad flash takes the whole CAN bus down. As long as Katapult survives you can re-flash over USB; only a corrupted bootloader forces SWD on the buried mainboard. **Take your own SWD dump first — that is your rollback.** (If you didn't and you're stuck, asnajder/zero-config publishes ST-LINK-flashable vendor recovery images, but they are third-party prebuilts of unknown provenance — emergency use only.) Proceed at your own risk.
