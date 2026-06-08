# Sovol Zero → mainline Klipper: the happy path

The clean, correct procedure to move a Sovol Zero from the vendor Klipper fork onto upstream Klipper. This is the "do it right the first time" version.

Architecture context is in [ARCHITECTURE.md](ARCHITECTURE.md). The short version: host (BTT CB1 / Allwinner H616) + three CAN STM32 MCUs — `mcu` (STM32H750 mainboard, also the USB-CAN bridge), `extruder_mcu` (STM32F103 toolhead), `hot_mcu` (optional chamber). Only Klipper is forked; everything else (Moonraker, Mainsail, crowsnest, KlipperScreen, Katapult, gs_usb) is stock upstream.

## Prerequisites

- **An SWD programmer.** ST-Link V2 (~$3 clone) is the community standard. A Flipper Zero running the **DAP Link** app works just as well as a CMSIS-DAP probe (this is what was used here). You need it because the vendor Katapult cannot be recovered over CAN once an app is broken.
- **ARM toolchain** to build firmware: `brew install --cask gcc-arm-embedded` (macOS) or distro `arm-none-eabi-gcc`.
- `openocd` ≥ 0.11 for flashing via the programmer.
- SSH access to the printer.

## Stage 0 — Back up everything first

1. **Full vendor stack** (file-level, resumable rsync — not a raw `dd` over WiFi): vendor `~/klipper` as a git bundle, `~/printer_data/config`, `~/printer_data/build/*.bin`, and the per-chip build configs `~/klipper/.config*`.
2. **Full SWD dump of each MCU you will reflash** — this is the only way to get an *exact* rollback (the mainboard H750 has no vendor `.bin` published anywhere):

   ```bash
   openocd -c "adapter driver cmsis-dap" -c "transport select swd" -c "adapter speed 1000" \
     -f target/stm32f1x.cfg -c "init" -c "halt" \
     -c "dump_image vendor-f103-FULL-flash.bin 0x08000000 0x10000" -c "shutdown"
   ```

   A valid dump starts with a sane vector table (initial SP in RAM `0x2000xxxx`, reset vector in flash `0x0800xxxx`), not all `0xFF`/`0x00`.

## Stage 1 — Build mainline firmware (correct offsets)

The single most important fact: **the Katapult bootloader offset is 8 KiB → the Klipper app lives at `0x8002000`, not `0x8000000`.** The vendor `.config` files on disk claim `0x8000000`; that is stale and wrong (it bricks the MCU).

Pin the upstream commit you build from. On macOS, force the cross toolchain for both compile and the linker-script preprocess step:

```bash
# Katapult (F103, 8MHz crystal, CAN PB8/PB9, double-reset entry)
cd ~/katapult            # git clone https://github.com/Arksine/katapult
cat > .config <<'EOF'
CONFIG_MACH_STM32=y
CONFIG_MACH_STM32F103=y
CONFIG_STM32_CLOCK_REF_8M=y
CONFIG_CANBUS=y
CONFIG_STM32_CANBUS_PB8_PB9=y
CONFIG_CANBUS_FREQUENCY=1000000
CONFIG_ENABLE_DOUBLE_RESET=y
EOF
make olddefconfig                    # yields FLASH_APPLICATION_ADDRESS=0x8000000, LAUNCH_APP_ADDRESS=0x8002000
make CROSS_PREFIX=arm-none-eabi- CPP=arm-none-eabi-cpp   # -> out/katapult.bin

# Klipper (same F103 chip/clock/CAN, app at 0x8002000)
cd ~/klipper-mainline    # git clone --depth 1 https://github.com/Klipper3d/klipper
cp ~/klipper/.config103 .config       # seed from vendor, then fix the offset:
#   remove CONFIG_STM32_FLASH_START_0000=y ; add CONFIG_STM32_FLASH_START_2000=y
make olddefconfig                     # confirm FLASH_APPLICATION_ADDRESS=0x8002000
make CROSS_PREFIX=arm-none-eabi- CPP=arm-none-eabi-cpp   # -> out/klipper.bin
```

The `CPP=arm-none-eabi-cpp` override is required on macOS (the Makefile defaults to the host `cpp`, which is clang and fails on the linker script).

## Stage 2 — Flash the toolhead (F103) via SWD

The toolhead board has a 4-pin 2.54 mm SWD header near the F103 (U6), marked **`G CK IO 3.3`**:

| Header | Signal | Programmer |
| --- | --- | --- |
| `G` | GND | GND |
| `CK` | SWCLK (PA14) | SWCLK |
| `IO` | SWDIO (PA13) | SWDIO |
| `3.3` | 3.3 V | 3.3 V (powers the MCU) |

