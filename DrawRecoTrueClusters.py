import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pathlib import Path

def DrawTrueRecoClustersXZ(true_clusters, predicted_clusters, event, apa, PLOTDIR_EVT, file_name=None):
    """Draw true and reco clusters in XZ projection for comparison."""
    marker_size = 1
    view = "XZ"

    fig, axes = plt.subplots(1, 2, figsize=(12, 6))

    # First subplot - True clusters
    axes[0].set_xlim(0, 500)
    axes[0].set_ylim(-250, 250)
    axes[0].set_xlabel("z [cm]")
    axes[0].set_ylabel("x [cm]")
    title = "True clusters: Event " + str(event) + ", " + apa + ", " + view
    if file_name:
        title += f" ({file_name})"
    axes[0].set_title(title)

    for cluster_id, points in true_clusters.items():
        points = np.array(points)
        true_x_cluster = points[:, 0]
        true_z_cluster = points[:, 2]
        scatter = axes[0].scatter(true_z_cluster, true_x_cluster, s=marker_size, alpha=0.5)
        color = scatter.get_facecolor()[0]
        axes[0].plot([], [], color=color, label=f'Cluster {cluster_id:.0f}')
    axes[0].legend()

    # Second subplot - Reco clusters
    axes[1].set_xlim(axes[0].get_xlim())
    axes[1].set_ylim(axes[0].get_ylim())
    axes[1].set_xlabel("z [cm]")
    axes[1].set_ylabel("x [cm]")
    title = "Reco clusters: Event " + str(event) + ", " + apa + ", " + view
    if file_name:
        title += f" ({file_name})"
    axes[1].set_title(title)

    for cluster_id, points in predicted_clusters.items():
        points = np.array(points)
        reco_x_cluster = points[:, 0]
        reco_z_cluster = points[:, 2]
        scatter = axes[1].scatter(reco_z_cluster, reco_x_cluster, s=1, alpha=0.5)
        color = scatter.get_facecolor()[0]
        axes[1].plot([], [], color=color, label=f'Cluster {cluster_id:.0f}')
    axes[1].legend()

    plt.tight_layout()
    plt.savefig(PLOTDIR_EVT / f"all_clusters_reco_true_event{event}_apa_{apa}_{view}.png")
   # plt.show(block=False)
    plt.close()

def DrawTrueRecoClustersYZ(true_clusters, predicted_clusters, event, apa, PLOTDIR_EVT, file_name=None):
    """Draw true and reco clusters in YZ projection for comparison."""
    marker_size = 1
    view = "YZ"

    fig, axes = plt.subplots(1, 2, figsize=(12, 6))

    # First subplot - True clusters
    axes[0].set_xlim(0, 500)
    axes[0].set_ylim(-250, 250)
    axes[0].set_xlabel("z [cm]")
    axes[0].set_ylabel("y [cm]")
    title = "True clusters: Event " + str(event) + ", " + apa + ", " + view
    if file_name:
        title += f" ({file_name})"
    axes[0].set_title(title)

    for cluster_id, points in true_clusters.items():
        points = np.array(points)
        true_y_cluster = points[:, 1]
        true_z_cluster = points[:, 2]
        scatter = axes[0].scatter(true_z_cluster, true_y_cluster, s=marker_size, alpha=0.5)
        color = scatter.get_facecolor()[0]
        axes[0].plot([], [], color=color, label=f'Cluster {cluster_id:.0f}')
    axes[0].legend()

    # Second subplot - Reco clusters
    axes[1].set_xlim(axes[0].get_xlim())
    axes[1].set_ylim(axes[0].get_ylim())
    axes[1].set_xlabel("z [cm]")
    axes[1].set_ylabel("y [cm]")
    title = "Reco clusters: Event " + str(event) + ", " + apa + ", " + view
    if file_name:
        title += f" ({file_name})"
    axes[1].set_title(title)

    for cluster_id, points in predicted_clusters.items():
        points = np.array(points)
        reco_y_cluster = points[:, 1]
        reco_z_cluster = points[:, 2]
        scatter = axes[1].scatter(reco_z_cluster, reco_y_cluster, s=1, alpha=0.5)
        color = scatter.get_facecolor()[0]
        axes[1].plot([], [], color=color, label=f'Cluster {cluster_id:.0f}')
    axes[1].legend()

    plt.tight_layout()
    plt.savefig(PLOTDIR_EVT / f"all_clusters_reco_true_event{event}_apa_{apa}_{view}.png")
   # plt.show(block=False)
    plt.close()

