# Streamlit 运营看板

`streamlit_app.py` 读取 SQL 已经计算完成的聚合指标，不扫描 Retailrocket 原始 CSV，也不在
页面中重新定义指标公式。

## 六个页面

1. 管理摘要：核心 KPI、三项预登记假设和三条运营故事；
2. 流量与活跃：DAU、滚动活跃、首次观察/回访结构、会话深度和交易趋势；
3. 漏斗与路径：严格有序漏斗、流失量、转化耗时和常见会话路径；
4. 留存与生命周期：D1/D3/D7/D14/D30 留存、周 Cohort 热力图和生命周期分群；
5. 商品与品类：匿名品类的流量、转化区间、同级差距和机会排序；
6. 数据质量：属性覆盖、重复/非法事件和漏斗顺序异常。

每个业务页面按 `What / So What / Now What / How to Verify` 组织，区分数据发现、业务意义、
运营动作和验证方法。

## 数据来源模式

- 本机存在 `D:\CodexData\product-ops-growth-analytics\exports\v0.3.0` 时，默认读取完整的
  17 张聚合导出表；
- 没有 D 盘导出时，自动读取仓库内 `demo_data/v0.4.0`。该目录仍是官方完整数据计算得到的
  真实聚合快照，只截取了高基数的路径与商品排行，不含访客级或交易级记录；
- 可用 `PRODUCT_OPS_DASHBOARD_EXPORT_DIR` 指定另一份通过相同数据契约的聚合导出。

桌面教学小样例不是看板输入。真实数据和后续 `v0.5.0` 模拟实验也不会混合计算。

## 启动

在仓库根目录执行：

```powershell
& 'D:\CodexData\product-ops-growth-analytics\envs\product-ops-growth-analytics\Scripts\python.exe' `
  -m streamlit run app/streamlit_app.py
```

也可以使用已经安装项目依赖的 Python：

```powershell
python -m streamlit run app/streamlit_app.py
```

如需强制检查公开聚合快照：

```powershell
$env:PRODUCT_OPS_DASHBOARD_EXPORT_DIR = (Resolve-Path 'demo_data/v0.4.0').Path
python -m streamlit run app/streamlit_app.py
```

## 更新公开聚合快照

完成 `v0.3.0` 指标导出后运行：

```powershell
python tools/build_dashboard_snapshot.py
```

生成脚本会记录源运行 ID、选取规则、行数、大小与 SHA-256，并阻止访客 ID、交易 ID 或
会话 ID 进入公开快照。
