"""Six-page Streamlit dashboard for the Retailrocket operations portfolio."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Any

from product_ops.dashboard import (
    DashboardDataError,
    DashboardSource,
    filter_date_range,
    hypothesis_row,
    load_dashboard_tables,
    metric_row,
    resolve_dashboard_source,
)

COLORS = {
    "blue": "#2563EB",
    "dark_blue": "#1E3A8A",
    "orange": "#F59E0B",
    "red": "#DC2626",
    "green": "#16A34A",
    "slate": "#64748B",
    "light_blue": "#93C5FD",
}
PAGE_OPTIONS = (
    "01 管理摘要",
    "02 流量与活跃",
    "03 漏斗与路径",
    "04 留存与生命周期",
    "05 商品与品类",
    "06 数据质量",
)


def main(streamlit_module: Any | None = None) -> int:
    """Load verified aggregate exports and render the dashboard."""

    st = streamlit_module
    if st is None:
        try:
            import streamlit as st  # type: ignore[no-redef]
        except ModuleNotFoundError:
            sys.stderr.write(
                "Streamlit is not installed. Install dashboard dependencies, then run: "
                "python -m streamlit run app/streamlit_app.py\n"
            )
            return 1

    try:
        import pandas as pd
        import plotly.express as px
        import plotly.graph_objects as go

    except ModuleNotFoundError as exc:
        sys.stderr.write(
            "Dashboard dependencies or the local product_ops package are missing: "
            f"{exc}. Install requirements-dev.txt from the repository root.\n"
        )
        return 1

    st.set_page_config(
        page_title="Retailrocket 产品运营分析",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _apply_style(st)

    try:
        source = resolve_dashboard_source()

        @st.cache_data(show_spinner="正在读取已聚合的运营指标……")
        def load_cached(directory: str, mode: str, label: str) -> dict[str, pd.DataFrame]:
            snapshot = DashboardSource(
                directory=Path(directory),
                mode=mode,
                label=label,
                manifest=source.manifest,
            )
            return load_dashboard_tables(snapshot)

        tables = load_cached(str(source.directory), source.mode, source.label)
    except (DashboardDataError, OSError, ValueError) as exc:
        st.error(f"看板数据校验失败：{exc}")
        st.stop()
        return 1

    activity = tables["daily_activity"]
    min_date = min(activity["activity_date"])
    max_date = max(activity["activity_date"])

    with st.sidebar:
        st.title("运营分析导航")
        page = st.radio("选择页面", PAGE_OPTIONS, label_visibility="collapsed")
        st.divider()
        st.subheader("全局时间筛选")
        date_value = st.date_input(
            "分析日期（UTC）",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        start_date, end_date = _normalize_date_range(date_value, min_date, max_date)
        st.caption("时间筛选应用于日粒度活跃、会话和交易趋势。其他页面会注明其有效范围。")
        st.divider()
        st.caption(f"数据源：{source.label}")
        st.caption("数据标记：真实数据 / REAL · 时区：UTC")
        st.caption("指标由 DuckDB SQL 预计算；页面不扫描原始 CSV。")

    st.title("Retailrocket 用户增长与产品运营分析")
    st.caption(
        "观察期：2015-05-03 至 2015-09-18（UTC）｜匿名电商行为数据｜"
        "不包含金额、渠道、真实商品名或实验分组"
    )
    if source.mode == "bundled_snapshot":
        st.info(
            "当前使用官方完整数据计算得到的公开聚合快照。核心指标为全量结果；"
            "仅行为路径和商品明细榜单做了行数截取，不含访客级或交易级记录。"
        )

    renderers = {
        PAGE_OPTIONS[0]: _render_management,
        PAGE_OPTIONS[1]: _render_activity,
        PAGE_OPTIONS[2]: _render_funnel,
        PAGE_OPTIONS[3]: _render_retention,
        PAGE_OPTIONS[4]: _render_category,
        PAGE_OPTIONS[5]: _render_quality,
    }
    renderers[page](
        st,
        tables,
        start_date,
        end_date,
        pd_module=pd,
        px_module=px,
        go_module=go,
    )
    return 0


def _apply_style(st: Any) -> None:
    st.markdown(
        """
        <style>
        [data-testid="stMetric"] {
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 14px;
            background: #FFFFFF;
        }
        [data-testid="stMetricLabel"] { color: #475569; }
        [data-testid="stMetricValue"] { color: #0F172A; font-size: 1.55rem; }
        [data-testid="stMetricDelta"] { color: #15803D; }
        div[data-testid="stAlert"] { border-radius: 10px; }
        .block-container { padding-top: 2rem; padding-bottom: 3rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _normalize_date_range(value: Any, minimum: date, maximum: date) -> tuple[date, date]:
    if isinstance(value, (tuple, list)) and len(value) == 2:
        start_date, end_date = value
        return min(start_date, end_date), max(start_date, end_date)
    if isinstance(value, date):
        return value, value
    return minimum, maximum


def _render_management(
    st: Any,
    tables: dict[str, Any],
    start_date: date,
    end_date: date,
    **_: Any,
) -> None:
    st.header("01 管理摘要")
    st.caption("本页核心指标与三项预登记假设均为完整观察窗口结果，不受侧栏日期筛选影响。")

    transaction = tables["transaction_summary"].iloc[0]
    funnel = tables["funnel_summary"]
    retention = tables["retention_summary"]
    sessions = metric_row(funnel, "behavior_view_coverage", funnel_scope="session")
    d7 = retention.loc[
        (retention["first_session_segment"] == "all") & (retention["day_n"] == 7)
    ].iloc[0]

    columns = st.columns(5)
    columns[0].metric("合格活跃访客", f"{int(transaction['active_visitor_count']):,}")
    columns[1].metric("含浏览会话", f"{int(sessions['denominator_count']):,}")
    columns[2].metric("唯一交易", f"{int(transaction['transaction_count']):,}")
    columns[3].metric("购买访客率", _pct(transaction["purchasing_visitor_rate"], 2))
    columns[4].metric("D7 活跃留存", _pct(d7["weighted_retention_rate"], 2))

    st.subheader("预登记假设结果")
    hypotheses = tables["hypothesis_results"].copy()
    h_cols = st.columns(3)
    status_labels = {
        "H1": "未达到业务门槛",
        "H2": "支持",
        "H3": "支持",
    }
    for index, hypothesis_id in enumerate(("H1", "H2", "H3")):
        row = hypothesis_row(hypotheses, hypothesis_id)
        if hypothesis_id == "H2":
            effect_text = _pct(row["observed_effect"], 2)
            threshold_text = _pct(row["threshold"], 0)
        else:
            effect_text = _pp(row["observed_effect"])
            threshold_text = _pp(row["threshold"], 1)
        with h_cols[index]:
            st.markdown(f"**{hypothesis_id} · {status_labels[hypothesis_id]}**")
            st.metric("观察效应", effect_text)
            st.caption(f"预设门槛：{threshold_text}；{row['evidence_summary']}")

    _story_block(
        st,
        "故事 A｜浏览到加购是当前首要诊断环节",
        what="严格漏斗总流失中，浏览→加购贡献 98.52%，远高于 60% 的预设阈值。",
        so_what="资源优先级应放在意向形成之前，而不是先大规模优化支付末端。",
        now_what="按匿名品类、会话深度和时点可售状态继续拆分，定位高流量、低加购区域。",
        verify="以严格浏览→加购率为主指标，购买率与退出率为护栏；随机实验验证具体改版。",
    )
    _story_block(
        st,
        "故事 B｜加购未购人群值得测试，但不能夸大价值",
        what="该人群 D7 留存比仅浏览高 0.656 个百分点，未达到 5 个百分点业务门槛。",
        so_what="统计显著不等于运营收益足够大；不能直接声称召回该人群会带来增长。",
        now_what="只做低成本、小流量的提醒时机和内容实验，避免全量投入。",
        verify="随机分组比较 D7 回访与购买率，并监控退订或投诉等触达护栏。",
    )
    _story_block(
        st,
        "故事 C｜匿名品类 299 应进入人工诊断清单",
        what="该品类会话转化率比同父级合格品类中位数低 2.119 个百分点。",
        so_what="它是排查优先级信号，不代表已找到具体商品行业或因果原因。",
        now_what="核查可售状态、商品路径和样本稳定性，再决定是否设计品类实验。",
        verify="以同口径品类转化率为主指标，并观察 Wilson 区间与交易量护栏。",
    )


def _render_activity(
    st: Any,
    tables: dict[str, Any],
    start_date: date,
    end_date: date,
    *,
    pd_module: Any,
    px_module: Any,
    **_: Any,
) -> None:
    st.header("02 流量与活跃")
    st.caption(
        f"当前筛选：{start_date} 至 {end_date}（UTC），共 {(end_date - start_date).days + 1} 日。"
    )
    activity = filter_date_range(tables["daily_activity"], "activity_date", start_date, end_date)
    sessions = filter_date_range(
        tables["daily_session_metrics"], "activity_date", start_date, end_date
    )
    transactions = filter_date_range(
        tables["transaction_daily"], "transaction_date", start_date, end_date
    )
    if activity.empty:
        st.warning("当前日期范围没有可展示的活跃数据，请扩大筛选范围。")
        return

    columns = st.columns(4)
    columns[0].metric("日均活跃访客", f"{activity['daily_active_visitors'].mean():,.0f}")
    peak = activity.loc[activity["daily_active_visitors"].idxmax()]
    columns[1].metric(
        "DAU 峰值", f"{int(peak['daily_active_visitors']):,}", str(peak["activity_date"])
    )
    columns[2].metric("会话数", f"{int(sessions['session_count'].sum()):,}")
    columns[3].metric("唯一交易", f"{int(transactions['transaction_count'].sum()):,}")

    active_long = activity.melt(
        id_vars="activity_date",
        value_vars=[
            "daily_active_visitors",
            "rolling_7d_active_visitors",
            "rolling_30d_active_visitors",
        ],
        var_name="指标",
        value_name="访客数",
    )
    active_long["指标"] = active_long["指标"].map(
        {
            "daily_active_visitors": "DAU",
            "rolling_7d_active_visitors": "滚动 7 日活跃",
            "rolling_30d_active_visitors": "滚动 30 日活跃",
        }
    )
    figure = px_module.line(
        active_long,
        x="activity_date",
        y="访客数",
        color="指标",
        title="活跃访客趋势",
        color_discrete_sequence=[COLORS["blue"], COLORS["light_blue"], COLORS["dark_blue"]],
    )
    _finish_figure(figure, y_title="去重匿名访客数")
    st.plotly_chart(figure, width="stretch")

    left, right = st.columns(2)
    first_return = activity.melt(
        id_vars="activity_date",
        value_vars=["first_observed_visitors", "returning_visitors"],
        var_name="访客类型",
        value_name="访客数",
    )
    first_return["访客类型"] = first_return["访客类型"].map(
        {"first_observed_visitors": "首次观察", "returning_visitors": "回访"}
    )
    figure = px_module.area(
        first_return,
        x="activity_date",
        y="访客数",
        color="访客类型",
        title="首次观察与回访访客",
        color_discrete_sequence=[COLORS["light_blue"], COLORS["blue"]],
    )
    _finish_figure(figure, y_title="去重匿名访客数")
    left.plotly_chart(figure, width="stretch")

    session_long = sessions.melt(
        id_vars="activity_date",
        value_vars=["average_events_per_session", "average_items_per_session"],
        var_name="指标",
        value_name="平均值",
    )
    session_long["指标"] = session_long["指标"].map(
        {"average_events_per_session": "每会话事件数", "average_items_per_session": "每会话商品数"}
    )
    figure = px_module.line(
        session_long,
        x="activity_date",
        y="平均值",
        color="指标",
        title="会话深度趋势",
        color_discrete_sequence=[COLORS["blue"], COLORS["orange"]],
    )
    _finish_figure(figure, y_title="平均值")
    right.plotly_chart(figure, width="stretch")

    _story_block(
        st,
        "如何使用这页",
        what="观察流量规模、回访构成与会话深度是否同步变化。",
        so_what="活跃增长若没有回访或深度支撑，可能只是一次性流量，而非稳定用户价值。",
        now_what="优先标记异常日期，再回到漏斗、留存或品类页寻找结构性变化。",
        verify="日期趋势只用于发现线索；还需控制品类与用户结构，并通过实验验证运营动作。",
    )


def _render_funnel(
    st: Any,
    tables: dict[str, Any],
    start_date: date,
    end_date: date,
    *,
    px_module: Any,
    **_: Any,
) -> None:
    st.header("03 漏斗与路径")
    st.caption("漏斗为完整观察窗口的严格有序会话结果；当前版本不按侧栏日期重算。")
    funnel = tables["funnel_summary"].copy()
    ordered_ids = ["ordered_view_to_cart_rate", "ordered_cart_to_purchase_rate"]
    ordered = (
        funnel.loc[funnel["funnel_scope"] == "session"]
        .set_index("metric_id")
        .loc[ordered_ids]
        .reset_index()
    )
    ordered["步骤"] = ["浏览 → 加购", "加购 → 购买"]
    ordered["转化率"] = ordered["metric_rate"]

    columns = st.columns(4)
    columns[0].metric("浏览→加购", _pct(ordered.iloc[0]["metric_rate"], 2))
    columns[1].metric("加购→购买", _pct(ordered.iloc[1]["metric_rate"], 2))
    abandonment = metric_row(funnel, "cart_abandonment_rate", funnel_scope="session")
    columns[2].metric("加购未购率", _pct(abandonment["metric_rate"], 2))
    view_to_purchase = metric_row(
        funnel,
        "ordered_view_to_purchase_rate",
        funnel_scope="session",
    )
    columns[3].metric("浏览→购买", _pct(view_to_purchase["metric_rate"], 2))

    left, right = st.columns(2)
    figure = px_module.bar(
        ordered,
        x="步骤",
        y="转化率",
        text=ordered["转化率"].map(lambda value: _pct(value, 2)),
        title="严格有序会话转化率",
        color="步骤",
        color_discrete_sequence=[COLORS["blue"], COLORS["orange"]],
    )
    figure.update_yaxes(range=[0, max(0.35, ordered["转化率"].max() * 1.2)], tickformat=".0%")
    _finish_figure(figure, y_title="转化率", show_legend=False)
    left.plotly_chart(figure, width="stretch")

    dropoff = ordered.assign(流失会话=ordered["dropoff_count"])
    figure = px_module.bar(
        dropoff,
        x="流失会话",
        y="步骤",
        orientation="h",
        text="流失会话",
        title="两步严格漏斗流失量",
        color_discrete_sequence=[COLORS["orange"]],
    )
    figure.update_xaxes(rangemode="tozero")
    _finish_figure(figure, x_title="流失会话数", y_title="")
    right.plotly_chart(figure, width="stretch")

    left, right = st.columns(2)
    latency = tables["funnel_latency_summary"].copy()
    latency["步骤"] = latency["funnel_step"].map(
        {
            "view_to_cart": "浏览→加购",
            "cart_to_transaction": "加购→购买",
            "view_to_transaction": "浏览→购买",
        }
    )
    latency_long = latency.melt(
        id_vars="步骤",
        value_vars=["median_latency_seconds", "p75_latency_seconds"],
        var_name="分位数",
        value_name="耗时（秒）",
    )
    latency_long["分位数"] = latency_long["分位数"].map(
        {"median_latency_seconds": "中位数", "p75_latency_seconds": "P75"}
    )
    figure = px_module.bar(
        latency_long,
        x="步骤",
        y="耗时（秒）",
        color="分位数",
        barmode="group",
        title="完成漏斗步骤的耗时",
        color_discrete_sequence=[COLORS["blue"], COLORS["light_blue"]],
    )
    figure.update_yaxes(rangemode="tozero")
    _finish_figure(figure, y_title="耗时（秒）")
    left.plotly_chart(figure, width="stretch")

    path_count = right.slider("展示前 N 条行为路径", 5, 25, 10)
    paths = tables["session_path_summary"].nlargest(path_count, "session_count").copy()
    paths = paths.sort_values("session_count")
    figure = px_module.bar(
        paths,
        x="session_count",
        y="event_path",
        orientation="h",
        title=f"最常见的 {path_count} 条会话路径",
        color_discrete_sequence=[COLORS["blue"]],
    )
    figure.update_xaxes(rangemode="tozero")
    _finish_figure(figure, x_title="会话数", y_title="行为路径")
    right.plotly_chart(figure, width="stretch")

    h2 = hypothesis_row(tables["hypothesis_results"], "H2")
    _story_block(
        st,
        "运营结论｜先诊断浏览到加购",
        what=f"该步骤贡献 {_pct(h2['observed_effect'], 2)} 的严格漏斗总流失。",
        so_what="这是优化优先级证据，但没有页面曝光、搜索词与真实价格，尚不能判断具体原因。",
        now_what="按品类、可售状态和会话深度形成问题清单，先做高流量区域的定性检查。",
        verify="实验主指标为严格浏览→加购率；购买率和退出率作为护栏，避免只把按钮点得更多。",
    )


def _render_retention(
    st: Any,
    tables: dict[str, Any],
    start_date: date,
    end_date: date,
    *,
    px_module: Any,
    go_module: Any,
    **_: Any,
) -> None:
    st.header("04 留存与生命周期")
    st.caption("留存使用可完整观察相应天数的 Cohort，避免把观察期不足者误判为流失。")
    summary = tables["retention_summary"].copy()
    segment_labels = {
        "all": "全部访客",
        "browse_only": "首会话仅浏览",
        "cart_no_purchase": "首会话加购未购",
        "first_session_purchase": "首会话购买",
    }
    available_segments = [
        value for value in segment_labels if value in set(summary["first_session_segment"])
    ]
    selected = st.multiselect(
        "首会话分群",
        available_segments,
        default=available_segments,
        format_func=lambda value: segment_labels[value],
    )
    selected_summary = summary.loc[summary["first_session_segment"].isin(selected)].copy()
    selected_summary["分群"] = selected_summary["first_session_segment"].map(segment_labels)

    if selected_summary.empty:
        st.warning("至少选择一个首会话分群。")
    else:
        figure = px_module.line(
            selected_summary,
            x="day_n",
            y="weighted_retention_rate",
            color="分群",
            markers=True,
            title="D1 / D3 / D7 / D14 / D30 活跃留存",
            color_discrete_sequence=[
                COLORS["dark_blue"],
                COLORS["slate"],
                COLORS["orange"],
                COLORS["green"],
            ],
        )
        figure.update_yaxes(rangemode="tozero", tickformat=".1%")
        _finish_figure(figure, x_title="距首次观察天数", y_title="加权留存率")
        st.plotly_chart(figure, width="stretch")

    left, right = st.columns([1.4, 1])
    weekly = tables["retention_cohort_weekly"].copy()
    weeks = sorted(weekly["cohort_week"].unique())
    if weeks:
        default_start = weeks[max(0, len(weeks) - 12)]
        selected_weeks = left.slider(
            "Cohort 周范围",
            min_value=weeks[0],
            max_value=weeks[-1],
            value=(default_start, weeks[-1]),
        )
        weekly = weekly.loc[
            (weekly["cohort_week"] >= selected_weeks[0])
            & (weekly["cohort_week"] <= selected_weeks[1])
        ]
    pivot = weekly.pivot(
        index="cohort_week", columns="week_number", values="retention_rate"
    ).sort_index()
    heatmap = go_module.Figure(
        data=go_module.Heatmap(
            z=pivot.values,
            x=[f"W{int(value)}" for value in pivot.columns],
            y=[str(value) for value in pivot.index],
            colorscale=[[0, "#EFF6FF"], [1, COLORS["blue"]]],
            colorbar={"title": "留存率", "tickformat": ".1%"},
            hovertemplate="Cohort %{y}<br>%{x}: %{z:.2%}<extra></extra>",
        )
    )
    heatmap.update_layout(title="周 Cohort 留存热力图", height=430)
    _finish_figure(heatmap, x_title="首次观察后周数", y_title="Cohort 周")
    left.plotly_chart(heatmap, width="stretch")

    lifecycle = tables["lifecycle_segment_summary"].copy()
    lifecycle_labels = {
        "first_session_bounce": "首次会话跳失",
        "active_browser": "活跃浏览未加购",
        "cart_no_purchase": "加购未购",
        "first_time_buyer": "首次购买",
        "repeat_buyer": "重复购买",
    }
    lifecycle["生命周期"] = lifecycle["lifecycle_segment"].map(lifecycle_labels)
    lifecycle = lifecycle.sort_values("visitor_count")
    figure = px_module.bar(
        lifecycle,
        x="visitor_count",
        y="生命周期",
        orientation="h",
        text=lifecycle["visitor_share"].map(lambda value: _pct(value, 1)),
        title="生命周期分群规模",
        color_discrete_sequence=[COLORS["blue"]],
    )
    figure.update_xaxes(rangemode="tozero")
    _finish_figure(figure, x_title="访客数", y_title="")
    right.plotly_chart(figure, width="stretch")

    h1 = hypothesis_row(tables["hypothesis_results"], "H1")
    _story_block(
        st,
        "运营结论｜召回人群适合小规模实验",
        what=(
            f"加购未购相对仅浏览的 D7 留存差异为 {_pp(h1['observed_effect'])}，"
            f"95% 区间 {_pp(h1['confidence_low_95'])}–{_pp(h1['confidence_high_95'])}。"
        ),
        so_what=f"差异未达到 {_pp(h1['threshold'], 1)} 的业务门槛，统计显著也不能替代收益判断。",
        now_what="用低成本触达测试提醒时机与内容，不建议直接对全部加购未购访客长期投放。",
        verify="随机分组比较 D7 回访与购买率；触达频率、退订和负反馈作为护栏。",
    )


def _render_category(
    st: Any,
    tables: dict[str, Any],
    start_date: date,
    end_date: date,
    *,
    px_module: Any,
    **_: Any,
) -> None:
    st.header("05 商品与品类")
    st.caption("品类和商品 ID 均为匿名编码；本页不得把匿名属性解释成价格、品牌或商品名称。")
    categories = tables["category_performance"].copy()
    valid_roots = sorted(int(value) for value in categories["root_categoryid"].dropna().unique())
    controls = st.columns(3)
    root_choice = controls[0].selectbox("根品类", ["全部"] + valid_roots)
    max_views = int(categories["view_session_count"].max())
    min_views = controls[1].number_input(
        "最少浏览会话数", min_value=0, max_value=max_views, value=500, step=100
    )
    opportunity_only = controls[2].checkbox("只看机会候选", value=False)

    filtered = categories.loc[categories["view_session_count"] >= min_views].copy()
    if root_choice != "全部":
        filtered = filtered.loc[filtered["root_categoryid"] == root_choice]
    if opportunity_only:
        filtered = filtered.loc[
            filtered["is_opportunity_candidate"].astype(str).str.lower() == "true"
        ]

    if filtered.empty:
        st.warning("当前筛选没有品类，请降低最少浏览会话数或取消机会候选限制。")
        return

    filtered["诊断标记"] = filtered["categoryid"].map(
        lambda value: "重点：299" if int(value) == 299 else "其他品类"
    )
    figure = px_module.scatter(
        filtered,
        x="view_session_count",
        y="session_conversion_rate",
        size="distinct_transaction_count",
        color="诊断标记",
        hover_name=filtered["categoryid"].map(lambda value: f"品类 {int(value)}"),
        hover_data={
            "view_session_count": ":,",
            "session_conversion_rate": ":.2%",
            "sibling_conversion_gap": ":.2%",
            "distinct_transaction_count": ":,",
        },
        log_x=True,
        title="品类流量与会话转化率",
        color_discrete_map={"重点：299": COLORS["orange"], "其他品类": COLORS["blue"]},
    )
    figure.update_yaxes(rangemode="tozero", tickformat=".1%")
    _finish_figure(figure, x_title="浏览会话数（对数刻度）", y_title="会话转化率")
    st.plotly_chart(figure, width="stretch")

    left, right = st.columns([1, 1.2])
    opportunities = filtered.nlargest(12, "category_opportunity_score").sort_values(
        "category_opportunity_score"
    )
    opportunities["品类"] = opportunities["categoryid"].map(lambda value: f"品类 {int(value)}")
    figure = px_module.bar(
        opportunities,
        x="category_opportunity_score",
        y="品类",
        orientation="h",
        title="机会分数排行（仅用于诊断排序）",
        color_discrete_sequence=[COLORS["orange"]],
    )
    figure.update_xaxes(rangemode="tozero")
    _finish_figure(figure, x_title="机会分数", y_title="")
    left.plotly_chart(figure, width="stretch")

    display_columns = [
        "categoryid",
        "parentid",
        "view_session_count",
        "cart_session_count",
        "converted_session_count",
        "session_conversion_rate",
        "conversion_wilson_low_95",
        "conversion_wilson_high_95",
        "sibling_conversion_gap",
        "is_opportunity_candidate",
    ]
    detail = filtered.nlargest(20, "view_session_count")[display_columns].rename(
        columns={
            "categoryid": "品类 ID",
            "parentid": "父品类 ID",
            "view_session_count": "浏览会话",
            "cart_session_count": "加购会话",
            "converted_session_count": "转化会话",
            "session_conversion_rate": "会话转化率",
            "conversion_wilson_low_95": "Wilson 下界",
            "conversion_wilson_high_95": "Wilson 上界",
            "sibling_conversion_gap": "同级转化差距",
            "is_opportunity_candidate": "机会候选",
        }
    )
    right.markdown("**高流量品类明细**")
    right.dataframe(
        detail.style.format(
            {
                "会话转化率": "{:.2%}",
                "Wilson 下界": "{:.2%}",
                "Wilson 上界": "{:.2%}",
                "同级转化差距": "{:.2%}",
            }
        ),
        width="stretch",
        hide_index=True,
    )

    st.subheader("匿名商品表现")
    st.caption(
        "商品表同样是会话级聚合结果，不含访客、交易或会话明细 ID。公开快照只保留展示性排行。"
    )
    items = tables["item_performance"].copy()
    category_ids = set(filtered["categoryid"])
    items = items.loc[items["categoryid"].isin(category_ids)]
    if items.empty:
        st.info("当前品类筛选在公开商品排行中没有记录；完整本地聚合导出可能仍有对应商品。")
    else:
        item_detail = items.nlargest(20, "view_session_count")[
            [
                "itemid",
                "categoryid",
                "view_session_count",
                "cart_session_count",
                "transaction_session_count",
                "ordered_view_to_cart_rate",
                "ordered_cart_to_purchase_rate",
            ]
        ].rename(
            columns={
                "itemid": "商品 ID",
                "categoryid": "品类 ID",
                "view_session_count": "浏览会话",
                "cart_session_count": "加购会话",
                "transaction_session_count": "交易会话",
                "ordered_view_to_cart_rate": "浏览→加购率",
                "ordered_cart_to_purchase_rate": "加购→购买率",
            }
        )
        st.dataframe(
            item_detail.style.format({"浏览→加购率": "{:.2%}", "加购→购买率": "{:.2%}"}),
            width="stretch",
            hide_index=True,
        )

    h3 = hypothesis_row(tables["hypothesis_results"], "H3")
    focus = categories.loc[categories["categoryid"] == 299].iloc[0]
    focus_conversion = _pct(focus["session_conversion_rate"], 3)
    _story_block(
        st,
        "运营结论｜品类 299 进入人工诊断清单",
        what=(
            f"982 个浏览会话中有 11 个同品类转化会话，转化率 {focus_conversion}；"
            f"低于同父级中位数 {_pp(h3['observed_effect'])}。"
        ),
        so_what="该差距超过 2 个百分点门槛，但分类匿名且区间较宽，只能说明需要进一步排查。",
        now_what="查看时点可售状态、路径和商品构成；有业务语义后再设计陈列或信息实验。",
        verify="追踪同口径会话转化率和 Wilson 区间；以交易量与相邻品类表现为护栏。",
    )


def _render_quality(
    st: Any,
    tables: dict[str, Any],
    start_date: date,
    end_date: date,
    *,
    px_module: Any,
    **_: Any,
) -> None:
    st.header("06 数据质量")
    st.caption("质量指标为完整观察窗口结果；异常行在原始层保留，只在正式指标分母中按规则排除。")
    quality = tables["data_quality_summary"].copy()
    quality_labels = {
        "item_category_property_coverage_rate": "事件时点品类属性覆盖",
        "item_availability_property_coverage_rate": "事件时点可售属性覆盖",
        "item_property_coverage_rate": "任一可解释属性覆盖",
        "category_linkage_rate": "有效品类树关联",
        "excluded_exact_duplicate_event_rate": "完全重复事件排除",
        "excluded_invalid_event_rate": "非法事件排除",
    }
    quality["质量指标"] = quality["metric_id"].map(quality_labels)
    quality["指标组"] = quality["metric_id"].map(
        lambda value: "覆盖率" if "coverage" in value or "linkage" in value else "排除率"
    )

    duplicate = metric_row(quality, "excluded_exact_duplicate_event_rate")
    linkage = metric_row(quality, "category_linkage_rate")
    property_coverage = metric_row(quality, "item_property_coverage_rate")
    columns = st.columns(4)
    columns[0].metric("原始事件", f"{int(duplicate['denominator_count']):,}")
    columns[1].metric(
        "重复事件标记", f"{int(duplicate['numerator_count']):,}", _pct(duplicate["metric_rate"], 3)
    )
    columns[2].metric("属性覆盖率", _pct(property_coverage["metric_rate"], 2))
    columns[3].metric("分类树关联率", _pct(linkage["metric_rate"], 2))

    coverage = quality.loc[quality["指标组"] == "覆盖率"].copy()
    figure = px_module.bar(
        coverage,
        x="metric_rate",
        y="质量指标",
        orientation="h",
        text=coverage["metric_rate"].map(lambda value: _pct(value, 2)),
        title="属性与分类关联覆盖率",
        color_discrete_sequence=[COLORS["blue"]],
    )
    figure.update_xaxes(range=[0, 1], tickformat=".0%")
    _finish_figure(figure, x_title="覆盖率", y_title="")
    st.plotly_chart(figure, width="stretch")

    left, right = st.columns(2)
    anomalies = tables["funnel_anomaly_summary"].copy()
    anomaly_labels = {
        "cart_before_view": "会话内加购早于浏览",
        "transaction_before_cart": "会话内交易早于加购",
        "transaction_without_cart": "有交易但无加购",
    }
    anomalies["异常类型"] = (
        anomalies["anomaly_id"].map(anomaly_labels).fillna(anomalies["anomaly_id"])
    )
    left.markdown("**漏斗顺序异常监控**")
    left.dataframe(
        anomalies[["异常类型", "anomaly_count", "reference_count", "anomaly_rate"]]
        .rename(
            columns={
                "anomaly_count": "异常数",
                "reference_count": "参考总数",
                "anomaly_rate": "异常率",
            }
        )
        .style.format({"异常率": "{:.3%}"}),
        width="stretch",
        hide_index=True,
    )
    with right.container(border=True):
        st.markdown("**解释边界**")
        st.markdown(
            "- 没有注册时间，首次观察不等于新注册。\n"
            "- 没有价格和金额，不计算 GMV、AOV 或 LTV。\n"
            "- 没有渠道和成本，不计算 CAC 或 ROAS。\n"
            "- 没有实验分组，描述性差异不解释为因果。\n"
            "- 匿名属性不命名为品牌、价格或真实商品名。"
        )

    _story_block(
        st,
        "如何使用这页",
        what="确认指标分母、属性覆盖和漏斗顺序异常是否足以支持业务解释。",
        so_what="数据质量不是附录：覆盖缺失或口径错误会直接改变运营优先级。",
        now_what="发现异常时回到 stg/core 层定位，不静默删除原始记录，也不弱化质量门禁。",
        verify="固定行数、幂等性、会话边界、交易去重和属性时点测试，并保留每次运行证据。",
    )


def _story_block(
    st: Any,
    title: str,
    *,
    what: str,
    so_what: str,
    now_what: str,
    verify: str,
) -> None:
    st.subheader(title)
    columns = st.columns(4)
    sections = (
        ("What｜发现", what),
        ("So What｜意义", so_what),
        ("Now What｜动作", now_what),
        ("How to Verify｜验证", verify),
    )
    for column, (heading, body) in zip(columns, sections, strict=True):
        with column.container(border=True):
            st.markdown(f"**{heading}**")
            st.write(body)


def _finish_figure(
    figure: Any,
    *,
    x_title: str | None = None,
    y_title: str | None = None,
    show_legend: bool = True,
) -> None:
    figure.update_layout(
        template="plotly_white",
        height=390,
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
        legend_title_text="",
        showlegend=show_legend,
        hoverlabel={"bgcolor": "white"},
    )
    if x_title is not None:
        figure.update_xaxes(title=x_title)
    if y_title is not None:
        figure.update_yaxes(title=y_title)


def _pct(value: Any, decimals: int = 1) -> str:
    return f"{float(value):.{decimals}%}"


def _pp(value: Any, decimals: int = 3) -> str:
    return f"{float(value) * 100:.{decimals}f} 个百分点"


if __name__ == "__main__":
    main()
