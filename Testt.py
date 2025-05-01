# Read LIDAR scan data from a text file with sections labeled "Level N".
# Each section contains lines of "angle,distance" for that vertical level of the scan.
input_file = 'lidar_scan.txt'
data = {}  # dict: level_number -> list of (angle_degrees, distance_mm)
with open(input_file, 'r') as f:
    current_level = None
    for line in f:
        line = line.strip()
        if not line:
            continue
        if line.startswith('Level'):
            # Start of a new level section, extract the level index
            parts = line.split()
            try:
                current_level = int(parts[1])  # e.g., "Level 1" -> 1
            except:
                current_level = None
            if current_level is not None:
                data[current_level] = []
        else:
            # Parse an "angle,distance" reading (two comma-separated values)
            parts = line.split(',')
            if len(parts) != 2 or current_level is None:
                continue
            angle = float(parts[0])
            distance = float(parts[1])  # distance in millimeters
            data[current_level].append((angle, distance))

# Convert parsed data into Cartesian coordinates (horizontal x, vertical y).
# Prepare lists for all point coordinates and distances.
x_vals = []
y_vals = []
d_vals = []
# Process each level (sorted for consistency)
for level, readings in sorted(data.items()):
    # Determine vertical height (in meters) for this scan level
    # Assuming 10 levels span 2 meters, each level is 0.2 m apart.
    height = (level - 1) * 0.2  # Level 1 -> 0.0m, Level 10 -> 1.8m
    for angle, dist in readings:
        # Convert angle to radians for trig functions
        theta = math.radians(angle)
        # Convert polar (angle, distance) to Cartesian coordinates:
        # Horizontal offset: x = r * sin(theta) (assuming 0° is straight ahead).
        # Vertical coordinate: y = height (level position). We ignore the forward (depth) component.
        # (Polar-to-Cartesian general formula: x = r*cos(theta), y = r*sin(theta)&#8203;:contentReference[oaicite:0]{index=0}.)
        x = dist * math.sin(theta)
        x_vals.append(x / 1000.0)  # convert mm to meters for x-axis
        y_vals.append(height)      # vertical position in meters
        d_vals.append(dist)

# Compute a baseline distance assuming the wall is roughly flat (perpendicular to sensor).
# Here we take the minimum distance at each level (front of wall) and average them.
base_distances = []
for level, readings in sorted(data.items()):
    if readings:
        # Minimum measured distance at this level (mm) - likely the nearest point (center of wall)
        min_dist = min(d for (_, d) in readings)
        base_distances.append(min_dist)
base_distance = (sum(base_distances) / len(base_distances)) if base_distances else 0

# Compute distance deviation from baseline (mm).
# Negative deviation means the point is closer than average (wall bulge),
# positive means farther than average (wall dent).
d_devs = [d - base_distance for d in d_vals]

# Define a grid for the wall: width 4m (-2 to +2) by height 2m (0 to 2).
nx = 200  # horizontal resolution (number of bins)
ny = 10   # vertical resolution (number of bins, matching 10 levels)
x_bins = np.linspace(-2.0, 2.0, nx + 1)
y_bins = np.linspace(0.0, 2.0, ny + 1)

# Bin all points into the 2D grid: count and average deviation per cell.
H_count, x_edges, y_edges = np.histogram2d(x_vals, y_vals, bins=[x_bins, y_bins])
H_sum, _, _ = np.histogram2d(x_vals, y_vals, bins=[x_bins, y_bins], weights=d_devs)
# H_count = count of points in each cell, H_sum = sum of deviations in each cell
H_mean = np.divide(H_sum, H_count, out=np.full_like(H_sum, np.nan), where=(H_count != 0))
# Transpose so that rows correspond to height levels
H_matrix = H_mean.T  # shape (ny, nx)

# Compute bin center coordinates for labeling axes
x_centers = (x_edges[:-1] + x_edges[1:]) / 2
y_centers = (y_edges[:-1] + y_edges[1:]) / 2

# Create a heatmap from the 2D matrix of distance deviations.
# Plotly Express can display a 2D array directly as a heatmap&#8203;:contentReference[oaicite:1]{index=1}.
fig = px.imshow(
    H_matrix,
    x=x_centers,
    y=y_centers,
    origin='lower',
    aspect='auto',
    labels={'x': 'Horizontal Position (m)', 'y': 'Height (m)', 'color': 'Distance Deviation (mm)'},
    color_continuous_scale='RdBu'  # diverging color scale (red vs. blue for deviations)
)
fig.update_layout(
    title='LIDAR Wall Scan Heatmap',
    xaxis_title='Horizontal Position (m)',
    yaxis_title='Height (m)',
    width=800, height=400
)
# Optionally, enforce equal scaling (so 1 meter equals 1 unit on both axes):
# fig.update_yaxes(scaleanchor="x", scaleratio=1)
fig.show()
