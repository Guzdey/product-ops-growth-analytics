# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 的组织方式和 [Semantic Versioning](https://semver.org/) 版本号。只有通过里程碑验收的内容才从 `Unreleased` 移入正式版本。

## [Unreleased]

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

### Fixed

- 将 PyArrow 固定为 `24.0.0`，满足 Streamlit `1.61.1` 的 `pyarrow<25` 依赖约束。
- 修正 CI 大文件守卫对合法 `sql/raw/` 分层目录的误判，只拦截仓库顶层数据目录。
- 将 SQLFluff 规则放入显式 `.sqlfluff`，确保本地与 CI 不读取用户级配置且仍执行仓库规则。

### `v0.1.0` 发布前剩余事项

- 创建并推送 `v0.1.0` 标签，发布并验证 GitHub Release。
- 发布完成后补充最终证据，并将本节内容整理为正式的 `[0.1.0] - 实际发布日期` 条目。

## Roadmap

- `v0.2.0`：全量 DuckDB 数据仓库。
- `v0.3.0`：Python 自动运营指标引擎。
- `v0.4.0`：Streamlit 看板与真实业务故事。
- `v0.5.0`：独立模拟渠道与 A/B 实验模块。
- `v1.0.0`：在线演示与求职作品集。
