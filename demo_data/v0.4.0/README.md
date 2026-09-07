# v0.4.0 公开聚合快照

本目录不是模拟数据，也不是桌面教学样例。它来自 Retailrocket 官方完整数据经过项目
`v0.3.0` DuckDB SQL 指标层计算后的聚合结果，`data_origin='real'`。

- 17 张 CSV 共约 427 KiB；
- 日、漏斗、留存、交易、生命周期、品类、质量和假设表保留全部聚合行；
- 行为路径仅保留按会话数排序的前 50 条；
- 商品表现仅保留浏览会话前 250 个商品，并补充品类 299 的最多 50 个商品；
- 不含 `visitorid`、`transactionid`、`session_id` 或原始行为明细；
- `dashboard_manifest.json` 记录源运行 ID、选取规则、行数、大小和 SHA-256。

快照用于无需下载完整数据的公开看板演示，不能替代官方完整 CSV，也不能用于重新推导
总体指标。数据及其受许可约束的衍生物遵循 CC BY-NC-SA 4.0，详见
[`docs/DATA_LICENSE.md`](../../docs/DATA_LICENSE.md)。
