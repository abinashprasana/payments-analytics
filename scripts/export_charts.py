import os
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db_connection import get_connection

SAVE_DIR = "outputs/charts/"

# Colour palette matches dashboard/app.py exactly
SUCCESS  = "#14B8A6"
WARNING  = "#F59E0B"
DANGER   = "#F43F5E"
INFO     = "#3B82F6"
GRID     = "rgba(255, 255, 255, 0.08)"
BG       = "rgba(14, 18, 30, 1)"

CATEGORY_COLORS = [
    "#8A2387", "#E94057", "#F27121",
    INFO, SUCCESS, WARNING, "#A855F7", "#22C55E",
]

CHART_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor=BG,
    plot_bgcolor=BG,
    font=dict(family="Arial, sans-serif", color="#E8ECF7"),
)


def chart_title(text):
    return dict(text=text, font=dict(size=17, color="#EEF2FF"), x=0.02, xanchor="left")


def ensure_save_dir():
    os.makedirs(SAVE_DIR, exist_ok=True)


def export_transaction_trends(conn):
    print("Exporting transaction_trends.png...", end="", flush=True)
    query = """
        SELECT
            DATE_TRUNC('month', transaction_date)::DATE AS transaction_month,
            COUNT(transaction_id) AS transaction_volume,
            SUM(amount) AS total_value
        FROM transactions
        WHERE status = 'completed'
        GROUP BY 1
        ORDER BY 1;
    """
    df = pd.read_sql_query(query, conn)

    # Two stacked panels — count on top, value on bottom — matching app.py layout
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.10,
        subplot_titles=["Completed Transaction Count", "Completed Transaction Value"],
    )

    fig.add_trace(
        go.Bar(
            x=df["transaction_month"],
            y=df["transaction_volume"],
            name="Transaction Count",
            marker_color=INFO,
            opacity=0.9,
        ),
        row=1, col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df["transaction_month"],
            y=df["total_value"],
            name="Transaction Value",
            line=dict(color=SUCCESS, width=3),
            mode="lines+markers",
            marker=dict(size=5, color=SUCCESS),
            fill="tozeroy",
            fillcolor="rgba(20, 184, 166, 0.14)",
        ),
        row=2, col=1,
    )

    fig.update_layout(
        **CHART_LAYOUT,
        title=chart_title("Transaction Trends Over Time"),
        showlegend=False,
        height=620,
        bargap=0.18,
        margin=dict(l=70, r=30, t=70, b=50),
    )
    fig.update_yaxes(title_text="Transactions", gridcolor=GRID, row=1, col=1)
    fig.update_yaxes(title_text="Value (EUR)", gridcolor=GRID, tickprefix="EUR ", row=2, col=1)
    fig.update_xaxes(tickformat="%b %Y", gridcolor=GRID, row=2, col=1)
    for annotation in fig.layout.annotations:
        annotation.font.color = "#AEB8CD"
        annotation.font.size = 13

    fig.write_image(os.path.join(SAVE_DIR, "transaction_trends.png"), engine="kaleido", width=1100, height=620)
    print(" done")


