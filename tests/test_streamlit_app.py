"""Streamlit AppTest coverage for six real pages and one simulated page."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from streamlit.testing.v1 import AppTest

from product_ops.dashboard import bundled_snapshot_directory

APP_PATH = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"


def _start_app(monkeypatch) -> AppTest:
    monkeypatch.setenv("PRODUCT_OPS_DASHBOARD_EXPORT_DIR", str(bundled_snapshot_directory()))
    return AppTest.from_file(APP_PATH).run(timeout=30)


def test_streamlit_management_page_uses_real_aggregate_snapshot(monkeypatch) -> None:
    app = _start_app(monkeypatch)

    assert not app.exception
    assert app.title[0].value == "Retailrocket 用户增长与产品运营分析"
    assert app.header[0].value == "01 管理摘要"
    assert len(app.sidebar.radio[0].options) == 7
    rendered_info = " ".join(item.value for item in app.info)
    assert "公开聚合快照" in rendered_info
    assert "不含访客级或交易级记录" in rendered_info
    assert any(item.label == "唯一交易" and item.value == "17,672" for item in app.metric)


def test_streamlit_all_pages_render_without_exceptions(monkeypatch) -> None:
    app = _start_app(monkeypatch)
    expected_headers = {
        "02 流量与活跃",
        "03 漏斗与路径",
        "04 留存与生命周期",
        "05 商品与品类",
        "06 数据质量",
        "07 模拟增长实验 / SIMULATED",
    }

    for page in expected_headers:
        app.sidebar.radio[0].set_value(page)
        app.run(timeout=30)
        assert not app.exception, page
        assert any(header.value == page for header in app.header)


def test_streamlit_filters_update_activity_and_retention(monkeypatch) -> None:
    app = _start_app(monkeypatch)
    app.sidebar.radio[0].set_value("02 流量与活跃")
    app.sidebar.date_input[0].set_value((date(2015, 7, 1), date(2015, 7, 31)))
    app.run(timeout=30)

    assert not app.exception
    assert any("共 31 日" in caption.value for caption in app.caption)

    app.sidebar.radio[0].set_value("04 留存与生命周期")
    app.run(timeout=30)

    assert not app.exception
    assert len(app.multiselect[0].options) == 4


def test_simulated_experiment_page_keeps_origin_and_decision_visible(monkeypatch) -> None:
    app = _start_app(monkeypatch)
    app.sidebar.radio[0].set_value("07 模拟增长实验 / SIMULATED")
    app.run(timeout=30)

    assert not app.exception
    assert any("全部渠道、成本、金额" in item.value for item in app.warning)
    assert any(item.label == "绝对提升" and item.value == "0.00 个百分点" for item in app.metric)

    app.selectbox[0].set_value("positive_effect")
    app.run(timeout=30)
    assert not app.exception
    assert any(item.label == "绝对提升" and item.value == "1.20 个百分点" for item in app.metric)
