# Product Ops Growth Analytics：Agent 工作规范

## 1. 项目目标

本仓库使用 Retailrocket 真实电商行为数据，构建一套面向用户增长/产品运营实习求职的可复现作品集。项目必须同时证明：

- 使用 SQL 管理全量 CSV、建设分层数据模型和统一指标口径；
- 使用 Python 自动完成导入、构建、指标计算、验证和导出；
- 使用 Streamlit 将真实发现转化为可解释的运营看板；
- 使用 Git、Pull Request、CI、标签和 GitHub Release 留下规范迭代证据；
- 从数据事实出发提出运营动作与实验方案，不把相关性夸大为因果关系。

项目使用根目录 `AGENTS.md` 作为协作约束，不创建独立 Skill。

## 2. 语言与命名

- README、业务报告、指标释义和运营建议以中文为主。
- Python 模块、函数、变量、SQL 表/列、配置键和 CLI 命令使用英文 `snake_case`。
- 首次出现的专业术语应同时给出中文解释和英文标识。
- 文档不得使用尚未验证的数字，不得写成“上线后提升 X%”。

## 3. 路径与存储

- 当前源码工作区：`C:\Users\18450\Desktop\analysis_ project`。
- 大型数据根目录：`D:\CodexData\product-ops-growth-analytics`。
- 原始 CSV：`D:\CodexData\product-ops-growth-analytics\raw\extracted`。
- Full mode 的唯一正式分析源是该目录下四个官方完整 CSV：`events.csv`、`item_properties_part1.csv`、`item_properties_part2.csv`、`category_tree.csv`。
- DuckDB、Parquet、临时计算、缓存和大型导出必须位于 D 盘数据根目录下。
- 代码不得依赖用户名写死路径；通过 `PRODUCT_OPS_DATA_HOME` 或项目配置解析数据根目录。
- C 盘只保存源码、文档、小型测试 Fixture 和少量展示截图。
- 下载或生成大型文件前必须先确认预估大小、D 盘目标路径和可用空间。
- 不移动、不删除、不覆盖现有原始数据；保留已有 `tools/` 与 `outputs/`，除非用户明确授权修改。

## 4. 数据处理约束

- 正式分析使用全量数据：2,756,101 条事件、20,275,902 条商品属性记录和 1,669 条分类关系；不得用桌面小样例替代正式结论。
- 现有 `outputs/retailrocket_sample/`、`tools/build_retailrocket_sample.py` 和 `tools/build_retailrocket_workbook.mjs` 仅用于教学、字段理解和格式预览。必须保留，但绝不作为正式指标、正式看板或业务结论的输入。
- 两份商品属性 CSV 必须全部进入 `raw`/`stg` 层；不能因为属性匿名而删减。
- 仅 `categoryid`、`available` 具有可直接解释含义；其他匿名属性保持原值，不命名为价格、品牌或商品名。
- 毫秒时间戳统一按 UTC 解释，并在展示层明确时区。
- 同一访客相邻事件间隔严格大于 30 分钟时开启新会话；恰好 30 分钟仍属于原会话。
- 订单数使用 `COUNT(DISTINCT transactionid)`；交易事件行数不能冒充订单数。
- 商品属性必须按事件时点做 ASOF/SCD2 关联，禁止用未来属性解释过去事件。
- 原始行不得静默删除。疑似重复、非法事件或关联缺失应增加质量标记并在报告中说明。

## 5. SQL、Python 与看板职责

- DuckDB 是本地分析仓库；采用 `meta`、`raw`、`stg`、`core`、`mart` 五层 Schema。
- SQL 是指标公式和大表聚合的唯一事实来源；同一指标不得在 Python 中维护另一套公式。
- Python 负责 CLI、流程编排、事务、日志、质量门禁、统计检验和结果导出。
- 禁止使用 Pandas 一次性加载约 2,027 万行商品属性；大表连接和聚合留在 DuckDB。
- Streamlit 只读取 `mart` 或导出的聚合数据，不直接扫描全量原始 CSV。
- 指标变更必须同步更新 `docs/METRIC_DICTIONARY.md`、测试和变更日志。

## 6. 真实数据与模拟数据边界

- Retailrocket 不含注册时间、真实价格、GMV、渠道、成本或实验分组；不得从匿名属性推测这些字段。
- `v0.1.0` 至 `v0.4.0` 的核心结论只使用真实 Retailrocket 行为数据。
- `v0.5.0` 才能增加渠道和 A/B 实验模拟模块，且使用独立 Schema/表名并设置 `data_origin='synthetic'`。
- 模拟数据的数据库表、导出、图表、截图和文字必须醒目标注“模拟数据 / SIMULATED”。
- 真实结论和模拟结论不能合并计算、不能并排制造可比错觉、不能共同支撑一条业务成果声明。

## 7. 验证与质量门禁

- 每项实现都应有与风险相称的测试，至少覆盖字段类型、行数、幂等性、会话边界、漏斗顺序、留存右截断、交易去重、属性时点和分类树异常。
- 核心指标使用小型确定性 Fixture 验证精确期望值；CI 不下载 Kaggle 全量数据。
- 提交前运行 Ruff、Pytest、SQL lint、CLI smoke test 和大文件/凭证检查。
- 验证失败不得绕过或弱化测试；先定位数据、口径或实现原因。
- 每个里程碑更新 `docs/PROGRESS.md` 和 `CHANGELOG.md`，Release Notes 必须列出验证证据与已知局限。

## 8. Git 与 GitHub 安全

- 禁止提交 ZIP、完整 CSV、DuckDB、完整 Parquet、虚拟环境、缓存、`.env`、Kaggle 凭证、GitHub Token 或其他秘密。
- 禁止使用 `git add .`、`git add -A` 或 `git add --all`；只能显式暂存已审阅的文件路径。
- 不使用破坏性命令，如 `git reset --hard` 或未经授权的文件清理。
- 只读 Git 检查可直接执行；以下每一步均应先展示准确范围并单独取得用户授权：安装依赖、GitHub 登录、创建远程仓库、stage、commit、push、创建 PR、merge、tag、创建 Release、公开部署。
- 使用短生命周期 `feat/...` / `fix/...` 分支、Conventional Commits、Pull Request 和受保护的 `main`。
- 每个完整工作单元可以提交并推送；只有通过验收的里程碑创建 SemVer 标签和 GitHub Release。

## 9. 许可

- 本仓库原创代码采用 MIT License，见 `LICENSE`。
- Retailrocket 数据及其受许可约束的衍生物采用 CC BY-NC-SA 4.0，见 `docs/DATA_LICENSE.md`。
- MIT License 不覆盖 Retailrocket 原始数据或受其许可约束的衍生数据。
- GitHub 不重新分发全量 Retailrocket 数据；公开聚合结果和样例必须保留来源、许可与真实/模拟标记。

## 10. 里程碑纪律

按 `docs/PROJECT_PLAN.md` 顺序推进：`v0.1.0` 项目地基、`v0.2.0` SQL 数据仓库、`v0.3.0` 自动指标、`v0.4.0` 看板与真实洞察、`v0.5.0` 模拟增长实验、`v1.0.0` 求职作品集与部署。当前里程碑未通过验收前，不提前发布下一版本。
