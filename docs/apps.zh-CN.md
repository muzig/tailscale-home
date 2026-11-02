# Tailnet Home 应用扩展规范（草案 v1）

[English](apps.md) · **简体中文**

> 状态：**v1，已实现**（`scan.py`、`public/index.html`、`deploy/nginx.conf`）。示例应用见 `examples/apps/progress/`。

## 1. 目标

Tailnet Home 现在能显示三类东西：tailnet 设备、服务（自动发现或手写）和 `notes/` 私人页面。另外，`live` 能把一个 JSON 接口里的几个值显示在磁贴背面。

我们想要的是：**像给安卓手机装 APK 一样，往主页里装一个「应用」**，让它在开始屏幕占一块动态磁贴，点开后在设备屏幕里打开自己的页面。区别是，这里的应用全部基于 Web 技术：一个目录里放静态文件，不需要构建，也不在服务器上执行。

第一个参考应用是 **Jarvis 进展**：个人助手把当前主线、等你决定的事和最近完成的工作导出成一个应用，放到主页上，手机一眼就能看到。

### 设计原则

- **装应用就是拷一个目录**，卸载就是删掉这个目录。不需要应用商店、不需要签名、不需要构建。
- **主页不执行应用代码。** `scan.py` 只读取 JSON，nginx 只提供静态文件，应用的 JS 只在浏览器沙箱里运行。
- **数据由应用的「生产者」推送进来。** 生产者是 tailnet 里任意一个能写文件的程序（脚本、CI、定时任务），主页本身不主动拉取私人数据。
- **默认私有。** 应用放在 git 忽略的 `var/` 里，只在 tailnet 内可访问，绝不进入仓库和 demo。
- **与现有功能兼容。** `notes/` 和 `live` 原样保留，可以把它们看成应用的简化形式。

### 不在 v1 范围内

应用商店或索引、签名与校验、服务器端运行时、后台任务、应用间通信、tailnet API 权限、应用设置页。

## 2. 概念对照

| 安卓 | Tailnet Home | 说明 |
|---|---|---|
| APK | 应用目录 `var/apps/<id>/` | 一个目录就是一个应用 |
| `AndroidManifest.xml` | `manifest.json` | 名称、版本、磁贴和入口 |
| Activity | `index.html` | 点开磁贴后在设备屏幕里打开 |
| App Widget | `tile.json` | 开始屏幕上的动态磁贴数据 |
| 安装 / 卸载 | 拷入 / 删除目录 | 下一次扫描（默认 ≤10 分钟）生效 |
| 后台服务推送 | 生产者 | 在外部生成并覆盖 `tile.json` 和页面 |
| 应用沙箱 | iframe `sandbox` + CSP | 应用读不到主页的存储和状态 |

## 3. 应用包结构

```
var/apps/<id>/
  manifest.json   # 必需
  tile.json       # 可选：动态磁贴数据，由生产者更新
  index.html      # 可选：应用页面（入口可在 manifest 里改）
  icon.svg        # 可选：图标
  ...             # 页面需要的其他静态文件（css、js、图片、json）
```

- `<id>`：小写字母、数字和短横线，2–40 个字符，必须与 `manifest.id` 一致；不一致则跳过这个应用。
- 所有路径都相对应用目录，不允许 `..`，也不允许指向目录外的绝对路径。
- 应用页面只能使用相对路径引用自己的资源，因为部署时它挂在 `/apps/<id>/` 下。

## 4. `manifest.json`