def DrawTrueRecoClustersXY(true_clusters, predicted_clusters, event, apa, PLOTDIR_EVT, file_name=None):
    """Draw true and reco clusters in XY projection for comparison."""
    marker_size = 1
    view = "XY"

    fig, axes = plt.subplots(1, 2, figsize=(12, 6))

    # First subplot - True clusters
    axes[0].set_xlim(-250, 250)
    axes[0].set_ylim(-250, 250)
    axes[0].set_xlabel("x [cm]")
    axes[0].set_ylabel("y [cm]")
    title = "True clusters: Event " + str(event) + ", " + apa + ", " + view
    if file_name:
        title += f" ({file_name})"
    axes[0].set_title(title)

    for cluster_id, points in true_clusters.items():
        points = np.array(points)
        true_x_cluster = points[:, 0]
        true_y_cluster = points[:, 1]
        scatter = axes[0].scatter(true_x_cluster, true_y_cluster, s=marker_size, alpha=0.5)
        color = scatter.get_facecolor()[0]
        axes[0].plot([], [], color=color, label=f'Cluster {cluster_id:.0f}')
    axes[0].legend()

    # Second subplot - Reco clusters
    axes[1].set_xlim(axes[0].get_xlim())
    axes[1].set_ylim(axes[0].get_ylim())
    axes[1].set_xlabel("x [cm]")
    axes[1].set_ylabel("y [cm]")
    title = "Reco clusters: Event " + str(event) + ", " + apa + ", " + view
    if file_name:
        title += f" ({file_name})"
    axes[1].set_title(title)

    for cluster_id, points in predicted_clusters.items():
        points = np.array(points)
        reco_x_cluster = points[:, 0]
        reco_y_cluster = points[:, 1]
        scatter = axes[1].scatter(reco_x_cluster, reco_y_cluster, s=1, alpha=0.5)
        color = scatter.get_facecolor()[0]
        axes[1].plot([], [], color=color, label=f'Cluster {cluster_id:.0f}')
    axes[1].legend()

    plt.tight_layout()
    plt.savefig(PLOTDIR_EVT / f"all_clusters_reco_true_event{event}_apa_{apa}_{view}.png")
   # plt.show(block=False)
    plt.close()

