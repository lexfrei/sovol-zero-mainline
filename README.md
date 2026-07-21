# sovol-zero-mainline

Source for **[sovol.lexfrei.dev](https://sovol.lexfrei.dev)** — a knowledge base for running Sovol printers on upstream Klipper instead of the vendor fork. The Sovol Zero is the first model documented; the structure is built to add others.

The site is a Hugo ([Book](https://github.com/alex-shpak/hugo-book) theme) site. The prose is bilingual (English source, Russian translation) and organized as four reusable layers — hardware, MCU firmware, OS, application — with runbooks that compose them for one concrete situation.

This repo also holds the two code artifacts the site documents:

- [`klipper-plugin/`](klipper-plugin/) — `sovol_codes.py`, an opt-in Klipper plugin that reproduces the vendor's numeric knob-screen codes on unmodified mainline.
- [`klipper-patches/`](klipper-patches/) — the vendor's Klipper modifications extracted as patches, with a provenance analysis.

## Build locally

```bash
git clone --recurse-submodules https://github.com/lexfrei/sovol-zero-mainline.git
cd sovol-zero-mainline
hugo server
```

Content lives in `content/en/` and `content/ru/` (mirrored trees). Push to `main` builds and deploys to GitHub Pages via `.github/workflows/hugo.yml`.

## Contributing

Verified on one printer. Corrections and additions — other probes, other board revisions, other Sovol models — are welcome; open a PR.

## License

[GPLv3](LICENSE). The `klipper-plugin/` and `klipper-patches/` derive from Klipper (itself GPLv3), so the whole repository is under GPLv3 for consistency.
