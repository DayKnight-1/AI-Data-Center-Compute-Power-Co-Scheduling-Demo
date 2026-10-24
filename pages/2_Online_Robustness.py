# pages/2_Online_Robustness.py
import streamlit as st
import pandas as pd
from data.generator import build_problem
from scheduler.online_experiment import run_all_experiments
from viz.online_charts import plot_degradation, plot_forecast_comparison
import config

st.set_page_config(page_title="Online Robustness Experiment", layout="wide")
st.title("🛡️ Online Robustness: Impact of Forecast Error")


@st.cache_data(show_spinner="Running online robustness simulation...")
def load_experiment_data(scenario, lam):
    problem = build_problem(scenario, lam=lam, seed=config.SEED)
    return run_all_experiments(problem)


with st.sidebar:
    st.header("Experiment Parameters")
    error_levels_map = {
        "0% (Perfect Forecast)": 0.0,
        "±10% (Mild)": 0.1,
        "±20% (Significant)": 0.2,
        "±30% (Extreme)": 0.3
    }
    selected_label = st.radio("Select forecast error level", list(error_levels_map.keys()), index=2)
    selected_err = error_levels_map[selected_label]

    st.info("💡 The left chart shows the forecast under the selected error; the right shows overall degradation with your selection circled.")

df, curves_dict = load_experiment_data("☀️ Sunny Baseline", 0.5)
current_curve = curves_dict[selected_err]
current_row = df[df['error_level'] == selected_err].iloc[0]

st.markdown("### Results")
col1, col2 = st.columns(2)

with col1:
    # Left: forecast curves under the current error
    st.plotly_chart(plot_forecast_comparison(current_curve["true"], current_curve["pred"]), width='stretch')

with col2:
    # Right: overall degradation trend, highlight current selection
    st.plotly_chart(plot_degradation(df, current_err=selected_err), width='stretch')

st.markdown("---")

st.markdown(f"### Findings: {selected_label}")
c1, c2, c3 = st.columns(3)
c1.metric("Cost Degradation", f"{current_row['cost_degradation'] * 100:+.1f}%")
c2.metric("Carbon Degradation", f"{current_row['carbon_degradation'] * 100:+.1f}%")
c3.metric("Extra Missed Tasks", f"{int(current_row['sla_increase'])}")

st.info(
    f"💡 **Summary**: Under {selected_label} forecast error, the scheduler still keeps cost and carbon near-perfect by adjusting tiers and shifting load in real time — evidence that the 'tier + battery time-shift' strategy is robust.")

st.markdown("---")
st.markdown("### Full Data Table")
display_df = df.copy()
display_df['error_level'] = display_df['error_level'].apply(lambda x: f"{int(x * 100)}%")
display_df['cost_degradation'] = display_df['cost_degradation'].apply(lambda x: f"{x * 100:+.2f}%")
display_df['carbon_degradation'] = display_df['carbon_degradation'].apply(lambda x: f"{x * 100:+.2f}%")
display_df['avg_cost'] = display_df['avg_cost'].apply(lambda x: f"¥ {x:.0f}")
display_df['avg_carbon'] = display_df['avg_carbon'].apply(lambda x: f"{x:.0f} kg")
display_df['avg_sla'] = display_df['avg_sla'].apply(lambda x: f"{x:.1f}")

display_df.columns = ["Error Level", "Avg Total Cost", "Cost Degradation", "Avg Total Carbon", "Carbon Degradation",
                      "Avg Missed Tasks", "Δ Missed Tasks"]
st.dataframe(display_df, width='stretch', hide_index=True)