def DrawTrueClusterWithMatchedReco(matched_info, clusters_true, clusters_reco, output_dir, event, apa, file_name=None):
    """
    Draw a single true cluster with all its matched reco clusters (1-to-many).
    True cluster in red, matched reco clusters in distinct colors.
    Shows efficiency/purity values in legend. Zooms to true cluster bounds ±30%.

    Parameters:
    - matched_info: Dict from MatchRecoTrueCluster1toMany with keys:
        'event', 'true_cluster_id', 'matched_reco_clusters' (list of dicts with reco_cluster_id, efficiency_energy_weighted, purity)
    - clusters_true: Dict of {true_cid: array of points}
    - clusters_reco: Dict of {reco_cid: array of points}
    - output_dir: Output directory
    - event: Event number
    - apa: APA identifier
    """
    true_cid            = matched_info['true_cluster_id']
    matched_reco_list   = matched_info['matched_reco_clusters']

    if true_cid not in clusters_true or not matched_reco_list:
        return

    true_points = np.array(clusters_true[true_cid])
    marker_size = 1
    colors = ['blue', 'green', 'orange', 'purple', 'cyan', 'magenta', 'brown', 'pink']

    fig, (ax_xz, ax_yz, ax_xy) = plt.subplots(1, 3, figsize=(24, 6))

    # Plot each matched reco cluster with different colors (first)
    for idx, reco_info in enumerate(matched_reco_list):
        reco_cid    = reco_info['reco_cluster_id']
        eff         = reco_info['efficiency_energy_weighted']
        pur         = reco_info['purity']

        if reco_cid not in clusters_reco:
            continue

        reco_points = np.array(clusters_reco[reco_cid])
        color       = colors[idx % len(colors)]
        label       = f'Reco ID={reco_cid:.0f} (ε={eff:.2f}, p={pur:.2f})'

        ax_xz.scatter(reco_points[:, 0], reco_points[:, 2], c=color, s=marker_size, alpha=0.7,
                      label=label)
        ax_yz.scatter(reco_points[:, 1], reco_points[:, 2], c=color, s=marker_size, alpha=0.7,
                      label=label)
        ax_xy.scatter(reco_points[:, 0], reco_points[:, 1], c=color, s=marker_size, alpha=0.7,
                      label=label)

    # Plot true cluster (red) on top of reco clusters
    ax_xz.scatter(true_points[:, 0], true_points[:, 2], c='red', s=marker_size, alpha=0.8,
                  label=f'True ID={true_cid:.0f}', zorder=10)
    ax_yz.scatter(true_points[:, 1], true_points[:, 2], c='red', s=marker_size, alpha=0.8,
                  label=f'True ID={true_cid:.0f}', zorder=10)
    ax_xy.scatter(true_points[:, 0], true_points[:, 1], c='red', s=marker_size, alpha=0.8,
                  label=f'True ID={true_cid:.0f}', zorder=10)

    # Calculate zoom bounds: 30% padding on all sides of true cluster
    x_min, x_max = true_points[:, 0].min(), true_points[:, 0].max()
    y_min, y_max = true_points[:, 1].min(), true_points[:, 1].max()
    z_min, z_max = true_points[:, 2].min(), true_points[:, 2].max()

    x_pad = (x_max - x_min) * 0.3
    y_pad = (y_max - y_min) * 0.3
    z_pad = (z_max - z_min) * 0.3

    x_lim = [x_min - x_pad, x_max + x_pad]
    y_lim = [y_min - y_pad, y_max + y_pad]
    z_lim = [z_min - z_pad, z_max + z_pad]

    # XZ projection
    ax_xz.set_xlim(x_lim)
    ax_xz.set_ylim(z_lim)
    ax_xz.set_xlabel('X [cm]', fontsize=12, fontweight='bold')
    ax_xz.set_ylabel('Z [cm]', fontsize=12, fontweight='bold')
    xz_title = f'True Cluster {true_cid:.0f} with Matched Reco (XZ) - Event {event}, {apa}'
    if file_name:
        xz_title += f' ({file_name})'
    ax_xz.set_title(xz_title, fontsize=12, fontweight='bold')
    ax_xz.legend(fontsize=18, loc='upper right', framealpha=0.9)
    ax_xz.grid(True, linestyle='--', alpha=0.3)

    # YZ projection
    ax_yz.set_xlim(y_lim)
    ax_yz.set_ylim(z_lim)
    ax_yz.set_xlabel('Y [cm]', fontsize=12, fontweight='bold')
    ax_yz.set_ylabel('Z [cm]', fontsize=12, fontweight='bold')
    yz_title = f'True Cluster {true_cid:.0f} with Matched Reco (YZ) - Event {event}, {apa}'
    if file_name:
        yz_title += f' ({file_name})'
    ax_yz.set_title(yz_title, fontsize=12, fontweight='bold')
    ax_yz.legend(fontsize=18, loc='upper right', framealpha=0.9)
    ax_yz.grid(True, linestyle='--', alpha=0.3)

    # XY projection
    ax_xy.set_xlim(x_lim)
    ax_xy.set_ylim(y_lim)
    ax_xy.set_xlabel('X [cm]', fontsize=12, fontweight='bold')
    ax_xy.set_ylabel('Y [cm]', fontsize=12, fontweight='bold')
    xy_title = f'True Cluster {true_cid:.0f} with Matched Reco (XY) - Event {event}, {apa}'
    if file_name:
        xy_title += f' ({file_name})'
    ax_xy.set_title(xy_title, fontsize=12, fontweight='bold')
    ax_xy.legend(fontsize=18, loc='upper right', framealpha=0.9)
    ax_xy.grid(True, linestyle='--', alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / f"true_cluster_{true_cid:.0f}_with_reco_event_{event}_{apa}_XY.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
   # plt.show(block=False)
    plt.close()

    # Lets Draw 1D histograms of
    # Apply Time Window Cut to true
    # For true points, we need to consider the time of the event (t0) and the drift time to calculate the recorded time (t_recorded).
    # time t0 is point[6], x0 is true x position (point[0])
    # x_collection is the position of the collection plane (-202.05 for APA0 and +202.05 for APA1)
    # x_drft = abs(x0 - x_collection) where x_collection is the collection plane position (202.05 for APA0 and -202.05 for APA1)
    # t_drift is x_drft / drift_velocity
    # t_recorded = t0 + t_drift
    # To apply time window cut, we need to calculate t_recorded for each point and check if it falls within the time window

    draw_time_window_cut = False
    if draw_time_window_cut:
        print("\nApplying time window cut to true cluster points and plotting time distribution...")
        print("APA: ", apa)
        drift_velocity = 0.1563  # cm/us
        if apa == "APA0":
            x_collection = -202.05
        else:
            x_collection = 202.05

        print ("Drift velocity: ", drift_velocity, " cm/us")
        print ("Collection plane position: ", x_collection, " cm")

        time_min    = -205     # in us, calculated based on max drift time (500 cm / 0.1563 cm/us) + some buffer
        time_max    = 1508.5   # in us, calculated based on max drift time (500 cm / 0.1563 cm/us) + some buffer

        # Save true_points[:, 6] in a text file for debugging
        np.savetxt(output_dir / f"true_cluster_{true_cid:.0f}_t0_values_event_{event}_{apa}.txt", true_points[:, 6], fmt='%.3f')


        t0          = true_points[:, 6] / 1000  # convert from ns to μs
        x0          = true_points[:, 0]
        x_drft      = abs(x0 - x_collection)
        t_drift     = x_drft / drift_velocity
        t_recorded  = t0 + t_drift
        # print min and max of t_recorded for debugging
        print(f"Recorded time (t_recorded) range for true cluster {true_cid:.0f}: {t_recorded.min():.2f} μs to {t_recorded.max():.2f} μs")

        # print number of true points before time window cut for debugging and how many points survive the time window cut
        print(f"Number of true points before time window cut: {len(true_points)}")
        points_after_time_window_cut = np.sum((t_recorded >= time_min) & (t_recorded <= time_max))
        print(f"Number of true points after time window cut: {points_after_time_window_cut}")
        print(f"Percentage of true points surviving time window cut: {points_after_time_window_cut / len(true_points) * 100:.2f}%")

        # print min and max of x, y, z for true cluster points for debugging
        print(f"True cluster {true_cid:.0f} X range: {x0.min():.2f} cm to {x0.max():.2f} cm")
        print(f"True cluster {true_cid:.0f} Y range: {true_points[:, 1].min():.2f} cm to {true_points[:, 1].max():.2f} cm")
        print(f"True cluster {true_cid:.0f} Z range: {true_points[:, 2].min():.2f} cm to {true_points[:, 2].max():.2f} cm")

        plt.figure(figsize=(10, 6))
        plt.hist(t_recorded, bins=100, alpha=0.7, color='blue')
        plt.xlabel('Recorded Time (μs)', fontsize=12, fontweight='bold')
        plt.ylabel('Number of Points', fontsize=12, fontweight='bold')
        plt.title(f'Recorded Time Distribution of True Cluster {true_cid:.0f} - Event {event}, {apa}', fontsize=12, fontweight='bold')
        plt.grid(True, linestyle='--', alpha=0.3)
        # Draw vertical lines for time window cuts
        plt.axvline(x=time_min, color='red', linestyle='--', label=f'TW Min ({time_min} μs)')
        plt.axvline(x=time_max, color='green', linestyle='--', label=f'TW Max ({time_max} μs)')
        plt.legend(fontsize=12)
        plt.tight_layout()
        plt.savefig(output_dir / f"true_cluster_{true_cid:.0f}_time_distribution_event_{event}_{apa}.png", dpi=100, bbox_inches='tight', pad_inches=0.3)
       # plt.show(block=False)
        plt.close()

        # lets also make 1D histograms of t0, t_drift, x0, x_drift for true cluster points
        plt.figure(figsize=(10, 6))
        plt.hist(t0, bins=100, alpha=0.7, color='orange')
        plt.xlabel('True Time t0 (μs)', fontsize=12, fontweight='bold')
        plt.ylabel('Number of Points', fontsize=12, fontweight='bold')
        plt.title(f'True Time t0 Distribution of True Cluster {true_cid:.0f} - Event {event}, {apa}', fontsize=12, fontweight='bold')
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / f"true_cluster_{true_cid:.0f}_t0_distribution_event_{event}_{apa}.png", dpi=100, bbox_inches='tight', pad_inches=0.3)
       # plt.show(block=False)
        plt.close()

        plt.figure(figsize=(10, 6))
        plt.hist(t_drift, bins=100, alpha=0.7, color='green')
        plt.xlabel('Drift Time (μs)', fontsize=12, fontweight='bold')
        plt.ylabel('Number of Points', fontsize=12, fontweight='bold')
        plt.title(f'Drift Time Distribution of True Cluster {true_cid:.0f} - Event {event}, {apa}', fontsize=12, fontweight='bold')
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / f"true_cluster_{true_cid:.0f}_drift_time_distribution_event_{event}_{apa}.png", dpi=100, bbox_inches='tight', pad_inches=0.3)
       # plt.show(block=False)
        plt.close()
        plt.figure(figsize=(10, 6))

        plt.hist(x0, bins=100, alpha=0.7, color='purple')
        plt.xlabel('True X Position (cm)', fontsize=12, fontweight='bold')
        plt.ylabel('Number of Points', fontsize=12, fontweight='bold')
        plt.title(f'True X Position Distribution of True Cluster {true_cid:.0f} - Event {event}, {apa}', fontsize=12, fontweight='bold')
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / f"true_cluster_{true_cid:.0f}_x0_distribution_event_{event}_{apa}.png", dpi=100, bbox_inches='tight', pad_inches=0.3)
       # plt.show(block=False)
        plt.close()

        plt.figure(figsize=(10, 6))
        plt.hist(x_drft, bins=100, alpha=0.7, color='cyan')
        plt.xlabel('Drift Distance (cm)', fontsize=12, fontweight='bold')
        plt.ylabel('Number of Points', fontsize=12, fontweight='bold')
        plt.title(f'Drift Distance Distribution of True Cluster {true_cid:.0f} - Event {event}, {apa}', fontsize=12, fontweight='bold')
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / f"true_cluster_{true_cid:.0f}_drift_distance_distribution_event_{event}_{apa}.png", dpi=100, bbox_inches='tight', pad_inches=0.3)
       # plt.show(block=False)
        plt.close()

