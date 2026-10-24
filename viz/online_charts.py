# viz/online_charts.py
import plotly.graph_objects as go
import pandas as pd


def plot_degradation(df: pd.DataFrame, current_err: float = None):
    fig = go.Figure()

    # Convert error levels to percentage labels; force categorical axis
    x_labels = [f"{int(e * 100)}%" for e in df['error_level']]

    fig.add_trace(go.Scatter(
        x=x_labels, y=df['cost_degradation'] * 100,
        mode='lines+markers', name='Cost Degradation',
        line=dict(color='firebrick', width=3), marker=dict(size=8)
    ))
    fig.add_trace(go.Scatter(
        x=x_labels, y=df['carbon_degradation'] * 100,
        mode='lines+markers', name='Carbon Degradation',
        line=dict(color='forestgreen', width=3), marker=dict(size=8)
    ))

    # Highlight the currently selected point
    if current_err is not None:
        row = df[df['error_level'] == current_err]
        if not row.empty:
            curr_label = f"{int(current_err * 100)}%"
            # Highlight cost point
            fig.add_trace(go.Scatter(
                x=[curr_label], y=[row['cost_degradation'].iloc[0] * 100],
                mode='markers', marker=dict(size=16, color='blue', symbol='circle-open', line=dict(width=3)),
                name='Current Selection'
            ))
            # Highlight carbon point
            fig.add_trace(go.Scatter(
                x=[curr_label], y=[row['carbon_degradation'].iloc[0] * 100],
                mode='markers', marker=dict(size=16, color='blue', symbol='circle-open', line=dict(width=3)),
                showlegend=False
            ))

    fig.update_layout(
        title="Forecast Error vs Metric Degradation",
        xaxis_title="Price Forecast Error Level",
        yaxis_title="Degradation vs Perfect Forecast (%)",
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor='white'
    )
    # Categorical x-axis avoids meaningless intermediate ticks
    fig.update_xaxes(type='category')
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    return fig


def plot_forecast_comparison(true_p, pred_p):
    fig = go.Figure()
    x = [f"{i:02d}:00" for i in range(24)]

    fig.add_trace(go.Scatter(x=x, y=true_p, name="True Price", line=dict(color="black", width=3)))
    fig.add_trace(go.Scatter(x=x, y=pred_p, name="Predicted Price", line=dict(color="red", width=2, dash='dash')))

    fig.update_layout(
        title="Example: Predicted vs True Price (one day)",
        xaxis_title="Time",
        yaxis_title="Price (CNY/kWh)",
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor='white'
    )
    return fig