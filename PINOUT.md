# Sovol Zero toolhead pinout & SWD flashing

Transcribed from Sovol's official pin definition (`Motherboard/Extra_Pin_definition.pdf` in [Sovol3d/SOVOL-ZERO](https://github.com/Sovol3d/SOVOL-ZERO)) — see that PDF for the full labelled board image. The toolhead MCU is an STM32F103 (`extruder_mcu`).

## Toolhead connectors

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

Note: the eddy sensor connector exposes `PB10`/`PB11`. On mainline Klipper drive the LDC1612 over **software I2C** on those pins, not hardware `i2c2` (see MIGRATION.md).

## Flashing

See [FLASHING.md](FLASHING.md) for the SWD procedure (Flipper Zero / DAP Link + openocd) — verified only on the toolhead.
