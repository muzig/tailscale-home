"""scan.py 冒烟测试：用假的 tailscale CLI 跑一遍，检查生成的 data.json。

    python3 tests/smoke.py
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "data.json"
    (Path(tmp) / "notes").mkdir()
    (Path(tmp) / "notes" / "draft.html").write_text("<title>Launch &amp; post</title>")
    env = {**os.environ, "TAILSCALE_BIN": str(HERE / "fake-tailscale")}
    subprocess.run([sys.executable, str(HERE.parent / "scan.py"), "-s", str(HERE / "fixtures" / "services.json"), "-o", str(out)],
                   env=env, check=True, timeout=60)
    data = json.loads(out.read_text())

devices = {d["name"]: d for d in data["devices"]}
services = {s["name"]: s for s in data["services"]}

assert data["title"] == "Test Home" and data["lang"] == "en"
assert data["labels"] == {"zh": {"media": "影音"}}
assert data["tailnet"] == "example.github"
assert data["devices"][0]["self"] and data["devices"][0]["name"] == "mac-mini"
assert devices["iphone"]["online"] is False, "offline peers keep their state"
assert [d["name"] for d in data["devices"]][-1] == "iphone", "offline devices sort last"
assert services["Jellyfin"]["url"] == "http://100.64.0.12:8096/", services["Jellyfin"]
assert services["Secure"]["url"] == "https://nas.example-tailnet.ts.net/x/", "https uses the MagicDNS name"
assert services["mac-mini"]["source"] == "serve" and services["mac-mini"]["url"] == "https://mac-mini.example-tailnet.ts.net/"
assert data["bookmarks"][0] == {**data["bookmarks"][0], "name": "Launch & post", "url": "notes/draft.html", "group": "Notes", "device": "mac-mini"}
assert data["bookmarks"][1]["name"] == "Docs"
print(f"ok: {len(data['devices'])} devices, {len(data['services'])} services")