def DrawLabels(true_clusters, event, apa, PLOTDIR_EVT, file_name=None):
    """
    Create a summary of true clusters by type (neutrino vs cosmic).
    q_true = 1 for neutrinos, q_true = 0 for cosmics.
    Draw a bar plot showing counts with legend containing neutrino cluster IDs.

    Parameters:
    - true_clusters: Dict of {cluster_id: array_of_points}
      where points have columns [x, y, z, cluster_id, q_true, energy, time]
    - event: Event number
    - apa: APA identifier
    - PLOTDIR_EVT: Output directory
    - file_name: Optional file name for title
    """
    neutrino_clusters = []
    cosmic_clusters = []

    for cluster_id, points in true_clusters.items():
        points = np.array(points)
        q_true_values = points[:, 4]  # q_true column
        q_true = int(q_true_values[0]) if len(q_true_values) > 0 else 0

        if q_true == 1:
            neutrino_clusters.append(cluster_id)
        else:
            cosmic_clusters.append(cluster_id)

    # Create figure with bar plot
    fig, ax = plt.subplots(figsize=(10, 6))

    categories = ['Neutrino\n(q_true=1)', 'Cosmic\n(q_true=0)']
    counts = [len(neutrino_clusters), len(cosmic_clusters)]
    colors = ['red', 'blue']

    bars = ax.bar(categories, counts, color=colors, alpha=0.7, edgecolor='black', linewidth=2)

    # Add count labels on bars
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(count)}',
                ha='center', va='bottom', fontsize=14, fontweight='bold')

    ax.set_ylabel('Number of Clusters', fontsize=12, fontweight='bold')
    ax.set_xlabel('Cluster Type', fontsize=12, fontweight='bold')
    title = f'True Clusters by Type: Event {event}, {apa}'
    if file_name:
        title += f' ({file_name})'
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')

    # Create legend with neutrino cluster IDs
    if neutrino_clusters:
        neutrino_ids = ', '.join([f'{cid:.0f}' for cid in sorted(neutrino_clusters)])
        legend_text = f'Neutrino Clusters: {neutrino_ids}'
    else:
        legend_text = 'No neutrino clusters'

    if cosmic_clusters:
        cosmic_ids = ', '.join([f'{cid:.0f}' for cid in sorted(cosmic_clusters)])
        if neutrino_clusters:
            legend_text += f'\nCosmic Clusters: {cosmic_ids}'
        else:
            legend_text = f'Cosmic Clusters: {cosmic_ids}'

    ax.text(0.5, 0.95, legend_text, transform=ax.transAxes,
            fontsize=11, verticalalignment='top', horizontalalignment='center',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout()
    plt.savefig(PLOTDIR_EVT / f"true_clusters_by_type_event{event}_apa_{apa}.png", dpi=100, bbox_inches='tight')
    plt.close()

def DrawTrueClusterWithDeadArea(true_cluster_points_full, deadarea_polygons, cluster_id, event, apa, output_dir, file_name=None):
    """
    Draw full true cluster in YZ projection with dead area regions overlaid.
    Dead areas are shown with dark black color overlay on the cluster.
    Dead areas are defined only in the YZ plane (independent of X coordinate).

    Parameters:
    - true_cluster_points_full: Array of all points in the true cluster [x, y, z, ...]
    - deadarea_polygons: List of dead area polygon vertices [[y, z], [y, z], ...]
    - cluster_id: Cluster ID
    - event: Event number
    - apa: APA identifier
    - output_dir: Output directory
    - file_name: Optional file name for title
    """
    from matplotlib.patches import Polygon as MplPolygon

    marker_size = 2
    fig, ax = plt.subplots(figsize=(10, 8))

    y = true_cluster_points_full[:, 1]
    z = true_cluster_points_full[:, 2]

    # YZ projection - draw full cluster
    ax.scatter(z, y, c='red', s=marker_size, alpha=0.7, label='True cluster (all points)', zorder=5)

    # Overlay dead area polygons in YZ plane with dark black color
    # Dead area JSON stores [y, z] but matplotlib expects [x, y] for plotting
    # Since we plot z on x-axis and y on y-axis, we need to swap to [z, y]
    for idx, polygon in enumerate(deadarea_polygons):
        polygon_array = np.array(polygon)
        # Swap columns: [y, z] -> [z, y] for correct plotting (Z on x-axis, Y on y-axis)
        polygon_swapped = polygon_array[:, [1, 0]]
        patch = MplPolygon(polygon_swapped, closed=True, alpha=0.6, color='black',
                          edgecolor='black', linewidth=2,
                          label='Dead area' if idx == 0 else '', zorder=4)
        ax.add_patch(patch)

    ax.set_xlim(0, 500)
    ax.set_ylim(-250, 250)
    ax.set_xlabel('Z [cm]', fontsize=12, fontweight='bold')
    ax.set_ylabel('Y [cm]', fontsize=12, fontweight='bold')
    title = f'True Cluster {cluster_id:.0f} - Full Cluster with Dead Area (YZ): Event {event}, {apa}'
    if file_name:
        title += f' ({file_name})'
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.legend(fontsize=11, loc='upper right', framealpha=0.9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / f"true_cluster_{cluster_id:.0f}_full_with_deadarea_event{event}_apa_{apa}.png",
                dpi=100, bbox_inches='tight')
    plt.close()

def DrawPointsBeforeAfterDeadArea(cluster_before, cluster_after, event, apa, output_dir, file_name=None):
    """
    Draw a bar chart showing number of points before and after dead area cut for affected clusters only.

    Parameters:
    - cluster_before: Dict of {cluster_id: point_count_before}
    - cluster_after: Dict of {cluster_id: point_count_after}
    - event: Event number
    - apa: APA identifier
    - output_dir: Output directory
    - file_name: Optional file name for title
    """
    # Only include clusters that were affected by dead area (lost points)
    affected_cluster_ids = []
    for cid in cluster_before.keys():
        before = cluster_before[cid]
        after = cluster_after.get(cid, 0)
        if after < before:  # Cluster lost points
            affected_cluster_ids.append(cid)

    affected_cluster_ids = sorted(affected_cluster_ids)

    if not affected_cluster_ids:
        return

    before_counts = [cluster_before[cid] for cid in affected_cluster_ids]
    after_counts = [cluster_after.get(cid, 0) for cid in affected_cluster_ids]

    fig, ax = plt.subplots(figsize=(12, 6))

    x = np.arange(len(affected_cluster_ids))
    width = 0.35

    bars_before = ax.bar(x - width/2, before_counts, width, label='Before dead area cut',
                         color='blue', alpha=0.7, edgecolor='black')
    bars_after = ax.bar(x + width/2, after_counts, width, label='After dead area cut',
                        color='green', alpha=0.7, edgecolor='black')

    # Add value labels on bars
    for bars in [bars_before, bars_after]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}',
                        ha='center', va='bottom', fontsize=9)

    ax.set_xlabel('Cluster ID', fontsize=12, fontweight='bold')
    ax.set_ylabel('Number of Points', fontsize=12, fontweight='bold')
    title = f'Points Before and After Dead Area Cut (Affected Clusters): Event {event}, {apa}'
    if file_name:
        title += f' ({file_name})'
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([f'{cid:.0f}' for cid in affected_cluster_ids], rotation=45, ha='right')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(output_dir / f"points_before_after_deadarea_event{event}_apa_{apa}.png",
                dpi=100, bbox_inches='tight')
    plt.close()


