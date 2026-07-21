---
title: MCU firmware
weight: 3
bookCollapseSection: true
---

# MCU firmware — Layer 2

The Katapult bootloaders and Klipper apps that run on the two STM32 MCUs. This layer survives the OS: the firmware lives in the MCUs, not on the eMMC, so a wiped or reflashed OS finds the MCUs exactly as it left them. If your MCUs already ran mainline, you can skip straight past this layer.

Moving to mainline means building upstream firmware for each chip and flashing it — the vendor's custom CAN command set rules out a host-only swap. The order that makes it safe:

- **[Building the firmware]({{< relref "build" >}})** — the four images, from one pinned `master` commit, on the printer host or a Mac. Includes the offset table and the reset-vector gate.
- **[Flashing over SWD]({{< relref "flashing" >}})** — the one-time SWD bootstrap of the toolhead with a Flipper Zero / DAP Link. The only time you open the head.
- **[MCU migration]({{< relref "mcu-migration" >}})** — the full sequence: flash the toolhead once over SWD, then the mainboard over USB-Katapult (no SWD), both onto new real-hardware UUIDs.
