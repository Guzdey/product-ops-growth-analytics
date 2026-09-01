"""Safe Streamlit landing page while the analytical dashboard is planned."""

from __future__ import annotations

import sys
from typing import Any


def main(streamlit_module: Any | None = None) -> int:
    """Render the placeholder page, or explain how to install Streamlit.

    The optional parameter makes the tiny page testable without importing the
    real Streamlit package. No data file is opened by this entry point.
    """

    st = streamlit_module
    if st is None:
        try:
            import streamlit as st  # type: ignore[no-redef]
        except ModuleNotFoundError:
            sys.stderr.write(
                "Streamlit is not installed. Install the project dashboard "
                "dependencies, then run: python -m streamlit run "
                "app/streamlit_app.py\n"
            )
            return 1

    try:
        from product_ops.config import load_project_config
    except ModuleNotFoundError:
        sys.stderr.write(
            "The local product_ops package is not installed. From the repository "
            "root, install the project in editable mode before starting Streamlit.\n"
        )
        return 1

    config = load_project_config()
    st.set_page_config(
        page_title="Retailrocket Product Operations Analytics",
        page_icon="📊",
        layout="wide",
    )
    st.title("Retailrocket 用户增长运营分析")
    st.info(
        "v0.2.0 已建设全量 DuckDB 数据仓库；运营指标与交互图表将在后续"
        "里程碑实现。本页面目前仅展示项目状态，不会读取或写入数据。"
    )
    st.subheader("模拟分析输入" if config.demo_mode else "正式分析输入")
    st.code(str(config.raw_data_dir), language=None)
    if config.demo_mode:
        st.caption(
            "当前为模拟数据 / SIMULATED 模式；尚未提供正式演示数据。"
            "桌面 Retailrocket 小样例仍不作为分析输入。"
        )
    else:
        st.caption(
            "仅使用 Retailrocket 官方完整数据集。桌面小样例只用于理解字段，不作为默认分析输入。"
        )
    return 0


if __name__ == "__main__":
    main()
