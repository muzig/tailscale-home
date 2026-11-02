# Tailnet Home Apps (draft spec v1)

**English** · [简体中文](apps.zh-CN.md)

> Status: **v1, implemented** (`scan.py`, `public/index.html`, `deploy/nginx.conf`). Example app: `examples/apps/progress/`.

## 1. Goal

Today Tailnet Home shows three kinds of things: tailnet devices, services (discovered or hand-written) and private pages in `notes/`. Separately, `live` puts a few values from a JSON endpoint on the back of a tile.

What we want: **install an "app" on the home page the way you install an APK on an Android phone**. It gets a live tile on the Start screen, and tapping it opens its own page inside the device screen. The difference is that an app here is plain web technology: a directory of static files, with no build step and nothing executed on the server.

The first reference app is **Jarvis progress**: a personal assistant exports its current focus, decisions waiting on the user and recent work as an app, so it's visible at a glance on the phone.

### Principles

- **Installing an app means copying a directory**; uninstalling means deleting it. No store, no signing, no build.
- **The home page never runs app code.** `scan.py` only reads JSON, nginx only serves static files, and app JavaScript runs only in a browser sandbox.
- **Data is pushed in by the app's producer.** A producer is any program on the tailnet that can write files (a script, CI, a timer). The home page doesn't pull private data itself.
- **Private by default.** Apps live in the git-ignored `var/`, are reachable only from the tailnet, and never enter the repo or the demo.
- **Compatible with what exists.** `notes/` and `live` stay as they are; think of them as simplified apps.

### Out of scope for v1

App store or index, signing and verification, server-side runtime, background jobs, inter-app messaging, tailnet API permissions, per-app settings pages.

## 2. Mapping

| Android | Tailnet Home | Notes |
|---|---|---|
| APK | App directory `var/apps/<id>/` | One directory is one app |
| `AndroidManifest.xml` | `manifest.json` | Name, version, tile and entry |
| Activity | `index.html` | Opens in the device screen when the tile is tapped |
| App Widget | `tile.json` | Live tile data on the Start screen |
| Install / uninstall | Copy in / delete the directory | Takes effect on the next scan (≤10 min by default) |
| Background push | Producer | Generates and overwrites `tile.json` and pages from outside |
| App sandbox | iframe `sandbox` + CSP | Apps can't read the home page's storage or state |

## 3. Package layout

```
var/apps/<id>/
  manifest.json   # required
  tile.json       # optional: live tile data, updated by the producer
  index.html      # optional: the app page (entry can be changed in the manifest)
  icon.svg        # optional: icon
  ...             # any other static files the page needs (css, js, images, json)
```

- `<id>`: lowercase letters, digits and hyphens, 2–40 characters, must equal `manifest.id`; otherwise the app is skipped.
- All paths are relative to the app directory: no `..`, no absolute paths outside it.
- App pages must reference their own assets with relative paths, because they're served under `/apps/<id>/`.

## 4. `manifest.json`

```json
{
  "api": 1,
  "id": "jarvis-progress",
  "name": "Jarvis",
  "name_i18n": { "zh": "Jarvis 进展" },
  "version": "0.1.0",
  "description": "The assistant's current focus, pending decisions and recent work",
  "entry": "index.html",
  "icon": "icon.svg",
  "glyph": "spark",
  "tile": {
    "size": "w",
    "data": "tile.json",
    "stale_after": 86400
  },
  "embed": true,
  "producer": "Jarvis on my-laptop"
}
```

