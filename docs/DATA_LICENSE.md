# Retailrocket 数据来源与许可说明

## 1. 数据来源

- 数据集名称：Retailrocket ecommerce dataset
- 官方发布页面：<https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset>
- 本项目分析内容：匿名访客事件、商品属性历史和分类树
- 本项目本地数据位置：`D:\CodexData\product-ops-growth-analytics\raw`

项目不会把匿名 ID 反向识别为个人、商品名称、品牌或真实分类。

## 2. 数据许可

Retailrocket 数据页面标注许可为 **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International（CC BY-NC-SA 4.0）**：

- 许可全文：<https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode>
- 许可摘要：<https://creativecommons.org/licenses/by-nc-sa/4.0/>

使用该数据及其受许可约束的改编物时，应：

1. **署名（BY）**：注明 Retailrocket 数据集名称、官方来源链接和许可链接，并说明是否进行了清洗、聚合或派生。
2. **非商业（NC）**：不得把受许可数据用于许可不允许的商业用途；用途不明确时应由使用者自行核查或取得权利人许可。
3. **相同方式共享（SA）**：公开分发受许可约束的改编数据时，应在相同许可下提供。
4. **不增加额外限制**：不得施加阻止他人行使许可权利的法律或技术限制。

本说明用于项目的许可边界管理，不构成法律意见；再利用者应阅读官方许可全文并自行判断具体用途。

## 3. 本项目的公开策略

- GitHub 仓库不重新分发约 1 GB 的完整 CSV、原始 ZIP、DuckDB 或完整 Parquet。
- 使用者应从 Retailrocket 官方 Kaggle 页面自行取得数据，并按 `docs/DATA_CONTRACT.md` 放置。
- 公开展示只使用小型聚合结果、图表、截图和人工构造测试 Fixture；聚合/改编资产保留数据来源和 CC BY-NC-SA 4.0 标记。
- 如未来需要提交真实行级样例，必须先确认最小范围、必要性、许可兼容和无识别风险，并取得用户明确授权。
- 数据处理说明至少记录：时间转换、会话划分、去重交易、商品属性时点关联、聚合和任何过滤规则。

建议公开署名文本：

```text
Data source: Retailrocket ecommerce dataset, available on Kaggle.
Licensed under CC BY-NC-SA 4.0. This project transforms the source data
through validation, sessionization, time-aware joins, and aggregation.
```

## 4. 代码许可与数据许可分离

仓库原创代码采用根目录 `LICENSE` 中的 MIT License。MIT License 只覆盖本项目原创软件代码和明确标注为原创的文档，不覆盖：

- Retailrocket 原始数据；
- 受 Retailrocket 数据许可约束的改编数据或衍生数据资产；
- 第三方依赖、商标或其他权利人的内容。

代码的 MIT 授权不能改变或替代数据的 CC BY-NC-SA 4.0 条款。

## 5. 真实数据与模拟数据标记

- Retailrocket 派生指标使用 `data_origin='real'`，并引用本说明。
- `v0.5.0` 自行生成的渠道/实验数据使用 `data_origin='synthetic'` 和“模拟数据 / SIMULATED”标记。
- 模拟数据生成代码采用 MIT License；模拟输出不冒充 Retailrocket 官方字段或真实业务结果。

## 6. 发布前许可检查

- [ ] README 和看板保留数据集名称、官方链接与 CC BY-NC-SA 4.0 链接。
- [ ] Git 候选文件中没有完整原始数据、数据库或不必要的行级明细。
- [ ] 数据派生过程和修改已说明。
- [ ] 真实与模拟结果标记清楚。
- [ ] 代码 MIT 与数据 CC BY-NC-SA 4.0 的适用范围没有混写。
- [ ] 若用途或发布内容发生变化，已重新评估许可并取得必要授权。