def export_merchant_performance(conn):
    print("Exporting merchant_performance.png...", end="", flush=True)
    query = """
        SELECT
            m.merchant_name,
            m.category,
            m.risk_tier,
            COALESCE(SUM(s.settled_amount), 0) AS total_revenue
        FROM merchants m
        INNER JOIN transactions t ON m.merchant_id = t.merchant_id
        INNER JOIN settlements s ON t.transaction_id = s.transaction_id
        WHERE t.status = 'completed'
        GROUP BY m.merchant_id, m.merchant_name, m.category, m.risk_tier
        ORDER BY total_revenue DESC
        LIMIT 10;
    """
    df = pd.read_sql_query(query, conn)

    fig = px.bar(
        df,
        x="total_revenue",
        y="merchant_name",
        color="category",
        orientation="h",
        labels={
            "total_revenue": "Settled Revenue (EUR)",
            "merchant_name": "Merchant Name",
            "category": "Industry Category",
        },
        color_discrete_sequence=CATEGORY_COLORS,
        category_orders={"merchant_name": df["merchant_name"].tolist()},
    )
    fig.update_layout(
        **CHART_LAYOUT,
        title=chart_title("Top Merchants by Settled Revenue"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(showgrid=True, gridcolor=GRID),
        yaxis=dict(autorange="reversed"),
        height=480,
        margin=dict(l=30, r=30, t=70, b=50),
    )
    fig.write_image(os.path.join(SAVE_DIR, "merchant_performance.png"), engine="kaleido", width=1100, height=480)
    print(" done")


def export_fraud_risk_by_category(conn):
    print("Exporting fraud_risk_by_category.png...", end="", flush=True)
    query = """
        SELECT
            m.category,
            COUNT(t.transaction_id) AS total_transactions,
            COUNT(f.flag_id) AS flagged_transactions,
            ROUND(COUNT(f.flag_id)::NUMERIC / COUNT(t.transaction_id) * 100, 2) AS fraud_rate_pct
        FROM transactions t
        INNER JOIN merchants m ON t.merchant_id = m.merchant_id
        LEFT JOIN fraud_flags f ON t.transaction_id = f.transaction_id
        GROUP BY m.category
        ORDER BY fraud_rate_pct DESC;
    """
    df = pd.read_sql_query(query, conn)

    fig = px.bar(
        df,
        x="category",
        y="fraud_rate_pct",
        labels={
            "category": "Category",
            "fraud_rate_pct": "Fraud Flag Rate (%)",
        },
        color="fraud_rate_pct",
        color_continuous_scale=[
            (0.0, SUCCESS),
            (0.5, WARNING),
            (1.0, DANGER),
        ],
    )
    fig.update_layout(
        **CHART_LAYOUT,
        title=chart_title("Fraud Flag Rate by Category"),
        yaxis=dict(title="Fraud Rate (%)", showgrid=True, gridcolor=GRID),
        xaxis=dict(title="Category", tickangle=-20),
        coloraxis_showscale=False,
        height=420,
        margin=dict(l=60, r=30, t=70, b=80),
    )
    fig.write_image(os.path.join(SAVE_DIR, "fraud_risk_by_category.png"), engine="kaleido", width=1100, height=420)
    print(" done")


def export_cohort_retention(conn):
    print("Exporting cohort_retention.png...", end="", flush=True)
    query = """
        WITH customer_cohorts AS (
            SELECT
                customer_id,
                DATE_TRUNC('month', join_date)::DATE AS cohort_month
            FROM customers
        ),
        monthly_active_customers AS (
            SELECT DISTINCT
                c.customer_id,
                cc.cohort_month,
                DATE_TRUNC('month', t.transaction_date)::DATE AS activity_month
            FROM transactions t
            INNER JOIN accounts a ON t.account_id = a.account_id
            INNER JOIN customers c ON a.customer_id = c.customer_id
            INNER JOIN customer_cohorts cc ON c.customer_id = cc.customer_id
            WHERE t.status = 'completed'
        ),
        cohort_sizes AS (
            SELECT
                cohort_month,
                COUNT(customer_id) AS cohort_size
            FROM customer_cohorts
            GROUP BY cohort_month
        ),
        cohort_retention AS (
            SELECT
                ma.cohort_month,
                (EXTRACT(YEAR FROM AGE(ma.activity_month, ma.cohort_month)) * 12 +
                 EXTRACT(MONTH FROM AGE(ma.activity_month, ma.cohort_month)))::INTEGER AS months_active_offset,
                COUNT(DISTINCT ma.customer_id) AS active_customers
            FROM monthly_active_customers ma
            GROUP BY ma.cohort_month, months_active_offset
        )
        SELECT
            cr.cohort_month,
            sz.cohort_size,
            cr.months_active_offset,
            ROUND(cr.active_customers::NUMERIC / sz.cohort_size * 100, 2) AS retention_rate
        FROM cohort_retention cr
        INNER JOIN cohort_sizes sz ON cr.cohort_month = sz.cohort_month
        WHERE cr.months_active_offset <= 12
        ORDER BY cr.cohort_month ASC, cr.months_active_offset ASC;
    """
    df = pd.read_sql_query(query, conn)
    cohort_pivot = df.pivot(
        index="cohort_month",
        columns="months_active_offset",
        values="retention_rate",
    )
    cohort_pivot.index = pd.to_datetime(cohort_pivot.index).strftime("%Y-%m")

    # Plotly heatmap matching app.py tab4 exactly
    fig = go.Figure(
        data=go.Heatmap(
            z=cohort_pivot.values,
            x=[f"Month {int(m)}" for m in cohort_pivot.columns],
            y=cohort_pivot.index,
            colorscale=[
                (0.0, "rgba(31, 41, 55, 0.92)"),
                (0.35, INFO),
                (0.7, SUCCESS),
                (1.0, WARNING),
            ],
            colorbar=dict(title="Retention (%)", ticksuffix="%"),
            zmin=0,
            zmax=max(20, df["retention_rate"].max()),
        )
    )
    fig.update_layout(
        **CHART_LAYOUT,
        title=chart_title("Monthly Customer Retention Heatmap"),
        xaxis=dict(title="Months After Joining"),
        yaxis=dict(title="Cohort Month", autorange="reversed"),
        height=580,
        margin=dict(l=80, r=30, t=70, b=60),
    )
    fig.write_image(os.path.join(SAVE_DIR, "cohort_retention.png"), engine="kaleido", width=1100, height=580)
    print(" done")


def main():
    ensure_save_dir()
    conn = get_connection()
    try:
        export_transaction_trends(conn)
        export_merchant_performance(conn)
        export_fraud_risk_by_category(conn)
        export_cohort_retention(conn)
    except Exception as e:
        print(f"\nError during chart export: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