def DrawTrueClusterCategories(cluster_category_results, clusters_true, output_dir, event=None, apa=None, file_name=None):
    """
    Visualize true cluster categories in XZ projection with track classification.
    Displays neutrino interactions as point clouds and cosmic rays as geometric tracks
    with angle labels positioned at track midpoints. Color-coded by track type:
    red (isochronous), green (normal), blue (prolonged).
    """
    if output_dir is None or not cluster_category_results:
        return

    fig, ax = plt.subplots(figsize=(14, 10))

    # Color mapping for track types
    color_map = {'isochronous': 'red', 'normal': 'green', 'prolonged': 'blue'}

    # Plot all points and track lines
    colors_tab = plt.cm.tab20(np.linspace(0, 1, len(cluster_category_results)))

    for idx, (cluster_id, data) in enumerate(cluster_category_results.items()):
        points = np.array(clusters_true[cluster_id])
        x_vals = points[:, 0]
        z_vals = points[:, 2]

        # Plot cluster points with marker size 1
        marker = 'o' if data['is_neutrino'] else 's'  # circle for neutrino, square for cosmic
        ax.scatter(z_vals, x_vals, s=1, alpha=0.6, color=colors_tab[idx], marker=marker, label=f'Cluster {cluster_id:.0f}')

        # Draw track line only for cosmic clusters (not for neutrino)
        if not data['is_neutrino']:
            z_line = [data['z_min'], data['z_max']]
            x_line = [data['x_at_z_min'], data['x_at_z_max']]
            ax.plot(z_line, x_line, color=color_map[data['track_type']], linewidth=3, alpha=0.8)

            # Add text label closer to the track line
            z_mid = (data['z_min'] + data['z_max']) / 2
            x_mid = (data['x_at_z_min'] + data['x_at_z_max']) / 2

            label_text = f"ID:{cluster_id:.0f}\nθ={data['theta_xz']:.1f}°\n{data['track_type']}"

            ax.text(z_mid, x_mid, label_text, fontsize=9, ha='center', va='center',
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7, edgecolor='black'),
                   fontweight='bold')

    ax.set_xlabel('Z [cm]', fontsize=12, fontweight='bold')
    ax.set_ylabel('X [cm]', fontsize=12, fontweight='bold')

    title = 'True Cluster Categories (XZ View) - Neutrino vs Cosmic'
    if event is not None and apa is not None:
        title += f' - Event {event}, {apa}'
    if file_name is not None:
        title += f' ({file_name})'
    ax.set_title(title, fontsize=14, fontweight='bold')

    # Create custom legend for track types
    legend_elements = [
        Line2D([0], [0], color='red', linewidth=3, label='Isochronous (θ < 20°)'),
        Line2D([0], [0], color='green', linewidth=3, label='Normal (20° ≤ θ ≤ 70°)'),
        Line2D([0], [0], color='blue', linewidth=3, label='Prolonged (θ > 70°)'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='gray', markersize=8, label='Neutrino (q_true=1)'),
        Line2D([0], [0], marker='s', color='w', markerfacecolor='gray', markersize=8, label='Cosmic (q_true=0)')
    ]
    ax.legend(handles=legend_elements, fontsize=11, loc='upper left')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plot_path = Path(output_dir) / 'cluster_category_xz_view.png'
    plt.savefig(plot_path, dpi=100, bbox_inches='tight')
    print(f"\nSaved cluster category XZ plot to: {plot_path}")
    plt.close()


