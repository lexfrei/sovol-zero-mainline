# Building the firmware

The MCU firmware (Katapult + Klipper) can be built either **on the printer's own host** or **on a Mac / Linux box**, then the `.bin` copied over. Both produce identical images — pick whichever is handy.

## Toolchain

### On the printer host (the Sovol Zero board's Allwinner H616, Debian aarch64)

`arm-none-eabi-gcc` is already installed — it's the vendor's own build chain. Clone the sources and build in place; no extra setup, and none of the macOS quirk below:

```bash
make CROSS_PREFIX=arm-none-eabi-
```

### On macOS

```bash
brew install --cask gcc-arm-embedded
```

It installs to `/Applications/ArmGNUToolchain/<version>/arm-none-eabi/bin/` (e.g. `15.2.rel1`) and is **not** added to `PATH`. Build with the full prefix and **override `CPP`**:

```bash
TC=/Applications/ArmGNUToolchain/<version>/arm-none-eabi/bin
make CROSS_PREFIX=$TC/arm-none-eabi- CPP=$TC/arm-none-eabi-cpp
```

The `CPP` override is mandatory on macOS: Klipper's Makefile preprocesses the linker script with `cpp`, which is clang there and dies with `cc: error: no input files`. On the host this isn't needed (its `cpp` is gcc).

## What to build

Build all four images from the **same Klipper `master` commit** (and a matching [Arksine/katapult](https://github.com/Arksine/katapult) checkout). Seed each `.config` from the vendor's on-disk one and fix the offset — the vendor `.config*` files claim `0x8000000`, which is stale (see [MIGRATION.md](MIGRATION.md)).

| Image | Target / seed | Offset option | App address | Save the output as |
| --- | --- | --- | --- | --- |
| Toolhead Katapult | F103, **`CANSERIAL`**, 8 MHz, CAN PB8/PB9 — seed `.config103` | — | `0x8000000` | `katapult-f103.bin` |
| Toolhead Klipper | F103, seed `.config103` | `STM32_FLASH_START_2000` | `0x8002000` | `klipper-f103.bin` |
| Mainboard Katapult **deployer** | **`MACH_STM32H743`** (+ `BUILD_DEPLOYER`) | `STM32_FLASH_START_20000` | `0x8020000` | `deployer-mainboard.bin` |
| Mainboard Klipper | **`MACH_STM32H743`**, seed `.config750` | `STM32_FLASH_START_20000` | `0x8020000` | `klipper-mainboard.bin` |

**Each build overwrites `out/klipper.bin` (or `out/katapult.bin` / `out/deployer.bin`), so copy the output to a distinct name before the next build** — otherwise the four images clobber each other and you risk flashing the toolhead's F103 image onto the mainboard, or vice versa. The flash steps in [MIGRATION.md](MIGRATION.md) use the "Save the output as" names above.

### Mainboard: build as STM32H743 (the validated 400 MHz clock)

Select **`MACH_STM32H743`**, not H750. On current Klipper master both targets offer the `0x8020000` offset (`STM32_FLASH_START_20000`) as a **stock menu option**, so neither needs a patch — but they differ on clock: **H750 defaults to 480 MHz, H743 to 400 MHz**, and 400 MHz is the speed this mainboard is validated at (the vendor and [asnajder/zero-config](https://github.com/asnajder/zero-config) both run it at 400). Building as H743 gives you the proven clock from a stock target. With `make menuconfig`:

- processor model **STM32H743**
- **25 MHz** crystal
- **128 KiB** application offset (→ `0x8020000`)
- USB-to-CAN-bus bridge, USB on PA11/PA12, CAN on PB8/PB9
- **GPIO pins to set at startup: `!PE11,!PB0`** — holds the aux/exhaust fans low until Klipper takes over, instead of letting them run at full power through the boot window

Build a **Katapult deployer** for the mainboard with the same H743 settings plus `BUILD_DEPLOYER=y` (auto-enabled when the app offset differs from the boot offset). It emits `deployer.bin` alongside `katapult.bin`; the deployer is what installs mainline Katapult over USB without SWD (see [MIGRATION.md](MIGRATION.md)).

### Toolhead Katapult: keep it `CANSERIAL`

Seed the toolhead Katapult `.config` from the vendor `.config103` and only change the offset. A **bare/hand-written seed makes `olddefconfig` default the comms interface to USB**, producing a Katapult that enters the bootloader but is silent on the CAN bus. `CANSERIAL` is what makes the toolhead CAN-flashable after the one SWD bootstrap.

### Footnote: building as H750

On current master `MACH_STM32H750` reaches the `0x8020000` offset too, so it needs no patch either — the support behind [Klipper3d/klipper#7219](https://github.com/Klipper3d/klipper/pull/7219) landed on master in commit `666781a6` on **2026-06-09**. A separate commit the same day split the clock default to H750 → 480 MHz / H743 → 400 MHz; before that, H750 also defaulted to 400 MHz. So on a current checkout the only thing separating the two targets is that clock default, and there is still no reason to pick H750 here. The one-line Kconfig patch that used to menu-enable the offset only matters if you pin a Klipper from before 2026-06-09 — which this master-tracking guide doesn't.

## Verify before flashing

Check each `.bin`'s reset handler — bytes 4–7, little-endian — lands at the target offset:

```bash
python3 -c "d=open('out/klipper.bin','rb').read(8); print(hex(int.from_bytes(d[4:8],'little')))"
```

- F103 at `0x8002000` → expect `0x08002xxx` (a `0x08000xxx` value means it was built for `0x8000000`, wrong).
- Mainboard at `0x8020000` → expect `0x0802xxxx` (a `0x0800xxxx` value means wrong offset — it will brick the bridge).
