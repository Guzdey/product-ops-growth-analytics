# Product Ops Growth Analytics

> **Product Operations × User Growth × Analytics Engineering**

基于 Retailrocket 真实电商行为数据的产品运营与用户增长分析项目。项目围绕用户活跃、
`view → addtocart → transaction` 转化漏斗、Cohort 留存、复购、生命周期分群和品类机会，
使用 DuckDB SQL 建模，使用 Python 编排与验证指标，并通过 Streamlit 呈现分析结果。

**English summary:** A reproducible product-operations analytics project that turns anonymous
e-commerce behavioral data into governed metrics, user segments, operational actions, and
testable growth hypotheses.

> **当前状态：** [`v0.1.0 — Project Foundation`](https://github.com/Guzdey/product-ops-growth-analytics/releases/tag/v0.1.0)
> 已完成并发布。目前已具备项目结构、数据契约、指标字典、CLI、测试和 CI；
> 全量数据仓库、正式指标和完整看板尚未实现。

## 项目概览

| 项目要素 | 内容 |
|---|---|
| 业务场景 | 匿名电商访客从浏览、加购到购买及后续回访的运营分析 |
| 数据规模 | 2,756,101 条行为事件、20,275,902 条商品属性历史、1,669 条分类关系 |
| 核心问题 | 漏斗流失、首访质量、留存、复购、生命周期分群和品类机会 |
| 分析方法 | 会话化、严格有序漏斗、Cohort、时态属性关联和数据质量检查 |
| 技术栈 | DuckDB SQL、Python 3.12、Streamlit、Plotly、Pytest、GitHub Actions |

```text
业务问题 → 数据口径 → SQL 指标 → 真实发现 → 用户分群 → 运营动作 → 实验验证
```

## 运营场景

| 运营问题 | 分析方法 | 支持的决策 |
|---|---|---|
| 用户在哪一步流失？ | 严格有序会话漏斗、同商品漏斗 | 确定浏览、加购或购买环节的优化优先级 |
| 哪类首访用户更值得运营？ | 首个会话行为、D1/D7/D14 留存 | 区分仅浏览、加购未购、首购和复购人群 |
| 哪些品类值得优化？ | 浏览规模、品类转化率、同级基准 | 识别高流量但转化偏弱的品类 |
| 运营动作是否有效？ | 核心指标、护栏指标和实验设计 | 验证策略效果，避免把相关性写成因果关系 |

以上是分析框架，不是预设结论。正式发现只会在全量 SQL、质量检查和指标测试通过后发布。

## 实现范围与状态

| 状态 | 内容 |
|---|---|
| 已完成 | 工程地基、分析框架、数据契约、指标字典、CLI 接口、测试与 CI |
| 下一步 | 导入全量 CSV，建设 `meta/raw/stg/core/mart` 五层 DuckDB 数据仓库 |
| 后续计划 | 在真实数据上实现指标、看板、运营洞察与验证方案 |

## 数据与边界

正式分析使用 [Retailrocket ecommerce dataset](https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset)：

- `events.csv`：2,756,101 条匿名访客行为事件；
- 两份 `item_properties`：合计 20,275,902 条商品属性历史；
- `category_tree.csv`：1,669 条分类关系；
- 解压 CSV 合计约 987.5 MB，原始数据只保存在本地，不上传 GitHub。

关键解释边界：

- “新增”仅指观察窗口内首次出现的访客，不等同于注册用户；
- 订单数使用唯一 `transactionid`，不能用交易事件行数代替；
- 只有 `categoryid`、`available` 可以直接解释，其他商品属性保持匿名；
- 数据没有真实金额、渠道成本或实验分组，因此不计算真实 GMV、AOV、CAC、ROAS 或 LTV；
- 仓库内教学样例只用于字段学习，不参与正式指标或业务结论。

数据与衍生物遵循 [CC BY-NC-SA 4.0](docs/DATA_LICENSE.md)。

## 技术架构

```mermaid
flowchart LR
    A["全量 CSV"] --> B["DuckDB 五层模型"]
    C["Python CLI"] --> B
    B --> D["SQL 指标集市"]
    D --> E["Streamlit / Plotly"]
    D --> F["聚合结果导出"]
    G["GitHub Actions"] --> H["测试 / PR / Release"]
```

- **DuckDB SQL**：负责大表连接、会话化、时态属性关联和指标聚合；
- **Python**：负责配置、流程编排、质量检查、统计检验和导出；
- **Streamlit + Plotly**：读取聚合结果并展示分析、策略与验证方案；
- **GitHub Actions**：执行代码、SQL、CLI、测试和敏感文件检查。

SQL 是指标公式的唯一来源，Python 不重复维护第二套指标口径。

## 当前版本运行

要求 Python 3.12。安装依赖：

```powershell
python -m pip install -r requirements-dev.txt
```

查看 CLI：

```powershell
python -m product_ops --help
```

启动当前占位页面：

```powershell
python -m streamlit run app/streamlit_app.py
```

> `v0.1.0` 的 CLI 和页面是安全占位接口，不读取全量 CSV，也不生成正式指标。

运行验证：

```powershell
python -m pip check
python -m ruff check src tests app
python -m pytest
python -m sqlfluff lint sql --ignore-local-config --config .sqlfluff
```

## 文档与许可

- [数据契约](docs/DATA_CONTRACT.md)：字段、表关系和质量规则；
- [运营指标字典](docs/METRIC_DICTIONARY.md)：指标公式、粒度和限制；
- [项目计划](docs/PROJECT_PLAN.md)与[当前进度](docs/PROGRESS.md)；
- [`v0.1.0` Release](https://github.com/Guzdey/product-ops-growth-analytics/releases/tag/v0.1.0)；
- 原创代码采用 [MIT License](LICENSE)，Retailrocket 数据不属于 MIT 授权范围。
