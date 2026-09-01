# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 的组织方式和 [Semantic Versioning](https://semver.org/) 版本号。只有通过里程碑验收的内容才从 `Unreleased` 移入正式版本。

## [Unreleased]

## [0.2.0] - 2026-09-01

### Added

- 将 `ingest`、`build`、`validate` 和 `run-all` 从安全占位接口实现为可执行的
  `v0.2.0` 全量 DuckDB 流程。
- 建立 `meta` 源文件清单、运行审计和机器可读质量检查，记录文件大小、
  SHA-256、行数、代码版本和异常中断恢复状态。
- 使用显式类型导入四个官方 CSV，并建立 `raw`、`stg`、`core` 数据模型：
  UTC 事件、30 分钟会话、唯一交易、商品属性历史、事件时点 ASOF 属性和递归分类树。
- 增加确定性 DuckDB Fixture，覆盖 29/30/31 分钟边界、多商品订单、未来信息防漏、
  分类路径、幂等重建和异常运行恢复。
- 增加 `docs/WAREHOUSE_GUIDE.md`，说明 CSV、DuckDB、SQL、Python、Git 与后续看板的联动。
- 增加 `docs/V0.2_QUALITY_REPORT.md`，记录全量行数、文件 Hash、质量结果、性能和已知局限。

### Changed

- SQLFluff 改用显式 Jinja 上下文检查路径与会话参数模板；CI 对已实现命令执行
  `--help` 冒烟测试，正式数据仍不进入 CI。
- 商品属性冲突统计先聚合后回连，并由属性历史模型复用，避免重复执行 2000 万级
  字符串窗口去重。
- 将 13 个建模语句拆分为独立事务并记录构建签名；相同输入和 SQL 可跳过已成功步骤，
  中断后可从未完成步骤继续。
- 项目包版本更新为 `0.2.0`，Streamlit 入口显示数据仓库阶段状态；指标和完整看板
  仍留在后续里程碑。

### Fixed

- 声明 DuckDB 读取 `TIMESTAMPTZ` Python 值所需的 `pytz` 运行依赖。
- 新运行会把进程异常结束后遗留的 `running` 审计记录标记为 `abandoned`，避免误报。

### Verification

- 官方完整数据导入结果为 2,756,101 条事件、20,275,902 条商品属性和 1,669 条分类关系。
- 全量质量门禁为 14 pass、1 warn、0 fail；唯一警告是 918 条已保留并标记的完全重复事件。
- 首次 13 步全量建模约 38.0 秒；相同输入再次执行为 0.339 秒，核心表行数不变。

## [0.1.0] - 2026-08-12

### Added

- 建立项目级 `AGENTS.md`，固化存储、数据、指标、测试和 Git 安全约束。
- 建立项目总计划、进度日志、指标字典、数据契约和数据许可说明。
- 建立业务导向 README 与 MIT 代码许可。
- 建立 Python 3.12 `src` 包、六命令无副作用 CLI、D 盘路径安全配置和真实/模拟来源标记。
- 建立 `meta/raw/stg/core/mart` SQL 占位目录、Streamlit 安全入口与 Pytest 契约测试。
- 建立 Ruff、SQLFluff、严格 `.gitignore` 和 GitHub Actions 质量门禁配置。
- 在 D 盘建立隔离的 Python 3.12 开发环境；本地 `pip check`、30 个 Pytest、Ruff、SQLFluff、六命令 CLI 与 Streamlit AppTest 全部通过。
- 创建公开 GitHub 仓库，推送空 `main` 基线与 `feat/v0.1-foundation` 项目地基分支；PR #1 已于 2026-08-11 squash 合并到 `main`，合并提交为 `30961a8`。
- GitHub Actions Run `31350600784` 已在项目地基提交上通过；合并后 `main` 的 Run `31469402516` 也已在 46 秒内成功完成 `Python 3.12 quality gate`，覆盖依赖一致性、数据与凭证守卫、Ruff、30 个 Pytest（含 Streamlit AppTest）、SQLFluff 和六命令 CLI 冒烟测试。
- 为 `main` 启用 classic protection rule `81577593`：要求通过 Pull Request 和 `Python 3.12 quality gate`，要求线性历史，不允许 bypass，并禁止 force push 与分支删除。
- 通过 PR #2 将发布证据 squash 合并到 `main`；最终发布提交为 `9b97914`，对应 Run `31498578803` 成功完成，总耗时 51 秒。
- 创建注释标签 `v0.1.0`（标签对象 `d63ec1d`），准确指向最终发布提交 `9b97914`。
- 发布公开正式 GitHub Release [`v0.1.0 — 项目地基 / Project Foundation`](https://github.com/Guzdey/product-ops-growth-analytics/releases/tag/v0.1.0)，无上传附件，不重新分发 Retailrocket 数据。

### Fixed

- 将 PyArrow 固定为 `24.0.0`，满足 Streamlit `1.61.1` 的 `pyarrow<25` 依赖约束。
- 修正 CI 大文件守卫对合法 `sql/raw/` 分层目录的误判，只拦截仓库顶层数据目录。
- 将 SQLFluff 规则放入显式 `.sqlfluff`，确保本地与 CI 不读取用户级配置且仍执行仓库规则。

## Roadmap

- `v0.2.0`：全量 DuckDB 数据仓库（已完成）。
- `v0.3.0`：Python 自动运营指标引擎。
- `v0.4.0`：Streamlit 看板与真实业务故事。
- `v0.5.0`：独立模拟渠道与 A/B 实验模块。
- `v1.0.0`：在线演示与求职作品集。

[Unreleased]: https://github.com/Guzdey/product-ops-growth-analytics/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Guzdey/product-ops-growth-analytics/releases/tag/v0.2.0
[0.1.0]: https://github.com/Guzdey/product-ops-growth-analytics/releases/tag/v0.1.0
