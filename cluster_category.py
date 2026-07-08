import numpy as np
from pathlib import Path
from DrawRecoTrueClusters import DrawTrueClusterCategories


def cluster_category(clusters_true, output_dir=None, event=None, apa=None, file_name=None, radius=1.0, min_points=10):
    """
    Categorize true clusters based on angle theta_xz in the XZ plane.

    - Neutrino clusters (q_true=1): always categorized as "normal"
    - Cosmic clusters (q_true=0): angle calculated using z_min and z_max with density requirements

    z_min: first Z value where at least min_points exist within radius after this Z
    z_max: last Z value where at least min_points exist within radius before this Z

    Classification by angle (cosmics only):
    - theta_xz < 20°: "isochronous"
    - theta_xz > 70°: "prolonged"
    - else: "normal"

    Parameters:
    -----------
    clusters_true : dict
        Dictionary mapping cluster_id to array of points [x, y, z, cluster_id, q_true, energy, time]
    output_dir : Path, optional
        Directory to save visualization plots
    event : int, optional
        Event number for plot titles
    apa : str, optional
        APA identifier for plot titles
    file_name : str, optional
        File name for plot titles
    radius : float, optional
        Radius around Z to count points (default: 1.0 cm)
    min_points : int, optional
        Minimum number of points required in radius (default: 10)

    Returns:
    --------
    dict
        Dictionary mapping cluster_id to track_type classification and properties
    """
    if not clusters_true:
        print("No true clusters to analyze")
        return {}

    results = {}

    print("\n" + "="*70)
    print("CLUSTER CATEGORY CLASSIFICATION (Neutrino/Cosmic, XZ plane angle)")
    print("="*70)

    for cluster_id, points in clusters_true.items():
        points = np.array(points)

        if len(points) < 2:
            print(f"True Cluster {cluster_id:6.0f}: Too few points ({len(points)}) to analyze")
            continue

        x_vals = points[:, 0]
        z_vals = points[:, 2]
        q_true = points[0, 4]  # Get q_true from first point (same for all points in cluster)

        # Determine if neutrino (q_true=1) or cosmic (q_true=0)
        is_neutrino = (q_true == 1)

        if is_neutrino:
            # Neutrino clusters: always categorize as "normal"
            track_type = "normal"
            theta_xz = None
            x_at_z_min = None
            x_at_z_max = None
            z_min = z_vals.min()
            z_max = z_vals.max()

            print(f"True Cluster {cluster_id:6.0f}: NEUTRINO  {track_type:15s} | Z range: {z_min:.2f}-{z_max:.2f} cm | (q_true={q_true:.0f})")

            results[cluster_id] = {
                'track_type': track_type,
                'theta_xz': theta_xz,
                'is_neutrino': True,
                'x_at_z_min': x_at_z_min,
                'x_at_z_max': x_at_z_max,
                'z_min': z_min,
                'z_max': z_max
            }
        else:
            # Cosmic clusters: find z_min and z_max based on density requirements
            # Sort points by Z
            sorted_indices = np.argsort(z_vals)
            z_sorted = z_vals[sorted_indices]
            x_sorted = x_vals[sorted_indices]

            # Find z_min: first Z where at least min_points exist in [Z, Z+radius]
            z_min = None
            x_at_z_min = None
            for z_test in z_sorted:
                points_in_range = np.sum((z_vals >= z_test) & (z_vals < z_test + radius))
                if points_in_range >= min_points:
                    z_min = z_test
                    # Get average X for points in this range
                    mask = (z_vals >= z_test) & (z_vals < z_test + radius)
                    x_at_z_min = np.mean(x_vals[mask])
                    break

            # Find z_max: last Z where at least min_points exist in [Z-radius, Z]
            z_max = None
            x_at_z_max = None
            for z_test in z_sorted[::-1]:  # Iterate backwards
                points_in_range = np.sum((z_vals > z_test - radius) & (z_vals <= z_test))
                if points_in_range >= min_points:
                    z_max = z_test
                    # Get average X for points in this range
                    mask = (z_vals > z_test - radius) & (z_vals <= z_test)
                    x_at_z_max = np.mean(x_vals[mask])
                    break

            # If we couldn't find valid z_min/z_max, use overall min/max
            if z_min is None:
                z_min = z_sorted[0]
                x_at_z_min = x_sorted[0]
            if z_max is None:
                z_max = z_sorted[-1]
                x_at_z_max = x_sorted[-1]

            # Calculate angle theta_xz with respect to z-axis
            dx = x_at_z_max - x_at_z_min
            dz = z_max - z_min

            if dz == 0:
                theta_xz = 90.0  # Vertical track
            else:
                theta_xz = np.abs(np.arctan(dx / dz) * 180.0 / np.pi)

            # Classify based on angle thresholds
            if theta_xz < 20:
                track_type = "isochronous"
            elif theta_xz > 70:
                track_type = "prolonged"
            else:
                track_type = "normal"

            print(f"True Cluster {cluster_id:6.0f}: COSMIC    {track_type:15s} | theta_xz={theta_xz:6.2f}° | Z range: {z_min:.2f}-{z_max:.2f} cm | X: {x_at_z_min:.2f}-{x_at_z_max:.2f} cm")

            results[cluster_id] = {
                'track_type': track_type,
                'theta_xz': theta_xz,
                'is_neutrino': False,
                'x_at_z_min': x_at_z_min,
                'x_at_z_max': x_at_z_max,
                'z_min': z_min,
                'z_max': z_max
            }

    # Draw cluster categories visualization
    DrawTrueClusterCategories(results, clusters_true, output_dir, event=event, apa=apa, file_name=file_name)

    print("="*70 + "\n")

    return results
