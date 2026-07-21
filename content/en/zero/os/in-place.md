---
title: In place, no eMMC reader
weight: 4
---

# Reprovisioning the OS without an eMMC reader

No reader, and you don't want to pull the module? You can put a fresh OS on the eMMC from the running board. The trick is the microSD slot: the H616 boots SD before eMMC, so you boot a fresh image from a card and clone it onto the eMMC from there.

There is no shortcut over USB — the board exposes no USB-C / OTG port, so the usual `sunxi-fel` + U-Boot `ums` route to reach the eMMC over USB is off the table (see [why FEL is out]({{< relref "armbian" >}}#the-board-the-emmc-and-why-fel-is-off-the-table)). SD-boot-and-clone is the only no-reader path.

## Boot from SD, clone to eMMC

```text
Sovobian on microSD  →  boot from SD  →  armbian-install  →  system now on eMMC
```

1. **Write the Sovobian image to a microSD** (Etcher, Armbian Imager, or `dd`). Use **Sovobian**, not a plain BTT CB1 image — Sovobian has the 40 MHz eMMC overlay baked in. Booting a stock CB1 image and cloning it would install a 120/150 MHz eMMC device tree, which "may appear to boot and then fail unpredictably" (see [the CB1 difference]({{< relref "armbian" >}}#what-almost-a-cb1-actually-means)).
2. **Insert the card and power on.** The board boots from the SD ahead of the eMMC. Do your first-boot setup — the friendly way is on [the easy-install page]({{< relref "quickstart" >}}).
3. **Clone the running SD system onto the eMMC:**

   ```bash
   sudo armbian-install
   ```

   Pick the option that installs the system to the eMMC and boots from it ("Boot from eMMC — system on eMMC"; on older images this tool is `nand-sata-install`). It copies the currently-running SD system, including `/boot`, onto the eMMC.
4. **Power off, pull the SD, power on.** The board now boots the freshly-installed system from the eMMC.

The friendly TUI does the same thing, if you'd rather click through a menu: `armbian-config` → System → install to eMMC.

{{< hint warning >}}

**Needs-verification on the Zero specifically.** The SD-boot + `armbian-install` route is confirmed on the SV08 (same H616 host, same CB1 lineage, same boot ROM) and endorsed by Sovobian's own docs, but a Zero-specific transcript wasn't found — treat the exact menu wording and the clone as reproduced-elsewhere, not Zero-verified. Two things to check after cloning: that the eMMC runs at the [verified 37.5 MHz clock]({{< relref "armbian" >}}#first-boot-verifying-the-emmc-clock) (i.e. the `overlay-user/` overlay travelled to the eMMC), and that the board still comes up on the eMMC alone. Keep the SD card — with no OTG, it is your only rescue path if the eMMC install goes wrong.

{{< /hint >}}

## Or just stay on the SD

Nothing forces the system onto the eMMC. Many people run the Zero entirely from a microSD and leave the stock eMMC module unscrewed on a shelf as a factory backup. Use a good card — intermittent SD-boot failures get reported, and a flaky card is the usual cause.

## Then what

Once the OS is where you want it, continue with the [application stack]({{< relref "/zero/application" >}}); if the MCUs are still on vendor firmware, do the [firmware migration]({{< relref "/zero/firmware" >}}) too.
