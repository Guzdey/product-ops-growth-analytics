# 运营指标字典

## 1. 使用原则

- 本文件定义指标口径；`v0.3.0` 可执行 SQL 是公式唯一事实来源。
- 真实数据核心指标已通过确定性 Fixture 和官方全量数据验证；完整结果见
  [`V0.3_METRICS_REPORT.md`](V0.3_METRICS_REPORT.md)。
- 真实数据指标标记 `real`；`synthetic` 指标只能来自 `v0.5.0` 独立模拟模块。
- 时间默认 UTC。访客“首次”只表示数据观察窗口内首次出现，不代表注册。
- 留存必须排除没有完整观察窗口的 Cohort，不能把尚不可观察当作未留存。
- 比率同时输出分子、分母和样本门槛；小样本结论必须标记。

## 2. 字段模板

每个可执行指标记录以下元数据：

| 字段 | 含义 |
|---|---|
| `metric_id` | 稳定英文标识 |
| `metric_name_cn` | 中文展示名称 |
| `business_question` | 指标回答的运营问题 |
| `formula` | 明确分子、分母和去重规则 |
| `grain` | 日期、会话、访客、交易、商品或品类粒度 |
| `window` | 观察或滚动时间窗 |
| `data_origin` | `real` 或 `synthetic` |
| `limitations` | 右截断、匿名字段、样本量等限制 |
| `status` | `planned`、`implemented`、`validated` |

## 3. 真实数据核心指标

| `metric_id` | 中文名称 | 公式/口径 | 粒度或窗口 | 主要用途 | 状态 |
|---|---|---|---|---|---|
| `daily_active_visitors` | 日活访客 DAU | 当日 `COUNT(DISTINCT visitorid)` | 日 | 流量规模趋势 | validated |
| `rolling_7d_active_visitors` | 滚动 WAU | 当日及前 6 日窗口内去重访客 | 日/7日 | 短周期活跃 | validated |
| `rolling_30d_active_visitors` | 滚动 MAU | 当日及前 29 日窗口内去重访客 | 日/30日 | 中周期活跃 | validated |
| `dau_mau_stickiness` | 活跃粘性 | `DAU / rolling_30d_active_visitors` | 日 | 访问频率，不等同产品注册粘性 | validated |
| `first_observed_visitors` | 首次观察访客 | 首次事件日期等于统计日的去重访客 | 日 | 观察窗口内新出现规模 | validated |
| `returning_visitors` | 回访访客 | 当日活跃且首个事件早于当日 | 日 | 回访规模 | validated |
| `session_count` | 会话数 | 30 分钟规则生成的唯一 `session_id` | 日 | 使用频次 | validated |
| `events_per_session` | 每会话事件数 | `event_count / session_count`，同时报告中位数/P75 | 日/会话 | 参与深度 | validated |
| `items_per_session` | 每会话商品数 | 每会话 `COUNT(DISTINCT itemid)`，汇总中位数/P75 | 会话 | 探索广度 | validated |
| `session_duration_seconds` | 会话时长 | `max(event_time)-min(event_time)`，报告中位数/P75 | 会话 | 决策过程；单事件会话为 0 | validated |
| `behavior_coverage_rate` | 行为覆盖率 | 发生某行为的会话 / 全部合格会话 | 会话 | 描述行为覆盖，不代表顺序转化 | validated |
| `ordered_view_to_cart_rate` | 浏览到加购率 | 同一会话存在 `addtocart_time > view_time` 的会话 / 有浏览会话 | 会话 | 定位浏览到意向流失 | validated |
| `ordered_cart_to_purchase_rate` | 加购到购买率 | 同一会话在有效加购后发生交易的会话 / 有有效加购会话 | 会话 | 定位购物车流失 | validated |
| `ordered_view_to_purchase_rate` | 浏览到购买率 | 同一会话存在严格有序 `view → transaction` / 有浏览会话 | 会话 | 总体有序转化 | validated |
| `same_item_funnel_rate` | 同商品严格漏斗转化 | 同一 `visitorid + session_id + itemid` 严格完成各步骤 / 相应前序集合 | 会话商品 | 排除跨商品行为混合 | validated |
| `cart_abandonment_rate` | 购物车放弃率 | 有加购但其后无交易的会话 / 有加购会话 | 会话 | 识别加购未购人群 | validated |
| `median_step_latency` | 漏斗步骤耗时 | 严格匹配步骤时间差的中位数/P75 | 会话 | 判断决策周期 | validated |
| `retention_d1` | D1 活跃留存 | Cohort 首次出现后第 1 日仍活跃访客 / 可完整观察 D1 的 Cohort 访客 | Cohort | 短期回访 | validated |
| `retention_d3` | D3 活跃留存 | 同上，第 3 日 | Cohort | 短期回访 | validated |
| `retention_d7` | D7 活跃留存 | 同上，第 7 日 | Cohort | 周期留存 | validated |
| `retention_d14` | D14 活跃留存 | 同上，第 14 日 | Cohort | 中期留存 | validated |
| `retention_d30` | D30 活跃留存 | 同上，第 30 日 | Cohort | 长期留存；受 4.5 个月窗口影响 | validated |
| `purchasing_visitor_rate` | 购买访客率 | 有交易的去重访客 / 活跃去重访客 | 期间 | 衡量访客购买覆盖 | validated |
| `transaction_count` | 去重交易数 | `COUNT(DISTINCT transactionid)` | 日/期间 | 订单代理指标，不等于交易事件行数 | validated |
| `distinct_items_per_transaction` | 每交易不同商品数 | 每个交易的去重 `itemid`，汇总均值/中位数 | 交易 | 订单商品丰富度，无数量字段 | validated |
| `repeat_purchase_visitor_rate` | 复购访客率 | 至少 2 个不同交易的访客 / 至少 1 个交易的访客 | 期间 | 购买持续性 | validated |
| `repurchase_interval_days` | 复购间隔 | 同访客相邻唯一交易时间差，中位数/P75 | 访客 | 触达时机 | validated |
| `category_session_conversion_rate` | 品类会话转化率 | 品类内发生交易的去重会话 / 品类内浏览会话 | 品类 | 比较品类表现 | validated |
| `category_opportunity_score` | 品类机会规模 | 浏览会话数 × `max(0, 同级转化中位数-当前转化率)` | 品类 | 排序理论转化缺口，不等于真实新增订单 | validated |
| `item_property_coverage_rate` | 属性覆盖率 | 在事件时点能关联有效属性的事件 / 需关联事件 | 属性 | 数据完整性 | validated |
| `category_linkage_rate` | 分类关联率 | 可解析 `categoryid` 与分类树的商品事件 / 有分类商品事件 | 分类 | 分类分析可靠性 | validated |

