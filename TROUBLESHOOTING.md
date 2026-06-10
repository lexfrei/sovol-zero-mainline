# Troubleshooting & tuning

Things that bite when running a Sovol Zero on mainline Klipper, and how to clear them. Facts and fixes only — see [MIGRATION.md](MIGRATION.md) for the full procedure.

## Flashing & CAN

### `canbus_query` / `flashtool.py -q` shows 0 nodes

If Klipper is **stopped**, a query returning `Total 0 uuids` is normal — those tools enumerate only un-initialised / bootloader nodes, and a Klipper-configured app node does not answer. Read it as "everything is running its application", not "the bus is dead". Start Klipper (or put a node into its bootloader) to see it in a query.

### Reflashing the toolhead over CAN fails with `Error sending command [CONNECT]`

The toolhead's Katapult must be built for CAN comms. If it was built (or `olddefconfig`-defaulted) for USB, it enters the bootloader but is silent on the bus. Build the F103 Katapult `CANSERIAL` (seed `.config` from a known-good CAN config, not a bare seed). A CAN-capable toolhead Katapult means future app updates flash over CAN — no need to open the head again.

### Changing Klipper version: flash all three, not just the host

Eddy **tap** (and other features that add MCU-side commands) require the host **and both MCU apps** to be the same Klipper commit. Moving only the host to master while the MCUs stay on a tag fails at startup with e.g. `mcu 'extruder_mcu': Unknown command: trigger_analog_query_state`. Rebuild and flash the app for the host, the F103, and the mainboard (built as `STM32H743` — see [BUILD.md](BUILD.md)) from the same commit. With a CAN-capable toolhead Katapult this no longer means opening the head — F103 over CAN, the mainboard over USB-Katapult.

### Don't trust the on-disk `.config` offset

The vendor `.config103` / `.config750` claim `FLASH_APPLICATION_ADDRESS=0x8000000`, which is stale — the app actually lives at `0x8002000` (F103) / `0x8020000` (mainboard). Read the real offset from the live bootloader (Katapult `CONNECT` reports `Application Start`), and gate every flash on the built `.bin`'s reset vector before writing. See [MIGRATION.md](MIGRATION.md) and [BUILD.md](BUILD.md).

## Eddy probe (LDC1612)

### `START_NACK` on the first probe / homing move

Two causes stack here:

1. **Mainline needs software I2C** on this board — the vendor's STM32F1 hardware-I2C errata workarounds aren't in mainline, so hardware `i2c2` throws `START_NACK`. Use `i2c_software_scl_pin` / `i2c_software_sda_pin` on `extruder_mcu:PB10` / `PB11`.
2. **The FFC is disturbed.** The eddy connector is factory heat-staked; disassembling the head breaks the stake and a slightly twisted cable gives the same NACK. Reseat the FFC (and re-anchor it with hot glue *outside* the contacts, not by re-melting the stake).

### `probe_eddy_current sensor not in valid range` after several soft restarts

The software-I2C sensor can get into a bad state across a series of soft Klipper restarts — a soft restart does not re-initialise it, a full **power-cycle** does. Power-cycle the printer rather than chasing the Z position; do not paper over it with `SET_KINEMATIC_POSITION` (that just sends the kinematic Z somewhere wrong).

### Eddy options rejected ("not valid in section")

You're on the `v0.13.0` tag, not `master`. `descend_z` and `max_sensor_hz` are tap-era keys that only exist on `master`; the tag has no tap and requires `z_offset` instead. This is one of the reasons the guide builds from `master` — if you pinned a tag anyway, match the eddy config to it (see [MIGRATION.md](MIGRATION.md)).

## Input shaping & accelerometer

### Resonance test → `MCU 'mcu' shutdown: Timer too close`

The Allwinner H616 host can't sustain a diagonal `TEST_RESONANCES` at full rate while the camera is streaming. Two fixes, both needed: `systemctl stop crowsnest` for the duration of the test, and `HZ_PER_SEC=2` (the config cap is 2.0). Restart crowsnest afterwards.

### Accelerometer traces look noisy

The vendor's noisy resonance traces come from two things, both fixed on mainline: the old single-frame LIS2DW read (mainline's chunked-FIFO `bulk_sensor` read is clean) and a hard-pinned narrow `[resonance_tester] min_freq: 35 / max_freq: 45` window that forces a bogus ~40 Hz result. On mainline with a wide window, `MEASURE_AXES_NOISE` sits at single-digit mm/s² per axis and the real resonance (often ~55–65 Hz on this frame) surfaces.

Before blaming the sensor for noise on **one** axis: a dead LIS2DW sprays all axes or NACKs, so single-axis noise points at a mechanical/wiring/driver source instead. The discriminating test is `MEASURE_AXES_NOISE` with the motors energised vs after `M84` — if the noise drops with motors off, it's TMC chopper standstill vibration the sensor honestly measures, not the sensor itself.

### Print acceleration vs resonance-test acceleration

A `[printer] max_accel` in the tens of thousands is a *resonance-test* ceiling, not a print value. After `SHAPER_CALIBRATE`, set `max_accel` to the binding per-axis suggested limit (often the `ei`-shaped axis, around ~6000–6500) for clean geometry, and keep the slicer's wall accelerations at or below it.

## Fans

### `fan3` / `PE14` drives nothing

The vendor config carries a `[fan_generic fan3] pin: PE14` for a board-cooling fan that was **dropped / unpopulated in the production release**. It drives nothing and only clutters the UI — remove the section.

## Host / OS

### Readiness check: query the API, not the log

Recent Klipper no longer emits the old `Stats` / `Klipper state: Ready` log lines, so grepping the log for readiness makes a ready printer look hung. Query Moonraker `/printer/info` (or the klippy socket `{"id":1,"method":"info"}`) → `state: ready`.

### `apt update` fails on `bullseye-backports`

The `bullseye-backports` suite was removed from the mirrors (404). Comment the active backports line in `/etc/apt/sources.list` (keep a backup) before any apt-based install. Stay within bullseye — a `bullseye→bookworm` dist-upgrade moves Python 3.9→3.11 and breaks the Klipper/Moonraker venvs, with no live rootfs recovery unless you can re-image the eMMC out-of-band (see [OS.md](OS.md)).
