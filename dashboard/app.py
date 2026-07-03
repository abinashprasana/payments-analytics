import os
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.db_connection import get_connection


st.set_page_config(
    page_title="Corporate Payments Analytics",
    page_icon=":credit_card:",
    layout="wide",
    initial_sidebar_state="expanded",
)


ACCENT_PURPLE = "#8A2387"
ACCENT_PINK = "#E94057"
ACCENT_ORANGE = "#F27121"
SUCCESS = "#14B8A6"
WARNING = "#F59E0B"
DANGER = "#F43F5E"
INFO = "#3B82F6"
GRID = "rgba(255, 255, 255, 0.08)"
CATEGORY_COLORS = [
    ACCENT_PURPLE,
    ACCENT_PINK,
    ACCENT_ORANGE,
    INFO,
    SUCCESS,
    WARNING,
    "#A855F7",
    "#22C55E",
]

CHART_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Outfit, sans-serif", color="#E8ECF7"),
    hoverlabel=dict(
        bgcolor="rgba(18, 22, 35, 0.95)",
        bordercolor="rgba(255,255,255,0.18)",
        font_size=13,
    ),
)


def section_header(title, body):
    st.markdown(
        f"""
        <div class="section-heading">
            <h2>{title}</h2>
            <p>{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_scope_card(label, value, note):
    st.markdown(
        f"""
        <div class="scope-card">
            <span>{label}</span>
            <strong>{value}</strong>
            <small>{note}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )


def insight_note(text):
    st.markdown(f'<p class="insight-note">{text}</p>', unsafe_allow_html=True)


def chart_title(text):
    return dict(text=text, font=dict(size=17, color="#EEF2FF"), x=0.02, xanchor="left")


