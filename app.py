"""
app.py - Streamlit Dashboard for the Hardware Sourcing & Specs Agent.

A polished, interactive UI with real-time agent progress tracking,
pricing charts, pin tables, and full reasoning trace display.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import json
import time
from datetime import datetime

import streamlit as st

# ── Page Configuration ──
st.set_page_config(
    page_title="Hardware Sourcing Agent",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Custom CSS for Premium Look
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global */
    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* Header gradient */
    .main-header {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    .main-header h1 {
        color: #fff;
        font-weight: 700;
        font-size: 2.2rem;
        margin: 0;
    }
    .main-header p {
        color: #a8a8d0;
        font-size: 1.05rem;
        margin: 0.3rem 0 0 0;
    }

    /* Component card */
    .component-card {
        background: linear-gradient(145deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #2a2a4a;
        border-radius: 14px;
        padding: 1.8rem;
        margin: 1rem 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    }
    .component-card h2 {
        color: #e94560;
        font-weight: 600;
        margin-top: 0;
    }
    .component-card p {
        color: #c4c4e0;
        line-height: 1.6;
    }
    .component-card .label {
        color: #7a7aaa;
        font-size: 0.85rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .component-card .value {
        color: #ffffff;
        font-size: 1.1rem;
        font-weight: 500;
    }

    /* Stock badge */
    .stock-badge {
        display: inline-block;
        padding: 0.4rem 1.2rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
    }
    .stock-in {
        background: rgba(46, 213, 115, 0.15);
        color: #2ed573;
        border: 1px solid rgba(46, 213, 115, 0.3);
    }
    .stock-out {
        background: rgba(255, 71, 87, 0.15);
        color: #ff4757;
        border: 1px solid rgba(255, 71, 87, 0.3);
    }

    /* Best deal card */
    .best-deal {
        background: linear-gradient(135deg, #0a3d62 0%, #1e3799 100%);
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        border-left: 4px solid #4bcffa;
        margin: 1rem 0;
    }
    .best-deal h3 {
        color: #4bcffa;
        margin: 0 0 0.3rem 0;
        font-size: 1rem;
    }
    .best-deal p {
        color: #fff;
        font-size: 1.2rem;
        font-weight: 600;
        margin: 0;
    }

    /* Reasoning trace */
    .trace-step {
        background: rgba(255,255,255,0.03);
        border-left: 3px solid #302b63;
        padding: 0.6rem 1rem;
        margin: 0.3rem 0;
        border-radius: 0 8px 8px 0;
        font-family: 'Inter', monospace;
        font-size: 0.85rem;
        color: #b0b0d0;
    }
    .trace-step:hover {
        background: rgba(255,255,255,0.06);
        border-left-color: #e94560;
    }

    /* Quick-select chips */
    .chip-container {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin: 0.5rem 0;
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #2a2a4a;
        border-radius: 12px;
        padding: 1rem;
    }

    /* Cross-validation badge */
    .cv-badge {
        display: inline-block;
        padding: 0.5rem 1.2rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.95rem;
        margin: 0.5rem 0;
    }
    .cv-high {
        background: rgba(46, 213, 115, 0.15);
        color: #2ed573;
        border: 1px solid rgba(46, 213, 115, 0.3);
    }
    .cv-medium {
        background: rgba(255, 165, 2, 0.15);
        color: #ffa502;
        border: 1px solid rgba(255, 165, 2, 0.3);
    }
    .cv-low {
        background: rgba(255, 71, 87, 0.15);
        color: #ff4757;
        border: 1px solid rgba(255, 71, 87, 0.3);
    }

    /* Cross-validation card */
    .cv-card {
        background: linear-gradient(145deg, #1a1a2e 0%, #0a3d62 100%);
        border: 1px solid #2a4a6a;
        border-radius: 14px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .cv-card h3 {
        color: #4bcffa;
        margin-top: 0;
    }
    .cv-check {
        color: #2ed573;
    }
    .cv-cross {
        color: #ff4757;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0c29 0%, #1a1a2e 100%);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Header
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

st.markdown(
    """
    <div class="main-header">
        <h1>🔧 Hardware Sourcing & Specs Agent</h1>
        <p>Autonomous AI agent that researches electronic components — datasheets, pricing, stock, and pinouts.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Sidebar
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    st.markdown("---")
    st.markdown("**Built with:**")
    st.markdown("- 🦜 LangGraph (StateGraph)")
    st.markdown("- 🔍 Tavily Search API")
    st.markdown("- 📐 Pydantic v2 Validation")
    st.markdown("- 🤖 Google Gemini Flash")
    st.markdown("- 🔄 Dual-LLM Cross-Validation")
    st.markdown("---")

    # Graph visualization
    st.markdown("### 📊 Agent Workflow")
    try:
        from src.agent import get_graph_mermaid
        mermaid_code = get_graph_mermaid()
        st.code(mermaid_code, language="mermaid")
    except Exception:
        st.info("Graph visualization available after first run")

    st.markdown("---")
    st.markdown(
        "<small style='color:#666'>Built with Antigravity AI</small>",
        unsafe_allow_html=True,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Input Section
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

col_input, col_btn = st.columns([4, 1])

with col_input:
    component_name = st.text_input(
        "🔎 Enter component name or part number",
        placeholder="e.g., ESP32-WROOM-32, NE555, STM32F103C8T6",
        key="component_input",
        label_visibility="collapsed",
    )

with col_btn:
    search_clicked = st.button(
        "🚀 Search", type="primary", use_container_width=True
    )

# Quick-select chips
st.markdown("**Quick Select:**")
chip_cols = st.columns(7)
quick_components = [
    "ESP32-WROOM-32", "NE555", "STM32F103C8T6",
    "ATmega328P", "RP2040", "LM7805", "MPU6050",
]

def select_chip(comp_name):
    st.session_state["component_input"] = comp_name
    st.session_state["from_chip"] = True

for i, comp in enumerate(quick_components):
    with chip_cols[i]:
        st.button(
            comp,
            key=f"chip_{comp}",
            use_container_width=True,
            on_click=select_chip,
            args=(comp,)
        )

if st.session_state.pop("from_chip", False):
    search_clicked = True

st.markdown("---")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Agent Execution & Results
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if search_clicked and component_name:
    st.session_state["execute_search"] = component_name

component_to_search = st.session_state.get("execute_search", "")

if component_to_search:
    if st.session_state.get("last_searched") != component_to_search:
        from src.agent import compile_graph, AgentState

        # Progress tracking
        with st.status(
            f"🤖 Agent researching **{component_to_search}**...",
            expanded=True,
        ) as status:
            try:
                app_compiled = compile_graph()

                initial_state: AgentState = {
                    "component_query": component_to_search,
                    "search_plan": "",
                    "search_results": [],
                    "datasheet_info": None,
                    "secondary_datasheet_info": None,
                    "cross_validation": None,
                    "pricing_data": [],
                    "stock_status": None,
                    "final_output": None,
                    "error_log": [],
                    "retry_count": 0,
                    "current_step": "initializing",
                    "reasoning_trace": [
                        f"[INIT] Agent initialized for: '{component_to_search}'"
                    ],
                }

                final_state = initial_state
                shown_steps = set([initial_state["reasoning_trace"][0]])
                
                st.write(f"🔹 {initial_state['reasoning_trace'][0]}")
                step_container = st.container()

                # Stream state updates dynamically
                for current_state in app_compiled.stream(initial_state, stream_mode="values"):
                    final_state = current_state
                    trace = current_state.get("reasoning_trace", [])
                    
                    with step_container:
                        for t in trace:
                            if t not in shown_steps:
                                st.write(f"🔹 {t}")
                                shown_steps.add(t)
                report = final_state.get("final_output")

                if report:
                    status.update(
                        label=f"✅ Research complete for **{component_to_search}**",
                        state="complete",
                        expanded=False,
                    )
                else:
                    status.update(
                        label=f"⚠️ Partial results for **{component_to_search}**",
                        state="error",
                    )
                
                st.session_state["cached_report"] = report
                st.session_state["cached_final_state"] = final_state
                st.session_state["last_searched"] = component_to_search

            except Exception as e:
                status.update(
                    label=f"❌ Agent error: {str(e)[:100]}",
                    state="error",
                )
                st.error(f"Agent execution failed: {e}")
                import traceback
                st.code(traceback.format_exc())
                st.session_state["cached_report"] = None
                st.session_state["cached_final_state"] = {}
                st.session_state["last_searched"] = component_to_search

    # Retrieve from cache
    report = st.session_state.get("cached_report")
    final_state = st.session_state.get("cached_final_state", {})

    # ── Display Results ──
    if report:
        st.markdown("## 📋 Component Report")

        # ── Component Info Card ──
        ds_url = report.get("datasheet_url", "")
        ds_button_html = f'<a href="{ds_url}" target="_blank" style="text-decoration: none; background-color: #e94560; color: white; padding: 6px 14px; border-radius: 4px; font-weight: 600; font-size: 0.9rem; margin-top: 0.5rem; display: inline-block;">📄 Official Datasheet</a>' if (ds_url and ds_url != "Not found") else ''

        st.markdown(
            f"""
            <div class="component-card">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <h2 style="margin-top: 0;">{report.get('component_name', 'N/A')}</h2>
                    {ds_button_html}
                </div>
                <p>{report.get('description', 'No description available')}</p>
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; margin-top: 1rem;">
                    <div>
                        <span class="label">Manufacturer</span><br>
                        <span class="value">{report.get('manufacturer', 'N/A')}</span>
                    </div>
                    <div>
                        <span class="label">Package</span><br>
                        <span class="value">{report.get('package_type', 'N/A')}</span>
                    </div>
                    <div>
                        <span class="label">Operating Voltage</span><br>
                        <span class="value">{report.get('operating_voltage', 'N/A')}</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Global Country Selector ──
        breakdown = report.get("pricing_breakdown", [])
        pricing_dicts = [e if isinstance(e, dict) else e.__dict__ for e in breakdown]
        unique_countries = sorted(list(set(e.get("country", "Global") for e in pricing_dicts)))
        selected_country = st.selectbox("🌍 View Metrics For:", options=["All Countries"] + unique_countries)

        filtered_breakdown = [e for e in pricing_dicts if selected_country == "All Countries" or e.get("country") == selected_country]

        num_entries = len(filtered_breakdown)
        if num_entries > 0:
            prices = [e.get("unit_price", 0) for e in filtered_breakdown]
            avg_price = sum(prices) / num_entries
            price_range_str = f"{min(prices):.2f} - {max(prices):.2f}"
            if selected_country == "All Countries":
                currency_symbol = ""
                price_range_str += " (Mixed)"
            else:
                c = filtered_breakdown[0].get("currency", "USD")
                currency_symbol = "₹" if c == "INR" else ("€" if c == "EUR" else ("£" if c == "GBP" else "$"))
            
            tot_stock = sum(e.get("stock_quantity", 0) for e in filtered_breakdown)
            in_stock = tot_stock > 0
        else:
            avg_price = 0.0
            price_range_str = "N/A"
            currency_symbol = ""
            tot_stock = 0
            in_stock = False

        # ── Metrics Row ──
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Average Price", f"{currency_symbol}{avg_price:.2f}", help="Average unit price across selected distributors")
        with col2:
            if price_range_str == "N/A":
                st.metric("Price Range", "N/A", help="Lowest to highest price available")
            else:
                st.metric("Price Range", f"{currency_symbol}{price_range_str}", help="Lowest to highest price available")
        with col3:
            st.metric("Total Stock", f"{tot_stock:,}", help="Total number of components physically available at distributor warehouses")
        with col4:
            st.metric(
                "Status",
                "✅ In Stock" if in_stock else "❌ Out of Stock",
                help="Whether any distributor has >0 units"
            )

        # ── Best Deal ──
        st.markdown(
            f"""
            <div class="best-deal">
                <h3>💎 Best Deal</h3>
                <p>{report.get('best_deal', 'N/A')}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Two-column layout: Pins + Pricing ──
        col_pins, col_pricing = st.columns(2)

        with col_pins:
            st.markdown("### 📌 Key Pins")
            pins = report.get("key_pins_summary", [])
            if pins:
                import pandas as pd
                pin_data = []
                for p in pins:
                    if isinstance(p, dict):
                        pin_data.append({
                            "Pin #": p.get("pin_number", "?"),
                            "Name": p.get("pin_name", "?"),
                            "Function": p.get("function", "?"),
                        })
                    else:
                        pin_data.append({
                            "Pin #": p.pin_number,
                            "Name": p.pin_name,
                            "Function": p.function,
                        })
                df_pins = pd.DataFrame(pin_data)
                st.dataframe(
                    df_pins,
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No pin data available")

        with col_pricing:
            st.markdown("### 💰 Pricing Comparison")
            if pricing_dicts:
                import pandas as pd
                
                with st.expander("⚙️ Advanced Filters", expanded=False):
                    f_col1, f_col2, f_col3 = st.columns(3)
                    with f_col1:
                        table_country_opts = sorted(list(set(e.get("country", "Global") for e in pricing_dicts)))
                        table_countries = st.multiselect("Country Filter", options=table_country_opts, default=table_country_opts)
                    with f_col2:
                        distr_opts = sorted(list(set(e.get("distributor", "Unknown") for e in pricing_dicts)))
                        table_distrs = st.multiselect("Distributor Filter", options=distr_opts, default=distr_opts)
                    with f_col3:
                        all_prices = [e.get("unit_price", 0) for e in pricing_dicts]
                        min_p, max_p = min(all_prices), max(all_prices)
                        price_bounds = (0.0, float(max_p + 1.0)) if min_p == max_p else (float(min_p), float(max_p))
                        price_range_filter = st.slider("Price Range", min_value=price_bounds[0], max_value=price_bounds[1], value=price_bounds)

                # Filter data for table
                table_filtered = []
                for entry in pricing_dicts:
                    if entry.get("country", "Global") not in table_countries:
                        continue
                    if entry.get("distributor", "Unknown") not in table_distrs:
                        continue
                    p = entry.get("unit_price", 0)
                    if not (price_range_filter[0] <= p <= price_range_filter[1]):
                        continue
                    
                    cur = entry.get("currency", "USD")
                    price_str = f"₹{p:.2f}" if cur == "INR" else (f"€{p:.2f}" if cur == "EUR" else (f"£{p:.2f}" if cur == "GBP" else f"${p:.2f}"))

                    table_filtered.append({
                        "Distributor": entry.get("distributor", "?"),
                        "Country": entry.get("country", "Global"),
                        "Price": price_str,
                        "MOQ": entry.get("moq", 0),
                        "Stock": entry.get("stock_quantity", 0),
                        "Purchase": entry.get("url", "#"),
                        "_RawPrice": p
                    })
                
                if table_filtered:
                    df_price = pd.DataFrame(table_filtered)
                    
                    st.dataframe(
                        df_price,
                        column_config={
                            "Distributor": st.column_config.TextColumn("Distributor", help="Distributor Name"),
                            "Country": st.column_config.TextColumn("Country", help="Operating Country of Supplier"),
                            "Price": st.column_config.TextColumn("Price", help="Unit price in local currency"),
                            "MOQ": st.column_config.NumberColumn("MOQ", help="Minimum Order Quantity (Smallest number of units allowed to purchase)", format="%d"),
                            "Stock": st.column_config.NumberColumn("Stock", help="Current stock physically available at warehouse", format="%d"),
                            "Purchase": st.column_config.LinkColumn("Purchase", help="Direct link to the distributor's product page", display_text="Buy Now"),
                            "_RawPrice": None
                        },
                        use_container_width=True,
                        hide_index=True,
                    )

                    # Normalized Bar chart using Altair
                    import altair as alt
                    chart_data = []
                    for row in table_filtered:
                        raw_p = row["_RawPrice"]
                        price_str = row["Price"]
                        
                        # Normalize to USD for chart height comparison dynamically
                        norm_p = raw_p
                        if "₹" in price_str: norm_p = raw_p / 84.0
                        elif "€" in price_str: norm_p = raw_p / 0.92
                        elif "£" in price_str: norm_p = raw_p / 0.79
                        
                        chart_data.append({
                            "Distributor": row["Distributor"],
                            "NormalizedPriceUSD": norm_p,
                            "LocalPriceStr": price_str
                        })
                        
                    df_chart = pd.DataFrame(chart_data)
                    bars = alt.Chart(df_chart).mark_bar(color="#e94560").encode(
                        x=alt.X("Distributor:N", axis=alt.Axis(labelAngle=-45, title="")),
                        y=alt.Y("NormalizedPriceUSD:Q", title="Price (Normalized to USD)"),
                        tooltip=["Distributor", "LocalPriceStr"]
                    )
                    
                    text = bars.mark_text(
                        align='center',
                        baseline='bottom',
                        dy=-5,
                        color='white'
                    ).encode(
                        text='LocalPriceStr:N'
                    )
                    
                    st.altair_chart((bars + text).properties(height=300), use_container_width=True)
                else:
                    st.warning("All pricing data filtered out. Try adjusting your filters!")
            else:
                st.info("No pricing data available")

        # ── Cross-Validation Results ──
        cv_data = report.get("cross_validation")
        if cv_data:
            confidence = cv_data.get("confidence_score", 0)
            verdict = cv_data.get("verdict", "UNKNOWN")

            if "HIGH" in verdict:
                badge_class = "cv-high"
                badge_icon = "🟢"
            elif "MEDIUM" in verdict:
                badge_class = "cv-medium"
                badge_icon = "🟡"
            else:
                badge_class = "cv-low"
                badge_icon = "🔴"

            st.markdown("### 🔄 Dual-LLM Cross-Validation")
            st.markdown(
                f"""
                <div class="cv-card">
                    <h3>{badge_icon} {verdict}</h3>
                    <p style="color: #c4c4e0;">Confidence Score: <b>{confidence:.0%}</b></p>
                    <p style="color: #888; font-size: 0.9rem;">
                        Primary: <b>{cv_data.get('primary_llm', 'N/A')}</b> &nbsp;|&nbsp;
                        Secondary: <b>{cv_data.get('secondary_llm', 'N/A')}</b>
                    </p>
                    <div style="margin-top: 0.8rem;">
                        <span class="{'cv-check' if cv_data.get('manufacturer_match') else 'cv-cross'}">{'✅' if cv_data.get('manufacturer_match') else '❌'} Manufacturer</span> &nbsp;&nbsp;
                        <span class="{'cv-check' if cv_data.get('description_match') else 'cv-cross'}">{'✅' if cv_data.get('description_match') else '❌'} Description</span> &nbsp;&nbsp;
                        <span class="{'cv-check' if cv_data.get('pin_count_match') else 'cv-cross'}">{'✅' if cv_data.get('pin_count_match') else '❌'} Pin Count</span> &nbsp;&nbsp;
                        <span class="{'cv-check' if cv_data.get('voltage_match') else 'cv-cross'}">{'✅' if cv_data.get('voltage_match') else '❌'} Voltage</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            discrepancies = cv_data.get("discrepancies", [])
            if discrepancies:
                with st.expander("⚠️ Discrepancies Found", expanded=True):
                    for d in discrepancies:
                        st.warning(d)

        # ── Reasoning Trace ──
        with st.expander("🧠 Agent Reasoning Trace", expanded=False):
            trace = report.get("agent_reasoning_trace", [])
            if trace:
                for i, step in enumerate(trace, 1):
                    st.markdown(
                        f'<div class="trace-step"><b>Step {i}:</b> {step}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No reasoning trace available")

        # ── Raw JSON ──
        with st.expander("📝 Raw JSON Output", expanded=False):

            class _DateEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    return super().default(obj)

            st.code(
                json.dumps(report, indent=2, cls=_DateEncoder),
                language="json",
            )

    # Show errors if any
    errors = final_state.get("error_log", [])
    if errors:
        with st.expander("⚠️ Errors / Warnings", expanded=False):
            for err in errors:
                st.warning(err)

elif search_clicked and not component_name:
    st.warning("Please enter a component name to search.")
else:
    # Landing state - show instructions
    st.markdown(
        """
        <div style="text-align: center; padding: 3rem; color: #888;">
            <h3>Enter a component name above to get started</h3>
            <p>Try searching for <b>ESP32-WROOM-32</b>, <b>NE555</b>, or <b>STM32F103C8T6</b></p>
        </div>
        """,
        unsafe_allow_html=True,
    )
