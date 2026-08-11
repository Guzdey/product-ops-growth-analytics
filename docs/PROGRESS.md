# 项目进度

最后更新：2026-08-11

## 当前状态

**当前里程碑：`v0.1.0` — PR #1 与合并后 `main` CI 已完成，等待标签和 Release**

本文件记录可由当前工作区或外部状态验证的进度。`v0.1.0` 标签、GitHub Release 和发布后最终证据尚未完成，因此不得将 `v0.1.0` 标记为完成。

## 里程碑看板

| 版本 | 状态 | 当前证据 | 完成门槛 |
|---|---|---|---|
| `v0.1.0` | **进行中** | PR #1 已 squash 合并至受保护的 `main`；合并提交 `30961a8` 的 Run `31469402516` 已通过；本地 30 个测试、Ruff、SQLFluff、六命令 CLI 和 Streamlit AppTest 均通过 | `v0.1.0` 标签和 GitHub Release 存在；最终发布证据已记录 |
| `v0.2.0` | 未开始 | D 盘全量原始 CSV 已存在 | 全量 DuckDB 分层仓库及数据质量验收 |
| `v0.3.0` | 未开始 | 指标口径模板已建立 | 自动指标、精确测试和真实假设检验 |
| `v0.4.0` | 未开始 | 页面信息架构已写入总计划 | Streamlit、三条真实故事和运营策略 |
| `v0.5.0` | 未开始 | 真实/模拟边界已固化 | 独立、可复现、醒目标注的模拟实验模块 |
| `v1.0.0` | 未开始 | 求职交付标准已写入总计划 | 在线 Demo、案例、面试材料和稳定 Release |

## 当前已确认资产

### 工作区

- 源码工作区：`C:\Users\18450\Desktop\analysis_ project`。
- 已有 `tools/` 与 `outputs/` 被视为用户资产，当前 Goal 不删除、不覆盖。

### D 盘原始数据

以下 `raw/extracted` 四个官方完整 CSV 是 Full mode 的唯一正式分析源：

| 文件 | 当前大小 |
|---|---:|
| `raw/retailrocket-ecommerce-dataset.zip` | 304,719,974 bytes |
| `raw/extracted/events.csv` | 94,237,913 bytes |
| `raw/extracted/item_properties_part1.csv` | 484,315,749 bytes |
| `raw/extracted/item_properties_part2.csv` | 408,929,907 bytes |
| `raw/extracted/category_tree.csv` | 14,454 bytes |

解压 CSV 合计 987,498,023 bytes（约 987.5 MB）。Goal 2 仍需通过程序核对行数、Hash、字段类型和可重复导入；“文件存在”不能替代数据质量验收。

### 教学样例边界

- `outputs/retailrocket_sample/`
- `tools/build_retailrocket_sample.py`
- `tools/build_retailrocket_workbook.mjs`
- 已生成的桌面小样例

上述资产继续保留，只用于教学、字段理解和格式预览；绝不用于正式指标、正式看板或业务结论。

## v0.1.0 检查清单

- [x] 建立根目录 `AGENTS.md`。
- [x] 建立 `README.md` 与 `CHANGELOG.md`。
- [x] 建立 `docs/PROJECT_PLAN.md` 与本进度文件。
- [x] 建立指标字典、数据契约、数据许可和 MIT 代码许可。
- [x] 完成 Python 3.12 项目骨架与依赖声明。
- [x] 完成六个 CLI 子命令骨架并验证 `--help`。
- [x] 完成 Ruff、Pytest、SQLFluff、六命令 CLI 和 Streamlit smoke test。
- [x] 完成严格 `.gitignore` 并验证大型文件/凭证不被跟踪。
- [x] 完成 GitHub Actions 首次运行并获得绿色 CI。
- [x] 经授权完成 Git 仓库、公开仓库、分支推送与 Draft PR #1。
- [x] PR #1 已 squash 合并，并验证合并后 `main` Run `31469402516` 成功。
- [x] `main` classic protection rule `81577593` 已启用并验证。
- [ ] 经授权创建并推送 `v0.1.0` 标签。
- [ ] 经授权发布并验证 GitHub Release。
- [ ] 完成发布后最终证据更新并关闭 Goal 1。

