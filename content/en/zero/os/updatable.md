---
title: Updatable Armbian
weight: 5
---

# Keeping Armbian updatable

The worry that an `apt` upgrade will "lose the dts" and break the eMMC is mostly unfounded, and the real constraint is narrower than it looks. This page separates the two.

> [!NOTE]
> **Experimental in one place.** Everything about *why* the kernel is held is confirmed and documented. The path *off* the hold (moving to a newer kernel and keeping onboard Ethernet) is not yet verified on the Zero — it's flagged below. Take a [full backup]({{< relref "recovery" >}}#back-up-first-the-checklist) before testing it.

## The 40 MHz overlay is already upgrade-proof

The eMMC clock cap is a **user overlay** — `overlay-user/sovol-zero-emmc-40mhz.dtbo`, enabled by `user_overlays=` in `armbianEnv.txt` (see [the overlay]({{< relref "armbian" >}}#the-40-mhz-overlay)). Kernel packages never touch `overlay-user/`, so it survives every `apt` kernel upgrade by design. There is nothing to protect and no reason to hold `linux-dtb` "to save the dts" — that's a misconception.

The fragile method it replaces is the one to avoid: dropping the vendor `sun50i-h616-sovol-emmc.dtb` into `/dtb/allwinner/` and pointing `fdtfile=` at it. *That* file is kernel-provided, so a `linux-dtb` upgrade overwrites it and the clock cap silently reverts. Use the user overlay, not a patched in-tree dtb.

## What the hold is actually for: onboard Ethernet

The one thing that genuinely breaks on a newer kernel is **onboard Ethernet** — and only onboard Ethernet. It works out of the box only on the 6.12.68 kernel (Armbian 26.2.1); 6.18+ either drops the interface entirely or hits a PHY probe race. The full diagnosis, with the upstream issue references, is on [the troubleshooting page]({{< relref "/zero/troubleshooting" >}}#armbian-kernel-branches-and-onboard-ethernet).

So the hold is a **kernel-pair hold, not a whole-system freeze**:

```bash
apt-mark hold linux-image-current-sunxi64 linux-dtb-current-sunxi64
```

With just those two held, `apt update && apt full-upgrade` updates everything else normally — userspace, Klipper's dependencies, security fixes. You are on a supported, updatable system; only the kernel is pinned, and only because of the Ethernet regression.

> [!CAUTION]
> **Never `apt full-upgrade` without the hold in place.** Without it the first upgrade replaces the kernel in place and takes onboard Ethernet with it — with no live rootfs recovery unless you can re-image the eMMC. Set the hold first.

## The WiFi hold was a false alarm

If you're on an older image that also pinned the kernel over a *WiFi* SDIO regression (a `/etc/apt/preferences.d/sovobian-kernel-hold` file), that pin was **retracted**: the SDIO `-110` failure didn't reproduce on healthy hardware and was traced to a PSU-damaged onboard radio, not a kernel regression ([armbian/build#10164](https://github.com/armbian/build/issues/10164)). Deleting that preferences file is correct — it's independent of, and unrelated to, the Ethernet kernel hold above. (If your onboard radio is in fact dead, that's [a hardware failure with its own fix]({{< relref "/zero/application/extras" >}}#usb-wifi-dongle-when-the-onboard-radio-dies), not something a kernel pin addresses.)

## Moving off the hold {#moving-off-the-hold}

The Ethernet fixes are tracked upstream — the missing-interface dts fix ([#10155](https://github.com/armbian/build/pull/10155)), the PHY probe-race fix ([#10242](https://github.com/armbian/build/pull/10242)), and two CB1 WiFi dts fixes ([#10240](https://github.com/armbian/build/pull/10240), [#10241](https://github.com/armbian/build/pull/10241)). Two ways forward, once you want a newer kernel:

1. **Wait for a stable release.** When those fixes ship in a stable Armbian release, `apt-mark unhold linux-image-current-sunxi64 linux-dtb-current-sunxi64` and upgrade normally. Check the issue links above for current status before unholding — as documented they were nightly/edge only.
2. **Go to 6.18 now with the local workaround** *(experimental — not yet verified on the Zero)*. Early-load the `pwm_sunxi_enhance` module so the `ac300` PHY wins the probe race: add it to `/etc/modules-load.d/` **and** `/etc/initramfs-tools/modules`, rebuild the initramfs, then move to the 6.18 kernel (`armbian-config` can switch the kernel branch). This is the documented workaround for the probe race, but "Ethernet came back on the Zero" hasn't been confirmed — treat it as a test to run with a backup and a fallback, not a recipe.

Until you've done one of these, treat "no network after `apt full-upgrade`" as the known Ethernet regression, not broken hardware.
