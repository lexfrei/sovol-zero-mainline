---
title: Стек KIAUH
weight: 1
---

# Стек прикладного слоя через KIAUH

Всё выше Klipper — Moonraker, Mainsail, Crowsnest — уже сток upstream, так что самая быстрая чистая установка — это [dw-0/kiauh](https://github.com/dw-0/kiauh). Склонируй его и ставь по порядку: **Klipper, Moonraker, Mainsail, Mainsail-Config, Crowsnest.**

Наведи хост Klipper на тот же чекаут `master`, из которого собраны твои MCU, с venv из его `requirements.txt`, и выстави `[update_manager klipper] channel: dev` в `moonraker.conf`, чтобы он трекал `master`.

## Два постустановочных фикса

Оба из опыта на этой плате:

- **Camera by-id path.** Наведи камеру Crowsnest на её путь `/dev/v4l/by-id/`, а не на `/dev/video0`. Индекс видео сдвигается между ядрами, так что числовое устройство нестабильно; путь by-id — стабилен. Смотри [troubleshooting]({{< relref "/zero/troubleshooting" >}}).
- **update_manager для Crowsnest v5.** Добавь сниппет `update_manager` для Crowsnest v5 дословно из `~/crowsnest/resources/moonraker_update.txt` — старый инлайновый сниппет для v5 неверный и ломает путь обновления.

## Включи CAN на хосте

Чтобы мост и тулхед появились, хосту нужна CAN-обвязка:

- линк `systemd-networkd`, поднимающий `can*` на 1 Мбит,
- `can` + `can_raw` в `/etc/modules-load.d/`,
- udev-правило на `tx_queue_len` 128.

При установке ОС с чистого листа это часть пресида — смотри [clean-slate]({{< relref "/zero/os/clean-slate" >}}). Поставь `scipy` в venv Klipper для eddy-пробы (смотри [плагины]({{< relref "plugins" >}})).

## Проверь, что стек жив

```bash
systemctl is-active klipper moonraker crowsnest   # all active
curl -s localhost:7125/printer/info               # state: ready
```

Klippy `ready` с обоими подключёнными CAN-UUID — доказательство, что весь стек — хост, MCU-мост, тулхед — жив. Спрашивай состояние у Moonraker через `/printer/info`, а не грепом по логу.

Дальше: [переведи конфиг]({{< relref "klipper-config" >}}), затем [поставь плагины]({{< relref "plugins" >}}), которые используешь.
