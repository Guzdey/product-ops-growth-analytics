# 项目进度

最后更新：2026-09-08

## 当前状态

**当前里程碑：`v0.5.0` 独立模拟渠道与 A/B 实验已合入 `main`，正在准备版本发布。**

第三部分已在 `v0.2.0` 数据仓库上生成活跃、漏斗、留存、交易、复购、生命周期和品类
指标，三项预登记假设均已如实输出。PR #8 已于 2026-09-05 Squash 合入 `main`。第四
部分通过 PR #9 合入 `main`，形成六页 Streamlit 真实数据看板。第五部分已在独立
`synthetic` Schema 中完成模拟渠道与 A/B 实验，并通过 PR #10 合入 `main`。

## 里程碑看板

| 版本 | 状态 | 当前证据 |
|---|---|---|
| `v0.1.0` | 已发布 | [GitHub Release](https://github.com/Guzdey/product-ops-growth-analytics/releases/tag/v0.1.0)、受保护 `main`、绿色 CI |
| `v0.2.0` | 已发布 | [GitHub Release](https://github.com/Guzdey/product-ops-growth-analytics/releases/tag/v0.2.0)、PR #5、PR #6、受保护 `main`、绿色 CI |
| `v0.3.0` | 待发布 | 全量指标 11 pass / 0 fail；PR #8 与 main CI 已通过，标签和 Release 待完成 |
| `v0.4.0` | 已合入 | PR #9、六页看板、真实聚合快照、三条运营故事和绿色 main CI；Release 待补 |
| `v0.5.0` | 发布准备 | PR #10、独立模拟 Schema、渠道指标、A/B 检验、第七页看板和绿色 main CI |
| `v1.0.0` | 未开始 | 求职作品集与公开部署 |

## v0.2.0 已完成

- [x] 检查 D 盘空间并将 DuckDB、导出和临时数据保留在 D 盘。
- [x] 对四个官方 CSV 记录文件大小、SHA-256、实际行数和导入运行 ID。
- [x] 用显式字段类型全量导入 2,756,101 条事件、20,275,902 条商品属性和
  1,669 条分类关系。
- [x] 建立 `meta`、`raw`、`stg`、`core`、`mart` 五个 Schema；`mart` 留给下一阶段填充。
- [x] 将毫秒时间戳统一转换为 UTC，并保留原始时间戳。
- [x] 建立稳定事件、30 分钟会话和唯一交易模型。
- [x] 建立完整商品属性、分类和可用状态历史区间。
- [x] 使用 ASOF 逻辑关联事件时点属性，未来信息泄漏检查为 0。
- [x] 递归建立匿名分类根节点、深度和路径，循环与缺失祖先检查均为 0。
- [x] 将 13 个建模语句拆成可恢复步骤；异常中断可标记为 `abandoned`。
- [x] 连续两次全量构建结果一致，第二次复用全部已成功步骤。
- [x] 确定性 Fixture 覆盖 29/30/31 分钟、多商品订单、ASOF、防未来泄漏、
  分类路径、幂等性和异常恢复。
- [x] [PR #5](https://github.com/Guzdey/product-ops-growth-analytics/pull/5) 已 Squash 合并；
  `main` 提交为 `343faf629fdf3c4f395d7f5f5e3f7ccbae001102`。
- [x] 合并后 [CI Run 33499570428](https://github.com/Guzdey/product-ops-growth-analytics/actions/runs/33499570428)
  成功完成，用时 1 分钟。
- [x] [PR #6](https://github.com/Guzdey/product-ops-growth-analytics/pull/6) 已 Squash 合并；
  发布提交为 `e99cdd293064d89fe7fb7698dcd962614f6e3d52`。
- [x] 最终 [CI Run 33505012015](https://github.com/Guzdey/product-ops-growth-analytics/actions/runs/33505012015)
  成功完成，用时约 49 秒。
- [x] 注释标签 `v0.2.0` 已推送，并发布无自定义数据附件的
  [GitHub Release](https://github.com/Guzdey/product-ops-growth-analytics/releases/tag/v0.2.0)。

## 全量验收摘要

| 项目 | 结果 |
|---|---:|
| 质量检查 | 14 pass / 1 warn / 0 fail |
| 核心事件 | 2,756,101 行 |
| 会话 | 1,761,675 行 |
| 唯一交易 | 17,672 笔 |
| 商品属性历史 | 20,275,902 行 |
| 首次全量建模 | 约 38.0 秒 |
| 相同输入再次建模 | 0.339 秒 |
| 本地 DuckDB | 约 2.60 GB，位于 D 盘 |
| 本地工程门禁 | 30 Pytest、Ruff、SQLFluff、CLI、依赖检查全部通过 |

唯一警告是 458 个完全重复事件组合，共涉及 918 行。原始记录全部保留并标记，
其中相对每组保留一行计算有 460 行额外重复；后续指标是否排除必须显式写入口径。
完整结果见 [`V0.2_QUALITY_REPORT.md`](V0.2_QUALITY_REPORT.md)。

## 当前风险与边界

- 数据没有金额、渠道、成本和实验分组，不能计算真实 GMV、AOV、CAC、ROAS 或 LTV。
- 除 `categoryid`、`available` 外，商品属性不可解释为价格、品牌或商品名。
- `v0.2.0` 标签固定指向 `e99cdd293064d89fe7fb7698dcd962614f6e3d52`；Release
  不包含完整数据、DuckDB、Parquet 或其他自定义数据附件。
- 完整 CSV、DuckDB 和质量 JSON 只保存在 D 盘，不进入公开仓库。

## v0.3.0 已完成（功能已合入，版本尚未发布）

- [x] 建立 31 项指标注册表和六个版本化 SQL 指标模块。
- [x] 实现活跃、会话、三类漏斗、路径、D1/D3/D7/D14/D30 与周留存。
- [x] 实现唯一交易、复购率、复购间隔、生命周期和 9 日风险阈值。
- [x] 实现商品/品类表现、Wilson 95% 区间、机会排序和数据覆盖质量。
- [x] 实现 `metrics`、`export` 与完整 `run-all` Python 编排。
- [x] 32 个确定性测试、Ruff 和 SQLFluff 全部通过。
- [x] 官方全量计算通过 11 项指标质量检查，`data_origin='real'`。
- [x] H1 未支持（D7 差 0.656pp）；H2 支持（最大步骤占总流失 98.52%）；
  H3 支持（匿名品类 299 低同级中位数 2.119pp）。
- [x] 导出 17 张隐私安全聚合关系的 CSV/Parquet、清单和 Markdown 摘要；共 10.39 MiB，
  文件大小、Hash、数据库行数和禁止字段检查全部通过。
- [x] [PR #8](https://github.com/Guzdey/product-ops-growth-analytics/pull/8) 已 Squash 合并，
  合并提交为 `188f22bc76218785b35151a7a8b4e06acb32d369`。
- [x] [main CI Run 33952566190](https://github.com/Guzdey/product-ops-growth-analytics/actions/runs/33952566190)
  已通过。
- [ ] 推送本地发布准备文档，创建 `v0.3.0` 标签和 Release。

## v0.4.0 已完成（功能已合入，版本尚未发布）

- [x] 建立管理摘要、流量活跃、漏斗路径、留存生命周期、商品品类和数据质量六页看板。
- [x] 建立日期、首会话分群、Cohort 周、根品类、最少样本和机会候选筛选。
- [x] 所有业务页面使用 `What / So What / Now What / How to Verify` 结构。
- [x] 将 H1、H2、H3 转化为三条可追溯的运营故事，明确动作、主指标、护栏和实验方案。
- [x] 生成 17 张、约 427 KiB 的真实聚合快照和 SHA-256 清单，不含访客级、交易级或
  会话级标识。
- [x] 看板自动优先读取 D 盘完整聚合导出，缺失时回退到仓库内公开聚合快照；两种模式
  都不扫描原始 CSV。
- [x] 修正深色主题 KPI 对比度、普通/同商品漏斗分母混用和首会话购买分群漏展示问题。
- [x] 使用 Streamlit AppTest 逐页启动，并通过本地浏览器完成六页视觉检查。
- [x] 全仓依赖检查、Ruff、38 个 Pytest、SQLFluff 和六个 CLI 帮助入口全部通过；公开快照
  与完整聚合导出首次读取分别约 0.040 秒和 0.362 秒。
- [x] PR #9 已 Squash 合并，合并提交 `495fbc11cc6a4777ee56903fbe527f73d979abd5`；
  合并后 main CI 通过。
- [ ] 推送本地标签并创建 GitHub Release。

## v0.5.0 已完成（功能已合入，版本尚未发布）

- [x] 固定随机种子 `20260809`，生成 40,000 条模拟实验分配；不复用真实 `visitorid`。
- [x] 建立独立 `synthetic` Schema，真实 `raw/stg/core/mart` 不参与模拟计算。
- [x] 同时实现无效果与正向效果场景，每场景对照/实验组各 10,000 人。
- [x] SQL 计算 CTR、点击后 CVR、分组转化率、CAC、ROAS、模拟 GMV/AOV 和退款率。
- [x] Python 输出绝对/相对提升、95% 置信区间、双侧比例检验和联合决策。
- [x] 正向场景 8.0%→9.2%，+1.2pp，95% CI [+0.423pp, +1.977pp]，p=0.0025；
  无效果场景为 8.0%→8.0%，p=1.0000。
- [x] 9 项质量检查全部通过；模拟参与者 ID 与真实 ID 重合数为 0。
- [x] 增加独立第七页看板与约 74 KiB 聚合快照，未包含参与者或订单明细。
- [x] 全仓门禁通过：44 个 Pytest、Ruff、SQLFluff、依赖检查和 CLI 检查全部成功。
- [x] [PR #10](https://github.com/Guzdey/product-ops-growth-analytics/pull/10) 已 Squash 合并，
  合并提交为 `f83e0d115d0a00a91be4ef4e3dd0490b72d67e02`。
- [x] 合并后的 [main CI Run 34221190332](https://github.com/Guzdey/product-ops-growth-analytics/actions/runs/34221190332)
  已通过。
- [ ] 创建 `v0.5.0` 标签和 GitHub Release。

## 下一步

1. 将本次发布证据文档通过短分支和 Pull Request 合入 `main`。
2. 在最终绿色 `main` 上创建并推送 `v0.5.0` 注释标签，再创建 GitHub Release。
3. 后续补齐 `v0.3.0`、`v0.4.0` 尚未完成的远程标签与 Release。
4. 进入 `v1.0.0` 求职作品集整理与公开部署。

## 这一阶段需要会讲的内容

面试或复盘时至少能够解释：CSV 为什么要导入数据库、五层模型分别解决什么问题、
为什么订单数要去重、30 分钟会话如何划分、ASOF 如何防止未来信息泄漏，以及为什么
原始重复行应先标记而不是直接删除。