Disconnect the head from the printer; the programmer's 3.3 V powers the MCU for flashing (a blue LED on the board confirms power). For a Flipper running DAP Link, SWC=pin 10, SWD=pin 12, GND=pin 11, 3V3=pin 9 (verify in the app's *Config → Help and Pinout*).

Test the link first (read-only), then flash both images and run:

```bash
# 1) sanity: read the chip
openocd -c "adapter driver cmsis-dap" -c "transport select swd" -c "adapter speed 1000" \
  -f target/stm32f1x.cfg -c "init" -c "dap info" -c "shutdown"   # expect Cortex-M3, device id 0x...410

# 2) erase + write Katapult + Klipper + run
openocd -c "adapter driver cmsis-dap" -c "transport select swd" -c "adapter speed 1000" \
  -f target/stm32f1x.cfg -c "init" -c "reset halt" \
  -c "stm32f1x mass_erase 0" \
  -c "flash write_image katapult.bin 0x08000000" \
  -c "flash write_image klipper.bin 0x08002000" \
  -c "reset run" -c "shutdown"
```

Verify it booted: halt and read `pc` — it should be inside the app region (`0x08003xxx`), and the vector tables at `0x08000000` (Katapult) and `0x08002000` (Klipper) should both be valid.

## Stage 3 — Reassemble, find the new UUID, fix config

Reassemble the head, reconnect its CAN, power the printer on.

**The CAN UUID changed.** Upstream Katapult/Klipper read the real hardware UID, so the toolhead no longer answers to the vendor's fake `61755fe321ac`:

```bash
python3 ~/katapult/scripts/flashtool.py -i can0 -q     # note the new UUID
```

Update `[mcu extruder_mcu] canbus_uuid` in the mainline `printer.cfg` to the new value.

## Stage 4 — Switch the host to mainline

Run mainline Klipper alongside the vendor install (separate `klippy-env-mainline` venv with the extra `msgspec` dep; mainline klippy.py + the mainline `printer.cfg`). Config translation from the vendor config:

