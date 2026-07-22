---
title: Architecture
weight: 1
---

# System architecture

A reference description of the Sovol Zero as shipped, captured from the running machine — host filesystem, Klipper config, MCU runtime, git remotes. It exists to support the migration: knowing exactly what hardware and software is in play, and which pieces are vendor-specific versus stock.

The Sovol Zero is a CoreXY printer, an industrialised derivative of the Voron 0, with a 150×150×150 mm build volume in a closed frame. It runs Klipper on a Linux host talking to multiple STM32 MCUs over CANbus. Internally Sovol calls it the "SV08 mini" — the vendor firmware package ships as `SV08mini_Update_Package-*.deb`, and it shares its CAN toolhead module with the SV08 Max — though it's sold only as the Sovol Zero.

## Compute and MCU topology

The printer is a Linux host plus **three CAN-connected STM32 MCUs** (the third is optional, for the chamber module).

| Node | Hardware | CAN UUID | Firmware (commit) | Role |
| --- | --- | --- | --- | --- |
| host | Allwinner H616 (64-bit, 1 GB RAM, hostname `SPI-XI`) | — | Klipper host `8a8b5e8` (1.4.5) | Klippy, Moonraker, web stack |
| `mcu` | STM32H750 (Cortex-M7, mainboard) | `0d1445047cdd` | `14d7b18-dirty` (built 2025-02-10) | XY steppers, Z, bed heater, board fans, display |
| `extruder_mcu` | STM32F103 (toolhead) | `61755fe321ac` | `cc8afd8-dirty` = 1.3.7 (built 2025-03-10) | Extruder, hotend, eddy sensor, accelerometer, part fan |
| `hot_mcu` | STM32 (chamber module, optional) | `58a72bb93aa4` | — | Chamber heater + fan + temp sensors |

Notes:

- The host talks to the MCUs over **CANbus**, not USB-serial. MCUs are addressed by `canbus_uuid` in `printer.cfg`.
- **Host and MCUs are built from different commits** (host 1.4.5, main MCU `14d7b18`, toolhead MCU 1.3.7, all `-dirty`). The Klipper protocol handshake is compatible, but "the printer's version" is not a single number — OTA updates the host more often than it reflashes the MCUs.
- Chip identity is confirmed in `src/stm32/chipid.c`: the mainboard MCU (UUID `0d1445…`) is an STM32H750 (`0x8f` discriminator, built from `.config750`), and the toolhead MCU (UUID `61755f…`) is an STM32F103 (`0x80`, `.config103`/`stm32f103xe`). There are three per-chip build configs on disk (`.config`, `.config103`, `.config750`). Firmware build tags carry the host hostname `SPI-XI`, i.e. the firmware is compiled on the printer itself.
- Caveat: the vendor `chipid.c` does not read the hardware `UID_BASE`; it synthesises the CAN UUID from a hardcoded array with a per-chip-family last byte. The CAN UUIDs are therefore baked into the firmware, not unique per silicon — an anti-pattern the migration reverts (mainline reads the real UID, so both MCUs come up on new UUIDs after reflashing).

### Why CAN, and why it isn't a choice

The host-to-toolhead link being CAN is dictated by the board wiring, not a Klipper option — it can't be swapped without rewiring the machine:

- The inter-board cable (toolhead ↔ mainboard) is a CANH/CANL differential pair on **PB8/PB9**. On the F103 those pins are CAN_RX/CAN_TX (and the I2C1 remap) — they carry **no USART alternate function at all**, so a UART cannot run on this cable. The F103's three USARTs sit on other pins (USART1 PA9/PA10, USART2 PA2/PA3, USART3 PB10/PB11), and those are already spoken for anyway — PB10/PB11 by the eddy sensor's software I2C, PA9/PA10 by the extruder driver (DIR) and the X-endstop. A UART toolhead on this cable is physically impossible.
- The F103 has no USB of its own; it reaches the host **only** through the mainboard. So the H750 **must** run in USB-CAN-bridge mode, or the toolhead is unreachable — the bridge is the only topology that makes both MCUs visible.
- It is also the *right* design: CAN keeps the moving toolhead's umbilical to two signal wires plus power instead of the ~10+ wires a direct (MCU-less) toolhead would drag through a constant flex.

## Software stack — what is forked

**Only Klipper is forked.** Everything else is stock upstream, merely on older 2024-era versions.

| Component | Origin | Forked? | Version on printer |
| --- | --- | --- | --- |
| Klipper | Sovol internal Gitea | **YES — vendor fork** | `8a8b5e8` (1.4.5) |
| Moonraker | `github.com/Arksine/moonraker.git` | No (stock) | `v0.9.3-1-g4e00a07` |
| mainsail-config | `github.com/mainsail-crew/mainsail-config.git` | No (stock) | `v1.2.1` |
| moonraker-timelapse | `github.com/mainsail-crew/moonraker-timelapse.git` | No (stock) | `v0.0.1-143` |
| crowsnest | `github.com/mainsail-crew/crowsnest.git` | No (stock) | `v4.1.9-1` |
| moonraker-obico | `github.com/TheSpaghettiDetective/moonraker-obico.git` | No (stock) | `v2.0.9` |

