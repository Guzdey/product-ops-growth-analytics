# `mart` layer

`v0.3.0` keeps metric formulas in six ordered SQL modules:

| File | Responsibility |
|---|---|
| `001_registry_activity.sql` | Metric registry, visitor-day, session and activity metrics |
| `002_funnel_paths.sql` | Behaviour, ordered and same-item funnels, paths and latency |
| `003_retention.sql` | Right-censored D1/D3/D7/D14/D30 and weekly Cohorts |
| `004_transactions_lifecycle.sql` | Clean unique transactions, repeat purchase and lifecycle |
| `005_product_category_quality.sql` | Item/category performance, Wilson intervals and coverage |
| `006_hypotheses.sql` | Pre-registered H1/H2/H3 results |

Python executes these files in order, records resumable step signatures, runs blocking checks,
adds the H1 statistical test and exports aggregate relations. Streamlit must read these marts or
their aggregate exports; it must not scan the full CSV files directly.
