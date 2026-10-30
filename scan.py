#!/usr/bin/env python3
"""Generate data.json for the Tailnet homepage.

Sources (merged, de-duplicated by URL):
  1. tailscale status --json        -> device list + online state
  2. tailscale serve status --json  -> services exposed by this machine
  3. services.json                  -> hand-maintained services (see services.example.json)
  4. --probe                        -> scan common ports on online peers
  5. "live" on a service           -> fetch a JSON URL and show a few values on the tile
  6. notes/*.html next to the output -> private pages, listed as bookmarks in a "Notes" group

Usage:
  python3 scan.py            # devices + serve + services.json
  python3 scan.py --probe    # also probe common web ports on online peers
"""
import argparse
import concurrent.futures as cf
import html
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import sys
import urllib.request
from urllib.parse import urlsplit
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAC_APP_CLI = "/Applications/Tailscale.app/Contents/MacOS/Tailscale"
KNOWN_PORTS = {3000: "Grafana / Gitea", 8096: "Jellyfin", 8123: "Home Assistant", 9000: "Portainer / MinIO",
               9090: "Prometheus / Cockpit", 11434: "Ollama"}
# 应用版 CLI 在 launchd 等无终端环境下会尝试启动 GUI，强制走命令行模式
CLI_ENV = {**os.environ, "TAILSCALE_BE_CLI": "1"}
PROBE_PORTS = [80, 443, 3000, 3001, 5000, 5173, 8000, 8080, 8081, 8096, 8123, 8443, 8888, 9000, 9090, 11434]


def find_cli():
    candidates = [os.environ.get("TAILSCALE_BIN"), MAC_APP_CLI, shutil.which("tailscale")]
    for c in candidates:
        if not c or not os.path.exists(c):
            continue
        r = subprocess.run([c, "version"], capture_output=True, text=True, env=CLI_ENV)
        if r.returncode == 0:
            return c
    sys.exit("tailscale CLI not found; set TAILSCALE_BIN to its path")


def ts_json(cli, *args):
    r = subprocess.run([cli, *args, "--json"], capture_output=True, text=True, env=CLI_ENV)
    if r.returncode != 0 or not r.stdout.strip():
        return {}
    return json.loads(r.stdout)


def short_name(dns_name):
    return dns_name.rstrip(".").split(".")[0]


def to_device(node, is_self=False):
    dns = node.get("DNSName", "").rstrip(".")
    return {
        "name": short_name(dns) if dns else node.get("HostName"),
        "hostname": node.get("HostName"),
        "dns": dns,
        "ip": (node.get("TailscaleIPs") or [""])[0],
        "os": node.get("OS", ""),
        "online": bool(node.get("Online")) or is_self,
        "self": is_self,
        "lastSeen": node.get("LastSeen"),
    }


def serve_services(serve, self_dev):
    out = []
    for hostport, cfg in (serve.get("Web") or {}).items():
        host, _, port = hostport.rpartition(":")
        base = f"https://{host}" + ("" if port == "443" else f":{port}")
        for path, h in (cfg.get("Handlers") or {}).items():
            target = h.get("Proxy") or h.get("Path") or h.get("Text") or ""
            out.append({
                "name": path if path != "/" else host.split(".")[0],
                "device": self_dev["name"],
                "url": base + path,
                "note": f"serve → {target}",
                "source": "serve",
                "_target": h.get("Proxy"),
            })
    return out


def host_for(dev, scheme):
    """统一用 Tailscale IP 访问；https 例外——serve 的证书和路由都绑在 MagicDNS 域名上，IP 打不开"""
    if scheme == "https":
        return dev["dns"] or dev["ip"]
    return dev["ip"] or dev["dns"]


