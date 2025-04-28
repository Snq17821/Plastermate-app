import streamlit as st
import numpy as np
import plotly.graph_objects as go
from scipy.ndimage import gaussian_filter

# --- Session State Management ---
# Initialize state variables
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
    pattern = np.sin(X * np.random.uniform(0.5, 1.5)) + np.cos(Y * np.random.uniform(0.5, 1.5))
    noise = np.random.rand(grid_points, grid_points) * np.random.uniform(0.3, 0.8)
    data = gaussian_filter(pattern + noise, sigma=2)
    fig = go.Figure(go.Heatmap(
        z=data, x=x, y=y, colorscale="Viridis", colorbar=dict(title="Thickness (mm)")
    ))
    fig.update_layout(
        title="Wall Plastering Heatmap (10m x 10m)",
        xaxis=dict(title="Width (m)", range=[0,10], dtick=1),
        yaxis=dict(title="Height (m)", range=[0,10], dtick=1, scaleanchor="x", scaleratio=1),
        height=700, margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig

# --- Callback for Saving and Selecting ---
def on_select_saved():
    sel = st.session_state.saved_scan_selectbox
    if sel and sel in st.session_state.saved_scans:
        st.session_state.selected_saved_scan_name = sel
        st.session_state.view_mode = "saved"
        st.session_state.latest_run_figure = None
    else:
        st.session_state.selected_saved_scan_name = None
        st.session_state.view_mode = "none"

# --- App Configuration ---
st.set_page_config(page_title="Plastermate", layout="wide")

# --- Sidebar ---
with st.sidebar:
    st.title("🧱 Plastermate")
    st.header("Controls")

    # Run New Analysis
    if st.button("▶️ New Analysis", type="primary", use_container_width=True):
        st.session_state.latest_run_figure = generate_heatmap()
        st.session_state.view_mode = "latest"
        st.session_state.selected_saved_scan_name = None

    st.markdown("---")
    st.header("Saved Scans")

    # Saved scans dropdown
    if st.session_state.saved_scans:
        names = list(st.session_state.saved_scans.keys())
        options = [""] + names
        # Determine selectbox index (0 = placeholder)
        idx = names.index(st.session_state.selected_saved_scan_name) + 1 \
            if st.session_state.selected_saved_scan_name in names else 0
        st.selectbox(
            "", options,
            index=idx,
            key="saved_scan_selectbox",
            on_change=on_select_saved,
            format_func=lambda v: "Choose a scan..." if v == "" else v,
            help="Select or clear a saved scan"
        )

        # Delete button
        if st.session_state.selected_saved_scan_name:
            if st.button(f"🗑️ Delete {st.session_state.selected_saved_scan_name}", use_container_width=True):
                del st.session_state.saved_scans[st.session_state.selected_saved_scan_name]
                st.success("Deleted successfully.")
                st.session_state.view_mode = "none"
                st.session_state.selected_saved_scan_name = None
                st.rerun()
    else:
        st.info("No scans saved yet.")

# --- Main Display ---
with st.container():
    mode = st.session_state.view_mode
    # Latest analysis view
    if mode == "latest" and st.session_state.latest_run_figure:
        st.subheader("Latest Heatmap")
        st.plotly_chart(st.session_state.latest_run_figure, use_container_width=True)

        with st.expander("💾 Save This Scan", expanded=True):
            scan_name = st.text_input(
                "Save As", key="custom_scan_name_input",
                placeholder=f"Scan {st.session_state.scan_counter}"
            )
            st.write("")
            if st.button("Save This Scan", type="primary", use_container_width=True, key="save_btn"):
                name = scan_name.strip() or f"Scan {st.session_state.scan_counter}"
                st.session_state.saved_scans[name] = st.session_state.latest_run_figure
                st.session_state.scan_counter += 1
                st.session_state.view_mode = "saved"
                st.session_state.selected_saved_scan_name = name
                st.success(f"Saved as '{name}' 🎉")
                st.rerun()

    # Saved scan view
    elif mode == "saved" and st.session_state.selected_saved_scan_name:
        name = st.session_state.selected_saved_scan_name
        st.subheader(f"Saved Scan: {name}")
        st.plotly_chart(st.session_state.saved_scans[name], use_container_width=True)

    # Placeholder
    else:
        st.info("Run a new analysis or select a saved scan to view.")
