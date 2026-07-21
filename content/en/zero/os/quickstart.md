---
title: Easy install
weight: 1
---

# Easy install — for most people

The [clean-slate page]({{< relref "clean-slate" >}}) bakes everything into the image offline, by hand. You don't have to. There's a friendlier path: flash a base image, let it come up, and answer a short wizard over SSH — the same first-run experience as any Armbian board. No ext4 editing, no `debugfs`.

Two facts make this easy on the Zero:

- **The board has a microSD slot, and the H616 boots SD before eMMC.** So you can run the whole thing from a microSD — no reader, no pulling the module, no risk to the stock eMMC. Leave the eMMC alone as a factory backup, or [move the system onto it later]({{< relref "in-place" >}}).
- **The first SSH login runs Armbian's friendly setup wizard** (`armbian-firstlogin`): it makes you change the root password, creates your user, and asks locale + timezone — right there in the SSH session.

Use the **[Sovobian](https://github.com/lexfrei/sovobian/releases)** image for all of these — it's upstream Armbian CB1 with the 40 MHz eMMC overlay already baked, and it ships the 6.12.68 kernel where onboard Ethernet works out of the box. A plain BTT CB1 image drives the eMMC at 3× the validated clock (see [the CB1 difference]({{< relref "armbian" >}}#what-almost-a-cb1-actually-means)) — don't use it.

Pick the option that fits you, easiest first.

## Option 1 — Armbian Imager, preseed in a GUI

Armbian Imager 2.0 (June 2026) added a Raspberry-Pi-Imager-style setup screen: pick vendor → board → image → storage, and fill in a username, password, WiFi (SSID + password + country code), timezone, and locale that it applies on first boot. Flash Sovobian to a microSD this way, boot, and the board is configured before you ever log in.

{{< hint warning >}}

**One caveat, and it's the Zero's radio.** The onboard RTL8189FTV can't complete WPA3-SAE. On a WPA2/WPA3-transition SSID a generic preseed that doesn't pin WPA-PSK will silently fail to join. If WiFi doesn't come up, that's almost certainly why — fall back to Option 2 (Ethernet), or pin `key-management: "psk"` by hand (see [the netplan block]({{< relref "armbian" >}}#headless-preseed-why-wifi-has-to-be-baked-in)).

{{< /hint >}}

## Option 2 — Ethernet cable, then SSH (most reliable)

The community default, and the one that just works. Flash Sovobian to a microSD (any imager), plug in an Ethernet cable, and:

```bash
ssh root@<printer-ip>     # default password: 1234
```

The first login runs the wizard — change the password, create your user, set locale/timezone. Then set up WiFi from a menu and unplug the cable:

```bash
sudo armbian-config       # Network → WiFi
```

Sovobian's 6.12.68 kernel is exactly the one where onboard Ethernet works, so the cable is reliable here. On Sovobian use `armbian-config` for WiFi — it's the minimal image (netplan + systemd-networkd), so `nmtui` / NetworkManager isn't installed.

## Option 3 — Minimal WiFi bake, friendly rest (no cable)

If you have no Ethernet and want WiFi-only without preseeding everything: bake in only the two WiFi files (`/etc/systemd/network/10-wlan0.link` and `/etc/netplan/30-wifi.yaml`, mode 0600, with `key-management: "psk"` pinned — see [the netplan block]({{< relref "armbian" >}}#headless-preseed-why-wifi-has-to-be-baked-in)), and **leave `/root/.not_logged_in_yet` in place**. WiFi then comes up at boot, while the friendly user/locale/timezone wizard still runs at your first SSH login. One-time expert prep on the image, friendly from then on.

## Not recommended for a first-timer

- **UART serial console** — the H616's login console is `ttyS0` (UART0, the SoC debug pads), not the UART3 the overlays enable. It needs a 3.3 V USB-TTL adapter on the debug pads and terminal fiddling. Skip it unless you already do this.
- **HDMI + keyboard** would be a friendlier local console than UART for running the wizard offline — but it's unconfirmed that the compact Zero board exposes an HDMI port (the SV08 does). Check your board before planning around it.

## Then what

You're now running from the microSD. That's a perfectly good place to stay — many people do. When you want the system on the onboard eMMC (to free the slot, or just for tidiness), move it there without a reader: [in place, no eMMC reader]({{< relref "in-place" >}}). From here, the rest is the same as any install — the [application stack]({{< relref "/zero/application" >}}) and, if your MCUs are still on vendor firmware, the [firmware migration]({{< relref "/zero/firmware" >}}).
