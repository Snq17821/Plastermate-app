import streamlit as st
import numpy as np
import plotly.graph_objects as go
from scipy.ndimage import gaussian_filter
import time
import math
import io # Needed to read the uploaded file content

# --- Session State Initialization ---
for key, default in {
    "saved_scans": {},
    "scan_counter": 1,
    "latest_run_figure": None,
    "view_mode": "none",      # "none", "latest", "saved"
    "selected_saved_scan_name": None,
    "just_saved": False,      # Flag to show success header
    "uploaded_file_state": None # To track the uploaded file
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- LiDAR Data Processing and Heatmap Generation ---
def process_lidar_data_and_generate_heatmap(file_content_string):
    """
    Processes LiDAR data from a string buffer and generates a Plotly heatmap
    with fixed ranges and a 1:1 aspect ratio for a 2m high x 4m wide wall.

    Args:
        file_content_string (str): The content of the uploaded LiDAR data file.

    Returns:
        plotly.graph_objects.Figure or None: The generated heatmap figure,
                                             or None if an error occurs.
    """
    levels, azimuths, dists = [], [], []
    try:
        lvl = None
        # Use io.StringIO to treat the string content like a file
        with io.StringIO(file_content_string) as f:
            for line in f:
                line = line.strip()
                if not line: continue
                if line.startswith('Level'):
                    # Basic validation
                    parts = line.split()
                    if len(parts) != 2 or not parts[1].isdigit():
                        st.error(f"Error parsing level line: '{line}'. Expected 'Level <number>'.")
                        return None
                    lvl = int(parts[1])
                elif lvl is not None: # Ensure we have a level before processing data points
                    # Basic validation
                    parts = line.split(',')
                    if len(parts) != 2:
                        st.error(f"Error parsing data line: '{line}'. Expected '<azimuth>,<distance>'.")
                        return None
                    try:
                        a, d = map(float, parts)
                    except ValueError:
                        st.error(f"Error converting data to numbers on line: '{line}'.")
                        return None
                    levels.append(lvl)
                    azimuths.append(a)
                    dists.append(d)
                else:
                    st.warning(f"Skipping data line before first 'Level' declaration: '{line}'")


        if not levels: # Check if any data was actually parsed
            st.error("No valid data points found in the file.")
            return None

        # 2) Convert polar (r, elev, azimuth) -> Cartesian (X, Z)
        #    Motor elevation per level = (level-1)*1.8 degrees
        X, Z = [], []
        for lvl, azi_deg, r in zip(levels, azimuths, dists):
            elev_deg = (lvl - 1) * 1.8          # 0, 1.8, 3.6, ... degrees
            theta_e = math.radians(elev_deg)     # motor tilt
            theta_a = math.radians(azi_deg)      # lidar scan angle

            # Compute true offsets in mm:
            x_mm = r * math.cos(theta_e) * math.sin(theta_a)
            z_mm = r * math.sin(theta_e)

            # Convert to meters
            X.append(x_mm / 1000.0)
            Z.append(z_mm / 1000.0)

        # 3) Compute per-level baseline and deviations
        unique_levels = set(levels)
        if not unique_levels:
            st.error("Could not determine any levels from the data.")
            return None

        base_per_level = {}
        for lvl_val in unique_levels:
            level_dists = [d for l, d in zip(levels, dists) if l == lvl_val]
            if not level_dists:
                st.warning(f"No distance measurements found for Level {lvl_val}. Using baseline 0 for this level.")
                base_per_level[lvl_val] = 0
            else:
                base_per_level[lvl_val] = min(level_dists)

        D = []
        for l, r in zip(levels, dists):
            if l in base_per_level:
                D.append(r - base_per_level[l])
            else:
                # This case should ideally not happen if unique_levels covered all levels
                # but added for robustness. Assigning deviation 0.
                D.append(0)


        # 4) Bin into 2D grid (horizontal X vs. vertical Z)
        nx, nz = 200, 200
        # Use fixed ranges for a 4m wide (-2 to 2) and 2m high (0 to 2) wall
        xb = np.linspace(-2.2, 2.2, nx + 1) # Added slight padding
        zb = np.linspace(0, 2.2, nz + 1)  # Added slight padding


        # Use histogram2d to average 'D' values in each bin
        H_sum, _, _   = np.histogram2d(X, Z, bins=[xb, zb], weights=D)
        H_count, _, _ = np.histogram2d(X, Z, bins=[xb, zb])

        # Avoid division by zero, replace with NaN, then fill NaNs
        with np.errstate(divide='ignore', invalid='ignore'):
            H_dev = H_sum / H_count # Bins with no points will be NaN
        H_filled = np.nan_to_num(H_dev, nan=0.0) # Fill NaNs with 0

        # 5) Gaussian-smooth
        H_smooth = gaussian_filter(H_filled, sigma=(3.0, 3.0)) # Adjust sigma as needed

        # 6) Plot as a heatmap of deviation
        xc = (xb[:-1] + xb[1:]) / 2
        zc = (zb[:-1] + zb[1:]) / 2

        fig = go.Figure(go.Heatmap(
            z=H_smooth.T,   # Transpose because histogram2d uses (X, Z) but heatmap expects (row=Y, col=X)
            x=xc,
            y=zc,
            colorscale='rainbow', # Or 'Viridis' etc.
            zmid=0, # Center colorscale at 0 deviation
            colorbar=dict(title='Deflection (mm)')
        ))
        fig.update_layout(
            title='Wall Defect Map (Processed LiDAR Data)',
            # Set fixed ranges for a 4m wide (-2 to 2) and 2m high (0 to 2) wall
            # and enforce 1:1 aspect ratio
            xaxis=dict(title='Horizontal (m)', range=[-2.2, 2.2], scaleanchor='y', scaleratio=1),
            yaxis=dict(title='Height (m)',     range=[0, 2.2], scaleanchor='x', scaleratio=1),
            height=700, # Adjust height as needed
            margin=dict(l=20, r=20, t=50, b=20)
        )
        return fig

    except Exception as e:
        st.error(f"An unexpected error occurred during processing: {e}")
        import traceback
        st.error(traceback.format_exc()) # Show detailed error in Streamlit for debugging
        return None


# --- Callback: Select Saved Scan ---
def on_select_saved():
    sel = st.session_state.get("saved_scan_selectbox", "")
    if sel in st.session_state.saved_scans:
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
    st.title("Plastermate") # Removed emoji
    st.header("Controls")

    # File Uploader
    uploaded_file = st.file_uploader("Choose a LiDAR data file (.txt)", type="txt", key="lidar_uploader")

    # Store uploaded file info in session state to persist across reruns
    if uploaded_file is not None:
        if st.session_state.uploaded_file_state is None or uploaded_file.file_id != st.session_state.uploaded_file_state['id']:
            try:
                # Read file content as string
                stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
                file_content = stringio.read()
                st.session_state.uploaded_file_state = {
                    "name": uploaded_file.name,
                    "content": file_content,
                    "id": uploaded_file.file_id
                }
                st.success(f"File '{uploaded_file.name}' loaded.")
            except Exception as e:
                st.error(f"Error processing file '{uploaded_file.name}': {e}")
                st.session_state.uploaded_file_state = None # Reset on error

    elif st.session_state.uploaded_file_state:
        # Show that a file is already loaded
        st.info(f"Using loaded file: {st.session_state.uploaded_file_state['name']}")


    # Analysis Button
    if st.button("New Analysis", type="primary", use_container_width=True): # Removed emoji
        if st.session_state.uploaded_file_state:
            with st.spinner("Processing LiDAR data and generating heatmap..."):
                # Process the stored file content
                new_figure = process_lidar_data_and_generate_heatmap(st.session_state.uploaded_file_state["content"])

            if new_figure:
                st.session_state.latest_run_figure = new_figure
                st.session_state.view_mode = "latest"
                st.session_state.selected_saved_scan_name = None
                st.session_state.just_saved = False
                st.rerun() # Rerun to update the main view immediately
            else:
                # Error messages are handled within the processing function
                st.session_state.latest_run_figure = None
                st.session_state.view_mode = "none"
        else:
            st.warning("Please upload a LiDAR data file first.")

    st.markdown("---")
    st.header("Saved Scans")

    # --- Saved Scans Section ---
    if st.session_state.saved_scans:
        names = list(st.session_state.saved_scans.keys())
        options = [""] + names # Add empty option for clearing selection
        # Find current index, default to 0 if not selected or not found
        try:
            idx = names.index(st.session_state.selected_saved_scan_name) + 1
        except (ValueError, TypeError):
            idx = 0

        st.selectbox(
            "Select a saved scan:",
            options,
            index=idx,
            key="saved_scan_selectbox",
            on_change=on_select_saved,
            format_func=lambda v: "Choose a scan..." if v == "" else v,
            help="Select a previously saved scan to view or delete."
           )

        if st.session_state.selected_saved_scan_name:
            if st.button(f"Delete '{st.session_state.selected_saved_scan_name}'", use_container_width=True): # Removed emoji
                del st.session_state.saved_scans[st.session_state.selected_saved_scan_name]
                st.snow()
                time.sleep(0.5) # Give time for animation
                st.success("Scan deleted.")
                # Reset view after deletion
                st.session_state.view_mode = "none"
                st.session_state.selected_saved_scan_name = None
                st.session_state.latest_run_figure = None # Clear latest figure too
                st.rerun() # Rerun to update selectbox and view
    else:
        st.info("No saved scans yet.")


# --- Main Area ---
with st.container():
    mode = st.session_state.view_mode

    # Latest Analysis View
    if mode == "latest" and st.session_state.latest_run_figure:
        st.subheader("Latest Heatmap Analysis")
        st.plotly_chart(st.session_state.latest_run_figure, use_container_width=True)

        with st.expander("Save This Scan", expanded=True): # Removed emoji
            default_name = f"Scan {st.session_state.scan_counter}"
            # Add file name to default save name if available
            if st.session_state.uploaded_file_state:
                base_name = st.session_state.uploaded_file_state['name'].split('.')[0]
                default_name = f"{base_name} - Scan {st.session_state.scan_counter}"

            name_input = st.text_input("Save As:", key="custom_scan_name_input",
                                       placeholder=default_name)
            if st.button("Save Analysis", type="primary", use_container_width=True, key="save_btn"):
                final_name = name_input.strip() or default_name
                # Check for duplicate name
                if final_name in st.session_state.saved_scans:
                    st.warning(f"A scan named '{final_name}' already exists. Please choose a different name.")
                else:
                    # Progress animation
                    progress = st.progress(0)
                    for i in range(1, 101):
                        time.sleep(0.005)
                        progress.progress(i)
                    progress.empty()
                    # Save the actual figure
                    st.session_state.saved_scans[final_name] = st.session_state.latest_run_figure
                    st.session_state.scan_counter += 1
                    # Celebration (st.balloons() doesn't use unicode chars in the code itself)
                    st.balloons()
                    st.session_state.just_saved = True # Set flag to show success on next rerun
                    # Reset view to placeholder after saving
                    st.session_state.view_mode = "none"
                    st.session_state.selected_saved_scan_name = None
                    st.session_state.latest_run_figure = None
                    st.rerun() # Rerun to show placeholder + success message

    # Saved Scan View
    elif mode == "saved" and st.session_state.selected_saved_scan_name:
        sel_name = st.session_state.selected_saved_scan_name
        if sel_name in st.session_state.saved_scans:
            with st.spinner(f"Loading saved scan: {sel_name}..."):
                time.sleep(0.3) # Short delay for effect
            st.subheader(f"Saved Scan: {sel_name}")
            st.plotly_chart(st.session_state.saved_scans[sel_name], use_container_width=True)
        else:
            st.error("Selected saved scan not found. It might have been deleted.")
            st.session_state.view_mode = "none" # Reset view
            st.session_state.selected_saved_scan_name = None


    # Placeholder View (Default)
    else:
        if st.session_state.just_saved:
            st.success("Scan saved successfully! You can select it from the sidebar.") # Removed emoji
            st.session_state.just_saved = False # Reset flag
        st.info("Upload a LiDAR data file and click 'New Analysis', or select a saved scan from the sidebar.")
