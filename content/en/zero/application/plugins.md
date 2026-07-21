---
title: Plugins
weight: 3
---

# Plugins and venv extras

The add-ons this machine actually runs, on top of the stock KIAUH stack.

## scipy — required by the eddy probe

Install `scipy` into the Klipper venv:

```bash
~/klippy-env/bin/pip install scipy
```

Without it the eddy probe calibration fails. If PyPI stalls when downloading from the board, sideload the wheels — see [troubleshooting]({{< relref "/zero/troubleshooting" >}}).

## sovol_codes — the knob-screen codes

The vendor firmware shows numeric codes on the knob screen (`101`/`103`, the `60+` shutdown range); mainline shows human-readable messages. To keep the codes on upstream Klipper, install the opt-in `sovol_codes.py` plugin:

```bash
cp sovol_codes.py ~/klipper/klippy/extras/sovol_codes.py
```

Then add `[sovol_codes]` to `printer.cfg` and restart Klipper. It reproduces the vendor codes with zero core edits, using only Klipper's public extension points. The plugin, its tests, and the fidelity notes (which codes fire on stock vs a vendor fork) are on [the resources page]({{< relref "/zero/resources" >}}).

## moonraker-timelapse

Clone it, then:

- symlink `component/timelapse.py` into `~/moonraker/moonraker/components/`,
- copy `klipper_macro/timelapse.cfg` to the config dir,
- add `[timelapse]` and its `update_manager` section to `moonraker.conf`.

## Shake&Tune

Install via its upstream installer. This is one of the things that needs a `NOPASSWD` sudo drop-in for the OS user — the installer runs `sudo` non-interactively. On a clean-slate OS install that drop-in is part of the preseed; see [clean-slate]({{< relref "/zero/os/clean-slate" >}}).

## After installing

If klippy reports a missing section, that section's plugin (screen codes, Shake&Tune) hasn't been reinstalled yet — install the plugin, don't delete the section.