```json
{
  "api": 1,
  "id": "jarvis-progress",
  "name": "Jarvis",
  "name_i18n": { "zh": "Jarvis 进展" },
  "version": "0.1.0",
  "description": "个人助手的当前主线、待决定事项和最近完成的工作",
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

| 字段 | 必需 | 说明 |
|---|---|---|
| `api` | 是 | 规范主版本，现在是 `1`。`scan.py` 跳过不认识的主版本并打印警告 |
| `id` | 是 | 与目录名一致 |
| `name` | 是 | 磁贴和 A–Z 列表里显示的名字 |
| `name_i18n` | 否 | 按界面语言覆盖名字，例如 `{"zh": "…"}` |
| `version` | 是 | 应用自身的 SemVer 版本，显示在详情里，便于确认更新是否已到位 |
| `description` | 否 | 一句话说明 |
| `entry` | 否 | 应用页面，默认 `index.html`；没有页面时写 `null`，此时磁贴点击无反应 |
| `icon` / `glyph` | 否 | 自带图标，或使用主页内置的图标名（与 `services.json` 的 `glyph` 相同）；都不写时显示首字母 |
| `tile.size` | 否 | `s`、`m` 或 `w`，默认 `m`；`start` 里写的大小优先 |
| `tile.data` | 否 | 磁贴数据文件，默认 `tile.json` |
| `tile.stale_after` | 否 | 秒数。`tile.json` 的 `updated` 超过这个时长就标成「过期」，默认不检查 |
| `embed` | 否 | 能否在设备屏幕里打开，默认 `true`；`false` 时显示启动页和「在新标签页打开」 |
| `producer` | 否 | 谁在更新这个应用，只用于显示，方便排查数据为什么不动 |

未知字段一律忽略，以便以后加字段不破坏旧主页。

## 5. `tile.json`（动态磁贴）

```json
{
  "updated": "2026-11-02T09:30:00+08:00",
  "lines": ["花园 · 停在选土", "待你决定 3 件", "今天完成 2 条"],
  "badge": 3,
  "status": "ok"
}
```

| 字段 | 说明 |
|---|---|
| `updated` | ISO 8601 时间，带时区。用来判断是否过期，也显示在应用详情里 |
| `lines` | 1–4 行文字，与现有 `live` 的显示方式相同：第一行大字，其余小字。每行超长部分省略 |
| `badge` | 可选，非负整数，显示在磁贴角落；`0` 或缺省时不显示 |
| `status` | 可选：`ok`、`warn` 或 `error`。`warn`/`error` 用醒目的颜色提示；过期由主页根据 `stale_after` 判断，不由应用自报 |

生产者应该**原子地**写入 `tile.json`：先写临时文件，再 `mv`（rsync 默认就这样做），避免扫描时读到写了一半的文件。

## 6. 主页如何加载应用

### 6.1 `scan.py`

1. 遍历 `data.json` 旁边的 `apps/*/manifest.json`（Docker 部署里就是 `var/apps/`）。
2. 校验 `api`、`id` 和路径；不合格的应用打印原因后跳过，不影响整次扫描（与 `live` 的失败处理一致）。
3. 读取 `tile.data`，计算是否过期。
4. 写入 `data.json` 新增的 `apps` 数组：

```json
"apps": [{
  "id": "jarvis-progress", "name": "Jarvis", "name_i18n": {"zh": "Jarvis 进展"},
  "version": "0.1.0", "url": "apps/jarvis-progress/index.html", "icon": "apps/jarvis-progress/icon.svg",
  "glyph": "spark", "size": "w", "embed": true, "producer": "Jarvis on my-laptop",
  "live": ["花园 · 停在选土", "待你决定 3 件", "今天完成 2 条"],
  "badge": 3, "status": "ok", "updated": "2026-11-02T09:30:00+08:00", "stale": false
}]
```

`scan.py` 只读 JSON，不执行应用里的任何东西，也不访问应用页面。

### 6.2 `index.html`

- 应用和服务、书签一样进入开始屏幕和 A–Z 列表；`services.json` 的 `start` 可以用应用的 `name` 或 `id` 来固定，例如 `{"name": "jarvis-progress", "size": "w"}`。
- 磁贴背面复用现有的 `live` 样式；`stale: true` 时整块磁贴变暗，并在背面加一行「N 小时前更新」。
- 点开后在 Phone / Dual screen 的设备屏幕里打开（`embed: false` 时显示启动页）。
- 用 `<iframe sandbox="allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox">` 打开应用页面，**不给** `allow-same-origin`。

### 6.3 nginx

```nginx
# 应用：./var/apps/<id>/，只提供静态文件
location /apps/ {
    alias /data/apps/;
    add_header Cache-Control "no-cache";
    # 直接打开也处于沙箱中：没有主页的同源权限
    add_header Content-Security-Policy "sandbox allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox";
    add_header X-Content-Type-Options "nosniff";
}
```

## 7. 安全与隐私模型

- **信任边界是「谁能写 `var/`」。** 能写 `var/apps/` 的人本来就能控制这台服务器，所以 v1 不做签名，但仍然把应用和主页隔离，避免一个写错的应用影响主页。
- **沙箱隔离。** 应用页面处于不透明来源（opaque origin），读不到主页的 `localStorage`（语言、显示模式、点击排序）、cookie，也不能修改主页 DOM。沙箱页面里 `localStorage` 不可用，需要状态的应用请把状态放在 URL hash 里，或由生产者写进 JSON。
- **只在 tailnet 内。** 与 `notes/` 相同，经 `tailscale serve` 暴露，不开公网端口。
- **不入库。** `var/` 已被 git 忽略；示例应用只能使用假数据，放在 `examples/apps/`。
- **生产者自己决定公开到什么粒度。** 规范建议：磁贴只显示摘要，敏感明细不写进应用，因为同一 tailnet 里的其他设备和共享用户也能打开主页。

## 8. 生产者约定

生产者不受限制：可以是 shell 脚本、Python、CI 任务，也可以在另一台机器上运行。推荐的发布方式：

```bash
# 在生产者机器上生成到本地目录，再整目录同步到主页服务器
rsync -a --delete ./build/jarvis-progress/ homesrv:~/src/self-hosted/tailscale-home/var/apps/jarvis-progress/
```

- `--delete` 让应用目录保持与生产者一致，删掉旧文件。
- 卸载：`ssh homesrv rm -rf ~/src/self-hosted/tailscale-home/var/apps/jarvis-progress`。
- 有测试通道时，先推到测试通道的 `var/apps/`，看过再推正式通道，见 [channels.zh-CN.md](channels.zh-CN.md)。应用被跳过或磁贴数据读不了时，原因显示在设置里的「诊断」页。
- 新安装或更新最迟在下一次扫描（LaunchAgent / systemd timer，默认 10 分钟）后出现。想立即生效，可以在同步后手动运行一次 `scan.py`。

## 9. 与现有功能的关系

| 现有功能 | 关系 |
|---|---|
| `notes/*.html` | 等同于「只有页面、没有 manifest 和磁贴」的应用，保留不变 |
| `services.json` 的 `live` | 拉取模式：主页去请求一个已有服务的接口。应用是推送模式：数据由生产者送来。两者并存 |
| `start` / `accent` | 应用参与固定和配色，规则与服务相同 |

## 10. 参考应用：Jarvis 进展

| 部分 | 内容 |
|---|---|
| 生产者 | Jarvis 仓库里的导出脚本，读 `memory/state.md`、各 effort README 和当天 calendar |
| 触发 | Jarvis 每次收工时导出并 rsync 到主页服务器 |
| 磁贴（`w`） | 当前主线与停在哪一步、等你决定的件数（`badge`）、今天完成的条数 |
| 页面 | 当前主线、等你决定的事（每件附推荐）、最近完成、各 effort 的状态 |
| 隐私 | 只显示进度级摘要（第几项、已具备／需补齐／待确认、当前步骤），不写金额、号码或证件细节 |
| 过期 | `stale_after` 设为 1 天，超过 1 天没更新就变暗，提醒 Jarvis 很久没收工 |

仓库里另放一份用假数据的 `examples/apps/progress/`，供 demo 和测试使用。

## 11. 实现计划与验收

| 步骤 | 内容 | 验收 |
|---|---|---|
| 1 | `scan.py` 读取 `apps/`，写出 `data.json.apps` | `tests/smoke.py` 覆盖：正常、id 不匹配、`api: 2`、tile.json 损坏、已过期 |
| 2 | nginx `/apps/` + CSP sandbox | 直接打开应用页面时 `document.domain` 访问或读主页 `localStorage` 失败 |
| 3 | `index.html` 渲染应用磁贴、`start` 固定、iframe 打开 | 手机宽度和 Dual screen 下都能打开；过期磁贴变暗 |
| 4 | `examples/apps/progress/` 和 demo 数据 | 在线 demo 能看到示例应用 |
| 5 | README、CHANGELOG、`services.example.json` 说明 | 中英文 README 都有「应用」一节 |
| 6 | Jarvis 进展作为第一个真实应用部署到 homesrv | 手机上看到磁贴并能打开；页面内容只有摘要级信息 |

## 12. 已定事项

1. **名称**：Apps / 应用，与 Windows Phone 的叫法一致。
2. **磁贴数据的读取时机**：由 `scan.py` 读入 `data.json`，最多延迟一个扫描周期；浏览器不直接请求 `tile.json`。
3. **`actions`**（长按磁贴出现的快捷链接）：留到 v2。
