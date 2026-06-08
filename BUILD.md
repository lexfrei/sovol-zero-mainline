# Building the firmware

The MCU firmware (Katapult + Klipper) can be built either **on the printer's own host** or **on a Mac / Linux box**, then the `.bin` copied over. Both produce identical images — pick whichever is handy.

## Toolchain

### On the printer host (BTT CB1, Debian aarch64)

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

Pin an upstream commit. For each MCU, seed `.config` from the vendor's on-disk one and fix the offset — the vendor `.config*` files claim `0x8000000`, which is stale (see [MIGRATION.md](MIGRATION.md)).

| Target | Source / seed | Offset option | App address |
| --- | --- | --- | --- |
| Katapult (F103) | [Arksine/katapult](https://github.com/Arksine/katapult) — 8 MHz, CAN PB8/PB9, double-reset | — | `0x8000000` |
| Klipper, F103 toolhead | [Klipper](https://github.com/Klipper3d/klipper), seed `.config103` | `STM32_FLASH_START_2000` | `0x8002000` |
| Klipper, H750 mainboard | Klipper, seed `.config750` | `STM32_FLASH_START_20000` | `0x8020000` |

The H750 needs a **one-line Kconfig patch** — `STM32_FLASH_START_20000` exists upstream but isn't menu-enabled for the H750:

```
# src/stm32/Kconfig, the STM32_FLASH_START_20000 bool:
bool "128KiB bootloader" if MACH_STM32H743 || MACH_STM32H723 || MACH_STM32F7 || MACH_STM32H750
```

(This is what [Klipper3d/klipper#7219](https://github.com/Klipper3d/klipper/pull/7219) carries upstream.)

## Verify before flashing

Check `out/klipper.bin`'s reset handler — bytes 4–7, little-endian — lands at or above the target offset:

```bash
python3 -c "d=open('out/klipper.bin','rb').read(8); print(hex(int.from_bytes(d[4:8],'little')))"
```

- F103 at `0x8002000` → expect `0x08002xxx`+ (a `0x08000xxx` value means it was built for `0x8000000`, wrong).
- H750 at `0x8020000` → expect `0x0802xxxx` (a `0x0800xxxx` value means wrong offset — it will brick the bridge).
