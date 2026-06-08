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

## Flashing the F103 over SWD

The toolhead Katapult is request-only and can't be recovered over CAN once an app is broken, so an SWD probe is the safety net. Use any CMSIS-DAP probe — an ST-Link V2 clone, or a **Flipper Zero running the DAP Link app**.

Wire the probe to the 4-pin SWD header (silk `5V3 IO CK G`), with the head **disconnected from the printer** — the probe's 3.3 V powers the MCU (a blue LED confirms power):

| Header pin | Signal | Probe |
| --- | --- | --- |
| `5V3` | 3.3 V | 3.3 V |
| `IO` | SWDIO | SWDIO |
| `CK` | SWCLK | SWCLK |
| `G` | GND | GND |

### Flipper Zero specifics

- Use the **DAP Link** app — *not* "SWD Probe" (that one only reads, it can't flash). DAP Link presents to the host as a CMSIS-DAP probe (`Combined VCP and CMSIS-DAP Adapter`).
- Default DAP Link GPIO mapping: SWC (SWCLK) = pin 10, SWD (SWDIO) = pin 12, GND = pin 11, 3V3 = pin 9. Confirm in the app's *Config → Help and Pinout* rather than trusting any single source.

### openocd

```bash
# sanity: read the chip (expect Cortex-M3, device id 0x...410)
openocd -c "adapter driver cmsis-dap" -c "transport select swd" -c "adapter speed 1000" \
  -f target/stm32f1x.cfg -c "init" -c "dap info" -c "shutdown"

# erase + write Katapult (0x08000000) + Klipper (0x08002000) + run
openocd -c "adapter driver cmsis-dap" -c "transport select swd" -c "adapter speed 1000" \
  -f target/stm32f1x.cfg -c "init" -c "reset halt" \
  -c "stm32f1x mass_erase 0" \
  -c "flash write_image katapult.bin 0x08000000" \
  -c "flash write_image klipper.bin 0x08002000" \
  -c "reset run" -c "shutdown"
```

Always dump the factory firmware first (`dump_image factory.bin 0x08000000 0x10000`) — a valid dump starts with a sane vector table (initial SP in RAM `0x2000xxxx`, reset vector in flash `0x0800xxxx`), and it is the only exact rollback for the toolhead.
