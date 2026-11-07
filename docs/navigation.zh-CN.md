# 能力类型与导航配置

首页使用 `services.json` 的 `start` 固定磁贴。全部应用按能力类型或名称显示完整入口列表。

`navigation` 为服务、书签和 Apps 指定能力类型与显示层级。它只控制导航，不停用服务，也不删除入口。

## 类型

| `category` | 类型 |
|---|---|
| `overview` | 总览 |
| `learn` | 学习 |
| `work` | 工作 |
| `assets` | 资产 |
| `create` | 创作 |
| `life` | 生活 |
| `infra` | 系统 |
| `other` | 其他 |

## 字段

`navigation` 的键为 App 的 `id`，或服务、书签的 `name`。App 的 `id` 配置优先于名称配置。

- `category` 指定所属能力类型。未配置时，页面根据条目自身的 `category`、名称和现有分组推断。
- `primary` 默认是 `true`。只有值为 `false` 的条目进入所属类型的“辅助入口”。
- “用途”视图直接显示主要入口，辅助入口可展开。
- “名称”视图直接显示全部入口。
- `start_grouped` 默认是 `false`。值为 `true` 时，首页按能力类型显示固定磁贴，并显示分类标题。设备区收在底部的可展开区域。
- `start` 独立决定首页磁贴。修改列表类型或显示层级不改变首页固定项。

以下示例引用名为 `Docs` 的书签与 `id` 为 `progress` 的 App。对应条目需要已存在。

```json
{
	"start": [{"name": "progress", "size": "w"}],
	"navigation": {
		"progress": {"category": "overview", "primary": true},
		"Docs": {"category": "learn", "primary": false}
	}
}
```

`scan.py` 将 `navigation` 写入 `data.json`。Preview 和正式通道各自使用独立配置，通道约定见[发布通道](channels.zh-CN.md)。

## 书签磁贴摘要

书签可选 `lines`、`badge` 和 `glyph` 字段。中、宽磁贴显示最多三行 `lines`，小磁贴仍显示图标。`badge` 显示短标记。摘要只展示配置提供的内容，不自动判断学习完成或更新课程进度。

真实规划正文留在所属私有项目。服务器配置中的书签 URL 可以指向已有的 Tailnet 页面；开源仓库只提供通用摘要显示能力和虚构测试数据。
