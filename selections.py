import numpy as np
import matplotlib.pyplot as plt
import json
from pathlib import Path
from matplotlib.path import Path as MplPath

# Filter clusters by minimum energy threshold.
# Keeps only clusters with total energy >= energy_cutoff.
def apply_energy_cutoff(true_points, energy_cutoff):
    cluster_sums = {}
    for point in true_points:
        cluster_sums[point[3]] = cluster_sums.get(point[3], 0) + point[5]
    true_points = np.array([point for point in true_points if cluster_sums[point[3]] >= energy_cutoff])
    return true_points

# Filter true clusters by minimum point count threshold.
# Removes clusters with fewer than min_points points.
def apply_min_true_points_cutoff(true_points, min_points):
    cluster_counts = {}
    for point in true_points:
        cluster_id = point[3]
        cluster_counts[cluster_id] = cluster_counts.get(cluster_id, 0) + 1
    true_points = np.array([point for point in true_points if cluster_counts[point[3]] >= min_points])
    return true_points

# Filter reconstructed clusters by minimum point count threshold.
# Removes clusters with fewer than min_points points.
def apply_min_reco_points_cutoff(reco_points, min_points):
    cluster_counts = {}
    for point in reco_points:
        cluster_id = point[3]
        cluster_counts[cluster_id] = cluster_counts.get(cluster_id, 0) + 1
    reco_points = np.array([point for point in reco_points if cluster_counts[point[3]] >= min_points])
    return reco_points

# Remove true points outside the fiducial volume boundaries.
# Keeps only points within x, y, z limits.
def apply_wire_readout_sensitive_yz_plane_cut_true(true_points, x_min, x_max, y_min, y_max, z_min, z_max):
    filtered_points = []
    for point in true_points:
        x, y, z = point[0], point[1], point[2]
        if x_min <= x <= x_max and y_min <= y <= y_max and z_min <= z <= z_max:
            filtered_points.append(point)
    return np.array(filtered_points) if filtered_points else np.array([]).reshape(0, 6)

# Remove reconstructed points outside the fiducial volume boundaries.
# Keeps only points within x, y, z limits.
def apply_wire_readout_sensitive_yz_plane_cut_reco(reco_points, x_min, x_max, y_min, y_max, z_min, z_max):
    filtered_points = []
    for point in reco_points:
        x, y, z = point[0], point[1], point[2]
        if x_min <= x <= x_max and y_min <= y <= y_max and z_min <= z <= z_max:
            filtered_points.append(point)
    return np.array(filtered_points) if filtered_points else np.array([]).reshape(0, 5)

# Reassign cluster IDs to true clusters sequentially.
# Ensures IDs start from 0 and are contiguous.
def reassign_cluster_ID_true(points_5d):
    clusters = {}
    for point in points_5d:
        cluster_id = point[3]
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(point)
    
    new_points = []
    for cluster_id, points in clusters.items():
        points = np.array(points)
        avg_xy = np.mean(points[:, 0])
        avg_xy = round(avg_xy, 2)
        if points[:, 4].any() == 1:
            avg_xy = 9999
        points[:, 3] = avg_xy
        new_points.append(points)
    
    points_5d_after_reassigning = np.vstack(new_points)
    return points_5d_after_reassigning

# Reassign cluster IDs to reconstructed clusters sequentially.
# Ensures IDs start from 0 and are contiguous.
def reassign_cluster_ID_reco(points_5d_reco):
    clusters = {}
    for point in points_5d_reco:
        cluster_id = point[3]
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(point)
    
    new_points = []
    for cluster_id, points in clusters.items():
        points  = np.array(points)
        avg_x   = np.mean(points[:, 0])
        avg_x   = round(avg_x, 3)  # or round(avg_y, 2) depending on your needs
        points[:, 3] = avg_x
        new_points.append(points)
    
    points_5d_after_reassigning = np.vstack(new_points)
    return points_5d_after_reassigning

