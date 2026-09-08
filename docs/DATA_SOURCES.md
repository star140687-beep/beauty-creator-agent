# Data Sources

本文档定义 Beauty Creator Agent 阶段 0 的数据边界和样例契约。当前只使用人工构造的小规模样例，不包含真实用户数据，也不启动全量数据采集或清洗。

## 1. 数据类型

### Product Knowledge

文件：`data/samples/products.jsonl`

用途：提供产品名称、品类、成分、适用肤质和经确认的产品描述，为后续 Product Research 与事实核验提供输入。

必需字段：

- `id`：样例内唯一标识。
- `brand`：品牌名。
- `product_name`：产品名。
- `category`：标准化品类。
- `description`：产品描述。
- `ingredients`：公开或用户提供的成分列表。
- `skin_types`：目标肤质列表。
- `claims`：可追溯的产品主张；当前仅为人工样例，不视为已核实的官方声明。
- `official_url`：官方来源 URL；未知时为 `null`。
- `source`：当前固定为 `sample`。
- `source_id`：用于后续 Evidence provenance 的唯一来源标识。

未来候选来源：品牌官网、产品包装/说明书、品牌授权资料。接入时必须保存原始 URL、抓取时间和内容版本。

### Consumer Reviews

文件：`data/samples/reviews.jsonl`

用途：支持消费者关注点、优缺点和结构化统计分析。评论观察不能冒充产品官方事实。

必需字段：

- `id`、`brand`、`product_name`、`category`。
- `skin_type`：未知或不适用时允许为 `null`。
- `rating`：1–5 分。
- `review_text`：评论正文。
- `recommended`：是否推荐；允许后续扩展为 `null`。
- `source`、`source_id`：记录来源与唯一标识。

未来候选来源：获得授权或许可的公开数据集、平台导出数据。接入前需确认许可、隐私和平台条款；不得收集姓名、账号、联系方式等不必要的个人信息。

### Content Examples

文件：`data/samples/content_examples.jsonl`

用途：提取平台表达方式、内容结构和语气模式，不用于复制原文或证明产品功效。

必需字段：

- `id`：样例内唯一标识。
- `platform`：`xiaohongshu`、`douyin`、`bilibili` 或 `weibo`。
- `category`、`title`、`body`、`hashtags`。
- `content_pattern`：内容结构标签。
- `tone`：语气标签。
- `source`、`source_id`：记录来源与唯一标识。

未来候选来源：取得适当授权的平台内容数据或自有内容库。只保存完成研究目的所需字段，并遵守版权和平台规则。

## 2. 通用约束

- 文件采用 UTF-8 编码的 JSON Lines；每行必须是一个独立 JSON 对象。
- `id` 和 `source_id` 在各自数据类型中必须唯一且稳定。
- 所有后续 Evidence 必须保留 `source_id`，不得把模型记忆当作外部事实来源。
- `sample` 数据只用于开发和测试，不得当作真实市场证据或发布素材。
- 原始数据、处理后数据和发布数据应分开保存；阶段 0 不创建或提交全量数据。
- 不提交 API Key、登录凭证、个人信息或未经授权的受版权保护全文。

## 3. 阶段 0 数据量

当前共 35 条人工样例：10 条 Product、15 条 Review、10 条 Content。规模足以支持后续 Contract 与 Fake Workflow 开发，同时避免过早处理全量数据。

## 4. 后续接入清单

每个真实数据源在接入前补充以下信息：

| 字段 | 说明 |
| --- | --- |
| 名称与 URL | 数据源标识与入口 |
| 所有者/提供方 | 数据责任方 |
| 许可与用途 | 是否允许下载、存储、处理和展示 |
| 获取方式 | API、导出、授权文件或其他方式 |
| 更新频率 | 一次性、每日、每周等 |
| 数据规模 | 预估记录数和文件大小 |
| 映射规则 | 原始字段到统一 schema 的对应关系 |
| Provenance | source_id、URL、时间戳和版本策略 |
| 隐私与安全 | PII、Secrets、访问控制和保留期限 |
| 质量风险 | 缺失、重复、偏差、语言和噪声 |

## 5. 当前状态

- Product / Review / Content 三类字段已确定。
- 小规模样例文件已建立。
- 尚未下载、导入或清洗任何全量数据。
- Python、Docker、uv 环境需要在进入阶段 1 前补齐或修复。

## 6. 真实数据与发布边界

### Open Beauty Facts 产品数据

仓库中的 `data/openbeautyfacts/products.jsonl` 是通过官方 API 获取的小型真实产品快照。数据库由 Open Beauty Facts contributors 维护，并按 ODbL 1.0 提供。快照保留条码、产品页面、抓取时间、许可证和稳定 `source_id`。

这些记录是众包数据，不等同于品牌官方材料，检索时归类为 `external_search`，可靠度为 `medium`。涉及功效、用法或安全性的内容仍应以品牌官方页面、包装或授权文件核验。

可用以下命令重新生成：

```powershell
uv run python scripts/download_openbeautyfacts.py --per-category 5
```

### Amazon Reviews 2023

McAuley Lab 将 Amazon Reviews 2023 主要提供给研究用途，并明确表示其无权替数据授予许可证。因此仓库不再分发评论正文。开发者在确认自己的用途符合适用条款后，可自行下载数据到被 Git 忽略的 `data/raw/`，再执行：

```powershell
uv run python scripts/normalize_amazon_reviews.py data/raw/All_Beauty.jsonl.gz
```

输出位于 `data/processed/`，不会进入 Git。转换器会去掉 reviewer name、user ID、图片、个人资料和交易元数据，仅保留研究所需的产品匿名标识、评分与文本。

### 国内平台内容

仓库不抓取或再分发小红书、抖音、Bilibili、微博正文。真实平台内容只能通过自有内容库、平台授权导出或许可明确的数据源接入；导入前必须记录版权、用途、保留期限和 provenance。