## 当前风险与控制

- **D 盘构建空间**：原始文件与 ZIP 已占约 1.29 GB；Goal 2 开始前检查可用空间，建议至少预留 5 GB。
- **数据解释**：匿名商品属性不能解释为价格、品牌或名称；仅 `categoryid`、`available` 有明确语义。
- **许可**：代码 MIT 与数据 CC BY-NC-SA 4.0 分开；GitHub 不重新分发全量数据。
- **结果真实性**：尚未完成全量指标，README 和简历不得出现业务提升数字。
- **外部状态**：创建标签、推送标签、发布 Release，以及最终证据文档的 stage、commit、push 和 PR 均按动作单独授权；已完成的 PR 合并、`main` CI 和分支保护均以远端状态验证。

## 最新检查点

### 2026-08-11 合并与分支保护检查点

- [PR #1](https://github.com/Guzdey/product-ops-growth-analytics/pull/1) 已 squash 合并到 `main`；合并提交为 [`30961a8`](https://github.com/Guzdey/product-ops-growth-analytics/commit/30961a85642898e3da6b9a242cd745ea5eb3cef2)。
- 合并后 [GitHub Actions Run `31469402516`](https://github.com/Guzdey/product-ops-growth-analytics/actions/runs/31469402516) 已成功完成 `Python 3.12 quality gate`，用时 46 秒。
- `main` 已启用 classic protection rule `81577593`：要求 Pull Request、`Python 3.12 quality gate` 和线性历史，不允许 bypass，并禁止 force push 与分支删除。
- 当前尚无 `v0.1.0` 标签或 GitHub Release；里程碑继续保持“进行中”。

### 2026-08-10 远程发布检查点

- 公开仓库：[Guzdey/product-ops-growth-analytics](https://github.com/Guzdey/product-ops-growth-analytics)。
- 远程 `main` 为隐私邮箱重写后的空基线提交 `81ff435`；远程 `feat/v0.1-foundation` 为项目地基提交 `72a4a22`，两者均已与本地 SHA 核对一致。
- [Draft PR #1](https://github.com/Guzdey/product-ops-growth-analytics/pull/1) 使用唯一分支对 `main ← feat/v0.1-foundation`，包含 1 个提交和 41 个文件；当前仍为 Draft，尚未合并。
- [GitHub Actions Run 31350600784](https://github.com/Guzdey/product-ops-growth-analytics/actions/runs/31350600784) 在提交 `72a4a22` 上成功完成 `Python 3.12 quality gate`，用时 44 秒。
- 远程 CI 已运行依赖安装与一致性检查、大型数据/敏感文件拒绝、Python lint、无生产数据单元测试、DuckDB SQL lint 和六命令 CLI 冒烟测试。
- 当前尚无 `v0.1.0` 标签或 Release；在 PR 合并、合并后 `main` CI 及发布证据完成前，里程碑继续保持“进行中”。

### 2026-08-09 本地质量门禁结果

以下内容保留为当日历史检查点；当前外部状态以 2026-08-10 远程发布检查点为准。

- 使用绑定 Python `3.12.13` 在 `D:\CodexData\product-ops-growth-analytics\envs\product-ops-growth-analytics` 建立虚拟环境；环境约 `665.60 MiB`，pip 缓存约 `169.40 MiB`，安装临时目录为空。
- `pip` resolver 安装成功，`python -m pip check` 输出 `No broken requirements found.`；PyArrow `24.0.0` 与 Streamlit `1.61.1` 的约束已由真实安装验证。
- Pytest：`30 passed`，包含正式/模拟配置边界、路径安全、六命令契约和真实 Streamlit AppTest。
- Ruff：`All checks passed!`；SQLFluff：`All Finished!`，继续执行 100 字符门禁。为避免读取用户级配置，SQL lint 固定使用 `--ignore-local-config --config .sqlfluff`，只依赖显式仓库配置。
- CLI `--help` 与 `ingest/build/metrics/validate/export/run-all` 六个命令均以 `config/project.example.toml` 成功执行；输出指向 D 盘四个官方完整 CSV，且无数据读写副作用。
- Streamlit AppTest 成功渲染标题和安全说明，没有应用异常；当前页面仍为不读取数据的 `v0.1.0` 占位入口。
- TOML、GitHub Actions YAML 与显式 `.sqlfluff` 配置解析通过；已验证 SQLFluff 实际读取 `dialect=duckdb`、`templater=raw`、`max_line_length=100`。
- Git 初始化前安全扫描覆盖 46 个非缓存、非教学输出文件：超过 `5 MiB` 的文件为 0，敏感路径候选为 0。CI 守卫已验证会拦截顶层 `raw/warehouse`，不会误伤合法 `sql/raw/`。
- 原始 CSV、ZIP、教学样例和已有 `tools/`/`outputs/` 均未移动、删除或覆盖；尚未执行任何 Git/GitHub 写操作。
- 经单独授权已执行 `git init -b main`；仓库仍无提交、无暂存文件，`git ls-files` 计数为 0。
- Git 显示 41 个源码、配置、测试、文档和保留教学脚本为可跟踪候选；`outputs/`、工具缓存、字节码、egg-info、顶层数据目录、CSV、DuckDB、Parquet、`.env` 和 Kaggle 凭证路径均由 `.gitignore` 正确排除。
- 经单独授权已从 GitHub CLI 官方 `v2.97.0` Release 下载 Windows AMD64 ZIP 到 D 盘；压缩包为 `14,938,517 bytes`，SHA-256 `35d7fe05c4dd1411ffda1e73dfc7c6f44b75c936ca51fa6595c657fdc0350cec`，校验通过后安装到 `D:\CodexData\product-ops-growth-analytics\tools\gh\2.97.0\bin\gh.exe`。
- GitHub CLI 当前明确为未登录。经单独授权启动设备登录时，本机到 GitHub 设备码接口发生 TCP 超时，未写入账号或凭证；内置浏览器可访问 GitHub，但也处于未登录状态，已将官方登录页作为用户接管页面保留。
- Git for Windows 自带 Git Credential Manager `2.9.0`，路径为 `D:\Git\mingw64\bin\git-credential-manager.exe`；当前尚未配置 credential helper，后续可在 push 授权点使用官方浏览器认证而无需传递明文 Token。
- 连续三个目标回合的最终复核均显示相同外部阻塞：本地与全局 `user.name/user.email` 全为空，GitHub CLI 未登录；最新仓库证据仍为 `main`、0 跟踪、0 暂存、0 提交、41 个候选文件。依据目标模式阻塞规则，当前 Goal 在此检查点正式暂停，不重复发起登录或提交授权。
- 用户随后提供 Git 姓名与邮箱；经单独授权已写入当前仓库的本地 Git 配置，全局身份仍为空。邮箱明文不写入将公开的项目文档。
- 经单独授权已在 `main` 创建空树基线提交；随后创建并切换到 `feat/v0.1-foundation`。为避免公开 Gmail，用户又批准将本仓库改用 GitHub `noreply` 邮箱，并单独批准把尚未推送的空基线重写为 `81ff435`；两个分支均指向该空树，正式文件仍未提交。
- 浏览器已确认当前 GitHub 登录账号为 `Guzdey`；GitHub CLI 仍未取得 OAuth 凭证，后续远程命令将在各自授权点使用安全登录流程，不传递明文 Token。
- 最新 stage 前扫描：41 个候选文件合计约 127 KB，最大文件约 16 KB，超过 5 MiB、数据格式或凭证路径候选均为 0；候选文件中未出现 Gmail 明文。`pip check`、Ruff、30 个 Pytest 和 SQLFluff 再次全部通过。

## 下一步

1. 通过 release-prep PR 合并本轮文档，并验证其合并后 `main` CI。
2. 分别请求创建和推送 `v0.1.0` 标签；标签必须指向 release-prep 合并后的最终 `main` 提交。
3. 单独请求发布 GitHub Release，并验证版本、标签、Release Notes 与许可说明。
4. 发布完成后通过最终证据 PR 更新 README、CHANGELOG 和本进度文件。
5. 最终证据合并且 `main` CI 通过后，才将 Goal 1 标记为完成；Goal 2 此前保持“未开始”。

## 更新格式

后续每个检查点追加或更新以下信息：

```text
已完成：
验证结果：
当前风险：
下一步：
需要用户决定：
```
