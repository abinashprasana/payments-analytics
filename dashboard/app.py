"""Streamlit Interactive Analytics Dashboard for Payments Analytics SQL.

This dashboard connects to the PostgreSQL database, runs cached analytical
queries, and presents key performance indicators, merchant rankings,
risk/fraud statistics, and cohort retention metrics using Plotly charts.
"""

import sys
import os
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Add the root directory to path to support importing db_connection
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.db_connection import get_connection

# Streamlit Page Setup for Premium Dark-Themed Aesthetic
st.set_page_config(
    page_title="Corporate Payments Analytics",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Typography & Design Accents
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .main-title {
        font-size: 40px;
        font-weight: 800;
        background: linear-gradient(90deg, #8A2387 0%, #E94057 50%, #F27121 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 20px;
        letter-spacing: -1px;
    }
    
    .stMetric {
        background-color: rgba(28, 30, 41, 0.4);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 26px;
        font-weight: 600;
        color: #FFFFFF;
    }
    
    div[data-testid="stMetricLabel"] {
        font-size: 13px;
        color: #A0AEC0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


@st.cache_data(ttl=600)
def fetch_overview_metrics():
    """Queries total count, total volume, and average transaction size."""
    conn = get_connection()
    query = """
        SELECT 
            COUNT(transaction_id) AS total_tx_count,
            COALESCE(SUM(amount), 0) AS total_tx_volume,
            COALESCE(AVG(amount), 0) AS avg_tx_value
        FROM transactions
        WHERE status = 'completed';
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df.iloc[0]


@st.cache_data(ttl=600)
def fetch_monthly_trends():
    """Queries monthly transaction aggregated metrics."""
    conn = get_connection()
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
    conn.close()
    return df


@st.cache_data(ttl=600)
def fetch_merchant_performance():
    """Queries top 10 merchants by settled volume."""
    conn = get_connection()
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
    conn.close()
    return df


@st.cache_data(ttl=600)
def fetch_risk_overview():
    """Queries transaction volume vs fraud occurrences across categories."""
    conn = get_connection()
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
    conn.close()
    return df


@st.cache_data(ttl=600)
def fetch_cohort_retention():
    """Queries monthly customer retention matrices."""
    conn = get_connection()
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
    conn.close()
    return df


# Main Header layout
st.markdown('<div class="main-title">Corporate Payments Analytics</div>', unsafe_allow_html=True)
st.write("MSc AI Portfolio Project — Synthetic Commercial Transaction Intelligence Dashboard")

# Tab Selection
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Overview", 
    "🏬 Merchant Analysis", 
    "🛡️ Risk Overview", 
    "👥 Cohort Retention"
])

# -----------------
# TAB 1: OVERVIEW
# -----------------
with tab1:
    st.subheader("Key Performance Indicators")
    try:
        metrics = fetch_overview_metrics()
        
        # Display KPIs in standard columns
        col1, col2, col3 = st.columns(3)
        col1.metric(
            label="Total Completed Transactions",
            value=f"{metrics['total_tx_count']:,}"
        )
        col2.metric(
            label="Total Transaction Volume (EUR)",
            value=f"€{metrics['total_tx_volume']:,.2f}"
        )
        col3.metric(
            label="Average Transaction Size",
            value=f"€{metrics['avg_tx_value']:,.2f}"
        )
        
        st.write("---")
        st.subheader("Transaction Trends Over Time")
        
        trends_df = fetch_monthly_trends()
        
        # Plotly Trend Chart
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Bar(
            x=trends_df['transaction_month'],
            y=trends_df['transaction_volume'],
            name="Transaction Count",
            yaxis="y",
            marker_color="#8A2387",
            opacity=0.85
        ))
        fig_trend.add_trace(go.Scatter(
            x=trends_df['transaction_month'],
            y=trends_df['total_value'],
            name="Transaction Volume (€)",
            yaxis="y2",
            line=dict(color="#F27121", width=3)
        ))
        
        fig_trend.update_layout(
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
            height=450,
            margin=dict(l=10, r=10, t=10, b=10)
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        
    except Exception as err:
        st.error(f"Failed to fetch overview metrics. Verify database state. Error: {err}")

# -----------------
# TAB 2: MERCHANT ANALYSIS
# -----------------
with tab2:
    st.subheader("Merchant Revenue Leaderboard")
    st.write("Top 10 merchants based on accumulated settlement processing payouts.")
    
    try:
        merchant_df = fetch_merchant_performance()
        
        # Top 10 Merchants Horizontal Bar Chart
        fig_merchants = px.bar(
            merchant_df,
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
            category_orders={"merchant_name": merchant_df['merchant_name'].tolist()}
        )
        
        fig_merchants.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(autorange="reversed"),
            height=480,
            margin=dict(l=10, r=10, t=10, b=10)
        )
        
        st.plotly_chart(fig_merchants, use_container_width=True)
        
        # Detailed stats grid
        st.dataframe(
            merchant_df.rename(columns={
                "merchant_name": "Merchant",
                "category": "Category",
                "risk_tier": "Risk Tier",
                "total_revenue": "Revenue (EUR)"
            }),
            column_config={
                "Revenue (EUR)": st.column_config.NumberColumn(format="€%,.2f")
            },
            use_container_width=True,
            hide_index=True
        )
        
    except Exception as err:
        st.error(f"Failed to load merchant insights: {err}")

# -----------------
# TAB 3: RISK OVERVIEW
# -----------------
with tab3:
    st.subheader("Compliance & Fraud Risk Profiles")
    st.write("Analyzing fraud flag rates relative to overall transaction counts by merchant category.")
    
    try:
        risk_df = fetch_risk_overview()
        
        col_chart, col_data = st.columns([2, 1])
        
        with col_chart:
            # Fraud rate bar chart
            fig_risk = px.bar(
                risk_df,
                x="category",
                y="fraud_rate_pct",
                labels={
                    "category": "Category",
                    "fraud_rate_pct": "Fraud Flag Rate (%)"
                },
                color="fraud_rate_pct",
                color_continuous_scale="Purples"
            )
            fig_risk.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(title="Fraud Rate (%)", showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
                xaxis=dict(title="Category"),
                coloraxis_showscale=False,
                height=400,
                margin=dict(l=10, r=10, t=10, b=10)
            )
            st.plotly_chart(fig_risk, use_container_width=True)
            
        with col_data:
            st.write("#### Risk Rates Table")
            st.dataframe(
                risk_df.rename(columns={
                    "category": "Category",
                    "total_transactions": "Total Tx",
                    "flagged_transactions": "Flags",
                    "fraud_rate_pct": "Fraud Rate"
                }),
                column_config={
                    "Fraud Rate": st.column_config.NumberColumn(format="%.2f%%")
                },
                use_container_width=True,
                hide_index=True
            )
            
    except Exception as err:
        st.error(f"Failed to load risk configurations: {err}")

# -----------------
# TAB 4: COHORT RETENTION
# -----------------
with tab4:
    st.subheader("Monthly Customer Retention Matrix")
    st.write(
        "Percent of customers returning to make completed transactions "
        "in subsequent months relative to their initial registration cohort month."
    )
    
    try:
        cohort_raw = fetch_cohort_retention()
        
        # Pivot values to construct a classic heatmap matrix
        cohort_pivot = cohort_raw.pivot(
            index="cohort_month",
            columns="months_active_offset",
            values="retention_rate"
        )
        
        # Format dates for cleaner row headers
        cohort_pivot.index = pd.to_datetime(cohort_pivot.index).strftime("%Y-%m")
        
        # Render a color-coded heatmap representation using Pandas Styler
        styled_cohort = (
            cohort_pivot.style
            .format("{:.2f}%", na_rep="-")
            .background_gradient(cmap="Purples", axis=None, low=0.0, high=100.0)
        )
        
        st.dataframe(styled_cohort, use_container_width=True)
        
    except Exception as err:
        st.error(f"Failed to calculate customer cohort retention: {err}")
