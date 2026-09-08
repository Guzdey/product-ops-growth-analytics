# synthetic

`synthetic` 是 `v0.5.0` 独立模拟增长实验 Schema，与 Retailrocket 的
`raw/stg/core/mart` 真实分析链路隔离。

- `001_initialize.sql`：只定义模拟实验分配和渠道日投入的输入表；
- `002_build_metrics.sql`：以 SQL 统一计算 CTR、CVR、CAC、ROAS、模拟 GMV/AOV 和退款率；
- 所有关系都带 `data_origin='synthetic'`；
- 访客级模拟分配只保存在本地 DuckDB，不进入公开导出。

固定随机种子、两比例检验、质量门禁和聚合导出由
`src/product_ops/experiments.py` 编排。
