# Streamlit application

`streamlit_app.py` is a safe status landing page. It does not open the
Retailrocket files or a DuckDB database. The `v0.3.0` warehouse and metric marts
are complete; the interactive analytical dashboard belongs to `v0.4.0`.

After installing the project dependencies, run it from the repository root:

```powershell
python -m streamlit run app/streamlit_app.py
```

The formal local input is always the official full Retailrocket dataset under
`D:\CodexData\product-ops-growth-analytics\raw\extracted`. The desktop sample
is for learning the columns only and is not a dashboard input.
