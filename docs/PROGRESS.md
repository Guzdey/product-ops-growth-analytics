# 项目进度

最后更新：2026-09-03

## 当前状态

**当前里程碑：`v0.3.0` 自动运营指标开发完成；等待 GitHub PR、CI 和正式发布。**

第三部分已在 `v0.2.0` 数据仓库上生成活跃、漏斗、留存、交易、复购、生命周期和品类
指标，三项预登记假设均已如实输出。当前尚未创建 `v0.3.0` PR、标签或 Release，因此
不能把本地完成状态写成已正式发布。

## 里程碑看板

| 版本 | 状态 | 当前证据 |
|---|---|---|
| `v0.1.0` | 已发布 | [GitHub Release](https://github.com/Guzdey/product-ops-growth-analytics/releases/tag/v0.1.0)、受保护 `main`、绿色 CI |
| `v0.2.0` | 已发布 | [GitHub Release](https://github.com/Guzdey/product-ops-growth-analytics/releases/tag/v0.2.0)、PR #5、PR #6、受保护 `main`、绿色 CI |
| `v0.3.0` | 待发布 | 全量指标 11 pass / 0 fail；聚合导出已验证，PR 和 Release 待完成 |
| `v0.4.0` | 未开始 | Streamlit 看板与真实运营故事 |
| `v0.5.0` | 未开始 | 独立模拟渠道与 A/B 实验 |
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

## v0.3.0 已完成（尚未发布）

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
- [ ] 审阅、显式暂存、提交、推送、PR、CI、合并、标签和 Release。

## 下一步

1. 显式暂存已审阅的 `v0.3.0` 文件，不包含用户私有 `.gitignore` 和 `.lsf` 文件。
2. 提交并推送功能分支，创建 Pull Request 后等待 GitHub Actions。
3. CI 通过后按授权顺序执行 merge、tag 和 Release。

## 这一阶段需要会讲的内容

面试或复盘时至少能够解释：CSV 为什么要导入数据库、五层模型分别解决什么问题、
为什么订单数要去重、30 分钟会话如何划分、ASOF 如何防止未来信息泄漏，以及为什么
原始重复行应先标记而不是直接删除。