st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');

    :root {
        --surface: rgba(18, 22, 35, 0.62);
        --border: rgba(255, 255, 255, 0.14);
        --border-soft: rgba(255, 255, 255, 0.07);
        --text: #EEF2FF;
        --muted: #AEB8CD;
    }

    html, body, [class*="css"], .stApp {
        font-family: 'Outfit', sans-serif;
    }

    .stApp {
        color: var(--text);
        background:
            radial-gradient(circle at 12% 8%, rgba(138, 35, 135, 0.24), transparent 26%),
            radial-gradient(circle at 88% 12%, rgba(242, 113, 33, 0.20), transparent 24%),
            linear-gradient(135deg, #080B13 0%, #101522 48%, #080B13 100%);
    }

    .block-container {
        max-width: 1260px;
        padding-top: 2.1rem;
        padding-bottom: 3rem;
    }

    header[data-testid="stHeader"] {
        background: transparent;
    }

    .hero-panel {
        position: relative;
        overflow: hidden;
        padding: 30px 34px;
        margin-bottom: 22px;
        border: 1px solid var(--border);
        border-radius: 8px;
        background:
            linear-gradient(135deg, rgba(255,255,255,0.16), rgba(255,255,255,0.05)),
            var(--surface);
        box-shadow: 0 24px 70px rgba(0, 0, 0, 0.28);
        backdrop-filter: blur(22px);
    }

    .hero-panel:before {
        content: "";
        position: absolute;
        inset: 0;
        border-top: 1px solid rgba(255,255,255,0.24);
        pointer-events: none;
    }

    .main-title {
        font-size: 42px;
        line-height: 1.05;
        font-weight: 800;
        background: linear-gradient(90deg, #8A2387 0%, #E94057 50%, #F27121 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0 0 12px;
        letter-spacing: 0;
    }

    .hero-copy {
        max-width: 780px;
        color: var(--muted);
        font-size: 17px;
        line-height: 1.6;
        margin: 0;
    }

    .section-heading {
        margin: 22px 0 14px;
    }

    .section-heading h2 {
        color: var(--text);
        font-size: 24px;
        line-height: 1.2;
        font-weight: 700;
        margin: 0 0 6px;
        letter-spacing: 0;
    }

    .section-heading p {
        color: var(--muted);
        font-size: 15px;
        line-height: 1.55;
        margin: 0;
    }

    .scope-card {
        box-sizing: border-box;
        height: 146px;
        padding: 18px 18px 16px;
        margin-bottom: 6px;
        border-radius: 8px;
        border: 1px solid var(--border-soft);
        background:
            linear-gradient(150deg, rgba(255,255,255,0.12), rgba(255,255,255,0.035)),
            rgba(13, 18, 31, 0.54);
        box-shadow: 0 16px 42px rgba(0, 0, 0, 0.20);
        backdrop-filter: blur(18px);
    }

    .scope-card span {
        display: block;
        color: var(--muted);
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 8px;
    }

    .scope-card strong {
        display: block;
        color: #FFFFFF;
        font-size: 25px;
        line-height: 1.15;
        font-weight: 750;
        letter-spacing: 0;
        margin-bottom: 8px;
    }

    .scope-card small {
        display: block;
        color: var(--muted);
        font-size: 13px;
        line-height: 1.45;
    }

    div[data-testid="stTabs"] button {
        color: var(--muted);
        background: rgba(255, 255, 255, 0.04);
        border-radius: 8px 8px 0 0;
        border: 1px solid rgba(255,255,255,0.06);
        margin-right: 4px;
        transition: all 160ms ease;
        font-weight: 500;
    }

    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: #FFFFFF;
        background:
            linear-gradient(135deg, rgba(233,64,87,0.34), rgba(242,113,33,0.16)),
            rgba(255,255,255,0.08);
        border-color: rgba(255,255,255,0.24);
        box-shadow:
            inset 0 -2px 0 #E94057,
            0 10px 24px rgba(233, 64, 87, 0.16);
        font-weight: 700;
    }

    .stMetric {
        min-height: 132px;
        padding: 22px 20px;
        border-radius: 8px;
        border: 1px solid var(--border);
        background:
            linear-gradient(150deg, rgba(255,255,255,0.15), rgba(255,255,255,0.045)),
            var(--surface);
        box-shadow: 0 18px 45px rgba(0, 0, 0, 0.22);
        backdrop-filter: blur(20px);
    }

    div[data-testid="stMetricValue"] {
        font-size: 30px;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: 0;
    }

    div[data-testid="stMetricLabel"] {
        font-size: 12px;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    label[data-testid="stMetricLabel"],
    label[data-testid="stMetricLabel"] * {
        color: var(--muted) !important;
        opacity: 1 !important;
    }

    div[data-testid="stMetricLabel"] p,
    div[data-testid="stMetricLabel"] div {
        color: var(--muted) !important;
        opacity: 1 !important;
    }

    div[data-testid="stMetricValue"] div {
        color: #FFFFFF !important;
    }

    div[data-testid="stPlotlyChart"],
    div[data-testid="stDataFrame"] {
        border-radius: 8px;
        border: 1px solid var(--border-soft);
        background:
            linear-gradient(145deg, rgba(255,255,255,0.09), rgba(255,255,255,0.025)),
            rgba(12, 16, 27, 0.50);
        box-shadow: 0 18px 48px rgba(0,0,0,0.22);
        padding: 8px;
        backdrop-filter: blur(18px);
    }

    .insight-note {
        margin: 8px 0 16px;
        color: var(--muted);
        font-size: 14px;
        line-height: 1.5;
    }

    .summary-panel {
        margin-top: 14px;
        padding: 22px 24px;
        border-radius: 8px;
        border: 1px solid var(--border-soft);
        background:
            linear-gradient(145deg, rgba(255,255,255,0.09), rgba(255,255,255,0.025)),
            rgba(12, 16, 27, 0.50);
        box-shadow: 0 18px 48px rgba(0,0,0,0.22);
        backdrop-filter: blur(18px);
    }

    .summary-panel h3 {
        color: var(--text);
        font-size: 18px;
        margin: 0 0 10px;
        letter-spacing: 0;
    }

    .summary-panel p {
        color: var(--muted);
        font-size: 15px;
        line-height: 1.6;
        margin: 0 0 10px;
    }

    hr {
        border-color: rgba(255,255,255,0.08);
        margin: 24px 0 10px;
    }

    .stAlert {
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=600)
def fetch_dataset_scope():
    conn = get_connection()
    query = """
        SELECT
            (SELECT COUNT(*) FROM customers) AS customer_count,
            (SELECT COUNT(*) FROM accounts) AS account_count,
            (SELECT COUNT(*) FROM merchants) AS merchant_count,
            (SELECT COUNT(*) FROM transactions) AS transaction_count,
            (SELECT COUNT(*) FROM settlements) AS settlement_count,
            (SELECT COUNT(*) FROM fraud_flags) AS fraud_flag_count,
            (SELECT MIN(transaction_date)::DATE FROM transactions) AS first_transaction_date,
            (SELECT MAX(transaction_date)::DATE FROM transactions) AS last_transaction_date;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df.iloc[0]


@st.cache_data(ttl=600)
def fetch_overview_metrics():
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


st.markdown(
    """
    <section class="hero-panel">
        <h1 class="main-title">Corporate Payments Analytics</h1>
        <p class="hero-copy">
            Built as part of an MSc AI portfolio project to practice real-world analytics
            on commercial payments data. The dataset spans three years of synthetic transaction
            activity across six relational tables: customers, accounts, merchants, transactions,
            settlements, and fraud flags. Each tab answers one analytical question about
            the data — from payment volume trends to merchant performance, fraud detection
            patterns, and customer retention.
        </p>
    </section>
    """,
    unsafe_allow_html=True,
)

try:
    scope = fetch_dataset_scope()
    scope_cols = st.columns(4)
    with scope_cols[0]:
        render_scope_card(
            "Customer Base",
            f"{scope['customer_count']:,}",
            f"{scope['account_count']:,} linked accounts",
        )
    with scope_cols[1]:
        render_scope_card(
            "Merchants",
            f"{scope['merchant_count']:,}",
            "Grouped by category and risk tier",
        )
    with scope_cols[2]:
        first_date = pd.to_datetime(scope["first_transaction_date"]).strftime("%b %Y")
        last_date = pd.to_datetime(scope["last_transaction_date"]).strftime("%b %Y")
        render_scope_card(
            "Transaction Window",
            f"{first_date} to {last_date}",
            f"{scope['transaction_count']:,} total transactions",
        )
    with scope_cols[3]:
        render_scope_card(
            "Risk Records",
            f"{scope['fraud_flag_count']:,}",
            f"{scope['settlement_count']:,} settlement records",
        )
except Exception:
    st.info("Dataset context will appear after the PostgreSQL tables are available.")


tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Overview",
        "Merchants",
        "Risk",
        "Retention",
        "Summary",
    ]
)


with tab1:
    section_header(
        "Executive Overview",
        "A quick view of completed transaction activity, total completed transaction amount, and average payment size.",
    )
    try:
        metrics = fetch_overview_metrics()

        col1, col2, col3 = st.columns(3)
        col1.metric(
            label="Total Completed Transactions",
            value=f"{int(metrics['total_tx_count']):,}",
        )
        col2.metric(
            label="Total Transaction Volume (EUR)",
            value=f"EUR {metrics['total_tx_volume']:,.2f}",
        )
        col3.metric(
            label="Average Transaction Size",
            value=f"EUR {metrics['avg_tx_value']:,.2f}",
        )

        st.write("---")
        section_header(
            "Transaction Trends Over Time",
            "Monthly completed transaction counts and completed transaction value are shown separately so the scale stays readable.",
        )

        trends_df = fetch_monthly_trends()

        fig_count = go.Figure()
        fig_count.add_trace(
            go.Bar(
                x=trends_df["transaction_month"],
                y=trends_df["transaction_volume"],
                name="Completed Transactions",
                marker_color=INFO,
                opacity=0.9,
                hovertemplate="%{x|%b %Y}<br>%{y:,.0f} completed payments<extra></extra>",
            )
        )

        fig_count.update_layout(
            **CHART_LAYOUT,
            title=chart_title("Completed Transaction Count"),
            showlegend=False,
            yaxis=dict(title="Transactions", gridcolor=GRID, tickformat="~s"),
            xaxis=dict(title="Month", tickformat="%b %Y"),
            height=420,
            bargap=0.18,
            margin=dict(l=16, r=16, t=54, b=16),
        )

        fig_value = go.Figure()
        fig_value.add_trace(
            go.Scatter(
                x=trends_df["transaction_month"],
                y=trends_df["total_value"],
                name="Completed Value",
                line=dict(color=SUCCESS, width=3),
                mode="lines+markers",
                marker=dict(size=6, color=SUCCESS),
                fill="tozeroy",
                fillcolor="rgba(20, 184, 166, 0.14)",
                hovertemplate="%{x|%b %Y}<br>EUR %{y:,.2f}<extra></extra>",
            )
        )

        fig_value.update_layout(
            **CHART_LAYOUT,
            title=chart_title("Completed Transaction Value"),
            showlegend=False,
            yaxis=dict(title="Value (EUR)", gridcolor=GRID, tickprefix="EUR ", tickformat="~s"),
            xaxis=dict(title="Month", tickformat="%b %Y"),
            height=420,
            margin=dict(l=16, r=16, t=54, b=16),
        )

        st.plotly_chart(fig_count, use_container_width=True)
        st.plotly_chart(fig_value, use_container_width=True)

        if not trends_df.empty:
            peak_row = trends_df.loc[trends_df["transaction_volume"].idxmax()]
            peak_month = pd.to_datetime(peak_row["transaction_month"]).strftime("%b %Y")
            insight_note(
                f"The highest completed transaction count is in {peak_month}, "
                f"with {int(peak_row['transaction_volume']):,} completed payments."
            )

    except Exception as err:
        st.error(f"Failed to fetch overview metrics. Verify database state. Error: {err}")


with tab2:
    section_header(
        "Merchant Revenue Leaderboard",
        "Merchants are ranked by settled amount, using completed transactions that have matching settlement records.",
    )

    try:
        merchant_df = fetch_merchant_performance()

        fig_merchants = px.bar(
            merchant_df,
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
            category_orders={"merchant_name": merchant_df["merchant_name"].tolist()},
        )

        fig_merchants.update_layout(
            **CHART_LAYOUT,
            title=chart_title("Top Merchants by Settled Revenue"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            xaxis=dict(showgrid=True, gridcolor=GRID),
            yaxis=dict(autorange="reversed"),
            height=480,
            margin=dict(l=16, r=16, t=54, b=16),
        )

        st.plotly_chart(fig_merchants, use_container_width=True)
        if not merchant_df.empty:
            top_merchant = merchant_df.iloc[0]
            insight_note(
                f"{top_merchant['merchant_name']} leads the table with "
                f"EUR {top_merchant['total_revenue']:,.2f} in settled revenue."
            )

        st.dataframe(
            merchant_df.rename(
                columns={
                    "merchant_name": "Merchant",
                    "category": "Category",
                    "risk_tier": "Risk Tier",
                    "total_revenue": "Revenue (EUR)",
                }
            ),
            column_config={
                "Revenue (EUR)": st.column_config.NumberColumn(format="EUR %,.2f")
            },
            use_container_width=True,
            hide_index=True,
        )

    except Exception as err:
        st.error(f"Failed to load merchant insights: {err}")


with tab3:
    section_header(
        "Compliance and Fraud Risk",
        "Fraud flag rates are compared across merchant categories using the fraud flag records in the dataset.",
    )

    try:
        risk_df = fetch_risk_overview()

        col_chart, col_data = st.columns([2, 1])

        with col_chart:
            fig_risk = px.bar(
                risk_df,
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
            fig_risk.update_layout(
                **CHART_LAYOUT,
                title=chart_title("Fraud Flag Rate by Category"),
                yaxis=dict(title="Fraud Rate (%)", showgrid=True, gridcolor=GRID),
                xaxis=dict(title="Category", tickangle=-20),
                coloraxis_showscale=False,
                height=400,
                margin=dict(l=16, r=16, t=54, b=16),
            )
            st.plotly_chart(fig_risk, use_container_width=True)
            if not risk_df.empty:
                highest_risk = risk_df.iloc[0]
                insight_note(
                    f"{highest_risk['category']} has the highest fraud flag rate "
                    f"at {highest_risk['fraud_rate_pct']:.2f}% in this dataset."
                )

        with col_data:
            section_header(
                "Risk Rates Table",
                "A category-level table showing transaction counts, fraud flags, and fraud rate.",
            )
            st.dataframe(
                risk_df.rename(
                    columns={
                        "category": "Category",
                        "total_transactions": "Total Transactions",
                        "flagged_transactions": "Flags",
                        "fraud_rate_pct": "Fraud Rate",
                    }
                ),
                column_config={
                    "Fraud Rate": st.column_config.NumberColumn(format="%.2f%%")
                },
                use_container_width=True,
                hide_index=True,
            )

    except Exception as err:
        st.error(f"Failed to load risk configurations: {err}")


with tab4:
    section_header(
        "Monthly Customer Retention Matrix",
        "The matrix shows the share of each registration cohort returning for completed transactions in later months.",
    )

    try:
        cohort_raw = fetch_cohort_retention()

        cohort_pivot = cohort_raw.pivot(
            index="cohort_month",
            columns="months_active_offset",
            values="retention_rate",
        )

        cohort_pivot.index = pd.to_datetime(cohort_pivot.index).strftime("%Y-%m")

        heatmap = go.Figure(
            data=go.Heatmap(
                z=cohort_pivot.values,
                x=[f"Month {int(month)}" for month in cohort_pivot.columns],
                y=cohort_pivot.index,
                colorscale=[
                    (0.0, "rgba(31, 41, 55, 0.92)"),
                    (0.35, INFO),
                    (0.7, SUCCESS),
                    (1.0, WARNING),
                ],
                colorbar=dict(title="Retention", ticksuffix="%"),
                hovertemplate=(
                    "Cohort %{y}<br>%{x}<br>Retention %{z:.2f}%<extra></extra>"
                ),
                zmin=0,
                zmax=max(20, cohort_raw["retention_rate"].max()),
            )
        )

        heatmap.update_layout(
            **CHART_LAYOUT,
            title=chart_title("Retention Heatmap"),
            xaxis=dict(title="Months After Joining"),
            yaxis=dict(title="Cohort Month", autorange="reversed"),
            height=560,
            margin=dict(l=16, r=16, t=54, b=44),
        )

        st.plotly_chart(heatmap, use_container_width=True)
        month_one = cohort_raw[cohort_raw["months_active_offset"] == 1]
        if not month_one.empty:
            insight_note(
                f"Average month-one retention across available cohorts is "
                f"{month_one['retention_rate'].mean():.2f}%."
            )

    except Exception as err:
        st.error(f"Failed to calculate customer cohort retention: {err}")


with tab5:
    section_header(
        "Project Summary",
        "A concise view of what this dashboard covers and how the analysis is organised.",
    )

    try:
        summary_scope = fetch_dataset_scope()

        summary_cols = st.columns(4)
        with summary_cols[0]:
            render_scope_card(
                "Data Coverage",
                f"{summary_scope['transaction_count']:,}",
                "transactions analysed across the project",
            )
        with summary_cols[1]:
            render_scope_card(
                "Core Tables",
                "6",
                "customers, accounts, merchants, transactions, settlements, fraud flags",
            )
        with summary_cols[2]:
            render_scope_card(
                "Main Views",
                "4",
                "overview, merchants, risk, and retention",
            )
        with summary_cols[3]:
            render_scope_card(
                "Tools Used",
                "SQL + Python",
                "Streamlit dashboard with Plotly charts",
            )

        st.markdown(
            """
            <div class="summary-panel">
                <h3>About This Project</h3>
                <p>
                    I built this project to get hands-on experience with the kind of data
                    analysis that comes up in real fintech and payments environments. Rather
                    than working with a single flat CSV, I designed a six-table relational
                    schema in PostgreSQL and wrote SQL queries to explore different parts of
                    the data: customer segmentation, merchant revenue, fraud compliance, and
                    cohort retention.
                </p>
                <p>
                    The data is fully synthetic, generated using Python and the Faker library,
                    so nothing here is real transaction data. The goal was to make the dataset
                    realistic enough that the analysis techniques and patterns would be meaningful
                    and transferable to real projects.
                </p>
                <p>
                    The Streamlit dashboard and a separate Power BI report both pull from the
                    same underlying data, which gave me practice presenting the same findings
                    in two different BI tools.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    except Exception as err:
        st.error(f"Failed to load project summary: {err}")
