# DuckDB 数据仓库使用说明

## 1. 这一部分解决什么问题

Retailrocket 的四个 CSV 只是文件，彼此不会自动建立关系。第二部分把它们导入一个 DuckDB 数据库，并用 SQL 建立稳定的数据层：事件通过 `itemid` 关联商品属性，商品在事件发生时关联当时有效的分类和可用状态，交易通过唯一 `transactionid` 聚合，会话通过访客相邻事件时间计算。

这一步不直接下“留存高低”或“漏斗好坏”的业务结论。它的目标是保证第三部分计算运营指标时，分母、去重、时间和关联口径都是可信的。

## 2. 技术如何联动

```text
官方 CSV
   ↓ Python 检查文件名、表头、大小、SHA-256
DuckDB raw（SQL 显式类型，全量保留）
   ↓ SQL 转换与质量标记
DuckDB stg（UTC 时间、异常标记）
   ↓ SQL 建模
DuckDB core（事件、会话、交易、属性历史、分类树）
   ↓ 第三部分 SQL 指标
DuckDB mart → Python 导出 → Streamlit 看板
```

- DuckDB 是数据库和 SQL 执行引擎，数据库文件位于 D 盘。
- SQL 是数据结构和转换口径的唯一事实来源，适合人工审查和面试讲解。
- Python 负责按固定顺序执行 SQL、记录运行、验证结果和导出报告。
- Git 只管理 Python、SQL、测试和文档；完整 CSV、DuckDB 与临时文件不上传。

## 3. 五层数据含义

| 层 | 主要表 | 用途 |
|---|---|---|
| `meta` | `source_file_manifest`、`pipeline_run`、`model_build_step`、`quality_check` | 回答数据从哪来、何时运行、执行到哪一步、是否通过 |
| `raw` | `events`、`item_properties`、`category_tree` | 不静默删除的原始记录 |
| `stg` | 同名三表 | 统一类型、UTC 时间和质量标记 |
| `core` | `fct_event`、`fct_session`、`fct_transaction`、属性历史、`dim_category` | 可复用业务实体 |
| `mart` | 第三部分实现 | 为运营报表准备的聚合指标 |

## 4. 常用命令

在仓库根目录执行：

```powershell
$python = 'D:\CodexData\product-ops-growth-analytics\envs\product-ops-growth-analytics\Scripts\python.exe'

& $python -m product_ops.cli ingest --config config\project.example.toml
& $python -m product_ops.cli build --config config\project.example.toml
& $python -m product_ops.cli validate --config config\project.example.toml --json
```

一次完成三步：

```powershell
& $python -m product_ops.cli run-all --config config\project.example.toml --json
```

`build` 会为 13 个建模语句分别记录输入与 SQL 签名。相同输入、相同 SQL 且目标表仍存在时，
再次执行会跳过已成功步骤；如果上次进程意外终止，新运行会把遗留状态标记为
`abandoned`，并从第一个未完成或已变化的步骤继续。

正式数据库默认写入：

```text
D:\CodexData\product-ops-growth-analytics\warehouse\product_ops.duckdb
```

质量报告默认写入：

```text
D:\CodexData\product-ops-growth-analytics\exports\v0.2.0\quality_report.json
```

## 5. 必须会解释的四个口径

1. 相邻事件间隔严格大于 30 分钟才开启新会话，所以 30 分钟仍属于同一会话，31 分钟才拆分。
2. 交易事件行数不等于订单数；一个订单有多个商品时会有多行，订单数按唯一 `transactionid` 计算。
3. 商品属性是随时间变化的，事件只能关联事件时间之前最近生效的属性，不能使用未来信息。
4. 原始异常不直接删除；先保留并标记，再由具体指标决定是否排除，排除逻辑必须可追溯。

## 6. 测试覆盖

CI 使用人工构造的小型数据，不下载正式数据，验证：

- 29/30/31 分钟会话边界；
- 多商品同订单去重；
- 属性 ASOF 关联与未来泄漏；
- 分类根节点、深度和路径；
- 连续两次构建不重复数据。

正式全量验收结果见 [`V0.2_QUALITY_REPORT.md`](V0.2_QUALITY_REPORT.md)。
