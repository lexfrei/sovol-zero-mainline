---
title: Плагины
weight: 3
---

# Плагины и допы venv

Дополнения, которые эта машина реально гоняет поверх стокового стека KIAUH.

## scipy — нужен eddy-пробе

Поставь `scipy` в venv Klipper:

```bash
~/klippy-env/bin/pip install scipy
```

Без него калибровка eddy-пробы падает. Если PyPI виснет при скачивании с платы, подсунь колёса вручную — смотри [troubleshooting]({{< relref "/zero/troubleshooting" >}}).

## sovol_codes — коды экрана-крутилки

Вендорская прошивка показывает числовые коды на экране-крутилке (`101`/`103`, диапазон shutdown `60+`); mainline показывает человекочитаемые сообщения. Чтобы сохранить коды на upstream Klipper, поставь опциональный плагин `sovol_codes.py`:

```bash
cp sovol_codes.py ~/klipper/klippy/extras/sovol_codes.py
```

Затем добавь `[sovol_codes]` в `printer.cfg` и перезапусти Klipper. Он воспроизводит вендорские коды с нулём правок в ядре, используя только публичные точки расширения Klipper. Плагин, его тесты и заметки о точности (какие коды срабатывают на стоке, а какие на вендорском форке) — на [странице ресурсов]({{< relref "/zero/resources" >}}).

## moonraker-timelapse

Склонируй, затем:

- симлинкни `component/timelapse.py` в `~/moonraker/moonraker/components/`,
- скопируй `klipper_macro/timelapse.cfg` в директорию конфигов,
- добавь `[timelapse]` и его секцию `update_manager` в `moonraker.conf`.

## Shake&Tune

Ставь через его upstream-инсталлер. Это одна из тех вещей, которым нужен `NOPASSWD`-дропин для пользователя ОС — инсталлер запускает `sudo` неинтерактивно. При установке ОС с чистого листа этот дропин — часть пресида; смотри [clean-slate]({{< relref "/zero/os/clean-slate" >}}).

## После установки

Если klippy жалуется на отсутствующую секцию, значит плагин этой секции (коды экрана, Shake&Tune) ещё не переустановлен — ставь плагин, не удаляй секцию.
