# v0.5.0 — 模拟增长实验（发布草案）

本版本新增与真实 Retailrocket 分析完全隔离的模拟渠道与 A/B 实验模块。它展示 CTR、
CVR、CAC、ROAS、模拟 GMV/AOV、效应量、95% 置信区间和双样本比例检验能力；不把任何
模拟结果表述成真实增长成果。

## 验收证据

- 固定随机种子 `20260809`，40,000 条实验分配；
- 两种预登记场景、每场景两组、每组 10,000 人；
- 9 项本地质量检查全部通过，模拟 ID 与真实 `visitorid` 重合数为 0；
- 公开快照 6 张聚合 CSV，约 74 KiB，无参与者或订单明细标识；
- 无效果场景正确输出“不上线”，正向效果场景只输出“逐步放量候选”；
- Release 不附加原始 Retailrocket 数据、DuckDB、Parquet 或模拟明细。

## GitHub 证据

- [PR #10](https://github.com/Guzdey/product-ops-growth-analytics/pull/10) 已 Squash 合并；
- 合并提交：`f83e0d115d0a00a91be4ef4e3dd0490b72d67e02`；
- [main CI Run 34221190332](https://github.com/Guzdey/product-ops-growth-analytics/actions/runs/34221190332)
  已成功完成；
- `v0.5.0` 标签与 GitHub Release 将在本次发布准备文档合入并通过主分支 CI 后创建。
