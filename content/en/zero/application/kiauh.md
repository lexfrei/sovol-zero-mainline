---
title: KIAUH stack
weight: 1
---

# The application stack via KIAUH

Everything above Klipper — Moonraker, Mainsail, Crowsnest — is already stock upstream, so the fastest clean install is [dw-0/kiauh](https://github.com/dw-0/kiauh). Clone it and install, in order: **Klipper, Moonraker, Mainsail, Mainsail-Config, Crowsnest.**

Point Klipper's host at the same `master` checkout your MCUs were built from, with a venv built from its `requirements.txt`, and set `[update_manager klipper] channel: dev` in `moonraker.conf` so it tracks `master`.

## Two post-install fixes

Both come from experience on this board:

- **Camera by-id path.** Point the Crowsnest camera at its `/dev/v4l/by-id/` path, not `/dev/video0`. The video index shifts between kernels, so the numeric device is not stable; the by-id path is. See [troubleshooting]({{< relref "/zero/troubleshooting" >}}).
- **Crowsnest v5 update_manager.** Add the Crowsnest v5 `update_manager` snippet verbatim from `~/crowsnest/resources/moonraker_update.txt` — the older inline snippet is wrong for v5 and breaks the update path.

## Enable CAN on the host

For the bridge and toolhead to appear, the host needs CAN plumbing:

- a `systemd-networkd` link bringing `can*` up at 1 Mbit,
- `can` + `can_raw` in `/etc/modules-load.d/`,
- a udev rule for `tx_queue_len` 128.

On a clean-slate OS install this is part of the preseed — see [clean-slate]({{< relref "/zero/os/clean-slate" >}}). Install `scipy` into the Klipper venv for the eddy probe (see [plugins]({{< relref "plugins" >}})).

## Verify the stack is alive

```bash
systemctl is-active klipper moonraker crowsnest   # all active
curl -s localhost:7125/printer/info               # state: ready
```

Klippy `ready` with both CAN UUIDs connected is the proof the whole stack — host, bridge MCU, toolhead — is alive. Query Moonraker `/printer/info` for the state, not a log grep.

Next: [translate the config]({{< relref "klipper-config" >}}), then [install the plugins]({{< relref "plugins" >}}) you use.