def DrawClusterBeforeAfterDeadArea(true_points_before, true_points_after, deadarea_data,
                                    event, apa, output_dir, file_name=None):
    """
    Draw true clusters before and after dead area cut with zoomed view of removed regions.
    Top row: Full view - left (before), right (after)
    Bottom row: Zoomed view around removed regions - left (before removed), right (after removed)
    Dead areas are overlaid on all views with 10 cm zoom around cut regions.
    """
    from matplotlib.patches import Polygon as MplPolygon
    from matplotlib.path import Path as MplPath

    fig, axes = plt.subplots(2, 2, figsize=(16, 14))

    marker_size = 1

    # Convert points to arrays
    true_before_arr = np.array(true_points_before) if len(true_points_before) > 0 else np.array([])
    true_after_arr = np.array(true_points_after) if len(true_points_after) > 0 else np.array([])

    # Identify removed points (in before but not in after)
    removed_mask = np.ones(len(true_before_arr), dtype=bool)
    if len(true_after_arr) > 0:
        for i, point in enumerate(true_before_arr):
            for after_point in true_after_arr:
                if np.allclose(point, after_point):
                    removed_mask[i] = False
                    break
    removed_points = true_before_arr[removed_mask]

    # Find bounds of removed regions for zooming
    if len(removed_points) > 0:
        z_removed_min = removed_points[:, 2].min()
        z_removed_max = removed_points[:, 2].max()
        y_removed_min = removed_points[:, 1].min()
        y_removed_max = removed_points[:, 1].max()
        z_zoom_min = max(0, z_removed_min - 5)
        z_zoom_max = min(500, z_removed_max + 5)
        y_zoom_min = y_removed_min - 5
        y_zoom_max = y_removed_max + 5
    else:
        z_zoom_min, z_zoom_max, y_zoom_min, y_zoom_max = 0, 500, -250, 250

    # Helper function to draw dead areas
    def draw_deadareas(ax):
        for idx, polygon in enumerate(deadarea_data):
            polygon_array = np.array(polygon)
            polygon_swapped = polygon_array[:, [1, 0]]
            patch = MplPolygon(polygon_swapped, closed=True, alpha=0.4, color='yellow',
                              edgecolor='black', linewidth=1.5,
                              label='Dead area' if idx == 0 else '', zorder=1)
            ax.add_patch(patch)

    # TOP-LEFT: Full view before dead area cut
    ax_before = axes[0, 0]
    if len(true_before_arr) > 0:
        ax_before.scatter(true_before_arr[:, 2], true_before_arr[:, 1], s=marker_size, alpha=0.6,
                         color='red', label='True clusters', zorder=3)
    draw_deadareas(ax_before)
    ax_before.set_xlabel('Z [cm]', fontsize=11, fontweight='bold')
    ax_before.set_ylabel('Y [cm]', fontsize=11, fontweight='bold')
    ax_before.set_title('Full View - Before Dead Area Cut', fontsize=12, fontweight='bold')
    ax_before.legend(fontsize=9, loc='upper right')
    ax_before.grid(True, alpha=0.3)
    ax_before.set_xlim(0, 500)
    ax_before.set_ylim(-250, 250)

    # TOP-RIGHT: Full view after dead area cut
    ax_after = axes[0, 1]
    if len(true_after_arr) > 0:
        ax_after.scatter(true_after_arr[:, 2], true_after_arr[:, 1], s=marker_size, alpha=0.6,
                        color='red', label='True clusters', zorder=3)
    draw_deadareas(ax_after)
    ax_after.set_xlabel('Z [cm]', fontsize=11, fontweight='bold')
    ax_after.set_ylabel('Y [cm]', fontsize=11, fontweight='bold')
    ax_after.set_title('Full View - After Dead Area Cut', fontsize=12, fontweight='bold')
    ax_after.legend(fontsize=9, loc='upper right')
    ax_after.grid(True, alpha=0.3)
    ax_after.set_xlim(0, 500)
    ax_after.set_ylim(-250, 250)

    # BOTTOM-LEFT: Zoomed view before dead area cut
    ax_zoom_before = axes[1, 0]
    if len(true_before_arr) > 0:
        ax_zoom_before.scatter(true_before_arr[:, 2], true_before_arr[:, 1], s=marker_size, alpha=0.6,
                              color='red', label='True clusters', zorder=3)
    draw_deadareas(ax_zoom_before)
    ax_zoom_before.set_xlabel('Z [cm]', fontsize=11, fontweight='bold')
    ax_zoom_before.set_ylabel('Y [cm]', fontsize=11, fontweight='bold')
    ax_zoom_before.set_title('Zoomed View - Before Dead Area Cut (10 cm zoom)', fontsize=12, fontweight='bold')
    ax_zoom_before.legend(fontsize=9, loc='upper right')
    ax_zoom_before.grid(True, alpha=0.3)
    ax_zoom_before.set_xlim(z_zoom_min, z_zoom_max)
    ax_zoom_before.set_ylim(y_zoom_min, y_zoom_max)

    # BOTTOM-RIGHT: Zoomed view after dead area cut (shows gap where points were removed)
    ax_zoom_after = axes[1, 1]
    if len(true_after_arr) > 0:
        ax_zoom_after.scatter(true_after_arr[:, 2], true_after_arr[:, 1], s=marker_size, alpha=0.6,
                             color='red', label='True clusters', zorder=3)
    draw_deadareas(ax_zoom_after)
    ax_zoom_after.set_xlabel('Z [cm]', fontsize=11, fontweight='bold')
    ax_zoom_after.set_ylabel('Y [cm]', fontsize=11, fontweight='bold')
    ax_zoom_after.set_title('Zoomed View - After Dead Area Cut (10 cm zoom)', fontsize=12, fontweight='bold')
    ax_zoom_after.legend(fontsize=9, loc='upper right')
    ax_zoom_after.grid(True, alpha=0.3)
    ax_zoom_after.set_xlim(z_zoom_min, z_zoom_max)
    ax_zoom_after.set_ylim(y_zoom_min, y_zoom_max)

    fig.suptitle(f'True Clusters Before/After Dead Area Cut - Event {event}, {apa}',
                fontsize=14, fontweight='bold')
    if file_name:
        fig.suptitle(fig._suptitle.get_text() + f' ({file_name})', fontsize=13, fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_dir / f"true_clusters_before_after_deadarea_event{event}_apa_{apa}.png",
                dpi=100, bbox_inches='tight')
    plt.close()

