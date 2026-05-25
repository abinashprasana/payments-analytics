"""Programmatic dashboard chart exporter for Payments Analytics SQL.

This script connects to the PostgreSQL database, executes analytical queries,
generates identical Plotly figures to those displayed in the Streamlit dashboard,
and exports them as PNG files to outputs/charts/.
"""

import os
import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Add current directory to path if run from root directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db_connection import get_connection

save_dir = "outputs/charts/"

def ensure_save_dir():
    os.makedirs(save_dir, exist_ok=True)

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
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df['transaction_month'],
        y=df['transaction_volume'],
        name="Transaction Count",
        yaxis="y",
        marker_color="#8A2387",
        opacity=0.85
    ))
    fig.add_trace(go.Scatter(
        x=df['transaction_month'],
        y=df['total_value'],
        name="Transaction Volume (€)",
        yaxis="y2",
        line=dict(color="#F27121", width=3)
    ))
    
    fig.update_layout(
        title="Transaction Trends Over Time",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(x=0.01, y=0.99),
        yaxis=dict(
            title="Transaction Count",
            side="left"
        ),
        yaxis2=dict(
            title="Total Value (EUR)",
            side="right",
            overlaying="y",
            showgrid=False
        ),
        xaxis=dict(title="Month"),
        height=450
    )
    
    output_path = os.path.join(save_dir, "transaction_trends.png")
    fig.write_image(output_path, engine="kaleido")
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
            "category": "Industry Category"
        },
        color_discrete_sequence=px.colors.qualitative.Bold,
        category_orders={"merchant_name": df['merchant_name'].tolist()}
    )
    
    fig.update_layout(
        title="Merchant Revenue Leaderboard",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(autorange="reversed"),
        height=480
    )
    
    output_path = os.path.join(save_dir, "merchant_performance.png")
    fig.write_image(output_path, engine="kaleido")
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
            "fraud_rate_pct": "Fraud Flag Rate (%)"
        },
        color="fraud_rate_pct",
        color_continuous_scale="Purples"
    )
    fig.update_layout(
        title="Compliance & Fraud Risk Profiles by Category",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(title="Fraud Rate (%)", showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
        xaxis=dict(title="Category"),
        coloraxis_showscale=False,
        height=400
    )
    
    output_path = os.path.join(save_dir, "fraud_risk_by_category.png")
    fig.write_image(output_path, engine="kaleido")
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
    
    # Pivot values to construct a classic heatmap matrix
    cohort_pivot = df.pivot(
        index="cohort_month",
        columns="months_active_offset",
        values="retention_rate"
    )
    
    # Format dates for cleaner row headers
    cohort_pivot.index = pd.to_datetime(cohort_pivot.index).strftime("%Y-%m")
    
    # Generate Heatmap figure using Plotly
    fig = px.imshow(
        cohort_pivot,
        text_auto=".2f",
        color_continuous_scale="Purples",
        labels=dict(x="Months Since Join", y="Cohort Month", color="Retention (%)"),
        aspect="auto"
    )
    
    fig.update_layout(
        title="Monthly Customer Retention Matrix Heatmap",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=450
    )
    
    output_path = os.path.join(save_dir, "cohort_retention.png")
    fig.write_image(output_path, engine="kaleido")
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
