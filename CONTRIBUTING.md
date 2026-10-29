# Contributing

Thanks for helping out! This is a small project, so the process is light.

## Develop locally

No build step and no dependencies beyond Python 3 and a running Tailscale client.

```bash
cp demo/data.json public/data.json      # fake tailnet, no Tailscale needed
python3 -m http.server -d public 8000   # open http://localhost:8000
```

Or scan your real tailnet:

```bash
cp services.example.json services.json
python3 scan.py --probe
python3 -m http.server -d public 8000
```

The whole UI is `public/index.html` (plain HTML/CSS/JS). The scanner is `scan.py` (standard library only).

## Pull requests

1. Fork and create a branch from `main`.
2. Keep changes focused; describe *what* and *why* in the PR.
3. Check the page at desktop width (light and dark) and at phone width (≤ 640px, always dark). If you changed `scan.py`, run `python3 tests/smoke.py`.
4. **Never commit real tailnet data** — `services.json`, `public/data.json` and `var/` are git-ignored for that reason. Use `demo/data.json` for screenshots.

## Issues

Bug reports with your OS, browser and Tailscale version (`tailscale version`) are the most useful.
