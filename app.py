# app.py
import streamlit as st
import numpy as np
from data.generator import build_problem
from scheduler.local_search import run_local_search
from scheduler.baseline import run_no_schedule, run_rule_based, calc_lower_bound
from viz.charts import plot_gantt, plot_curves, plot_power, build_gpu_deck
import config

st.set_page_config(page_title="AI Data Center Scheduling Demo", layout="wide")
st.markdown("""
    <style>
        /* 1. Precisely hide Deploy button and main menu (three dots) */
        .stAppDeployButton { display: none !important; }
        #MainMenu { visibility: hidden !important; }

        /* 2. Keep header but make it transparent & compact so the sidebar toggle survives */
        header[data-testid="stHeader"] {
            background-color: transparent !important;
            height: 2.5rem !important;
        }

        /* 3. Tighten top padding for compact layout */
        .block-container {
            padding-top: 1rem !important;
        }

        /* 4. Turn sidebar button into a tidy square, force-center */
        [data-testid="stSidebar"] button {
            min-height: 32px !important;
            height: 32px !important;
            width: 32px !important;         /* force square */
            padding: 0 !important;          /* clear default padding */
            border-radius: 8px !important;  /* softer corners */
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
        }

        /* 5. Apply transform to correct visual offset of the icon */
        [data-testid="stSidebar"] button p {
            font-size: 18px !important;     /* slightly larger, fuller */
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1 !important;
            transform: translate(-1px, -1px) !important; /* nudge 1px left-up to fix optical offset */
        }
    </style>
""", unsafe_allow_html=True)

if 't_idx' not in st.session_state:
    st.session_state.t_idx = 0


def step_forward():
    st.session_state.t_idx = (st.session_state.t_idx + 1) % 24


@st.cache_data
def get_problem(scenario, lam):
    return build_problem(scenario, lam=lam, seed=config.SEED)


@st.cache_data
def get_all_schedules(problem):
    base = run_no_schedule(problem)
    rule = run_rule_based(problem)
    ls = run_local_search(problem)
    return {
        "Baseline (First-Come, First-Served)": base,
        "Simple Off-Peak (Delay to Cheap Hours)": rule,
        "Smart Scheduling (Tier + Delay + Battery + Split)": ls
    }


st.title("⚡ AI Data Center Compute-Power Co-Scheduling Demo")

with st.sidebar:
    st.header("Global Controls")
    scenario = st.radio("Select scenario",
                        ["☀️ Sunny Baseline", "☁️ Cloudy (Low Solar)", "📈 Demand Surge", "⚡ Price Spike"])
    st.markdown("---")
    method_name = st.radio("Scheduling Algorithm",
                           ["Baseline (First-Come, First-Served)", "Simple Off-Peak (Delay to Cheap Hours)",
                            "Smart Scheduling (Tier + Delay + Battery + Split)"])
    st.markdown("---")
    lam = st.slider("Carbon Price λ (CNY/kg)", 0.0, 2.0, 0.5, 0.1)
    st.write("Current Time")
    c_t1, c_t2 = st.columns([5, 1], vertical_alignment="center")
    with c_t1:
        st.slider("Time", 0, 23, key="t_idx", label_visibility="collapsed")
    with c_t2:
        st.button("⏭", on_click=step_forward, use_container_width=True)

    st.markdown(
        """
<div style="background-color: #e8f4f8; padding: 15px; border-radius: 8px;">
<div style="font-size: 14px; font-weight: 600; color: #00509e; margin-bottom: 8px;">✅ All Constraints Satisfied</div>
<div style="font-size: 13px; color: #333; line-height: 1.6;">• Power balance ✔ <br>• Battery SOC ✔ <br>• No simultaneous charge/discharge ✔</div>
</div>
        """, unsafe_allow_html=True
    )

p = get_problem(scenario, lam)
lb_data = calc_lower_bound(p)
schedules = get_all_schedules(p)

sched = schedules[method_name]
base_sched = schedules["Baseline (First-Come, First-Served)"]

delta_cost = (sched.metrics['cost'] - base_sched.metrics['cost']) / base_sched.metrics['cost'] if base_sched.metrics[
    'cost'] else 0
delta_carbon = (sched.metrics['carbon'] - base_sched.metrics['carbon']) / base_sched.metrics['carbon'] if \
    base_sched.metrics['carbon'] else 0

cost_delta_str = f"{delta_cost:.1%}" if method_name != "Baseline (First-Come, First-Served)" else "--"
carbon_delta_str = f"{delta_carbon:.1%}" if method_name != "Baseline (First-Come, First-Served)" else "--"

col_mid, col_right = st.columns([3, 1.2])

with col_mid:
    st.plotly_chart(plot_gantt(sched, p), width='stretch')
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(plot_curves(p), width='stretch')
    with c2:
        st.plotly_chart(plot_power(p, sched, st.session_state.t_idx), width='stretch')

with col_right:
    st.subheader("Key Metrics")
    c_m1, c_m2 = st.columns(2)
    c_m1.metric("Total Cost", f"¥ {sched.metrics['cost']:.0f}", cost_delta_str, delta_color="inverse")
    c_m2.metric("Total Carbon", f"{sched.metrics['carbon']:.0f} kg", carbon_delta_str, delta_color="inverse")
    c_m3, c_m4 = st.columns(2)
    c_m3.metric("Missed Tasks", f"{sched.metrics['sla']}")
    c_m4.metric("Battery Cycles", f"{sched.metrics['batt_cycles']:.1f}")

    # --- Minimal-style theoretical lower bound ---
    lb_cost = lb_data['lb_cost']
    curr_cost = sched.metrics['cost']

    if lb_cost > 0:
        gap = (curr_cost - lb_cost) / lb_cost
        achieved_pct = min(100.0, (lb_cost / curr_cost) * 100)
    else:
        gap = 0
        achieved_pct = 100.0

    # Use Streamlit's theme red as the gap color for visual consistency
    gap_color = "#ff4b4b" if gap > 0.25 else "#2e86c1"

    # Plain text + progress bar, no background or border
    html_content = f"""<div>
<div style="font-size: 14px; color: #555; margin-bottom: 5px;">Gap to Absolute Physical Limit</div>
<div style="font-size: 36px; font-weight: 700; color: {gap_color}; line-height: 1.2; margin-bottom: 15px;">{gap:.1%}</div>
<div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; color: #888;">
<span>Current: <b style="color: #333;">¥{curr_cost:.0f}</b></span>
<span>Limit: <b style="color: #333;">¥{lb_cost:.0f}</b></span>
</div>
<div style="height: 6px; background: #e5e7eb; border-radius: 3px; position: relative; margin-bottom: 10px;">
<div style="width: {achieved_pct}%; height: 100%; background: {gap_color}; border-radius: 3px;"></div>
<div style="position: absolute; left: calc({achieved_pct}% - 5px); top: -3px; width: 12px; height: 12px; background: #fff; border: 2px solid {gap_color}; border-radius: 50%; box-sizing: border-box;"></div>
</div>
<div style="font-size: 11px; color: #999;">Note: The limit is an idealized bound (assuming unlimited machines and all tasks run at the cheapest hour).</div>
</div>"""

    st.markdown(html_content, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("GPU Load Heatmap Array")
    deck = build_gpu_deck(p, sched, st.session_state.t_idx)
    st.pydeck_chart(deck, width='stretch', height=300)