# Group points by their cluster ID.
# Returns dictionary mapping cluster ID to list of points.
def GroupClustersByID(points_5d):
    clusters = {}
    for point in points_5d:
        cluster_id = point[3]
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(point)
    return clusters

# Shift Z coordinate values of reconstructed clusters by a fixed offset.
# Used to align reco and true coordinate systems.
def ShiftRecoClusterZValues(clusters_reco, shift_value=0.5):
    for cluster_id, points in clusters_reco.items():
        points          = np.array(points)
        shifted_points  = points[:, 2]
        shifted_points  = shifted_points + shift_value
        points[:, 2]    = shifted_points
        clusters_reco[cluster_id] = points
    return clusters_reco

# Apply Time Window Cut to true
# For true points, we need to consider the time of the event (t0) and the drift time to calculate the recorded time (t_recorded).
# time t0 is point[6], x0 is true x position (point[0])
# x_collection is the position of the collection plane (-202.05 for APA0 and +202.05 for APA1)
# x_drft = abs(x0 - x_collection) where x_collection is the collection plane position (202.05 for APA0 and -202.05 for APA1)
# t_drift is x_drft / drift_velocity
# t_recorded = t0 + t_drift
# To apply time window cut, we need to calculate t_recorded for each point and check if it falls within the time window

def apply_time_window_cut(cluster, time_window_min, time_window_max, apa):
    print("Applying Time Window Cut")
    print("APA: ", apa)

    drift_velocity  = 0.1563  # cm/us
    time_min        = time_window_min
    time_max        = time_window_max

    if apa == "APA0":
        x_collection = -202.05
    else:
        x_collection = 202.05

    # print number of points before time window cut for debugging
    print(f"Number of points before time window cut: {len(cluster)}")

    # Track per-cluster statistics and t_recorded values
    cluster_before = {}
    cluster_after = {}
    t_recorded_before = {}  # t_recorded values before cut, per cluster
    t_recorded_after = {}   # t_recorded values after cut, per cluster

    filtered_points = []
    for point in cluster:
        x0          = point[0]                      # true absolute x position in cm
        t0          = point[6]/1000                 # true absolute time. Converted from ns to us
        x_drift     = abs(x0 - x_collection)        # drift distance in cm
        t_drift     = x_drift / drift_velocity      # drift time in us
        t_recorded  = t0 + t_drift                  # recorded time in us

        cluster_id = int(point[3])
        cluster_before[cluster_id] = cluster_before.get(cluster_id, 0) + 1

        if cluster_id not in t_recorded_before:
            t_recorded_before[cluster_id] = []
        t_recorded_before[cluster_id].append(t_recorded)

        if time_min <= t_recorded <= time_max:      # check if recorded time falls within the time window
            filtered_points.append(point)
            cluster_after[cluster_id] = cluster_after.get(cluster_id, 0) + 1

            if cluster_id not in t_recorded_after:
                t_recorded_after[cluster_id] = []
            t_recorded_after[cluster_id].append(t_recorded)

    # print number of points after time window cut for debugging
    print(f"Number of points after time window cut: {len(filtered_points)}")

    # Debug: show clusters that lost all points or significant points
    for cid in cluster_before:
        if cid not in cluster_after:
            print(f"  WARNING: Cluster {cid} lost all {cluster_before[cid]} points to time window cut")
        else:
            lost = cluster_before[cid] - cluster_after[cid]
            if lost > 0:
                pct = (lost / cluster_before[cid]) * 100
                print(f"  Cluster {cid}: {cluster_before[cid]} -> {cluster_after[cid]} points ({lost} removed, {pct:.1f}%)")

    # Create visualization of t_recorded distribution for all clusters
    all_clusters = sorted(list(cluster_before.keys()))
    if all_clusters:
        fig, axes = plt.subplots(len(all_clusters), 1, figsize=(10, 4 * len(all_clusters)), sharex=True)
        if len(all_clusters) == 1:
            axes = [axes]

        for idx, cid in enumerate(all_clusters):
            ax = axes[idx]

            # Plot all t_recorded before cut
            t_before = np.array(t_recorded_before[cid])
            ax.hist(t_before, bins=20, alpha=0.5, label=f'Before cut ({len(t_before)} points)', color='blue', edgecolor='black')

            # Plot t_recorded after cut (if cluster survived)
            if cid in t_recorded_after:
                t_after = np.array(t_recorded_after[cid])
                ax.hist(t_after, bins=20, alpha=0.5, label=f'After cut ({len(t_after)} points)', color='green', edgecolor='black')

            # Draw time window boundaries
            ax.axvline(time_min, color='red', linestyle='--', linewidth=2, label=f'Time window min: {time_min}')
            ax.axvline(time_max, color='red', linestyle='--', linewidth=2, label=f'Time window max: {time_max}')

            # Get y-axis limits for shading
            y_min, y_max = ax.get_ylim()
            ax.fill_betweenx([y_min, y_max], time_min, time_max, alpha=0.2, color='green', label='Valid time window')

            # Check if cluster lost all points
            status = "REMOVED" if cid not in cluster_after else "KEPT"
            ax.set_xlabel('t_recorded (μs)')
            ax.set_ylabel('Number of points')
            ax.set_title(f'Cluster {cid}: t_recorded distribution - {status}')
            ax.legend()
            ax.grid(True, alpha=0.3)

        fig.tight_layout()
        fig.savefig('time_window_cut_analysis.png', dpi=100, bbox_inches='tight')
        print(f"\nVisualization saved to: time_window_cut_analysis.png")
        plt.show()

    return np.array(filtered_points) if filtered_points else np.array([]).reshape(0, cluster.shape[1])


