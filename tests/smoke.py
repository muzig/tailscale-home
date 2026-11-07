"""scan.py 冒烟测试：用假的 tailscale CLI 跑一遍，检查生成的 data.json。

    python3 tests/smoke.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "data.json"
    (Path(tmp) / "notes").mkdir()
    (Path(tmp) / "notes" / "draft.html").write_text("<title>Launch &amp; post</title>")
    # apps/：示例应用 + 各种不合格的应用
    apps = Path(tmp) / "apps"
    shutil.copytree(HERE.parent / "examples" / "apps" / "progress", apps / "progress")
    def app(name, manifest, tile=None):
        (apps / name).mkdir()
        (apps / name / "manifest.json").write_text(json.dumps(manifest))
        if tile is not None:
            (apps / name / "tile.json").write_text(tile if isinstance(tile, str) else json.dumps(tile))
    app("wrong-id", {"api": 1, "id": "other", "name": "X"})
    app("future", {"api": 2, "id": "future", "name": "X"})
    app("escape", {"api": 1, "id": "escape", "name": "X", "icon": "../../data.json"})
    app("broken-tile", {"api": 1, "id": "broken-tile", "name": "Broken tile", "entry": None}, "{not json")
    app("fresh", {"api": 1, "id": "fresh", "name": "Fresh", "tile": {"size": "s", "stale_after": 3600}},
        {"updated": "2999-01-01T00:00:00Z", "lines": ["a", "b", "c", "d", "e"], "badge": 0, "status": "warn"})
    app("old", {"api": 1, "id": "old", "name": "Old", "tile": {"stale_after": 3600}},
        {"updated": "2000-01-01T00:00:00+08:00", "lines": ["x"]})
    (apps / "no-manifest").mkdir()
    env = {**os.environ, "TAILSCALE_BIN": str(HERE / "fake-tailscale"), "FIXTURES": str(HERE / "fixtures")}
    subprocess.run([sys.executable, str(HERE.parent / "scan.py"), "-s", str(HERE / "fixtures" / "services.json"), "-o", str(out)],
                   env=env, check=True, timeout=60)
    data = json.loads(out.read_text())

devices = {d["name"]: d for d in data["devices"]}
services = {s["name"]: s for s in data["services"]}

assert data["title"] == "Test Home" and data["lang"] == "en"
assert services["Jellyfin"]["live"] == ["89%", "366 km · asleep"], services["Jellyfin"]
assert "live" not in services["Broken"], "a failing live source is skipped"
assert data["start"] == ["Jellyfin", {"name": "Docs", "size": "m"}] and data["accent"] == "emerald"
assert data["start_grouped"] is True
assert data["navigation"] == {"Docs": {"category": "learn", "primary": False}}
assert data["tailnet"] == "example.github"
assert data["devices"][0]["self"] and data["devices"][0]["name"] == "mac-mini"
assert devices["iphone"]["online"] is False, "offline peers keep their state"
assert [d["name"] for d in data["devices"]][-1] == "iphone", "offline devices sort last"
assert services["Jellyfin"]["url"] == "http://100.64.0.12:8096/", services["Jellyfin"]
assert services["Secure"]["url"] == "https://nas.example-tailnet.ts.net/x/", "https uses the MagicDNS name"
assert services["mac-mini"]["source"] == "serve" and services["mac-mini"]["url"] == "https://mac-mini.example-tailnet.ts.net/"
assert data["bookmarks"][0] == {**data["bookmarks"][0], "name": "Launch & post", "url": "notes/draft.html", "group": "Notes", "device": "mac-mini"}
assert data["bookmarks"][1]["name"] == "Docs"
apps = {a["id"]: a for a in data["apps"]}
assert sorted(apps) == ["broken-tile", "fresh", "old", "progress"], sorted(apps)
assert apps["old"]["stale"] is True and apps["old"]["size"] == "m"
p = apps["progress"]
assert p["url"] == "apps/progress/index.html" and p["size"] == "w" and p["embed"] and p["kind"] == "app"
assert p["live"][0] == "Garden · at soil" and p["badge"] == 3 and "stale" in p, p
assert p["name_i18n"] == {"zh": "进展"} and p["glyph"] == "spark"
assert apps["broken-tile"]["url"] is None and "live" not in apps["broken-tile"], "broken tile data drops only the tile"
f = apps["fresh"]
assert f["size"] == "s" and len(f["live"]) == 4 and "badge" not in f and f["status"] == "warn" and f["stale"] is False, f
diag = data["diagnostics"]
assert data["channel"] == "stable" and isinstance(diag["duration_ms"], int) and "commit" in diag
by = {(i["source"], i["name"]): i["message"] for i in diag["issues"]}
assert set(by) >= {("live", "Broken"), ("app", "wrong-id"), ("app", "future"), ("app", "escape"), ("app", "broken-tile")}, by
assert "$FIXTURES" in by[("live", "Broken")] and str(HERE) not in by[("live", "Broken")], "env values used by live are redacted"
print(f"ok: {len(data['devices'])} devices, {len(data['services'])} services")
