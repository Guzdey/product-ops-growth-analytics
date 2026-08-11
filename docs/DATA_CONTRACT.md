# Retailrocket 数据契约

## 1. 目的

本契约定义原始 Retailrocket CSV 的位置、预期结构、数据类型、关联方式和异常处理。`v0.2.0` 的导入程序应在写入分析层前验证本契约；不符合时停止构建并输出差异，不能静默修正原始文件。

## 2. 数据位置与版本

官方来源：<https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset>

本地数据根目录通过 `PRODUCT_OPS_DATA_HOME` 配置，当前环境为：

```text
D:\CodexData\product-ops-growth-analytics
```

Full mode 的唯一正式输入是 `raw/extracted` 下表列出的四个官方完整 CSV。`outputs/retailrocket_sample/`、`tools/build_retailrocket_sample.py`、`tools/build_retailrocket_workbook.mjs` 和桌面小样例不属于本数据契约的正式输入，只能用于教学和字段理解；不得将其行数、分布或结果用于正式指标、看板和结论，也不得为了建设正式管道而删除这些现有资产。

当前已确认文件：

| `source_id` | 相对路径 | 当前大小 | 预期数据行数（不含表头） |
|---|---|---:|---:|
| `events` | `raw/extracted/events.csv` | 94,237,913 bytes | 2,756,101 |
| `item_properties_part1` | `raw/extracted/item_properties_part1.csv` | 484,315,749 bytes | 两文件合计 20,275,902 |
| `item_properties_part2` | `raw/extracted/item_properties_part2.csv` | 408,929,907 bytes | 两文件合计 20,275,902 |
| `category_tree` | `raw/extracted/category_tree.csv` | 14,454 bytes | 1,669 |

压缩包 `raw/retailrocket-ecommerce-dataset.zip` 当前为 304,719,974 bytes。文件大小是当前本地基线，不替代 Goal 2 对 SHA-256、行数和字段的正式验证。

## 3. CSV 结构

### 3.1 `events.csv`

原始列顺序必须为：

```text
timestamp,visitorid,event,itemid,transactionid
```

| 列 | DuckDB 原始类型 | 可空 | 规则 |
|---|---|---|---|
| `timestamp` | `BIGINT` | 否 | Unix epoch 毫秒；派生 `event_time_utc` |
| `visitorid` | `BIGINT` | 否 | 匿名访客标识，不代表账号或自然人 |
| `event` | `VARCHAR` | 否 | 已知值：`view`、`addtocart`、`transaction`；未知值保留并标记 |
| `itemid` | `BIGINT` | 否 | 匿名商品标识 |
| `transactionid` | `BIGINT` | 是 | 通常仅交易事件有值；空值不得转换为 0 |

质量规则：

- 不静默删除重复行；增加 `is_exact_duplicate` 和源文件行号/稳定行标识。
- `event='transaction'` 且交易 ID 为空、或非交易事件带交易 ID，均进入质量报告。
- 同一交易可能包含多条商品事件；订单数必须按唯一 `transactionid` 计算。

### 3.2 `item_properties_part1.csv` 与 `item_properties_part2.csv`

原始列顺序必须为：

```text
timestamp,itemid,property,value
```

| 列 | DuckDB 原始类型 | 可空 | 规则 |
|---|---|---|---|
| `timestamp` | `BIGINT` | 否 | Unix epoch 毫秒；表示属性快照/变化时间 |
| `itemid` | `BIGINT` | 否 | 与事件 `itemid` 关联 |
| `property` | `VARCHAR` | 否 | `categoryid`、`available` 可解释；数字/匿名属性按字符串保存 |
| `value` | `VARCHAR` | 是 | 保留原始文本，不做未经依据的语义解码 |

质量规则：

- 两份文件必须完整合并，记录 `source_file`，不得只导入明确含义的属性。
- 同一商品、属性、时间戳多值时保留原始记录并报告冲突。
- 属性历史整理为 `[valid_from, valid_to)`；事件只能关联事件时间之前最近有效值。
- `categoryid` 的值在语义层安全转换为整数；转换失败时保留原值并标记。
- `available` 的解释范围只能依据数据说明和观察值验证，不外推库存数量。

