# Changelog

All notable changes to this project. Versions follow [Semantic Versioning](https://semver.org).

## [Unreleased]

### Added
- `start` in `services.json`: pin only the tiles you want to the phone Start screen; everything else stays in the A–Z list
- `accent` in `services.json`: the phone tile color

### Changed
- Phone: all tiles use one accent color like Windows Phone (devices stay grey), and later tiles no longer fill gaps in the device rows
- Letter tiles skip leading punctuation

## [0.4.0] — 2026-10-30

### Changed
- The UI is English by default instead of following the browser language

### Added
- Live tiles: a `live` block on a service fetches a JSON URL during the scan and shows the values on the tile back
- Language button next to the clock; the choice is remembered per browser
- `labels` in `services.json`: show group names in Chinese when the viewer switches language
- Phone: swipe left on the Start screen for the A–Z list, swipe right (or the new back button) to return; the panel follows your finger
- The overview tile is now a live tile that cycles through online devices, offline devices and service reachability
- Private notes: `.html` files in `notes/` next to `data.json` are listed in a Notes group (or the tag set in `notes_group`) and served at `/notes/`

## [0.3.0] — 2026-10-29

### Added
- Live demo on GitHub Pages, built from `demo/data.json`; demo data is labelled and never shows as stale
- Docker image on GHCR for every release: `ghcr.io/muzig/tailscale-home` (amd64 + arm64)
- GitHub CI: scanner smoke test with a fake `tailscale` CLI, JSON and page-script checks, image build
- Issue and PR templates, Code of Conduct, Dependabot for Actions and the nginx base image

### Changed
- The Noto Sans font ships with the page; it no longer loads from Google Fonts, so the page makes no requests outside your tailnet

## [0.2.0] — 2026-10-29

### Added
- Phone layout styled after the Windows Phone 8.1 Start screen: black background, one continuous 4-column tile grid, status bar with signal bars for devices online, turnstile entrance, and an A–Z list of all services behind the → button

## [0.1.0] — 2026-10-29

First public release.

- Start page listing every tailnet device and self-hosted service (from `tailscale serve`, optional port probing and `services.json`)
- Reachability checked by the scanner, keyboard navigation, most-used services first
- English and Chinese UI
- Push-to-deploy with Gitea Actions on macOS; Docker Compose + systemd timer on Linux

[0.4.0]: https://github.com/muzig/tailscale-home/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/muzig/tailscale-home/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/muzig/tailscale-home/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/muzig/tailscale-home/releases/tag/v0.1.0
