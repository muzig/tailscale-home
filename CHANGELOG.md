# Changelog

All notable changes to this project. Versions follow [Semantic Versioning](https://semver.org).

## [Unreleased]

### Added
- Phone: swipe left on the Start screen for the A–Z list, swipe right (or the new back button) to return; the panel follows your finger
- The overview tile is now a live tile that cycles through online devices, offline devices and service reachability

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

[0.3.0]: https://github.com/muzig/tailscale-home/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/muzig/tailscale-home/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/muzig/tailscale-home/releases/tag/v0.1.0