### 3.3 `category_tree.csv`

原始列顺序必须为：

```text
categoryid,parentid
```

| 列 | DuckDB 原始类型 | 可空 | 规则 |
|---|---|---|---|
| `categoryid` | `BIGINT` | 否 | 分类节点标识，应唯一 |
| `parentid` | `BIGINT` | 是 | 空值表示根节点 |

质量规则：

- 检查重复 `categoryid`、自引用、环、缺失父节点和不可达节点。
- 分类树只能提供匿名层级，不能把 ID 猜测为真实行业或类目名称。

## 4. 分层输出契约

### `meta`

- `meta.source_file_manifest`：`source_id`、绝对/相对路径、bytes、SHA-256、mtime、预期/实际行数、导入时间、代码提交号。
- `meta.pipeline_run`：运行 ID、命令、开始/结束时间、状态、输入 Hash、代码提交号和错误摘要。

### `raw`

- `raw.events`
- `raw.item_properties`
- `raw.category_tree`

`raw` 保留原始字段值并增加血缘字段，不覆盖源 CSV。

### `stg`

- `stg.events`：显式类型、`event_time_utc`、质量标记。
- `stg.item_properties`：合并来源、属性时间、合法转换列。
- `stg.category_tree`：分类键和结构质量标记。

### `core`

- `core.fct_event`：一行一个原始事件，稳定 `event_id`。
- `core.fct_session`：一行一个访客会话。
- `core.fct_transaction`：一行一个唯一交易。
- `core.item_property_history`：商品属性有效时间区间。
- `core.dim_category`：分类父子、深度、根和匿名路径。

### `mart`

`mart` 表由 `docs/METRIC_DICTIONARY.md` 驱动，至少包括活跃、会话、漏斗、留存、交易/复购、生命周期、品类机会和数据质量。每张 Mart 必须明确粒度、日期范围和 `data_origin`。

## 5. 关联与时间规则

- 事件 ↔ 商品：`itemid`。
- 商品 ↔ 分类：事件时点有效的 `property='categoryid'` 值转换后关联 `category_tree.categoryid`。
- 交易：`transactionid` 是订单代理键，`visitorid` 和时间用于质量检查而不是替代键。
- 会话：按 `visitorid, timestamp, stable_event_id` 排序；相邻事件间隔 `> 30 minutes` 才新建会话。
- 相同毫秒事件使用稳定源顺序打破排序平局；不得根据事件类型人为重排制造漏斗。
- 所有分析时间为 UTC；如果展示其他时区，必须保留 UTC 并在图表中声明转换。

## 6. 缺失、异常和删除策略

- 原始层不静默删除；清洗层通过质量标记决定是否进入具体指标。
- 关联不到属性或分类不是自动错误，必须报告覆盖率并允许“unknown”。
- 观察窗口末端尚不可观察的留存不记为 0，应从对应分母排除。
- 未知事件不进入已知行为漏斗，但保留在事件总量和质量报告。
- 所有排除逻辑必须在 SQL、指标字典和质量报告中留痕。

## 7. 版本与兼容性

- 数据契约变化必须更新本文件、测试和 CHANGELOG。
- 破坏字段、粒度或指标含义的变更必须提升相应模型/项目版本并提供迁移说明。
- 构建应幂等：相同输入 Hash、配置和代码版本产生相同核心表与指标快照。

## 8. 发布边界

- 原始 ZIP、完整 CSV、DuckDB 和完整 Parquet 不进入 Git/GitHub。
- CI 使用人工构造、无真实访客明细的小型 Fixture。
- 在线演示仅发布不含 `visitorid` 明细的小型聚合结果。
- 数据及受其许可约束的衍生资产遵循 `docs/DATA_LICENSE.md`；原创代码遵循 MIT License。
