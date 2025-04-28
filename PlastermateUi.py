import streamlit as st
import numpy as np
import plotly.graph_objects as go
from scipy.ndimage import gaussian_filter
import time

# --- Session State Initialization ---
for key, default in {
    "saved_scans": {},
    "scan_counter": 1,
    "latest_run_figure": None,
    "view_mode": "none",      # "none", "latest", "saved"
    "selected_saved_scan_name": None
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- Heatmap Generation ---
def generate_heatmap():
    wall_width, wall_height, grid_points = 10, 10, 100
    x = np.linspace(0, wall_width, grid_points)
    y = np.linspace(0, wall_height, grid_points)
    X, Y = np.meshgrid(x, y)
    noise = np.random.rand(grid_points, grid_points) * np.random.uniform(0.3, 0.8)
    pattern = np.sin(X * np.random.uniform(0.5, 1.5)) + np.cos(Y * np.random.uniform(0.5, 1.5))
    data = gaussian_filter(pattern + noise, sigma=2)
    fig = go.Figure(go.Heatmap(
        z=data, x=x, y=y, colorscale="Viridis",
        colorbar=dict(title="Thickness (mm)")
    ))
    fig.update_layout(
        title="Wall Plastering Heatmap (10m x 10m)",
        xaxis=dict(title="Width (m)", range=[0,10], dtick=1),
        yaxis=dict(title="Height (m)", range=[0,10], dtick=1, scaleanchor="x", scaleratio=1),
        height=700, margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig

# --- Callback: Select Saved Scan ---
def on_select_saved():
    sel = st.session_state.get("saved_scan_selectbox", "")
    if sel and sel in st.session_state.saved_scans:
        st.session_state.selected_saved_scan_name = sel
        st.session_state.view_mode = "saved"
        st.session_state.latest_run_figure = None
    else:
        st.session_state.selected_saved_scan_name = None
        st.session_state.view_mode = "none"

# --- Page Config ---
st.set_page_config(page_title="Plastermate", layout="wide")

# --- Sidebar ---
with st.sidebar:
    st.title("🧱 Plastermate")
    st.header("Controls")

    # New Analysis
    if st.button("▶️ New Analysis", type="primary", use_container_width=True):
        st.session_state.latest_run_figure = generate_heatmap()
        st.session_state.view_mode = "latest"
        st.session_state.selected_saved_scan_name = None

    st.markdown("---")
    st.header("Saved Scans")

    if st.session_state.saved_scans:
        names = list(st.session_state.saved_scans.keys())
        options = [""] + names
        idx = 0
        if st.session_state.selected_saved_scan_name in names:
            idx = names.index(st.session_state.selected_saved_scan_name) + 1
        st.selectbox(
            "", options,
            index=idx,
            key="saved_scan_selectbox",
            on_change=on_select_saved,
            format_func=lambda v: "Choose a scan..." if v == "" else v,
            help="Select or clear a saved scan"
        )
        if st.session_state.selected_saved_scan_name:
            if st.button(
                f"🗑️ Delete {st.session_state.selected_saved_scan_name}", use_container_width=True
            ):
                del st.session_state.saved_scans[st.session_state.selected_saved_scan_name]
                # Snow animation
                st.snow()
                # Brief pause to show effect
                time.sleep(0.5)
                st.success("Scan deleted.")
                # Reset view
                st.session_state.view_mode = "none"
                st.session_state.selected_saved_scan_name = None
                st.rerun()
    else:
        st.info("No saved scans.")

# --- Main Area ---
with st.container():
    mode = st.session_state.view_mode

    # Latest Analysis View
    if mode == "latest" and st.session_state.latest_run_figure:
        st.subheader("Latest Heatmap")
        st.plotly_chart(st.session_state.latest_run_figure, use_container_width=True)

        # Save Section
        with st.expander("💾 Save This Scan", expanded=True):
            name_input = st.text_input(
                "Save As", key="custom_scan_name_input",
                placeholder=f"Scan {st.session_state.scan_counter}"
            )
            if st.button(
                "Save This Scan", type="primary", use_container_width=True, key="save_btn"
            ):
                final_name = name_input.strip() or f"Scan {st.session_state.scan_counter}"
                # Progress animation
                progress = st.progress(0)
                for i in range(1, 101):
                    time.sleep(0.005)
                    progress.progress(i)
                progress.empty()
                # Save
                st.session_state.saved_scans[final_name] = st.session_state.latest_run_figure
                st.session_state.scan_counter += 1
                # Celebration
                st.balloons()
                st.success(f"Successfully saved as '{final_name}'!")
                # Reset to default
                st.session_state.view_mode = "none"
                st.session_state.selected_saved_scan_name = None
                st.session_state.latest_run_figure = None
                st.rerun()

    # Saved Scan View
    elif mode == "saved" and st.session_state.selected_saved_scan_name:
        sel_name = st.session_state.selected_saved_scan_name
        with st.spinner("Loading saved scan..."):
            time.sleep(0.5)
        st.subheader(f"Saved Scan: {sel_name}")
        st.plotly_chart(st.session_state.saved_scans[sel_name], use_container_width=True)

    # Placeholder View
    else:
        st.info("Run a new analysis or select a saved scan to view.")
