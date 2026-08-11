# Streamlit application

`streamlit_app.py` is the safe `v0.1.0` landing page. It does not open the
Retailrocket files or a DuckDB database. The analytical dashboard will be
implemented after the warehouse and metric marts exist in later milestones.

After installing the project dependencies, run it from the repository root:

```powershell
python -m streamlit run app/streamlit_app.py
```

The formal local input is always the official full Retailrocket dataset under
`D:\CodexData\product-ops-growth-analytics\raw\extracted`. The desktop sample
is for learning the columns only and is not a dashboard input.