# Remove true points that lie inside dead area regions.
# Dead areas are defined as 2D polygons in (y, z) coordinates.
# Points inside any dead area polygon are removed.
def apply_deadarea_cut_true(true_points, apa, view_type="2view", output_dir=None, event=None, file_name=None):
    """
    Remove true points that fall inside dead area regions.
    If a cluster is affected by dead area, draw it with the dead area regions.

    Parameters:
    -----------
    true_points : ndarray
        Array of true points with shape (N, M) where columns are:
        [x, y, z, cluster_id, charge, energy, time]
    apa : str
        Which APA ("APA0" or "APA1")
    view_type : str
        Which view to use ("2view" or "3view")
    output_dir : Path, optional
        Directory to save visualization plots of affected clusters
    event : int, optional
        Event number for plot titles
    file_name : str, optional
        File name for plot titles

    Returns:
    --------
    ndarray
        Filtered true points with those inside dead areas removed
    """
    print("Applying Dead Area Cut")
    print(f"APA: {apa}, View: {view_type}")

    # Load dead area JSON files
    deadarea_base = Path(__file__).parent / "Deadareas"

    if view_type == "2view":
        deadarea_path = deadarea_base / "2viewactive_2viewdead"
    else:
        deadarea_path = deadarea_base / "3viewactive_1viewdead"

    if apa == "APA0":
        deadarea_file = deadarea_path / "0-channel-deadarea-apa0-face0.json"
    else:
        deadarea_file = deadarea_path / "0-channel-deadarea-apa1-face0.json"

    if not deadarea_file.exists():
        print(f"Warning: Dead area file not found at {deadarea_file}")
        print("Returning points unmodified")
        return true_points

    # Load dead area data
    with open(deadarea_file, 'r') as f:
        deadarea_data = json.load(f)

    # Create list of matplotlib Path objects for each dead area polygon
    # Dead area coordinates are [y, z] pairs
    polygon_paths = []
    for shape in deadarea_data:
        # Convert list of [y, z] coordinates to (y, z) tuples for matplotlib
        vertices = np.array([[p[0], p[1]] for p in shape])
        path = MplPath(vertices)
        polygon_paths.append(path)

    # Count statistics before and after
    points_before = len(true_points)
    cluster_before = {}
    cluster_after = {}
    affected_clusters = {}  # Track clusters with points removed
    full_clusters = {}  # Store full cluster data before filtering

    # Group points by cluster ID to get full clusters
    for point in true_points:
        cluster_id = int(point[3])
        cluster_before[cluster_id] = cluster_before.get(cluster_id, 0) + 1
        if cluster_id not in full_clusters:
            full_clusters[cluster_id] = []
        full_clusters[cluster_id].append(point)

    # Filter points: keep only those NOT inside any dead area
    # Dead areas are defined only in YZ plane (independent of X coordinate)
    filtered_points = []
    for point in true_points:
        # Extract only YZ coordinates (dead areas are independent of X)
        y, z = point[1], point[2]
        point_yz = np.array([[y, z]])

        # Check if point (in YZ plane) is inside any dead area polygon
        is_in_deadarea = False
        for path in polygon_paths:
            if path.contains_points(point_yz)[0]:
                is_in_deadarea = True
                break

        # Keep point if it's NOT in any dead area
        if not is_in_deadarea:
            filtered_points.append(point)
            cluster_id = int(point[3])
            cluster_after[cluster_id] = cluster_after.get(cluster_id, 0) + 1
        else:
            # Track affected cluster (point is inside dead area)
            cluster_id = int(point[3])
            if cluster_id not in affected_clusters:
                affected_clusters[cluster_id] = {'before': 0, 'after': 0}
            affected_clusters[cluster_id]['before'] += 1

    points_after = len(filtered_points)
    points_removed = points_before - points_after

    print(f"Number of points before dead area cut: {points_before}")
    print(f"Number of points after dead area cut: {points_after}")
    print(f"Points removed: {points_removed} ({100*points_removed/points_before:.1f}%)" if points_before > 0 else "")

    # Show per-cluster statistics
    for cid in sorted(cluster_before.keys()):
        before = cluster_before[cid]
        after = cluster_after.get(cid, 0)
        if after == 0:
            print(f"  Cluster {cid}: {before} -> {after} points (REMOVED)")
        elif after < before:
            removed = before - after
            pct = (removed / before) * 100
            print(f"  Cluster {cid}: {before} -> {after} points ({removed} removed, {pct:.1f}%)")

    # Draw clusters before and after dead area cut
    if output_dir is not None:
        try:
            from DrawRecoTrueClusters import DrawClusterBeforeAfterDeadArea, DrawPointsBeforeAfterDeadArea
            #DrawClusterBeforeAfterDeadArea(true_points, filtered_points, deadarea_data, event, apa, output_dir, file_name)
            DrawPointsBeforeAfterDeadArea(cluster_before, cluster_after, event, apa, output_dir, file_name)
            print(f"\nDrew before/after dead area visualizations")
        except Exception as e:
            print(f"Warning: Could not draw before/after visualizations: {e}")

    # Draw affected clusters with dead area overlay if output_dir is provided
    if output_dir is not None and affected_clusters:
        try:
            from DrawRecoTrueClusters import DrawTrueClusterWithDeadArea
            print(f"\nDrawing {len(affected_clusters)} clusters affected by dead area...")
            for cluster_id in affected_clusters.keys():
                # Draw the FULL cluster (before filtering) with dead area overlay
                if cluster_id in full_clusters:
                    full_cluster_points = np.array(full_clusters[cluster_id])
                    DrawTrueClusterWithDeadArea(full_cluster_points, deadarea_data, cluster_id, event, apa, output_dir, file_name)
                    print(f"  Drew cluster {cluster_id} (full cluster with dead area overlay)")
        except Exception as e:
            print(f"Warning: Could not draw affected clusters: {e}")

    return np.array(filtered_points) if filtered_points else np.array([]).reshape(0, true_points.shape[1])
