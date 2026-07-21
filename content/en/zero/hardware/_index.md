---
title: Hardware
weight: 2
bookCollapseSection: true
---

# Hardware — Layer 1

The physical machine, captured as shipped. Nothing here changes during a migration; you just need to know its quirks, because they constrain every layer above. A dead port, a sensor that late units don't populate, a camera with no hardware flip — plan around what the board actually has.

- **[Architecture]({{< relref "architecture" >}})** — the full system map: host plus three CAN MCUs, what's forked versus stock, motion, thermal, sensors, and where each vendor quirk lives.
- **[Toolhead pinout & SWD header]({{< relref "toolhead" >}})** — the STM32F103 toolhead connectors, the eddy-sensor pins, and the SWD header you flash once. This toolhead is shared with the SV08 Max.
