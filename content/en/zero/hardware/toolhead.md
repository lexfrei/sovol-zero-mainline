---
title: Toolhead pinout & SWD
weight: 2
---

# Toolhead pinout & SWD header

Transcribed from Sovol's official pin definition (`Motherboard/Extra_Pin_definition.pdf` in [Sovol3d/SOVOL-ZERO](https://github.com/Sovol3d/SOVOL-ZERO)) — see that PDF for the full labelled board image. The toolhead MCU is an STM32F103 (`extruder_mcu`), board silk `MINI-ZJB-V1.0`.

## Connectors

| Connector | Pins (as silk-screened) |
| --- | --- |
| Cooling fan | `24V` · PWM `PA6` · FG `PA1` |
| Fan (top) | `24V` · PWM `PA7` · FG `PA2` |
| Model fan | `24V` · PWM `PB0` · FG `PA3` |
| Nozzle thermistor | `PA5` · `GND` |
| Heating block | `GND` · `24V` · `PB1` · `GND` · `PA4` |
| Heater | `24V` · MC_HEATER `PB7` |
| 24 V supply | `GND` · `24V` |
| Extruder motor | DIR `PA9` · STEP `PA8` · EN `PA11` · UART `PA12` |
| X-axis limit | `PA10` · `GND` · `5V` |
| Limit / sensor | `5V` · `GND` · `PC15` · `PC14` |
| **Eddy current sensor** | `5V3` · `GND` · **`PB10` (SCL)** · **`PB11` (SDA)** |
| Mainboard comm (CAN) | CANL · `GND` · CANH  (CAN_R `PB8` · CAN_T `PB9`) |
| **SWD header** (silk `5V3 IO CK G`) | `5V3` = 3.3 V · `IO` = SWDIO (`PA13`) · `CK` = SWCLK (`PA14`) · `G` = GND |

The eddy sensor connector exposes `PB10`/`PB11`. On mainline Klipper drive the LDC1612 over **software I2C** on those pins, not hardware `i2c2` — see [the Klipper config page]({{< relref "/zero/application/klipper-config" >}}).

The SWD header is what you flash once to bootstrap the toolhead. Wiring and the openocd procedure are on [the flashing page]({{< relref "/zero/firmware/flashing" >}}).

## This toolhead is shared with the SV08 Max

The Zero and the SV08 Max carry **the same toolhead module** — identical part numbers in the CAD BOM, pin-for-pin factory configs, the same Katapult boot-UUID (`61755fe321ac`), and a byte-identical pin-definition PDF (`Extra_Pin_definition.pdf`, md5 `b187deb9362b339f55287591f3d510f1` in both official repos). Same board (`MINI-ZJB-V1.0`), same STM32F103, same eddy probe (LDC1612), same LIS2DW accelerometer.

The Max differs only in how the head is *populated and mounted*, not in the board:

| | Zero | SV08 Max |
| --- | --- | --- |
| Part cooling | 1 blower (5020, `fan0` on `PB0`) | 2 blowers: 5020 `PB0` + **3010 `fan1` on `PA7`** |
| Hotend `max_temp` | 355 | 310 (firmware cap) |
| X carriage / mount | Zero sled | larger-machine adapter |

The key detail: `PA7` ("Fan top") is on the Zero's board but left unpopulated. The Max hangs a second fan on it. That's why this pinout page is a component, not a Zero-only fact — a second model reuses it verbatim, and the only config delta is adding or dropping `fan1` on `PA7`.

Not shared: the **mainboard** and its device tree. Zero (`MB_JC_XL_500`, 1×Z) and Max (`MB_JC_XZ_500`, 4×Z quad-gantry, AC bed, feed port) are different PCBs of the same H616 + STM32H750 platform, with different DTS/dtb. Mainboards are not interchangeable as-is.