def manual_url(s, devices):
    """services.json 里只写 device + port/path 时拼出地址（与页面逻辑一致）"""
    dev = next((d for d in devices if d["name"] == s.get("device")), None)
    port = s.get("port")
    scheme = s.get("scheme") or ("https" if port == 443 else "http")
    host = host_for(dev, scheme) if dev else s.get("device", "")
    suffix = f":{port}" if port and port not in (80, 443) else ""
    return f"{scheme}://{host}{suffix}{s.get('path', '/')}"


def opener():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    # tailnet 内部请求直连，不走 macOS 系统代理（urllib 默认会读取）
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=ctx))


def reachable(url, ips):
    """服务返回任何 HTTP 响应（含 4xx/5xx）即算可达。

    不走 DNS：本机若有 Clash 之类的 fake-ip，*.ts.net 会被解析成 198.18.x。
    直接连设备的 Tailscale IP，https 用域名做 SNI（tailscale serve 按 SNI 分发）。
    """
    u = urlsplit(url)
    https = u.scheme == "https"
    port = u.port or (443 if https else 80)
    try:
        sock = socket.create_connection((ips.get(u.hostname, u.hostname), port), timeout=4)
        with sock:
            if https:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                sock = ctx.wrap_socket(sock, server_hostname=u.hostname)
            sock.settimeout(4)
            sock.sendall(f"HEAD {u.path or '/'} HTTP/1.1\r\nHost: {u.netloc}\r\nConnection: close\r\n\r\n".encode())
            return sock.recv(5) == b"HTTP/"
    except OSError:
        return False


def fetch_title(url):
    try:
        with opener().open(url, timeout=2) as r:
            body = r.read(65536).decode("utf-8", "ignore")
    except Exception:
        return None
    m = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
    return html.unescape(m.group(1)).strip() if m else None


def dig(data, path):
    """按 a.b.0.c 取 JSON 里的值。"""
    for key in path.split(".") if path else []:
        data = data[int(key)] if isinstance(data, list) else data[key]
    return data


def live(spec):
    """动态磁贴的数据：请求 spec["url"] 的 JSON，按 show 里的模板生成几行文字。

    模板写法 "{batteryLevel}% · {idealRange:.0f} km"：花括号里是 JSON 路径，冒号后是 Python 格式。
    url 和 headers 里的 $VAR 从环境变量展开，令牌不必写进 services.json。
    """
    headers = {"Accept": "application/json", **{k: os.path.expandvars(v) for k, v in spec.get("headers", {}).items()}}
    req = urllib.request.Request(os.path.expandvars(spec["url"]), headers=headers)
    with opener().open(req, timeout=5) as r:
        data = dig(json.load(r), spec.get("root", ""))

    def fill(m):
        v = dig(data, m.group(1))
        return format(v, m.group(2)) if m.group(2) else str(v)
    return [re.sub(r"\{([^{}:]+)(?::([^{}]*))?\}", fill, line) for line in spec.get("show", [])]


def probe(dev, port):
    try:
        with socket.create_connection((dev["ip"], port), timeout=0.8):
            pass
    except OSError:
        return None
    scheme = "https" if port in (443, 8443) else "http"
    url = f"{scheme}://{host_for(dev, scheme)}" + ("" if port in (80, 443) else f":{port}") + "/"
    title = fetch_title(url)
    if not title and dev["os"] == "macOS" and port == 5000:
        return None  # macOS AirPlay 接收器，不是 Web 服务
    return {
        "name": title or KNOWN_PORTS.get(port) or f"{dev['name']}:{port}",
        "device": dev["name"],
        "url": url,
        "note": f"port {port}",
        "source": "probe",
    }


