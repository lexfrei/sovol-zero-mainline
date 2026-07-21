---
title: Application
weight: 4
bookCollapseSection: true
---

# Application — Layer 4

The Klipper host, Moonraker, the web UI, crowsnest, the extras — and the config set that ties them together. This is the layer you touch most, and its config is the most volatile artifact in the whole machine: calibration blocks, macros, and saved variables change with every tuning session. Keep the config set in git and re-snapshot after every session.

Everything above Klipper is already stock upstream, so this layer is mostly install-and-configure, not code porting:

- **[KIAUH stack]({{< relref "kiauh" >}})** — install Klipper (master), Moonraker, Mainsail, Crowsnest, with the two post-install fixes that bite on this board.
- **[Klipper config]({{< relref "klipper-config" >}})** — translate the config off the vendor one: eddy on software I2C, tap, `homing_override`, and the vendor modules to drop.
- **[Plugins]({{< relref "plugins" >}})** — `sovol_codes`, `scipy` for the eddy probe, timelapse, Shake&Tune.
- **[Calibration]({{< relref "calibration" >}})** — drive current, the eddy freq→height table, tap threshold, input shaper, and a supervised first print.
- **[Extras]({{< relref "extras" >}})** — optional hardware proven on a real machine: a USB WiFi dongle, the BTT SFS V2.0 filament sensor, and the backup pair that makes kernel experiments reversible.
