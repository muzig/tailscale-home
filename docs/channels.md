# Release channels: stable and preview

**English** · [简体中文](channels.zh-CN.md)

Run two copies of Tailnet Home side by side on the same server. UI changes and new apps get looked at on the preview channel first, then go to stable.

| | Stable | Preview |
|---|---|---|
| Code | `main` branch | `preview` branch |
| Deploy dir | `~/src/self-hosted/tailscale-home` | `~/src/self-hosted/tailscale-home-preview` |
| Local port | `127.0.0.1:4183` | `127.0.0.1:4185` |
| Tailnet address | `https://<server>.<tailnet>.ts.net/` | `https://<server>.<tailnet>.ts.net:8444/` |
| Data | Its own `var/`: `services.json`, `apps/`, `notes/`, `data.json` | A separate `var/`, independent of stable |
| Scan agent | `local.tailscale-home.scan` | `local.tailscale-home-preview.scan` |
| Log | `~/Library/Logs/local.tailscale-home.scan.log` | `~/Library/Logs/local.tailscale-home-preview.scan.log` |
| UI | Normal | Orange `PREVIEW` mark in the status bar, `[PREVIEW]` in the tab title |
| Diagnostics page | In Settings only with `?debug=1` | Always in Settings |

## Releasing

### UI and code

1. Commit on `preview` and push to Gitea: it deploys to the preview channel.
2. Open the `:8444` address on your phone; if something's off, check Settings → Diagnostics.
3. When it's right, merge `preview` into `main` and push: it deploys to stable.

Rollback works as before: set `IMAGE_TAG` in that channel's deploy dir `.env` to an older commit prefix and run `docker compose up -d --no-build`. Each channel has its own `.env`.

### Apps and data

App producers take the same two steps: push to the preview channel's `var/apps/`, check the tile and page, then push to stable.

```bash
# 1. preview
rsync -a --delete ./build/my-app/ homesrv:~/src/self-hosted/tailscale-home-preview/var/apps/my-app/
# 2. stable
rsync -a --delete ./build/my-app/ homesrv:~/src/self-hosted/tailscale-home/var/apps/my-app/
```

Copy stable's `services.json` into the preview channel to try new `start` or `live` settings there.

## Diagnostics page

Every scan writes `channel` and `diagnostics` into `data.json`. The page shows:

- **Channel and version**: the deploy dir's current commit, so you can tell the new code is live.
- **Last scan**: time, duration, and whether port probing was on.
- **Problems**: skipped apps (id mismatch, wrong `api`, path outside the app), unreadable `tile.json`, failing `live` tiles, each with the reason. Values referenced as `$VAR` in a `live` url or headers (usually tokens) are replaced back with `$VAR` and never reach the page.
- **Apps**: each app's id, version, last update, staleness and producer.
- A link to the raw **`data.json`**.

Like the home page itself, diagnostics are visible only inside the tailnet. Stable hides the page by default so day-to-day use stays uncluttered.

## One-time setup on the server

```bash
# Expose the preview channel on the tailnet's port 8444 (stable stays at / on 443)
tailscale serve --bg --https=8444 http://127.0.0.1:4185
```

The first push of the `preview` branch creates the preview deploy dir, scan agent and container.

For a Linux setup without CI, do the same by hand: a second clone in another directory, `HOME_PORT=4185` and `COMPOSE_PROJECT_NAME=tailscale-home-preview` in its `.env`, and `--channel preview` on its scan command.

## Just one channel

Do nothing: without a `preview` branch there is only stable, and the page looks exactly as before.