The Klipper fork's history is squashed (no upstream `Kevin O'Connor` authorship survives) — an opaque vendor snapshot, not a clean rebase. The vendor delta from import to HEAD is ~715 insertions across host `klippy/` and MCU `src/`. The [patch provenance analysis]({{< relref "/zero/resources" >}}) breaks down what changed and why.

Running systemd services: `klipper`, `moonraker`, `crowsnest`, `KlipperScreen`, `moonraker-obico`.

Third-party Klipper extras (non-stock but not Sovol-specific): `gcode_shell_command.py` (Arksine's shell-command plugin, used by the OTA/IP macros).

## Motion system

CoreXY. Aggressive limits inherited from the Voron 0 speed-printing lineage:

- `max_velocity: 1200`, `max_accel: 40000`, `minimum_cruise_ratio: 0.5`, `square_corner_velocity: 5.0`
- Z: `max_z_velocity: 20`, `max_z_accel: 500`

| Axis | Driver | Run current | Step/dir/enable | Endstop | Notes |
| --- | --- | --- | --- | --- | --- |
| X | TMC5160 (SW-SPI) | 3.5 A | `PE1 / !PD7 / !PD5` | `^extruder_mcu:PA10` | rot. dist 40, 16 µsteps |
| Y | TMC5160 (SW-SPI) | 3.5 A | `PD3 / !PD2 / !PD0` | `^PD1` | rot. dist 40, 16 µsteps |
| Z | TMC2209 (UART `PA6`, addr 3) | 1.5 A | `PA5 / !PA4 / !PA7` | `probe:z_virtual_endstop` | rot. dist 4, lead screw |
| Extruder | TMC2209 (UART `extruder_mcu:PA12`, addr 3) | 0.8 A | `extruder_mcu:PA8/PA9/PA11` | — | rot. dist 6.5 (Orbiter-style) |

The XY motors use TMC5160 at 3.5 A — substantial drivers, consistent with the high accelerations.

## Probing and bed leveling

Two distinct probing systems, both on the toolhead MCU, both feeding `z_offset_calibration` (a vendor-only module):

- **Eddy-current (non-contact):** `[probe_eddy_current eddy]`, sensor `ldc1612` on `extruder_mcu` I2C bus `i2c2`. Offsets `x=-19.8, y=-0.75, z_offset=3.5`. Continuously scans the bed to build the mesh (`[bed_mesh]` 20×20, bicubic, area 12,12→132,140). The factory calibration table is stored in `printer.cfg`'s SAVE_CONFIG block (`reg_drive_current=15`).
- **Contact (load/strain):** the vendor `z_offset_calibration` module uses a single load sensor under the bed to find nozzle-to-bed contact (`internal_endstop_offset: -0.20`). Both `non_contact_probe` and `contact_probe` point at the eddy sensor; the contact path is the vendor's tensometric Z-zero.
- `Z` homes via `probe:z_virtual_endstop`; `safe_z_home` at `96, 76.2`.

For migration: current upstream covers the eddy sensor natively — `probe_eddy_current` with `METHOD=scan/rapid_scan/tap`. The under-bed strain gauge does NOT map to upstream `load_cell`/`load_cell_probe`/`hx71x`: its interface is not an ADC stream but a plain GPIO endstop (PD9 tare pulse, PD10 contact trigger), driven by a community config recipe — and the sensor comes and goes by revision: v1.0 used it for Z-zero (the eddy read only the mesh), while v1.1 dropped it and moved Z-zero to eddy tap. The load-cell version shipped in production for a while, so it isn't only a v1.0 board leftover — but later units arrive with no sensor and no mounting holes, so check for the physical part before planning around it. The vendor MCU adds custom commands (`ldc1612_setup_home`, `query_ldc1612_home_state`) that have no stock equivalent, so migrating requires reflashing the MCUs from upstream `src/` and rewriting these config sections.

## Thermal

| Heater | Pin | Sensor | Max | Control |
| --- | --- | --- | --- | --- |
| Extruder | `extruder_mcu:PB7` | custom ADC table `my_thermistor_e` | 355 °C | PID |
| Bed | `PD12` | `my_thermistor` (100 k) | 125 °C | PID |
| Chamber (optional) | `hot_mcu:PA0` | EPCOS 100K | 70 °C | watermark |

> [!WARNING]
> **Check the hotend for its copper bushing.** Older hotend revisions came without it, and they still turn up — the listing shows a bushing the unit may not have. It's not subtle: without the bushing the heatbreak sits loose in the heatsink and visibly wobbles. And it matters thermally — the heatsink can't pull heat off the heatbreak, so the radiator does nothing, thermal paste doesn't save it, and you get heat creep and clogs. To spot it: the current hotend is gold-coloured and has the insert, an older one is a plain tube. Sovol replaces an affected hotend for free — tell the seller it's the withdrawn older version. Shared Zero/SV08 Max toolhead, so it applies to both.

Fans:

- `[fan_generic fan0]` — part cooling (`extruder_mcu:PB0`)
- `[fan_generic fan2]` — auxiliary (`PE11`); `[fan_generic fan3]` (`PE14`)
- `[temperature_fan exhaust_fan]` — chamber exhaust through the carbon filter (`PB0`, watermark, target 32 °C, tach on `PB1`)
- `[heater_fan hotend_fan]` — hotend (`extruder_mcu:PA6`, on at 45 °C)
- `[heater_fan chamber_fan]` (chamber module, `hot_mcu:PA6`)

Chamber module adds `M141`/`M191` macros (set/wait chamber temp) and a `heater_generic chamber_heater`.

## Other sensors

- **Accelerometer:** `[lis2dw]` on `extruder_mcu` via software SPI (`PB12-PB15`), `axes_map: x,z,y`. Used by `[resonance_tester]`.
- **Filament:** `[filament_switch_sensor]` on `PB2`, `pause_on_runout: False`.

**Vendor gotcha — input shaper:** `[resonance_tester]` is hard-pinned to `min_freq: 35, max_freq: 45` — the narrow search window the printer reviews complained about, baked into the shipped config, not just the firmware. Saved result: `shaper_x = mzv @ 40.2`, `shaper_y = zv @ 42.6`. Mainline's LIS2DW chunked-FIFO read produces cleaner traces.

## Display, LED, UI

- `[display]` — UC1701 monochrome LCD (the knob screen), on the EXP1/EXP2 headers with a click encoder.
- `[neopixel Screen_Colour]` — 3 RGB LEDs backlighting the screen (`EXP1_6`).
- `[output_pin main_led]` — main chamber light (`PD13`).
- `KlipperScreen.service` runs alongside the LCD.
- The vendor firmware shows numeric "Tip code" / error codes on this screen (101/103, the 60+ shutdown range). That UI was wired invasively into Klipper core; it is reproduced as the opt-in [`sovol_codes` plugin]({{< relref "/zero/resources" >}}) for the migration.

## Networking and remote access

- Moonraker on `:7125`, Mainsail (nginx, `server_name _`) on `:80`, Moonraker-Obico for remote access.
- `trusted_clients` includes the home LAN ranges; `cors_domains` covers `*.lan`, `*.local`, mainsail/fluidd hosts.
- WiFi: if the SSID is in WPA2/WPA3-transition mode, the vendor's old WiFi stack cannot complete SAE, so the profile must be pinned to `wpa-psk`. On the mainline OS, netplan pins `key-management: "psk"` — see [the Armbian page]({{< relref "/zero/os/armbian" >}}).
- **Camera:** `/dev/video0` via crowsnest/ustreamer (`[cam 1]`, 720×540, MJPEG on `:8080`). The camera (MGS1, `364d:6366`) is mounted upside down, and there is no hardware flip: it exposes no v4l2 flip control, ustreamer cannot rotate, and the USB Extension Unit's vendor controls are raw register blobs with no flip toggle — correct it client-side with `rotation: 180` in the Moonraker webcam definition.

## OTA and MCU flashing

- Host OTA: `~/ota_client.sh` (vendor), triggered by the `_OTA` macro.
- MCU firmware: prebuilt `.bin` files in `~/printer_data/build/`, flashed over CAN by `canbus_uuid` via the bootloader (Katapult/CanBoot-style) with the vendor's `flash_can.py` (Klipper's CAN-flash helper — distinct from Katapult's `flashtool.py`, which the migration uses). Macros `_MCU_UP` / `_EXTRUDER_MCU_UP` / `_EXTRA_MCU_UP` drive the per-MCU update scripts.
- Implication for migration: switching to upstream Klipper means building upstream firmware for each MCU's chip and flashing the `.bin` over CAN, in lockstep with the host — the custom CAN command set rules out a host-only swap. See [MCU firmware]({{< relref "/zero/firmware" >}}).

## Migration summary

Upstream now covers essentially all of the Sovol-specific hardware natively — eddy-current (`probe_eddy_current` scan/tap), LED (`neopixel`), fans (`temperature_fan`/`heater_fan`), both MCU chips (`stm32f1` for the toolhead F103, `stm32h7` for the mainboard H750 — and stock H7 support is newer than the vendor's), and all input shapers. The fork persists mainly because Sovol predated those upstream additions. Migrating is therefore largely **config rewriting + MCU reflashing**, not code porting, plus the `sovol_codes` plugin for the screen UI. The only genuinely vendor-only host modules are `z_offset_calibration.py` and `probe_pressure.py` — and the latter is not superseded by upstream `load_cell_probe`: the strain-gauge interface is a GPIO endstop, not an ADC the `hx71x` path could read. On late units the sensor is absent anyway.
