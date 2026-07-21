---
title: Runbooks
weight: 1
bookCollapseSection: false
---

# Runbooks — pick your path

A runbook doesn't repeat the how-to. It routes you through the layer components in the right order for one concrete situation, and forwards you from each step to the next. Read [the four-layer model]({{< relref "/concepts" >}}) once, then pick the path that matches where you're starting.

```mermaid
flowchart TD
    A[Where are you starting?] --> B{Does the printer boot?}
    B -->|No, or a bad flash to undo| R[Recovery]
    B -->|Yes| C{Replacing the OS?}
    C -->|No, migrate in place| OS1[Over stock firmware]
    C -->|Yes, and I have an eMMC reader| OS2[With an eMMC reader]
    C -->|Yes, but no reader| OS3[Over stock firmware<br/>OS reprovision in place]
```

- **[Over stock firmware]({{< relref "over-stock" >}})** — the printer works and you migrate in place. The vendor OS stays; the application and MCU firmware move to upstream; the OS is optional at the end.
- **[With an eMMC reader]({{< relref "emmc-reader" >}})** — clean-slate build from a blank or reflashed eMMC: OS first, application on top, MCUs usually untouched because they survived whatever you're rebuilding from.
- **[Recovery]({{< relref "recovery" >}})** — a machine that won't boot, or a bad flash to roll back.

No reader and you still want a fresh OS? You can reprovision the OS in place — see [in place, no eMMC reader]({{< relref "/zero/os/in-place" >}}) — then join the application steps of either runbook.
