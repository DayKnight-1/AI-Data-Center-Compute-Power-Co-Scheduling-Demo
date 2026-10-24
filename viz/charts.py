# viz/charts.py
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import pydeck as pdk
from scheduler.model import Problem, Schedule


def plot_gantt(schedule: Schedule, p: Problem):
    fig = go.Figure()
    T = int(p.horizon / p.dt)

    x_hours = list(range(T))
    fig.add_trace(go.Scatter(
        x=x_hours, y=p.curves.rigid_load,
        fill='tozeroy', mode='lines', name='Real-time Inference (kW)',
        line=dict(color='rgba(200, 200, 200, 0.5)', width=1),
        fillcolor='rgba(220, 220, 220, 0.3)',
        yaxis='y2', hoverinfo='skip'
    ))

    colors = {"slow": "rgba(46, 134, 193, 0.4)", "std": "rgba(46, 134, 193, 0.8)", "fast": "rgba(46, 134, 193, 1.0)"}
    colors_elastic = {"slow": "rgba(82, 190, 128, 0.4)", "std": "rgba(82, 190, 128, 0.8)",
                      "fast": "rgba(82, 190, 128, 1.0)"}

    y_labels = []

    # Sort by task ID for stable rendering
    sorted_tasks = sorted(p.tasks, key=lambda x: x.id)

    for task in sorted_tasks:
        blocks = schedule.assignment.get(task.id, [])

        # Handle unscheduled (missed) tasks
        if not blocks:
            if task.kind == "deadline":
                y_label = f"T{task.id:02d} Training (D:{int(task.deadline):02d}) ❌ Missed"
            else:
                y_label = f"T{task.id:02d} Elastic ❌ Missed"
            y_labels.append(y_label)

            # Draw a bold red dotted line across the whole day to indicate it should have run
            fig.add_trace(go.Scatter(
                x=[0, 24], y=[y_label, y_label],
                mode='lines', line=dict(color='red', width=2, dash='dot'),
                name='Unfinished Task', showlegend=False, hoverinfo='text',
                hovertext=f"Task {task.id} missed its deadline!"
            ))
            # Put a big red cross at the deadline
            if task.kind == "deadline":
                fig.add_trace(go.Scatter(
                    x=[task.deadline], y=[y_label],
                    mode='markers', marker=dict(symbol='x', size=12, color='red'),
                    showlegend=False, hoverinfo='skip'
                ))
            continue  # Skip the normal bar drawing

        # Scheduled tasks
        if task.kind == "deadline":
            y_label = f"T{task.id:02d} Training (D:{int(task.deadline):02d})"
        else:
            y_label = f"T{task.id:02d} Elastic"
        y_labels.append(y_label)

        # Merge consecutive blocks
        segments = []
        curr_start = blocks[0][0]
        curr_tier = blocks[0][1]
        curr_dur = 1
        for i in range(1, len(blocks)):
            if blocks[i][0] == blocks[i - 1][0] + 1 and blocks[i][1] == curr_tier:
                curr_dur += 1
            else:
                segments.append((curr_start, curr_dur, curr_tier))
                curr_start = blocks[i][0]
                curr_tier = blocks[i][1]
                curr_dur = 1
        segments.append((curr_start, curr_dur, curr_tier))

        is_interrupted = schedule.interrupt_count.get(task.id, 0) > 0
        c_map = colors if task.kind == "deadline" else colors_elastic

        for (start_t, dur, tier) in segments:
            fig.add_trace(go.Bar(
                y=[y_label], x=[dur], base=[start_t], orientation='h',
                marker=dict(
                    color=c_map[tier],
                    pattern=dict(shape='/', fgcolor='white') if is_interrupted else None
                ),
                name=task.kind, showlegend=False,
                hoverinfo="text", hovertext=f"T{task.id} | Tier: {tier} | Interrupted: {is_interrupted}"
            ))

        # Deadline marker for deadline tasks
        if task.kind == "deadline":
            fig.add_trace(go.Scatter(
                x=[task.deadline], y=[y_label],
                mode='markers', marker=dict(symbol='triangle-down', size=10, color='orange'),
                name='Deadline', showlegend=False, hoverinfo='text', hovertext=f"Deadline: {int(task.deadline):02d}:00"
            ))

    # Legend
    fig.add_trace(go.Bar(y=[y_labels[0] if y_labels else ""], x=[0], marker=dict(color="rgba(46, 134, 193, 1.0)"),
                         name="Deadline Task (Blue)", showlegend=True, hoverinfo='skip'))
    fig.add_trace(go.Bar(y=[y_labels[0] if y_labels else ""], x=[0], marker=dict(color="rgba(82, 190, 128, 1.0)"),
                         name="Elastic Task (Green)", showlegend=True, hoverinfo='skip'))
    fig.add_trace(go.Bar(y=[y_labels[0] if y_labels else ""], x=[0],
                         marker=dict(color="gray", pattern=dict(shape='/', fgcolor='white')), name="Hatched = Interrupted",
                         showlegend=True, hoverinfo='skip'))
    fig.add_trace(go.Scatter(x=[0], y=[y_labels[0] if y_labels else ""], mode='lines',
                             line=dict(color='red', width=2, dash='dot'), name="Dotted Red = Missed", showlegend=True,
                             hoverinfo='skip'))

    fig.update_layout(
        title="Task Scheduling Gantt Chart",
        xaxis=dict(tickvals=list(range(0, 25, 4)), ticktext=[f"{i:02d}:00" for i in range(0, 25, 4)], range=[0, 24]),
        yaxis=dict(type='category', autorange="reversed", title=""),
        yaxis2=dict(overlaying='y', side='right', range=[0, max(p.curves.rigid_load) * 1.5], showgrid=False,
                    title="Rigid Load (kW)"),
        barmode='overlay',
        height=450, margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor='white',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig


def plot_curves(p: Problem):
    fig = go.Figure()
    x = [f"{i:02d}:00" for i in range(int(p.horizon))]
    fig.add_trace(go.Scatter(x=x, y=p.curves.grid_price, name="Grid Price", line=dict(color="red", width=2)))
    fig.add_trace(
        go.Scatter(x=x, y=p.curves.green_avail / 100, name="Green Power", line=dict(color="green", width=2)))
    fig.add_trace(go.Scatter(x=x, y=p.curves.carbon, name="Carbon Intensity", line=dict(color="orange", width=2, dash='dot')))
    fig.update_layout(
        title="Power–Carbon Price Mismatch", height=300,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig


def plot_power(p: Problem, schedule: Schedule, t_idx: int):
    x = [f"{i:02d}:00" for i in range(int(p.horizon))]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=schedule.green_power, name="Green Power", marker_color="mediumseagreen"))
    fig.add_trace(go.Bar(x=x, y=schedule.grid_power, name="Grid", marker_color="salmon"))
    fig.add_trace(go.Scatter(x=x, y=schedule.soc, name="Battery SOC", yaxis="y2", line=dict(color="blue", width=3)))
    fig.add_vline(x=t_idx, line_width=3, line_dash="dash", line_color="red")
    fig.update_layout(
        title=f"Power Allocation & Battery SOC (Now: {t_idx:02d}:00)", barmode='stack', height=300,
        yaxis2=dict(overlaying='y', side='right', range=[0, 1200]),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig


def build_gpu_deck(p, schedule, t_idx: int):
    grid_data = []
    total_load = schedule.green_power[t_idx] + schedule.grid_power[t_idx]

    # Assume 2.0 kW per fully-loaded GPU; compute average utilization
    avg_load_ratio = min(1.0, (total_load / 400.0) / 2.0)

    # Deterministic pseudo-random (seeded by t_idx) for visual variety
    rng = np.random.default_rng(t_idx * 42 + 100)

    # --- Shanghai center & scale ---
    CENTER_LON = 121.47
    CENTER_LAT = 31.23
    # Step size for array density (0.02° ≈ 2.2 km; 20 points ≈ 44 km)
    SPAN = 0.02

    for r in range(20):
        for c in range(20):
            # Add variance: some GPUs busy, some idle
            variance = rng.uniform(0.3, 1.3)
            val = min(1.0, avg_load_ratio * variance)

            # Color mapping
            if val < 0.3:
                color = [0, 255, 0, 255]  # Green
            elif val < 0.7:
                color = [255, 255, 0, 255]  # Yellow
            else:
                color = [255, 0, 0, 255]  # Red

            # --- Map to Shanghai vicinity ---
            # Center c and r (0-19) and spread around Shanghai center
            lon = CENTER_LON + (c - 9.5) * SPAN
            lat = CENTER_LAT + (r - 9.5) * SPAN

            # --- Adjust column height and radius ---
            # Horizontally compressed, so vertical scale is also reduced (else needles)
            # Height scaled down: base 1 km, max ~16 km
            grid_data.append({
                "pos": [lon, lat],
                "color": color,
                "elev": val * 15000 + 1000
            })

    df = pd.DataFrame(grid_data)

    layer = pdk.Layer(
        "ColumnLayer", df,
        get_position="pos",
        get_elevation="elev",
        elevation_scale=1,
        radius=1000,  # Radius ~1 km so gaps remain between columns
        get_fill_color="color",
        extruded=True,
        pickable=True
    )

    # --- Recenter view on Shanghai ---
    view_state = pdk.ViewState(
        latitude=CENTER_LAT,
        longitude=CENTER_LON,
        zoom=8.5,
        pitch=60,
        bearing=45
    )

    return pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style=None,     # Disable map style
        map_provider=None,  # Disable map provider (if map still appears, pydeck version issue)
        height=300          # Set Deck default height
    )