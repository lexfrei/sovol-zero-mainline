---
title: Sovol on mainline Klipper
type: docs
---

# Sovol on mainline Klipper

A knowledge base for running Sovol printers on upstream [Klipper](https://github.com/Klipper3d/klipper) instead of Sovol's vendor fork — host and MCUs on one upstream version, nothing to rebase.

The material is organised as **four independent layers** — hardware, MCU firmware, OS, application. Each layer is a set of components you can read on its own. The **runbooks** don't repeat any of it; they route you through the right components in order for one concrete situation, so you assemble exactly the path your machine needs.

## Pick your model

- **[Sovol Zero]({{< relref "/zero" >}})** — Allwinner H616 host, STM32H750 mainboard (also the USB-CAN bridge), STM32F103 CAN toolhead. Verified end-to-end on one printer.

More models slot in beside it — the SV08 Max, for one, shares the Zero's exact toolhead, so that component is written once and reused.

## Start with the idea, then a path

- New here? Read **[the four-layer model]({{< relref "/concepts" >}})** first — it explains why a dead OS never touches your MCUs, and which artifact you actually lose if you skip backups.
- Ready to work? Jump to the **[Sovol Zero runbooks]({{< relref "/zero/runbooks" >}})** and pick the one that matches your situation: migrating in place over the stock firmware, rebuilding from a blank eMMC, or recovering a machine that won't boot.