### 留存汇总补充规则

总体 Dn 留存使用符合观察条件的 Cohort 留存人数之和除以对应 Cohort 初始人数之和，不直接平均各 Cohort 百分比。首购后复购率另行计算，不与活跃留存混称。

### 品类置信区间与门槛

- 仅对至少 200 个浏览会话的品类进入主机会榜单。
- 转化率报告 Wilson 95% 置信区间。
- `category_opportunity_score` 是用于排序的理论缺口，不声明为可实现订单提升。

## 4. 用户生命周期分群

| `segment_id` | 暂定定义 | 运营含义 | 状态 |
|---|---|---|---|
| `first_session_bounce` | 仅一个会话、无加购和交易 | 首访价值表达或内容匹配可能不足 | validated |
| `active_browser` | 至少两个会话但从未加购/交易 | 有兴趣、购买意向较弱 | validated |
| `cart_no_purchase` | 曾加购但观察窗内未交易 | 高意向挽回人群 | validated |
| `first_time_buyer` | 恰好一个唯一交易 | 首购承接和二购培育 | validated |
| `repeat_buyer` | 至少两个唯一交易 | 高价值维护与复购运营 | validated |
| `at_risk` | 多会话或购买访客，距观察期末至少 9 日未活跃 | 独立风险标签；9 日来自回访间隔 P75 向上取整 | validated |

## 5. 模拟数据指标（v0.5.0 后）

以下指标不得出现在真实 Retailrocket 结果中：

| `metric_id` | 中文名称 | 公式 | `data_origin` | 状态 |
|---|---|---|---|---|
| `click_through_rate` | 点击率 CTR | `clicks / impressions` | synthetic | planned |
| `campaign_conversion_rate` | 活动转化率 CVR | `conversions / clicks`，并同时提供曝光口径 | synthetic | planned |
| `customer_acquisition_cost` | 获客成本 CAC | `campaign_cost / acquired_customers` | synthetic | planned |
| `return_on_ad_spend` | 广告支出回报 ROAS | `attributed_revenue / campaign_cost` | synthetic | planned |
| `gross_merchandise_value` | 模拟 GMV | 模拟订单金额之和 | synthetic | planned |
| `average_order_value` | 模拟客单价 AOV | `simulated_gmv / distinct_transaction_count` | synthetic | planned |
| `absolute_uplift` | 绝对提升 | `treatment_rate - control_rate` | synthetic | planned |
| `relative_uplift` | 相对提升 | `(treatment_rate-control_rate)/control_rate` | synthetic | planned |

实验必须同时报告样本量、效应大小、95% 置信区间、p 值和护栏指标；统计显著不自动等于业务值得上线。
