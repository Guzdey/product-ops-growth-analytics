"""The dashboard module must remain import-safe before Streamlit is installed."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any


class FakeStreamlit:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def set_page_config(self, **kwargs: Any) -> None:
        self.calls.append(("set_page_config", kwargs))

    def title(self, value: str) -> None:
        self.calls.append(("title", value))

    def info(self, value: str) -> None:
        self.calls.append(("info", value))

    def subheader(self, value: str) -> None:
        self.calls.append(("subheader", value))

    def code(self, value: str, **kwargs: Any) -> None:
        self.calls.append(("code", value))

    def caption(self, value: str) -> None:
        self.calls.append(("caption", value))


def _load_app_module() -> ModuleType:
    app_path = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
    spec = importlib.util.spec_from_file_location("project_streamlit_app", app_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_app_renders_safe_placeholder_with_injected_streamlit(monkeypatch) -> None:
    monkeypatch.delenv("PRODUCT_OPS_DATA_HOME", raising=False)
    monkeypatch.delenv("PRODUCT_OPS_DEMO_MODE", raising=False)
    app_module = _load_app_module()
    fake_streamlit = FakeStreamlit()

    exit_code = app_module.main(fake_streamlit)

    assert exit_code == 0
    assert ("code", r"D:\CodexData\product-ops-growth-analytics\raw\extracted") in (
        fake_streamlit.calls
    )
    rendered_text = " ".join(str(value) for _, value in fake_streamlit.calls)
    assert "官方完整数据集" in rendered_text
    assert "不会读取或写入数据" in rendered_text


def test_app_labels_demo_mode_as_simulated(monkeypatch) -> None:
    monkeypatch.setenv("PRODUCT_OPS_DATA_HOME", "/tmp/product-ops/dashboard-demo")
    monkeypatch.setenv("PRODUCT_OPS_DEMO_MODE", "true")
    app_module = _load_app_module()
    fake_streamlit = FakeStreamlit()

    exit_code = app_module.main(fake_streamlit)

    assert exit_code == 0
    rendered_text = " ".join(str(value) for _, value in fake_streamlit.calls)
    assert "模拟数据 / SIMULATED" in rendered_text
    assert "官方完整数据集" not in rendered_text


def test_streamlit_runtime_smoke(monkeypatch) -> None:
    """Run the page with Streamlit's real test runtime used by CI."""

    from streamlit.testing.v1 import AppTest

    monkeypatch.delenv("PRODUCT_OPS_DATA_HOME", raising=False)
    monkeypatch.delenv("PRODUCT_OPS_DEMO_MODE", raising=False)
    app_path = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"

    app = AppTest.from_file(app_path).run(timeout=20)

    assert not app.exception
    assert app.title[0].value == "Retailrocket 用户增长运营分析"
    assert "不会读取或写入数据" in app.info[0].value
