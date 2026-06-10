# Sovol Zero → mainline Klipper: the procedure

The clean way to put a Sovol Zero fully on upstream Klipper — host plus both MCUs, app *and* bootloader, no vendor bytes in the firmware. Build everything from the **same Klipper `master` commit** (see [Which Klipper version](README.md#which-klipper-version) — `master`, not an old tag, is what gets you eddy tap).

Architecture context is in [ARCHITECTURE.md](ARCHITECTURE.md). The short version: host (Allwinner H616, on Sovol's all-in-one Zero control board) + three CAN STM32 MCUs — `mcu` (STM32H750 mainboard, also the USB-CAN bridge), `extruder_mcu` (STM32F103 toolhead), `hot_mcu` (optional chamber). Only Klipper is forked; everything else (Moonraker, Mainsail, crowsnest, KlipperScreen, Katapult, gs_usb) is stock upstream.

## Prerequisites

- **An SWD programmer.** ST-Link V2 (~$3 clone), or a Flipper Zero running the **DAP Link** app (a CMSIS-DAP probe). It is needed once, to bootstrap the toolhead — the vendor Katapult is request-only and can't be recovered over CAN, so you flash a CAN-capable mainline Katapult onto the toolhead over SWD the first time, and never open the head again.
- **ARM toolchain** to build firmware: `arm-none-eabi-gcc` (already on the printer host) or `brew install --cask gcc-arm-embedded` on macOS. See [BUILD.md](BUILD.md).
- `openocd` ≥ 0.11 for the SWD flash.
- SSH access to the printer.

## Stage 0 — Back up first

1. **The vendor stack** (file-level, resumable rsync — not a raw `dd` over WiFi): vendor `~/klipper` as a git bundle, `~/printer_data/config`, `~/printer_data/build/*.bin`, and the per-chip build configs `~/klipper/.config*` (they're useful seeds even though their flash offsets are stale).
2. **An SWD dump of the toolhead** before you erase it — the surest exact rollback:

   ```bash
   openocd -c "adapter driver cmsis-dap" -c "transport select swd" -c "adapter speed 1000" \
     -f target/stm32f1x.cfg -c "init" -c "halt" \
     -c "dump_image vendor-f103-FULL-flash.bin 0x08000000 0x10000" -c "shutdown"
   ```

   A valid dump opens with a sane vector table (initial SP in RAM `0x2000xxxx`, reset vector in flash `0x0800xxxx`), not all `0xFF`/`0x00`. The mainboard's SWD header is buried, so its build-from-source rollback is a vendor-equivalent firmware compiled from your backed-up vendor `~/klipper` at the same `0x8020000` offset (USB-Katapult-flashable). [asnajder/zero-config](https://github.com/asnajder/zero-config) also publishes ST-LINK-flashable vendor recovery images, but as third-party prebuilts of unverifiable provenance they're an emergency fallback only.

## Stage 1 — Build the firmware (from `master`)

Toolchain and the host-vs-macOS differences are in [BUILD.md](BUILD.md); it also covers the offset table, the per-image output names (each `make` overwrites `out/`, so copy each result to a distinct name), and the reset-vector gate in detail. You build four images, all from the same `master` commit:

| Image | Target | Offset | How it's flashed |
| --- | --- | --- | --- |
| Toolhead Katapult | F103, **CANSERIAL** | `0x8000000` | SWD (once) |
| Toolhead Klipper | F103 | `0x8002000` | SWD (once), then CAN |
| Mainboard Katapult deployer | **`MACH_STM32H743`** | `0x8020000` | USB-Katapult |
| Mainboard Klipper | **`MACH_STM32H743`** | `0x8020000` | USB-Katapult |

Two things make this clean:

- **Build the mainboard as `MACH_STM32H743`,** not H750. On current master both targets reach the `0x8020000` offset with no patch, but H750 defaults to 480 MHz while H743 defaults to **400 MHz** — the clock this mainboard is validated at. H743 gives you the proven clock from a stock target (see [BUILD.md](BUILD.md)).
- **Build the toolhead Katapult `CANSERIAL`,** seeding its `.config` from the vendor `.config103` (a bare seed defaults `olddefconfig` to USB, which would be silent on the CAN bus). A CAN-capable Katapult is what lets every future toolhead update flash over CAN with no head-opening.

The mainboard Katapult **deployer** (`BUILD_DEPLOYER=y`, auto-enabled when the app offset differs from the boot offset) is what installs mainline Katapult over USB without SWD. **Gate every image on its reset vector** before flashing: bytes 4–7 (little-endian) must land at the app offset (`0x08002xxx` for the F103, `0x0802xxxx` for the mainboard). A `0x08000xxx` vector means it was built for the wrong offset and will brick the chip — rebuild.

## Stage 2 — Flash the toolhead, once, over SWD

This is the only time you open the head. It writes the CAN-capable mainline Katapult and the Klipper app; afterwards the toolhead flashes over CAN forever. The header and probe wiring are in [PINOUT.md](PINOUT.md) and [FLASHING.md](FLASHING.md). Disconnect the head; the probe's 3.3 V powers the MCU.

```bash
# sanity: read the chip (expect Cortex-M3, device id 0x...410)
openocd -c "adapter driver cmsis-dap" -c "transport select swd" -c "adapter speed 1000" \
  -f target/stm32f1x.cfg -c "init" -c "dap info" -c "shutdown"

# erase + write CANSERIAL Katapult (0x08000000) + Klipper (0x08002000) + run
openocd -c "adapter driver cmsis-dap" -c "transport select swd" -c "adapter speed 1000" \
  -f target/stm32f1x.cfg -c "init" -c "reset halt" \
  -c "stm32f1x mass_erase 0" \
  -c "flash write_image katapult-f103.bin 0x08000000" \
  -c "flash write_image klipper-f103.bin 0x08002000" \
  -c "reset run" -c "shutdown"
```

Reassemble the head, reconnect its CAN, power on. The toolhead now answers on a **new real-hardware UUID** (mainline reads the real UID instead of the vendor's fake `61755fe321ac`):

```bash
python3 ~/katapult/scripts/flashtool.py -i can0 -q     # note the new UUID
```

## Stage 3 — Flash the mainboard, over USB-Katapult, no SWD

The mainboard is the USB-CAN bridge, so it's reachable over USB even though its SWD header is buried. Replace both its bootloader (via the deployer) and its app. (`flashtool.py` is `~/katapult/scripts/flashtool.py` — run these from that directory or put it on `PATH`.)

```bash
# 1) request the bridge into its (stock) Katapult — it re-enumerates as a USB serial device
flashtool.py -i can0 -u <mainboard-uuid> -r        # stock vendor Katapult appears under /dev/serial/by-id/ as usb-katapult_stm32h750xx-*

# 2) install mainline Katapult by flashing the deployer through the stock bootloader
flashtool.py -d /dev/serial/by-id/usb-katapult_stm32h750xx-* -f deployer-mainboard.bin   # re-enumerates h750xx → h743xx = success

# 3) flash the Klipper app through the freshly-installed mainline Katapult
flashtool.py -d /dev/serial/by-id/usb-katapult_stm32h743xx-* -f klipper-mainboard.bin   # via the new mainline (H743) Katapult
```

The USB id reflects the MCU target the *bootloader* was built for, so the change from `h750xx` (stock vendor Katapult) to `h743xx` confirms the mainline (H743) Katapult is now in control — that re-enumeration is your go signal between steps 2 and 3. The bridge's USB re-enumerates during these steps (SSH/flash output may drop, the write still completes). **Don't touch power or USB mid-write** — a clean flash is recoverable through Katapult, but an interrupted write that corrupts Katapult itself is the one case that forces SWD on the buried mainboard. After it boots, the mainboard also comes up on a **new real UUID** (the fake `0d1445047cdd` is gone); `flashtool.py -i can0 -q` to read it.

If you'd rather not bootstrap the toolhead over SWD at all, the same deployer trick can in principle go over CAN through the *working* vendor toolhead app — but the toolhead has no USB and no CAN recovery if that flash corrupts, so SWD-once (Stage 2) is the safe path.

## Stage 4 — Host and config

Point Klipper's host at the same `master` checkout + a venv built from its `requirements.txt`, and set `[update_manager klipper] channel: dev` in `moonraker.conf` so it tracks `master`. Translate the config off the vendor one:

- **Eddy on software I2C.** The vendor ran the LDC1612 on hardware `i2c2`, but only because its F103 firmware carries STM32F1 hardware-I2C errata workarounds mainline lacks; on mainline hardware `i2c2` throws `START_NACK` → shutdown. Use bitbang: replace `i2c_bus: i2c2` with `i2c_software_scl_pin: extruder_mcu:PB10` and `i2c_software_sda_pin: extruder_mcu:PB11`. Software I2C sustains single reads, tap homing, and the rapid_scan bulk stream — corroborated independently by [asnajder/zero-config](https://github.com/asnajder/zero-config).
- **Eddy `[probe_eddy_current]` on `master`:** `descend_z` (the rename of the old `z_offset`; the old name stays as a deprecated alias) and `max_sensor_hz`; `reg_drive_current` and the freq→height table are written by calibration (`SAVE_CONFIG`), never hand-set. Drop the vendor-only `vir_contact_speed`, and set `descend_z` to the calibration *approach* height (~0.5 mm) — do **not** carry the vendor's old `z_offset` *value* into it; the real nozzle-to-sensor offset is absorbed into the calibration table. *(If you pin the `v0.13.0` tag instead, those tap-era keys are rejected and `z_offset` is required — another reason to be on `master`.)*
- **Z homing.** There is no mechanical Z endstop. Use `[homing_override]` (not `[safe_z_home]`): `set_position_z: 0` → a safety z-hop → home X/Y on their mechanical endstops → `G28 Z` onto `probe:z_virtual_endstop`. On `master` you also get **tap** (`PROBE METHOD=tap`) for nozzle-contact Z.
- **Drop the vendor-only modules.** `[z_offset_calibration]` and macros that call `RUN_PROBE_VIR_CONTACT` / `Z_OFFSET_CALIBRATION` are replaced by upstream eddy/tap; rewrite or remove them. The vendor OTA / IP-display shell macros are cruft — drop them (only add the third-party `gcode_shell_command.py` if you keep a macro that genuinely needs a shell command).
- Update `[mcu] canbus_uuid` / `[mcu extruder_mcu] canbus_uuid` to the new real UUIDs from Stages 2–3.

Start Klipper and confirm: both MCUs load on the same `master` version (the command counts match, no `is not compatible` / `Unknown command` skew), and `state: ready` (query Moonraker `/printer/info`, not a log grep — see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)).

## Stage 5 — Calibrate and verify

- `LDC_CALIBRATE_DRIVE_CURRENT` → `PROBE_EDDY_CURRENT_CALIBRATE` (the freq→height table), then `PROBE_EDDY_CURRENT_TAP_CALIBRATE` for `tap_threshold`. `SAVE_CONFIG` after each.
- Input shaper: `TEST_RESONANCES` — mainline's chunked-FIFO LIS2DW read gives a clean trace, and with a wide `[resonance_tester]` window (not the vendor's pinned 35–45 Hz) the real resonance surfaces. On this host the diagonal test needs the camera stopped — see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
- Functional: `G28` homes via eddy, `BED_MESH_CALIBRATE METHOD=rapid_scan` completes, a test print runs. Set `max_accel` to the binding per-axis `SHAPER_CALIBRATE` limit for clean geometry, not the resonance-test ceiling.

## Optional — screen codes

The vendor firmware shows numeric knob-screen codes (101/103, the 60+ shutdown range); mainline shows human-readable messages. To keep the codes, install the opt-in `klipper-plugin/sovol_codes.py` and add `[sovol_codes]` to `printer.cfg`. See [klipper-plugin/README.md](klipper-plugin/README.md).