| Field | Required | Meaning |
|---|---|---|
| `api` | yes | Spec major version, currently `1`. `scan.py` skips unknown majors with a warning |
| `id` | yes | Must equal the directory name |
| `name` | yes | Shown on the tile and in the A–Z list |
| `name_i18n` | no | Name per UI language, e.g. `{"zh": "…"}` |
| `version` | yes | The app's own SemVer, shown in details so you can tell an update arrived |
| `description` | no | One sentence |
| `entry` | no | App page, default `index.html`; `null` for no page (the tile then isn't clickable) |
| `icon` / `glyph` | no | Own icon, or a built-in glyph name (same as `glyph` in `services.json`); neither means a letter tile |
| `tile.size` | no | `s`, `m` or `w`, default `m`; a size given in `start` wins |
| `tile.data` | no | Tile data file, default `tile.json` |
| `tile.stale_after` | no | Seconds. If `tile.json`'s `updated` is older, the tile is marked stale. Not checked by default |
| `embed` | no | Whether it may open inside the device screen, default `true`; `false` shows the launch screen with *Open in a new tab* |
| `producer` | no | Who updates the app; display only, helps when data stops moving |

Unknown fields are ignored so new fields never break older home pages.

## 5. `tile.json` (live tile)

```json
{
  "updated": "2026-11-02T09:30:00+08:00",
  "lines": ["Garden · at soil", "3 decisions waiting", "2 done today"],
  "badge": 3,
  "status": "ok"
}
```

| Field | Meaning |
|---|---|
| `updated` | ISO 8601 with time zone. Used for staleness and shown in the app details |
| `lines` | 1–4 lines, rendered like today's `live`: first line large, the rest small, overflow ellipsized |
| `badge` | Optional non-negative integer in the tile corner; hidden when `0` or missing |
| `status` | Optional `ok`, `warn` or `error`; `warn`/`error` get a warning color. Staleness is decided by the home page from `stale_after`, not reported by the app |

Producers should write `tile.json` **atomically** (temp file, then `mv`; rsync does this by default) so a scan never reads a half-written file.

## 6. How the home page loads apps

### 6.1 `scan.py`

1. Look for `apps/*/manifest.json` next to `data.json` (`var/apps/` in the Docker setup).
2. Validate `api`, `id` and paths; print the reason and skip invalid apps without failing the scan (same as `live`).
3. Read `tile.data` and work out staleness.
4. Write a new `apps` array into `data.json`:

```json
"apps": [{
  "id": "jarvis-progress", "name": "Jarvis", "name_i18n": {"zh": "Jarvis 进展"},
  "version": "0.1.0", "url": "apps/jarvis-progress/index.html", "icon": "apps/jarvis-progress/icon.svg",
  "glyph": "spark", "size": "w", "embed": true, "producer": "Jarvis on my-laptop",
  "live": ["Garden · at soil", "3 decisions waiting", "2 done today"],
  "badge": 3, "status": "ok", "updated": "2026-11-02T09:30:00+08:00", "stale": false
}]
```

`scan.py` only reads JSON; it never executes anything from an app or fetches app pages.

### 6.2 `index.html`

- Apps join the Start screen and the A–Z list like services and bookmarks; `start` in `services.json` can pin them by `name` or `id`, e.g. `{"name": "jarvis-progress", "size": "w"}`.
- The tile back reuses the existing `live` style; `stale: true` dims the tile and adds an "updated N hours ago" line.
- Tapping opens the app inside the Phone / Dual screen device screen (launch screen when `embed: false`).
- App pages load in `<iframe sandbox="allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox">` — **without** `allow-same-origin`.

### 6.3 nginx

```nginx
# Apps: ./var/apps/<id>/, static files only
location /apps/ {
    alias /data/apps/;
    add_header Cache-Control "no-cache";
    # Sandboxed even when opened directly: no same-origin access to the home page
    add_header Content-Security-Policy "sandbox allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox";
    add_header X-Content-Type-Options "nosniff";
}
```

## 7. Security and privacy

- **The trust boundary is "who can write `var/`".** Anyone who can write `var/apps/` already controls the server, so v1 has no signing — but apps are still isolated from the home page so a broken app can't break it.
- **Sandboxed.** App pages get an opaque origin: no access to the home page's `localStorage` (language, display mode, click ranking) or cookies, and no access to its DOM. `localStorage` is unavailable inside the sandbox; apps that need state should keep it in the URL hash or have the producer write it into JSON.
- **Tailnet only.** Same as `notes/`: exposed through `tailscale serve`, no public ports.
- **Never committed.** `var/` is already git-ignored; example apps use fake data only and live in `examples/apps/`.
- **Producers choose how much to show.** Recommended: tiles show summaries only and sensitive details stay out of the app, since other devices and shared users on the tailnet can open the home page too.

## 8. Producer conventions

Producers can be anything — a shell script, Python, a CI job — on any machine. Recommended way to publish:

```bash
# Build into a local directory on the producer, then sync the whole directory to the home server
rsync -a --delete ./build/jarvis-progress/ homesrv:~/src/self-hosted/tailscale-home/var/apps/jarvis-progress/
```

- `--delete` keeps the app directory identical to the producer's and removes old files.
- Uninstall: `ssh homesrv rm -rf ~/src/self-hosted/tailscale-home/var/apps/jarvis-progress`.
- With a preview channel, push to its `var/apps/` first and to stable after checking; see [channels.md](channels.md). When an app is skipped or its tile data can't be read, the reason shows in Settings → Diagnostics.
- New installs and updates appear after the next scan at the latest (LaunchAgent / systemd timer, 10 minutes by default). Run `scan.py` once after syncing to see it immediately.

## 9. Relation to existing features

| Feature | Relation |
|---|---|
| `notes/*.html` | Equivalent to an app with a page but no manifest or tile; unchanged |
| `live` in `services.json` | Pull: the home page calls an existing service's endpoint. Apps are push: the producer delivers the data. Both stay |
| `start` / `accent` | Apps take part in pinning and coloring with the same rules as services |

## 10. Reference app: Jarvis progress

| Part | Content |
|---|---|
| Producer | An export script in the Jarvis repo reading `memory/state.md`, each effort README and today's calendar |
| Trigger | Jarvis exports and rsyncs to the home server at the end of every session |
| Tile (`w`) | Current focus and where it stopped, number of decisions waiting (`badge`), items done today |
| Page | Current focus, pending decisions (each with a recommendation), recent work, status of each effort |
| Privacy | Progress-level summaries only (item number, have / missing / to confirm, current step); no amounts, numbers or document details |
| Staleness | `stale_after` of 1 day: the tile dims when Jarvis hasn't wrapped up a session in over a day |

The repo also gets a fake-data `examples/apps/progress/` for the demo and tests.

## 11. Implementation plan and acceptance

| Step | Work | Accepted when |
|---|---|---|
| 1 | `scan.py` reads `apps/` and writes `data.json.apps` | `tests/smoke.py` covers: valid, id mismatch, `api: 2`, broken tile.json, stale |
| 2 | nginx `/apps/` + CSP sandbox | Opened directly, an app page can't read the home page's `localStorage` |
| 3 | `index.html` renders app tiles, `start` pinning, iframe opening | Opens at phone width and in Dual screen; stale tiles are dimmed |
| 4 | `examples/apps/progress/` and demo data | The live demo shows the example app |
| 5 | README, CHANGELOG, `services.example.json` notes | Both READMEs have an "Apps" section |
| 6 | Jarvis progress deployed to homesrv as the first real app | Tile visible and opens on the phone; the page holds summaries only |

## 12. Decisions

1. **Name**: Apps, Windows Phone's own term.
2. **When tile data is read**: `scan.py` reads it into `data.json`, at most one scan period late; the browser never fetches `tile.json` itself.
3. **`actions`** (shortcuts on a long-press of the tile): deferred to v2.
