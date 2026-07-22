---
title: Klipper config
weight: 2
---

# Translating the config to mainline

The vendor `printer.cfg` doesn't run as-is on upstream Klipper — a few sections depend on vendor-only firmware behaviour. Translate these off the vendor config; the rest carries over.

## Eddy on software I2C

The vendor ran the LDC1612 on hardware `i2c2`, but only because its F103 firmware carries STM32F1 hardware-I2C errata workarounds that mainline lacks; on mainline, hardware `i2c2` throws `START_NACK` → shutdown. Use bitbang instead:

```ini
# replace  i2c_bus: i2c2  with:
i2c_software_scl_pin: extruder_mcu:PB10
i2c_software_sda_pin: extruder_mcu:PB11
```

Software I2C sustains single reads, tap homing, and the rapid_scan bulk stream — corroborated independently by [asnajder/zero-config](https://github.com/asnajder/zero-config).

## Eddy `[probe_eddy_current]` on `master`

Use `descend_z` (the rename of the old `z_offset`; the old name stays as a deprecated alias) and `max_sensor_hz`. `reg_drive_current` and the freq→height table are written by calibration (`SAVE_CONFIG`), never hand-set. Drop the vendor-only `vir_contact_speed`, and set `descend_z` to the calibration *approach* height (~0.5 mm) — do **not** carry the vendor's old `z_offset` *value* into it; the real nozzle-to-sensor offset is absorbed into the calibration table.

If you pin the `v0.13.0` tag instead of `master`, those tap-era keys are rejected and `z_offset` is required — another reason to be on `master`.

## Z homing — `homing_override`, not `safe_z_home`

There is no mechanical Z endstop. Use `[homing_override]`:

- `set_position_z: 0`
- a safety z-hop
- home X/Y on their mechanical endstops
- `G28 Z` onto `probe:z_virtual_endstop`

On `master` you also get **tap** (`PROBE METHOD=tap`) for nozzle-contact Z.

## Drop the vendor-only modules

- `[z_offset_calibration]` and macros that call `RUN_PROBE_VIR_CONTACT` / `Z_OFFSET_CALIBRATION` are replaced by upstream eddy/tap — rewrite or remove them.
- The vendor OTA / IP-display shell macros are cruft — drop them. Only add the third-party `gcode_shell_command.py` if you keep a macro that genuinely needs a shell command.

## Point the MCUs at their new UUIDs

Update `[mcu] canbus_uuid` / `[mcu extruder_mcu] canbus_uuid` to the new real UUIDs from the [MCU migration]({{< relref "/zero/firmware/mcu-migration" >}}) (mainline reads the real hardware UID, so both MCUs came up on fresh UUIDs).

## A few facts that bite

- **Origin (0,0) is the front-left corner.** The Creality K1c — a common config donor — has it front-right, so a reused K1 config gives mirrored coordinates and a wrong-way mesh. Fix the axis directions rather than fighting the mesh.
- **No dedicated toolhead-temp sensor.** For a rough head readout, read the F103 die itself: `[temperature_sensor Toolhead_Temp]` with `sensor_type: temperature_mcu` and `sensor_mcu: extruder_mcu`.
- **Some units have the X and Y stepper connectors physically swapped.** If an axis runs the wrong way or the wrong motor turns, swap them in config rather than rewiring.
- **The buzzer is unpopulated** though its circuit is on the board; the F103's active buzzer can't vary pitch (and Klipper has no `M300`). If you fit one: `[output_pin beeper] pin: EXP1_1`.

## Then start Klipper

Confirm both MCUs load on the same `master` version — the command counts match, no `is not compatible` / `Unknown command` skew — and `state: ready` (query Moonraker `/printer/info`, not a log grep). Then move to [calibration]({{< relref "calibration" >}}).

## Restoring a config from backup {#restoring-a-config-from-backup}

If you're rebuilding rather than translating fresh, restore `printer.cfg` **with its `SAVE_CONFIG` block** — the eddy frequency table, `tap_threshold`, and bed mesh live there and cannot be retyped — plus `saved_variables.cfg`. Fix absolute paths if the OS user changed (`[save_variables]` filename is the classic one). If klippy reports an unknown section or option, the matching plugin is missing or the config carries an option a newer plugin dropped — install or trim accordingly, don't delete whole sections blindly.