def notes(out_dir, group="Notes", device=None):
    """Private pages dropped into <out dir>/notes/, newest first. nginx serves them at /notes/."""
    files = sorted((out_dir / "notes").glob("*.html"), key=lambda f: f.stat().st_mtime, reverse=True)
    marks = []
    for f in files:
        m = re.search(r"<title>(.*?)</title>", f.read_text(errors="replace"), re.S | re.I)
        when = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        marks.append({"name": html.unescape(m.group(1).strip()) if m else f.stem,
                      "url": f"notes/{f.name}", "group": group, "note": when, "kind": "note", "device": device})
    return marks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true", help="probe common web ports on online devices")
    ap.add_argument("-o", "--out", default=str(ROOT / "public" / "data.json"))
    ap.add_argument("-s", "--services", default=str(ROOT / "services.json"), help="hand-written services file")
    args = ap.parse_args()

    cli = find_cli()
    status = ts_json(cli, "status")
    if not status:
        sys.exit("`tailscale status` failed. Is Tailscale running?")

    self_dev = to_device(status["Self"], is_self=True)
    devices = [self_dev] + sorted(
        (to_device(p) for p in (status.get("Peer") or {}).values()),
        key=lambda d: (not d["online"], d["name"].lower()),
    )

    services_file = Path(args.services)
    manual = json.loads(services_file.read_text()) if services_file.exists() else {}
    services = [dict(s, source="manual") for s in manual.get("services", [])]

    discovered = serve_services(ts_json(cli, "serve", "status"), self_dev)
    for s in discovered:
        target = s.pop("_target")
        if target:
            s["name"] = fetch_title(target) or s["name"]

    if args.probe:
        # 本机 443 归 tailscale serve 管，已从 serve 配置读取，不再重复探测
        jobs = [(d, p) for d in devices if d["online"] and d["ip"] for p in PROBE_PORTS
                if not (d["self"] and p == 443)]
        with cf.ThreadPoolExecutor(max_workers=64) as ex:
            discovered += [r for r in ex.map(lambda a: probe(*a), jobs) if r]

    for s in services:
        s.setdefault("url", manual_url(s, devices))

    # 同一服务可能经多个入口被发现（如 serve 的 https 根路径和 nginx 的 80 端口），
    # 按 URL 及「设备 + 页面标题」去重，手动项和 serve 项优先
    seen = {s["url"].rstrip("/") for s in services} | {u.rstrip("/") for u in manual.get("hide", [])}
    named = {(s.get("device"), s["name"]) for s in services}
    for s in discovered:
        url, key = s["url"].rstrip("/"), (s["device"], s["name"])
        if url not in seen and key not in named:
            seen.add(url)
            named.add(key)
            services.append(s)

    # 可达性在扫描端检查：浏览器受本地网络权限、混合内容、DNS 等限制，探测结果不可信。
    # 离线设备上的服务不检查，页面直接显示「离线」
    online = {d["name"] for d in devices if d["online"]}
    ips = {d["dns"]: d["ip"] for d in devices if d["dns"] and d["ip"]}
    check = [s for s in services if s.get("device") in online]
    with cf.ThreadPoolExecutor(max_workers=32) as ex:
        for s, ok in zip(check, ex.map(lambda s: reachable(s["url"], ips), check)):
            s["up"] = ok

    # 动态磁贴：失败只跳过这一块，不影响整次扫描
    for s in services:
        spec = s.pop("live", None)
        if spec:
            try:
                s["live"] = live(spec)
            except Exception as e:
                print(f"live data for {s['name']} failed: {e}", file=sys.stderr)

    data = {
        "title": manual.get("title", "Tailnet Home"),
        "lang": manual.get("lang", ""),   # 空则由浏览器语言决定
        "tailnet": (status.get("CurrentTailnet") or {}).get("Name", ""),
        "suffix": status.get("MagicDNSSuffix", ""),
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "devices": devices,
        "services": services,
        "bookmarks": notes(Path(args.out).resolve().parent, manual.get("notes_group") or "Notes", self_dev["name"]) + manual.get("bookmarks", []),
        "labels": manual.get("labels", {}),   # 分组名的其他语言显示名
    }
    Path(args.out).write_text(json.dumps(data, ensure_ascii=False, indent=2))
    online = sum(d["online"] for d in devices)
    print(f"wrote {args.out}: {len(devices)} devices ({online} online), {len(services)} services")


if __name__ == "__main__":
    main()