- Drop `[z_offset_calibration]` (vendor-only module) → use upstream eddy `METHOD=tap` for contact Z.
- In `[probe_eddy_current]`: drop `vir_contact_speed` (vendor-only); add `max_sensor_hz` (mainline warns otherwise); `z_offset` still works (mainline maps it to `descend_z`).
- **The eddy LDC1612 must move to software I2C on mainline.** The vendor ran it on hardware `i2c2` (PB10/PB11), but only because the vendor F103 firmware carries heavy STM32F1 hardware-I2C errata workarounds (retry-on-busy, full bus-recovery, and *don't shut down on an F1 I2C error*) that mainline does not have. On mainline, hardware `i2c2` throws `START_NACK` → printer shutdown the moment the probe is used. Switch to bitbang: replace `i2c_bus: i2c2` with `i2c_software_scl_pin: extruder_mcu:PB10` and `i2c_software_sda_pin: extruder_mcu:PB11`. Software I2C sustains both single reads (drive-current cal, Z tap homing) and the rapid_scan bulk FIFO stream — verified end to end.
- Add the third-party `gcode_shell_command.py` to `klippy/extras/` (used by the OTA/IP macros).
- Macros that call `RUN_PROBE_VIR_CONTACT` / `Z_OFFSET_CALIBRATION` (vendor commands) need rewriting to upstream eddy tap. These do not block startup (gcode is validated at call time), only calibration/print flows.

Point `klipper.service` at the mainline checkout + venv. Reversible: repoint at the vendor `~/klipper`.

The mainline host loads the vendor H750 fine (compatible data dictionary, 122 commands) — but leaving it there is the exact version skew this whole migration exists to kill: a mainline host driving a vendor-fork MCU, three `deprecated code` warnings, and a continued fork dependency on the one component with the least visibility. Finish the job. Stage 4b takes the mainboard to mainline too — it is the highest-risk step, but it is doable entirely over USB, and once it lands the host and all MCUs are on one upstream version with zero skew.

## Stage 4b — H750 mainboard to mainline (over USB-Katapult, no SWD)

The mainboard MCU is an STM32H750 that doubles as the USB-CAN bridge. Reflashing it is the highest-stakes step (brick it and the whole CAN bus dies; the H750 SWD header is on the buried mainboard), but it *is* doable entirely over USB. The only thing that makes it look impossible is the flash layout:

- **The app lives at `0x8020000`, not `0x8000000`.** That is past the H750's 128 KiB of internal flash. The Sovol Zero mainboard carries additional flash — believed to be a QSPI chip (per the [Klipper #7219](https://github.com/Klipper3d/klipper/pull/7219) discussion, confirmed by multiple Zero owners) — and the stock Katapult places the app there at a 128 KiB offset. What matters in practice: build the app for `0x8020000` and flash it over the stock Katapult. Do **not** use the textbook 32 KiB offset on top of the stock Katapult — it bricks the chip (SWD recovery). And don't trust `.config750` (it says `0x8000000`, stale like `.config103` was).
- **Mainline already supports this offset** — `STM32_FLASH_START_20000` → `0x8020000` exists upstream; it is just not menu-enabled for the H750. The entire vendor "port" is one line in `src/stm32/Kconfig`:

  ```
  config STM32_FLASH_START_20000
      bool "128KiB bootloader" if MACH_STM32H743 || MACH_STM32H723 || MACH_STM32F7 || MACH_STM32H750
  ```

**Read the real offset from the bootloader itself** — non-destructive, no SWD. Request the bridge into Katapult, connect, read `Application Start`, send `COMPLETE` to boot the app back (the app is untouched; a power-cycle always returns the vendor firmware). The bridge drops for ~30 s. Katapult's `CONNECT` only reads; it does not erase or write.

**Build** (seed from vendor `.config750`, switch the offset symbol):

```bash
cp ~/klipper/.config750 .config
#   remove CONFIG_STM32_FLASH_START_0000=y ; add CONFIG_STM32_FLASH_START_20000=y
make olddefconfig                     # confirm FLASH_APPLICATION_ADDRESS=0x8020000
make CROSS_PREFIX=arm-none-eabi- CPP=arm-none-eabi-cpp   # -> out/klipper.bin
```

Before flashing, **gate on the reset vector**: `out/klipper.bin` bytes 4–7 (little-endian) must be in `0x0802xxxx`. A `0x0800xxxx` vector means it was built for the wrong offset and will brick the bridge — abort.

**Build a rollback first.** The same `.config750` + `0x8020000` from the **vendor** source produces a vendor-equivalent firmware (same `chipid.c` → same fake UUID `0d1445047cdd`), flashable through the same Katapult-USB path. That is a *software* rollback that does not need an SWD dump — it covers the "mainline flashed but misbehaves" case (it does not cover an interrupted write that corrupts Katapult itself).

**Flash over USB-Katapult** (the vendor's own path — no SWD):

```bash
# 1) request bootloader: bridge reboots and appears as usb-katapult_stm32h750xx
flash_can.py -i can0 -u <h750-uuid> -r -f /dev/null
# 2) flash via that serial device (flasher writes to Katapult's reported 0x8020000)
flash_can.py -d /dev/serial/by-id/usb-katapult_stm32h750xx-* -f out/klipper.bin
```

**Do not touch power or USB during the write.** Katapult survives a clean app flash (you can re-flash the rollback through it), but an interrupted write corrupts the app with no remote recovery left — that is the one path back to the buried mainboard SWD header.

After flashing, the H750 comes up with a **new real-hardware UUID** (the fake `0d1445047cdd` is gone, exactly like the F103). Query `canbus_query.py can0`, update `[mcu] canbus_uuid`, restart. Confirm `Loaded MCU 'mcu'` now shows the mainline version (command count jumps, e.g. 122 → 144) and the `deprecated code` warnings are gone.

**This flashes the mainline Klipper *app*, not the bootloader.** The H750 keeps the stock vendor Katapult — the app is written over it. Putting mainline Katapult on the H750 (built with the same 128 KiB H750 support, [Arksine/katapult#177](https://github.com/Arksine/katapult/pull/177)) is a further step that needs SWD on the mainboard; it isn't required to clear the version skew, since that comes from the app. For a true clean-room mainline (zero vendor bytes), the two remaining vendor layers are this H750 Katapult and the OS/eMMC image (the latter needs an eMMC programmer).

## Stage 5 — Recalibrate and verify

- `PROBE_EDDY_CURRENT_CALIBRATE`, input shaper (`TEST_RESONANCES` — the LIS2DW chunked-FIFO read in mainline gives a cleaner trace), Z offset via eddy tap.
- Functional: `G28` homes via eddy, `BED_MESH_CALIBRATE METHOD=rapid_scan` completes, a test print runs.
- The vendor eddy calibration table (the SAVE_CONFIG block) carries over — mainline reads the same format.

## Optional — screen codes

The vendor firmware shows numeric knob-screen codes (101/103, the 60+ shutdown range). Mainline shows human-readable messages. To keep the codes, install the opt-in `klipper-plugin/sovol_codes.py` and add `[sovol_codes]` to `printer.cfg`. See `klipper-plugin/README.md`.
