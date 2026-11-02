# 发布通道：正式与测试

[English](channels.md) · **简体中文**

同一台服务器上并排运行两份 Tailnet Home。界面改动和新应用先在测试通道里看过，确认没问题再进入正式通道。

| | 正式（stable） | 测试（preview） |
|---|---|---|
| 代码来源 | `main` 分支 | `preview` 分支 |
| 部署目录 | `~/src/self-hosted/tailscale-home` | `~/src/self-hosted/tailscale-home-preview` |
| 本机端口 | `127.0.0.1:4183` | `127.0.0.1:4185` |
| tailnet 地址 | `https://<服务器>.<tailnet>.ts.net/` | `https://<服务器>.<tailnet>.ts.net:8444/` |
| 数据 | 自己的 `var/`：`services.json`、`apps/`、`notes/`、`data.json` | 独立的一份 `var/`，与正式通道互不影响 |
| 扫描任务 | `local.tailscale-home.scan` | `local.tailscale-home-preview.scan` |
| 日志 | `~/Library/Logs/local.tailscale-home.scan.log` | `~/Library/Logs/local.tailscale-home-preview.scan.log` |
| 界面 | 正常 | 状态栏有橙色「测试版」标记，标签页标题带 `[测试版]` |
| 诊断页 | 地址加 `?debug=1` 才在设置里出现 | 设置里一直有 |

## 发布流程

### 界面和代码

1. 在 `preview` 分支上提交，push 到 Gitea：自动部署到测试通道。
2. 在手机上打开 `:8444` 地址查看；有问题就看设置里的「诊断」页。
3. 确认后把 `preview` 合并进 `main` 并 push：自动部署到正式通道。

回滚方法与以前相同：在对应部署目录的 `.env` 里把 `IMAGE_TAG` 改成旧的 commit 前缀，再执行 `docker compose up -d --no-build`。两个通道的 `.env` 各自独立。

### 应用和数据

应用的生产者也走同样的两步：先推到测试通道的 `var/apps/`，看过磁贴和页面后再推到正式通道。

```bash
# 1. 测试
rsync -a --delete ./build/my-app/ homesrv:~/src/self-hosted/tailscale-home-preview/var/apps/my-app/
# 2. 正式
rsync -a --delete ./build/my-app/ homesrv:~/src/self-hosted/tailscale-home/var/apps/my-app/
```

测试通道的 `services.json` 可以从正式通道复制一份再改，用来试新的 `start`、`live` 配置。

## 诊断页

`scan.py` 每次扫描都会在 `data.json` 里写入 `channel` 和 `diagnostics`。诊断页显示以下内容：

- **通道和版本**：部署目录当前的 commit，用来确认新代码已经上线。
- **最近扫描**：时间、耗时，是否开启了端口探测。
- **问题**：被跳过的应用（id 不匹配、`api` 版本不对、路径越界）、读不了的 `tile.json`、取数失败的 `live` 磁贴，以及具体原因。`live` 的 url 和 headers 里用 `$VAR` 引用的值（通常是令牌）会被替换回 `$VAR`，不会出现在页面上。
- **应用**：每个应用的 id、版本、更新时间、是否过期，以及由谁推送。
- **原始 `data.json`** 的链接。

诊断内容与主页本身一样只在 tailnet 内可见。正式通道默认不显示诊断页，避免平时看到无关的细节。

## 一次性设置（服务器上）

```bash
# 把测试通道挂到 tailnet 的 8444 端口（正式通道仍是 443 的 /）
tailscale serve --bg --https=8444 http://127.0.0.1:4185
```

第一次 push `preview` 分支时，部署流程会自动创建测试通道的部署目录、扫描任务和容器。

不使用 CI 的 Linux 部署可以照搬：再 clone 一份到另一个目录，在 `.env` 里设 `HOME_PORT=4185` 和 `COMPOSE_PROJECT_NAME=tailscale-home-preview`，扫描命令加上 `--channel preview`。

## 只想要一个通道

什么都不用做：不建 `preview` 分支，就只有正式通道，界面和以前一样。
