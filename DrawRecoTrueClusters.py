import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pathlib import Path
from scipy.spatial import KDTree

def DrawTrueRecoClustersXZ(true_clusters, predicted_clusters, event, apa, PLOTDIR_EVT, file_name=None,
                             filename_stem="all_clusters_reco_true", true_label="True clusters"):
    """Draw true and reco clusters in XZ projection for comparison.

    filename_stem / true_label exist so the same drawer can produce a SUBSET view of the
    same event: pass a filtered true_clusters plus a distinct stem and left-panel label
    (see DrawNeutrinoRecoClusters). Defaults reproduce the original all-clusters plot
    exactly, so existing callers are unaffected.
    """
    marker_size = 1
    view = "XZ"

    fig, axes = plt.subplots(1, 2, figsize=(12, 6))

    # First subplot - True clusters
    axes[0].set_xlim(0, 500)
    axes[0].set_ylim(-250, 250)
    axes[0].set_xlabel("z [cm]")
    axes[0].set_ylabel("x [cm]")
    title = true_label + ": Event " + str(event) + ", " + apa + ", " + view
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
    if true_clusters:
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
    if predicted_clusters:
        axes[1].legend()

    plt.tight_layout()
    plt.savefig(PLOTDIR_EVT / f"{filename_stem}_event{event}_apa_{apa}_{view}.png")
   # plt.show(block=False)
    plt.close()

def DrawTrueRecoClustersYZ(true_clusters, predicted_clusters, event, apa, PLOTDIR_EVT, file_name=None,
                             filename_stem="all_clusters_reco_true", true_label="True clusters"):
    """Draw true and reco clusters in YZ projection for comparison.

    filename_stem / true_label exist so the same drawer can produce a SUBSET view of the
    same event: pass a filtered true_clusters plus a distinct stem and left-panel label
    (see DrawNeutrinoRecoClusters). Defaults reproduce the original all-clusters plot
    exactly, so existing callers are unaffected.
    """
    marker_size = 1
    view = "YZ"

    fig, axes = plt.subplots(1, 2, figsize=(12, 6))

    # First subplot - True clusters
    axes[0].set_xlim(0, 500)
    axes[0].set_ylim(-250, 250)
    axes[0].set_xlabel("z [cm]")
    axes[0].set_ylabel("y [cm]")
    title = true_label + ": Event " + str(event) + ", " + apa + ", " + view
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
    if true_clusters:
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
    if predicted_clusters:
        axes[1].legend()

    plt.tight_layout()
    plt.savefig(PLOTDIR_EVT / f"{filename_stem}_event{event}_apa_{apa}_{view}.png")
   # plt.show(block=False)
    plt.close()

def DrawTrueRecoClustersXY(true_clusters, predicted_clusters, event, apa, PLOTDIR_EVT, file_name=None,
                             filename_stem="all_clusters_reco_true", true_label="True clusters"):
    """Draw true and reco clusters in XY projection for comparison.

    filename_stem / true_label exist so the same drawer can produce a SUBSET view of the
    same event: pass a filtered true_clusters plus a distinct stem and left-panel label
    (see DrawNeutrinoRecoClusters). Defaults reproduce the original all-clusters plot
    exactly, so existing callers are unaffected.
    """
    marker_size = 1
    view = "XY"

    fig, axes = plt.subplots(1, 2, figsize=(12, 6))

    # First subplot - True clusters
    axes[0].set_xlim(-250, 250)
    axes[0].set_ylim(-250, 250)
    axes[0].set_xlabel("x [cm]")
    axes[0].set_ylabel("y [cm]")
    title = true_label + ": Event " + str(event) + ", " + apa + ", " + view
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
    if true_clusters:
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
    if predicted_clusters:
        axes[1].legend()

    plt.tight_layout()
    plt.savefig(PLOTDIR_EVT / f"{filename_stem}_event{event}_apa_{apa}_{view}.png")
   # plt.show(block=False)
    plt.close()

def DrawNeutrinoRecoClusters(true_clusters, predicted_clusters, event, apa, PLOTDIR_EVT, file_name=None):
    """
    The same three XZ/YZ/XY true-vs-reco panels as DrawTrueRecoClusters{XZ,YZ,XY}, but with
    the left panel restricted to the TRUE NEUTRINO clusters of the event. The right panel is
    unchanged -- the full set of selected (beam-window) reco clusters -- so the pair answers
    "which of the reconstructed clusters is the neutrino, and did anything reconstruct it"
    without the cosmic tracks covering the picture.

    Written as a wrapper rather than three more drawers: it calls the same functions with a
    filtered true_clusters and its own filename stem, so the two sets can never drift apart
    in axes, limits or styling.

    Neutrino clusters are selected on q_true>0 (column 4 = nu_idx: 0=cosmic, 1/2/...=which
    interaction), not on the 99990+nu_idx cluster_id, so this stays correct for any pipeline
    whose true points carry q_true, whatever its ID scheme.

    Files: neutrino_clusters_reco_true_event{event}_apa_{apa}_{XZ,YZ,XY}.png

    An event with no true neutrino still gets its three plots, with an empty left panel --
    that is a real and interesting state (nothing to find), not a reason to skip the plot.
    """
    neutrino_clusters = {cid: pts for cid, pts in true_clusters.items()
                         if np.any(np.array(pts)[:, 4] > 0)}

    for draw in (DrawTrueRecoClustersXZ, DrawTrueRecoClustersYZ, DrawTrueRecoClustersXY):
        draw(neutrino_clusters, predicted_clusters, event, apa, PLOTDIR_EVT, file_name=file_name,
             filename_stem="neutrino_clusters_reco_true", true_label="True neutrino clusters")


def DrawTrueClusterWithMatchedReco(matched_info, clusters_true, clusters_reco, output_dir, event, apa, file_name=None,
                                    radius_efficiency=1, min_recopoints_threshold=5):
    """
    Draw a single true cluster with all its matched reco clusters (1-to-many).
    True cluster in red, matched reco clusters in distinct colors.
    Shows efficiency/purity values in legend. Zooms to true cluster bounds ±30%.
    A second row of views below shows only the true points that did not match
    any reco cluster (i.e. the points that were missed in the efficiency estimation).
    A true point is considered matched if, for at least one matched reco cluster,
    it has more than `min_recopoints_threshold` reco points within `radius_efficiency`
    - mirrors the per-point criterion used in EvaluateEfficiency.

    Parameters:
    - matched_info: Dict from MatchTruetoReco_OneToMany with keys:
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
    true_coords = true_points[:, :3]
    marker_size = 1
    colors = ['blue', 'green', 'orange', 'purple', 'cyan', 'magenta', 'brown', 'pink']

    fig, ((ax_xz, ax_yz, ax_xy), (ax_missed_xz, ax_missed_yz, ax_missed_xy)) = plt.subplots(
        2, 3, figsize=(24, 12), sharex='col', sharey='col')

    # Track which true points matched at least one reco cluster (same criterion as EvaluateEfficiency)
    matched_mask = np.zeros(len(true_points), dtype=bool)

    # Plot each matched reco cluster with different colors (first)
    for idx, reco_info in enumerate(matched_reco_list):
        reco_cid    = reco_info['reco_cluster_id']
        eff         = reco_info['efficiency_energy_weighted']
        pur         = reco_info['purity']

        if reco_cid not in clusters_reco:
            continue

        reco_points = np.array(clusters_reco[reco_cid])
        reco_coords = reco_points[:, :3]
        color       = colors[idx % len(colors)]
        label       = f'Reco ID={reco_cid:.0f} (ε={eff:.2f}, p={pur:.2f})'

        ax_xz.scatter(reco_points[:, 2], reco_points[:, 0], c=color, s=marker_size, alpha=0.7,
                      label=label)
        ax_yz.scatter(reco_points[:, 2], reco_points[:, 1], c=color, s=marker_size, alpha=0.7,
                      label=label)
        ax_xy.scatter(reco_points[:, 0], reco_points[:, 1], c=color, s=marker_size, alpha=0.7,
                      label=label)

        reco_tree = KDTree(reco_coords)
        neighbors = reco_tree.query_ball_point(true_coords, r=radius_efficiency)
        matched_mask |= np.array([len(n) > min_recopoints_threshold for n in neighbors])

    missed_points = true_points[~matched_mask]
    
    # Plot true cluster (red) on top of reco clusters
    ax_xz.scatter(true_points[:, 2], true_points[:, 0], c='red', s=marker_size, alpha=0.8,
                  label=f'True ID={true_cid:.0f}', zorder=10)
    ax_yz.scatter(true_points[:, 2], true_points[:, 1], c='red', s=marker_size, alpha=0.8,
                  label=f'True ID={true_cid:.0f}', zorder=10)
    ax_xy.scatter(true_points[:, 0], true_points[:, 1], c='red', s=marker_size, alpha=0.8,
                  label=f'True ID={true_cid:.0f}', zorder=10)

    # Plot only the missed (unmatched) true points on the second row
    if len(missed_points) > 0:
        missed_label = f'True ID={true_cid:.0f} (missed, {len(missed_points)}/{len(true_points)} pts)'
        ax_missed_xz.scatter(missed_points[:, 2], missed_points[:, 0], c='red', s=marker_size, alpha=0.8,
                              label=missed_label)
        ax_missed_yz.scatter(missed_points[:, 2], missed_points[:, 1], c='red', s=marker_size, alpha=0.8,
                              label=missed_label)
        ax_missed_xy.scatter(missed_points[:, 0], missed_points[:, 1], c='red', s=marker_size, alpha=0.8,
                              label=missed_label)

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
    ax_xz.set_xlim(z_lim)
    ax_xz.set_ylim(x_lim)
    ax_xz.set_xlabel('Z [cm]', fontsize=12, fontweight='bold')
    ax_xz.set_ylabel('X [cm]', fontsize=12, fontweight='bold')
    xz_title = f'True Cluster {true_cid:.0f} with Matched Reco (XZ) - Event {event}, {apa}'
    if file_name:
        xz_title += f' ({file_name})'
    ax_xz.set_title(xz_title, fontsize=12, fontweight='bold')
    ax_xz.legend(fontsize=18, loc='upper right', framealpha=0.9)
    ax_xz.grid(True, linestyle='--', alpha=0.3)

    # YZ projection
    ax_yz.set_xlim(z_lim)
    ax_yz.set_ylim(y_lim)
    ax_yz.set_xlabel('Z [cm]', fontsize=12, fontweight='bold')
    ax_yz.set_ylabel('Y [cm]', fontsize=12, fontweight='bold')
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

    # Missed XZ projection
    ax_missed_xz.set_xlim(z_lim)
    ax_missed_xz.set_ylim(x_lim)
    ax_missed_xz.set_xlabel('Z [cm]', fontsize=12, fontweight='bold')
    ax_missed_xz.set_ylabel('X [cm]', fontsize=12, fontweight='bold')
    missed_xz_title = f'True Cluster {true_cid:.0f} Missed Points (XZ) - Event {event}, {apa}'
    if file_name:
        missed_xz_title += f' ({file_name})'
    ax_missed_xz.set_title(missed_xz_title, fontsize=12, fontweight='bold')
    if len(missed_points) > 0:
        ax_missed_xz.legend(fontsize=18, loc='upper right', framealpha=0.9)
    ax_missed_xz.grid(True, linestyle='--', alpha=0.3)

    # Missed YZ projection
    ax_missed_yz.set_xlim(z_lim)
    ax_missed_yz.set_ylim(y_lim)
    ax_missed_yz.set_xlabel('Z [cm]', fontsize=12, fontweight='bold')
    ax_missed_yz.set_ylabel('Y [cm]', fontsize=12, fontweight='bold')
    missed_yz_title = f'True Cluster {true_cid:.0f} Missed Points (YZ) - Event {event}, {apa}'
    if file_name:
        missed_yz_title += f' ({file_name})'
    ax_missed_yz.set_title(missed_yz_title, fontsize=12, fontweight='bold')
    if len(missed_points) > 0:
        ax_missed_yz.legend(fontsize=18, loc='upper right', framealpha=0.9)
    ax_missed_yz.grid(True, linestyle='--', alpha=0.3)

    # Missed XY projection
    ax_missed_xy.set_xlim(x_lim)
    ax_missed_xy.set_ylim(y_lim)
    ax_missed_xy.set_xlabel('X [cm]', fontsize=12, fontweight='bold')
    ax_missed_xy.set_ylabel('Y [cm]', fontsize=12, fontweight='bold')
    missed_xy_title = f'True Cluster {true_cid:.0f} Missed Points (XY) - Event {event}, {apa}'
    if file_name:
        missed_xy_title += f' ({file_name})'
    ax_missed_xy.set_title(missed_xy_title, fontsize=12, fontweight='bold')
    if len(missed_points) > 0:
        ax_missed_xy.legend(fontsize=18, loc='upper right', framealpha=0.9)
    ax_missed_xy.grid(True, linestyle='--', alpha=0.3)

    plt.tight_layout()
    reco_ids_str = '_'.join(f"{r['reco_cluster_id']:.0f}" for r in matched_reco_list)
    plt.savefig(output_dir / f"true_cluster_{true_cid:.0f}_with_reco_{reco_ids_str}_event_{event}_{apa}.png",
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

        # q_true>0, NOT q_true==1: q_true carries nu_idx in the charge-light pipeline
        # (0=cosmic, 1/2/3/...=which neutrino interaction), so ==1 would count only the
        # first interaction of an event as neutrino. Equivalent to ==1 for the legacy
        # pipelines' plain 0/1 flag.
        if q_true > 0:
            neutrino_clusters.append(cluster_id)
        else:
            cosmic_clusters.append(cluster_id)

    # Create figure with bar plot
    fig, ax = plt.subplots(figsize=(10, 6))

    categories = ['Neutrino\n(q_true>0)', 'Cosmic\n(q_true=0)']
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


def DrawLabelsAggregated(cluster_type_records, output_dir, level_name, filename_prefix, apa, file_name=None,
                         vertex_records=None):
    """
    Bar chart of true CLUSTER counts: Neutrino (any q_true>0, aggregated
    across however many distinct neutrino indices are present) vs Cosmic
    (q_true=0). Used at Event/File/Job level alike -- cluster_type_records
    can span multiple events (see metadata.build_true_cluster_type_records()).

    This is the two-bar aggregate view DrawLabels/DrawLabelPerFile/
    DrawLabelPerJob already provide, reproduced here reading is_neutrino from
    build_true_cluster_type_records() (q_true>0 check) instead of
    cluster_category_results (q_true==1 exact-match check, silently wrong once
    q_true can be a neutrino index of 2 or higher). Since
    reassign_cluster_ID_true already merges every neutrino point into one
    cluster_id=9999 regardless of index, this never shows more than 1
    neutrino cluster -- for a per-neutrino-index breakdown, see
    DrawLabelsByNuIdx instead.

    Parameters:
    - cluster_type_records: List of dicts from metadata.build_true_cluster_type_records(),
        each with 'cluster_id', 'is_neutrino'
    - output_dir: Output directory
    - level_name: Label for the title (e.g. 'Event 9', 'File Level', 'Job Level')
    - filename_prefix: Suffix used in the output filename (e.g. 'event_9', 'file', 'job')
    - apa: APA identifier (label only, e.g. "Combined")
    - file_name: Optional input file name for title
    - vertex_records: Optional metadata.build_neutrino_vertex_records() output; when
        given, a leading bar shows the TOTAL true neutrino interactions from mc.json
        (deposits or not, cut or not) alongside the surviving-cluster counts
    """
    if not cluster_type_records:
        return

    n_neutrino = sum(1 for r in cluster_type_records if r['is_neutrino'])
    n_cosmic   = sum(1 for r in cluster_type_records if not r['is_neutrino'])

    fig, ax = plt.subplots(figsize=(10, 6))
    if vertex_records:
        # Neutrino bar = every true neutrino INTERACTION in mc.json (deposits or
        # not, cut or not). Neither the depositing count nor the post-cut
        # surviving count is shown here -- true_neutrino_breakdown_*.png splits
        # exactly these interactions three ways, and removed_true_neutrino_info.txt
        # records what went missing and why.
        # NOTE the two bars are different quantities: neutrino INTERACTIONS
        # against cosmic CLUSTERS. They are not directly comparable, which is why
        # each bar names its source.
        categories = ['Total true neutrinos\n(mc.json interactions)',
                      'Cosmic clusters\n(q_true=0)']
        counts = [len(vertex_records), n_cosmic]
        colors = ['red', 'blue']
    else:
        # No vertex records (other pipelines): original neutrino/cosmic CLUSTER counts
        categories = ['Neutrino\n(q_true>0)', 'Cosmic\n(q_true=0)']
        counts = [n_neutrino, n_cosmic]
        colors = ['red', 'blue']
    bars = ax.bar(categories, counts, width=0.4, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2., height, f'{int(count)}',
                ha='center', va='bottom', fontsize=14, fontweight='bold')

    ax.set_ylabel('Number of Clusters', fontsize=12, fontweight='bold')
    ax.set_xlabel('Cluster Type', fontsize=12, fontweight='bold')
    title = f'True Clusters by Type (Aggregated): {level_name}, {apa}'
    if file_name:
        title += f' ({file_name})'
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_dir / f'labels_aggregated_{filename_prefix}_{apa}.png', dpi=100, bbox_inches='tight')
    plt.close()


def DrawLabelsByNuIdx(cluster_type_records, output_dir, level_name, filename_prefix, apa, file_name=None):
    """
    Bar chart of true CLUSTER counts split by nu_idx: Cosmic (q_true=0),
    1st/2nd/3rd/... neutrino (nu_idx=1/2/3/...). Used at Event/File/Job level
    alike -- cluster_type_records can span multiple events.

    Unlike DrawLabelsAggregated (one "any neutrino" bucket, capped at 1 per
    event since reassign_cluster_ID_true merges every neutrino point into a
    single cluster_id=9999), this expands cluster 9999 using
    cluster_type_records' 'nu_idx_values' field (build_true_cluster_type_records)
    -- one count per DISTINCT nu_idx value found, so multiple neutrino
    interactions merged under the same cluster_id are still counted
    separately here. Bar labels/count of bars adapt to whatever nu_idx values
    are actually present in the data (e.g. only "1st neutrino" bars appear if
    no event has 2+ neutrino interactions).

    Parameters:
    - cluster_type_records: List of dicts from metadata.build_true_cluster_type_records(),
        each with 'is_neutrino', 'nu_idx_values'
    - output_dir: Output directory
    - level_name: Label for the title (e.g. 'Event 9', 'File Level', 'Job Level')
    - filename_prefix: Suffix used in the output filename (e.g. 'event_9', 'file', 'job')
    - apa: APA identifier (label only, e.g. "Combined")
    - file_name: Optional input file name for title
    """
    if not cluster_type_records:
        return

    n_cosmic = sum(1 for r in cluster_type_records if not r['is_neutrino'])
    nu_idx_counts = {}
    for r in cluster_type_records:
        for nu_idx in r.get('nu_idx_values', []):
            nu_idx_counts[nu_idx] = nu_idx_counts.get(nu_idx, 0) + 1

    ordinal = {1: '1st', 2: '2nd', 3: '3rd'}
    categories = ['Cosmic\n(q_true=0)']
    counts = [n_cosmic]
    colors = ['blue']
    for nu_idx in sorted(nu_idx_counts):
        label = ordinal.get(nu_idx, f'{nu_idx}th')
        categories.append(f'{label} neutrino\n(nu_idx={nu_idx})')
        counts.append(nu_idx_counts[nu_idx])
        colors.append('red')

    fig, ax = plt.subplots(figsize=(max(10, 2 * len(categories)), 6))
    bars = ax.bar(categories, counts, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2., height, f'{int(count)}',
                ha='center', va='bottom', fontsize=14, fontweight='bold')

    ax.set_ylabel('Number of Clusters', fontsize=12, fontweight='bold')
    ax.set_xlabel('Cluster Type', fontsize=12, fontweight='bold')
    title = f'True Clusters by Type (By Neutrino Index): {level_name}, {apa}'
    if file_name:
        title += f' ({file_name})'
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_dir / f'labels_by_nu_idx_{filename_prefix}_{apa}.png', dpi=100, bbox_inches='tight')
    plt.close()


def _count_cluster_types(metadata_list):
    """
    Count neutrino vs cosmic true clusters, and cosmic sub-categories, from a metadata list
    produced by add_metadata_true_clusters (one entry per true cluster per event).
    Also returns the number of unique events represented in the list.
    """
    neutrino_count = sum(1 for m in metadata_list if m['cluster_type'] == 'neutrino')
    cosmic_count   = sum(1 for m in metadata_list if m['cluster_type'] == 'cosmic')

    cosmic_categories = {'isochronous': 0, 'normal': 0, 'prolonged': 0}
    for m in metadata_list:
        if m['cluster_type'] == 'cosmic':
            cosmic_categories[m['cluster_category']] = cosmic_categories.get(m['cluster_category'], 0) + 1

    num_events = len(set(m['event'] for m in metadata_list))
    return neutrino_count, cosmic_count, cosmic_categories, num_events

def _draw_neutrino_cosmic_bar(metadata_list, output_dir, apa, level_name, filename_prefix, file_name=None):
    """
    Bar chart of neutrino vs cosmic true cluster counts, aggregated over many events
    (file level or job level).
    """
    if not metadata_list:
        return

    neutrino_count, cosmic_count, _, num_events = _count_cluster_types(metadata_list)

    fig, ax = plt.subplots(figsize=(10, 6))
    categories = ['Neutrino', 'Cosmic']
    counts     = [neutrino_count, cosmic_count]
    colors     = ['red', 'blue']

    bars = ax.bar(categories, counts, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2., height, f'{int(count)}',
                ha='center', va='bottom', fontsize=14, fontweight='bold')

    ax.set_ylabel('Number of True Clusters', fontsize=12, fontweight='bold')
    ax.set_xlabel('Cluster Type', fontsize=12, fontweight='bold')
    title = f'True Clusters by Type - {level_name}, {num_events} events, {apa}'
    if file_name:
        title += f' ({file_name})'
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(output_dir / f"true_clusters_by_type_{filename_prefix}_{num_events}events_{apa}.png",
                dpi=100, bbox_inches='tight')
    plt.close()

def _draw_cosmic_category_bar(metadata_list, output_dir, apa, level_name, filename_prefix, file_name=None):
    """
    Bar chart of cosmic true cluster sub-categories (isochronous, normal, prolonged),
    aggregated over many events (file level or job level).
    """
    if not metadata_list:
        return

    _, cosmic_count, cosmic_categories, num_events = _count_cluster_types(metadata_list)
    if cosmic_count == 0:
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    categories = ['Isochronous', 'Normal', 'Prolonged']
    counts     = [cosmic_categories['isochronous'], cosmic_categories['normal'], cosmic_categories['prolonged']]
    colors     = ['orange', 'green', 'purple']

    bars = ax.bar(categories, counts, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2., height, f'{int(count)}',
                ha='center', va='bottom', fontsize=14, fontweight='bold')

    ax.set_ylabel('Number of Cosmic True Clusters', fontsize=12, fontweight='bold')
    ax.set_xlabel('Cosmic Track Category', fontsize=12, fontweight='bold')
    title = f'Cosmic Clusters by Category - {level_name}, {num_events} events, {apa}'
    if file_name:
        title += f' ({file_name})'
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(output_dir / f"cosmic_clusters_by_category_{filename_prefix}_{num_events}events_{apa}.png",
                dpi=100, bbox_inches='tight')
    plt.close()

def DrawLabelPerFile(file_metadata_list, output_dir, apa, file_name=None):
    """
    File-level version of DrawLabels. Draws two bar charts aggregated over all events in a file:
    1. Neutrino vs cosmic true cluster counts.
    2. Cosmic true clusters broken down into isochronous, normal, and prolonged categories.

    Parameters:
    - file_metadata_list: List of per-true-cluster metadata dicts from add_metadata_true_clusters,
      with keys 'event', 'cluster_type' ('neutrino'/'cosmic'), 'cluster_category'
      ('isochronous'/'normal'/'prolonged')
    - output_dir: Output directory
    - apa: APA identifier
    - file_name: Optional file name for title
    """
    _draw_neutrino_cosmic_bar(file_metadata_list, output_dir, apa, 'File Level', 'file', file_name=file_name)
    _draw_cosmic_category_bar(file_metadata_list, output_dir, apa, 'File Level', 'file', file_name=file_name)

def DrawLabelPerJob(job_metadata_list, output_dir, apa):
    """
    Job-level version of DrawLabels. Draws two bar charts aggregated over all events across all files:
    1. Neutrino vs cosmic true cluster counts.
    2. Cosmic true clusters broken down into isochronous, normal, and prolonged categories.

    Parameters:
    - job_metadata_list: List of per-true-cluster metadata dicts from add_metadata_true_clusters,
      with keys 'event', 'cluster_type' ('neutrino'/'cosmic'), 'cluster_category'
      ('isochronous'/'normal'/'prolonged')
    - output_dir: Output directory
    - apa: APA identifier
    """
    _draw_neutrino_cosmic_bar(job_metadata_list, output_dir, apa, 'Job Level', 'job')
    _draw_cosmic_category_bar(job_metadata_list, output_dir, apa, 'Job Level', 'job')

def _draw_match_multiplicity_bar(metadata_list, output_dir, apa, level_name, filename_prefix,
                                 category_label, category_suffix, bar_color, file_name=None):
    """
    Single bar chart of true-reco match multiplicity for one cluster category.
    Bins: 0 (unmatched), 1, 2, 3, 4, 5, and 5+ (more than 5) matched reco clusters.
    Unmatched true clusters (total_efficiency == 0, whose single metadata entry is the
    8888 sentinel) fill the '0' bin.
    """
    if not metadata_list:
        return

    num_events = len(set(m['event'] for m in metadata_list))

    bin_labels = ['0', '1', '2', '3', '4', '5', '5+']
    counts     = [0] * len(bin_labels)
    for m in metadata_list:
        if m['total_efficiency'] <= 0:
            counts[0] += 1
        elif m['num_reco_matches'] <= 5:
            counts[m['num_reco_matches']] += 1
        else:
            counts[6] += 1

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(bin_labels, counts, color=bar_color, alpha=0.7, edgecolor='black', linewidth=2)
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2., height, f'{int(count)}',
                ha='center', va='bottom', fontsize=14, fontweight='bold')

    ax.set_ylabel('Number of True Clusters', fontsize=12, fontweight='bold')
    ax.set_xlabel('Number of Matched Reco Clusters', fontsize=12, fontweight='bold')
    title = f'True-Reco Match Multiplicity ({category_label}) - {level_name}, {num_events} events, {apa}'
    if file_name:
        title += f' ({file_name})'
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    multiplicity_dir = output_dir / "true_reco_matched_multiplicity"
    multiplicity_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(multiplicity_dir / f"true_reco_match_multiplicity_{category_suffix}_{filename_prefix}_{apa}.png",
                dpi=100, bbox_inches='tight')
    plt.close()

def DrawTrueRecoMatchMultiplicity(metadata_list, output_dir, apa, level_name, filename_prefix, file_name=None):
    """
    Bar charts of how many true clusters match to how many reco clusters, using the
    per-true-cluster metadata from add_metadata_true_clusters ('num_reco_matches' key).
    Bins: 0 (unmatched), 1, 2, 3, 4, 5, and 5+ (more than 5) matched reco clusters.

    Draws one chart for all clusters, plus separate charts for neutrino clusters,
    all cosmic clusters, and each cosmic sub-category (isochronous, normal, prolonged).
    Categories with no clusters are skipped.

    Parameters:
    - metadata_list: List of per-true-cluster metadata dicts from add_metadata_true_clusters
    - output_dir: Output directory
    - apa: APA identifier
    - level_name: Label for the title (e.g. 'Event 5', 'File Level', 'Job Level')
    - filename_prefix: Suffix used in the output filename (e.g. 'event_5', 'file', 'job')
    - file_name: Optional input file name for title
    """
    if not metadata_list:
        return

    categories = [
        ('All Clusters',       'all',                lambda m: True,                                                                     'steelblue'),
        ('Neutrino',           'neutrino',           lambda m: m['cluster_type'] == 'neutrino',                                          'red'),
        ('All Cosmics',        'cosmic',             lambda m: m['cluster_type'] == 'cosmic',                                            'blue'),
        ('Isochronous Cosmic', 'isochronous_cosmic', lambda m: m['cluster_type'] == 'cosmic' and m['cluster_category'] == 'isochronous', 'orange'),
        ('Normal Cosmic',      'normal_cosmic',      lambda m: m['cluster_type'] == 'cosmic' and m['cluster_category'] == 'normal',      'green'),
        ('Prolonged Cosmic',   'prolonged_cosmic',   lambda m: m['cluster_type'] == 'cosmic' and m['cluster_category'] == 'prolonged',   'purple'),
    ]

    for category_label, category_suffix, selector, bar_color in categories:
        category_metadata = [m for m in metadata_list if selector(m)]
        _draw_match_multiplicity_bar(category_metadata, output_dir, apa, level_name, filename_prefix,
                                     category_label, category_suffix, bar_color, file_name=file_name)

    # Write lookup text files for true clusters with a reco-match count other than 1
    _write_non_one_match_clusters(metadata_list, output_dir, level_name, filename_prefix, apa, file_name=file_name)

def _write_non_one_match_clusters(metadata_list, output_dir, level_name, filename_prefix, apa, file_name=None):
    """
    Write true clusters whose reco-match count is not exactly 1 (i.e. 0, 2, 3, 4, 5, or 5+)
    to text files for later lookup when inspecting cluster plots. Separate files are written
    for neutrino clusters and for all cosmic clusters; the cosmic file additionally lists each
    cluster's cosmic sub-category (isochronous, normal, prolonged).

    Match count is corrected the same way as the multiplicity bar charts: a true cluster with
    total_efficiency <= 0 (unmatched, 8888 sentinel) counts as 0 matches rather than the raw
    num_reco_matches value of 1.
    """
    if not metadata_list:
        return

    def _corrected_count(m):
        return 0 if m['total_efficiency'] <= 0 else m['num_reco_matches']

    flagged = [m for m in metadata_list if _corrected_count(m) != 1]
    if not flagged:
        return

    num_events = len(set(m['event'] for m in metadata_list))
    multiplicity_dir = output_dir / "true_reco_matched_multiplicity"
    multiplicity_dir.mkdir(parents=True, exist_ok=True)

    def _header(category_label):
        lines = [
            f"{category_label} True Clusters with Reco-Match Count != 1",
            f"Level: {level_name}, {apa}, {num_events} events" + (f" ({file_name})" if file_name else ""),
            "=" * 80,
        ]
        return lines

    # Neutrino clusters
    neutrino_flagged = [m for m in flagged if m['cluster_type'] == 'neutrino']
    if neutrino_flagged:
        lines = _header("Neutrino")
        lines.append(f"{'event':<20}{'true_cluster_id':<18}{'num_reco_matches':<18}")
        for m in sorted(neutrino_flagged, key=lambda m: (str(m['event']), m['true_cluster_id'])):
            lines.append(f"{str(m['event']):<20}{m['true_cluster_id']:<18.0f}{_corrected_count(m):<18}")
        with open(multiplicity_dir / f"non_one_match_neutrino_{filename_prefix}_{apa}.txt", 'w') as f:
            f.write('\n'.join(lines) + '\n')

    # All cosmic clusters, with sub-category (isochronous/normal/prolonged) noted
    cosmic_flagged = [m for m in flagged if m['cluster_type'] == 'cosmic']
    if cosmic_flagged:
        lines = _header("Cosmic")
        lines.append(f"{'event':<20}{'true_cluster_id':<18}{'num_reco_matches':<18}{'cosmic_category':<15}")
        for m in sorted(cosmic_flagged, key=lambda m: (m['cluster_category'], str(m['event']), m['true_cluster_id'])):
            lines.append(f"{str(m['event']):<20}{m['true_cluster_id']:<18.0f}{_corrected_count(m):<18}{m['cluster_category']:<15}")
        with open(multiplicity_dir / f"non_one_match_cosmic_{filename_prefix}_{apa}.txt", 'w') as f:
            f.write('\n'.join(lines) + '\n')

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
    #print(f"\nSaved cluster category XZ plot to: {plot_path}")
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


# ============================================================================
# CHARGE-LIGHT MATCHING FORMAT (additive; existing functions above are untouched)
# ============================================================================

def draw_clustering_global_clusters(all_clusters, beam_window_clusters, event, apa, output_dir, file_name=None):
    """
    Draw clustering-global clusters (post charge-light-matching) in XZ, YZ,
    XY projections as a 2x3 grid of panels: row 1 = all clusters, row 2 =
    only clusters whose associated flash (via
    metadata.build_img_cluster_flash_metadata()) falls inside the beam
    window. XZ/YZ put Z on the x-axis (matching DrawTrueRecoClustersXZ/YZ's
    convention above). Event level only -- not meant to be aggregated to
    file/job level.

    Parameters:
    - all_clusters, beam_window_clusters: dicts {cluster_id: points}, points
        columns [x, y, z, cluster_id, charge]. Grouped by clustering-global.json's
        own cluster_id (a different numbering scheme than img-global's cluster_id --
        see build_img_cluster_flash_metadata in metadata.py). beam_window_clusters
        must be a subset of all_clusters (same cluster_id keys) so both panels
        use the same color per cluster ID.
    - event: Event number
    - apa: APA label (e.g. "Combined")
    - output_dir: Output directory
    - file_name: Optional input file name for title
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Same color for the same cluster_id in both rows, instead of each
    # subplot's independent color cycle -- see draw_img_global_clusters in
    # DrawRecoTrueFlashes.py for the identical rationale.
    color_cycle = plt.rcParams['axes.prop_cycle'].by_key()['color']
    cluster_colors = {
        cluster_id: color_cycle[i % len(color_cycle)]
        for i, cluster_id in enumerate(sorted(all_clusters.keys()))
    }

    # "All Clusters" row skips the per-cluster legend if there are many
    # clusters, same reasoning as draw_img_global_clusters.
    rows = [
        ("All Clusters", all_clusters, len(all_clusters) <= 20),
        ("Clusters In Beam Window", beam_window_clusters, True),
    ]
    # (view_label, x_col, y_col, xlim, ylim, xlabel, ylabel)
    views = [
        ("XZ", 2, 0, (0, 500), (-250, 250), "z [cm]", "x [cm]"),
        ("YZ", 2, 1, (0, 500), (-250, 250), "z [cm]", "y [cm]"),
        ("XY", 0, 1, (-250, 250), (-250, 250), "x [cm]", "y [cm]"),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(18, 12))

    for row_idx, (row_label, clusters, show_legend) in enumerate(rows):
        for col_idx, (view_label, x_col, y_col, xlim, ylim, xlabel, ylabel) in enumerate(views):
            ax = axes[row_idx, col_idx]
            ax.set_xlim(xlim)
            ax.set_ylim(ylim)
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            title = f"{row_label}: Event {event}, {apa}, {view_label}"
            if file_name:
                title += f" ({file_name})"
            ax.set_title(title, fontsize=10)

            for cluster_id, points in clusters.items():
                points = np.array(points)
                color = cluster_colors[cluster_id]
                ax.scatter(points[:, x_col], points[:, y_col], s=1, alpha=0.5, color=color)
                if show_legend:
                    ax.plot([], [], color=color, label=f'Cluster {cluster_id:.0f}')
            if clusters and show_legend:
                ax.legend(fontsize=6, loc='upper right')
            elif clusters:
                ax.text(0.98, 0.98, f'{len(clusters)} clusters', transform=ax.transAxes,
                        fontsize=8, ha='right', va='top',
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))

    plt.tight_layout()
    plt.savefig(output_dir / f"clustering_global_clusters_event{event}_{apa}.png", dpi=100)
    plt.close()


def DrawNeutrinoVertices(vertex_records, output_dir, level_name, filename_prefix, apa,
                         file_name=None, x_min=None, x_max=None, y_min=None, y_max=None,
                         z_min=None, z_max=None, volume_label="wire-readout sensitive box"):
    """
    2D scatter of TRUE NEUTRINO interaction vertices (mc.json), in XZ, YZ and XY
    projections, as a 2x2 grid whose fourth panel carries the shared legend.
    Event/File/Job level alike -- vertex_records can span any number of events
    (metadata.build_neutrino_vertex_records).

    ALL interactions are drawn -- in-volume, out-of-volume, and those that
    deposited nothing. Colour encodes in/out of the volume, marker fill encodes
    whether anything was deposited (open = no deposits).

    Vertices are split by whether they fall inside the volume bounds, and the
    volume itself is drawn as a rectangle in each panel, so the in/out
    classification can be judged by eye rather than taken on trust -- the point
    being to decide from the job-level plot which volume definition to adopt.
    Axes auto-scale to the data (out-of-volume vertices sit far outside the
    detector, hundreds of cm away) while always containing the box, so nothing
    is silently clipped out of view.

    Only neutrinos appear here: cosmics have no mc.json interaction vertex.

    Parameters:
    - vertex_records: List of dicts from metadata.build_neutrino_vertex_records(),
        each with 'vertex_x', 'vertex_y', 'vertex_z', 'vertex_in_volume'
    - output_dir: Output directory
    - level_name: Label for the title (e.g. 'Event 9', 'File Level', 'Job Level')
    - filename_prefix: Suffix used in the output filename (e.g. 'event_9', 'file', 'job')
    - apa: APA identifier (label only, e.g. "Combined")
    - file_name: Optional input file name for title
    - x_min..z_max: volume bounds to draw; the box is skipped if any is None
    - volume_label: how the box is described in the legend
    """
    # ALL interactions are drawn -- in-volume and out-of-volume, including those
    # that deposited nothing in the active volume. This is a map of where the
    # neutrinos were, so leaving any out would misrepresent the sample. All
    # markers are solid; COLOUR alone separates the three groups (green =
    # in-volume, orange = out-of-volume with deposits, purple = out-of-volume
    # with none -- the last are absent from every cluster-level plot and are
    # itemised in removed_true_neutrino_info.txt).
    drawn = [r for r in vertex_records
             if r.get('vertex_x') is not None and r.get('vertex_y') is not None and r.get('vertex_z') is not None]
    if not drawn:
        return

    def _deposited(record):
        # A surviving cluster obviously deposited; precut_n_points catches the
        # ones the cuts later removed (only available when
        # build_neutrino_vertex_records was given clusters_true_precut).
        return bool(record.get('has_true_cluster') or record.get('precut_n_points', 0) > 0)

    groups = [
        ([r for r in drawn if r.get('vertex_in_volume') is True and _deposited(r)],
         'green', 'o', True, 'in volume, deposits'),
        ([r for r in drawn if r.get('vertex_in_volume') is True and not _deposited(r)],
         'green', 'o', False, 'in volume, NO deposits'),
        ([r for r in drawn if r.get('vertex_in_volume') is not True and _deposited(r)],
         'darkorange', '^', True, 'out of volume, deposits'),
        # Own COLOUR, not just an open marker: these are the interactions that are
        # invisible to the detector entirely (mc.json Edep = 0, no sed points), and
        # where they sit relative to the volume is the thing worth seeing. Sharing
        # orange with the depositing out-of-volume group made the two separable
        # only by fill, which is far too subtle at this point density.
        ([r for r in drawn if r.get('vertex_in_volume') is not True and not _deposited(r)],
         'purple', '^', True, 'out of volume, NO deposits'),
    ]
    have_box = all(b is not None for b in (x_min, x_max, y_min, y_max, z_min, z_max))

    # (view, x key, y key, xlabel, ylabel, box x range, box y range)
    views = [
        ("XZ", 'vertex_z', 'vertex_x', "z [cm]", "x [cm]", (z_min, z_max), (x_min, x_max)),
        ("YZ", 'vertex_z', 'vertex_y', "z [cm]", "y [cm]", (z_min, z_max), (y_min, y_max)),
        ("XY", 'vertex_x', 'vertex_y', "x [cm]", "y [cm]", (x_min, x_max), (y_min, y_max)),
    ]

    # 2x2: the three projections plus a dedicated legend panel. One shared legend
    # at readable size beats the same three entries repeated in every panel, and
    # the freed corner costs nothing since there are only three views.
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    panels = [axes[0, 0], axes[0, 1], axes[1, 0]]
    legend_ax = axes[1, 1]
    legend_handles = None

    # Spell the bounds out in the legend: "in volume" is meaningless without the
    # numbers behind it, and these are the values that decide every in/out count
    # in this plot and the bar charts beside it.
    if have_box:
        box_label = (f"{volume_label}\n"
                     f"x: [{x_min:g}, {x_max:g}] cm\n"
                     f"y: [{y_min:g}, {y_max:g}] cm\n"
                     f"z: [{z_min:g}, {z_max:g}] cm")
    else:
        box_label = volume_label

    for ax, (view_label, xk, yk, xlabel, ylabel, box_x, box_y) in zip(panels, views):
        for group, color, marker, filled, label in groups:
            if group:
                ax.scatter([r[xk] for r in group], [r[yk] for r in group],
                           s=34, alpha=0.75, marker=marker,
                           facecolors=(color if filled else 'none'), edgecolors=color,
                           linewidths=1.4, label=f'{label} ({len(group)})')

        if have_box:
            ax.add_patch(plt.Rectangle((box_x[0], box_y[0]), box_x[1] - box_x[0], box_y[1] - box_y[0],
                                       fill=False, edgecolor='black', linewidth=1.8, linestyle='--',
                                       label=box_label))
            # Always show the whole box plus the data, with a margin on the wider of the two
            xs = [r[xk] for r in drawn] + list(box_x)
            ys = [r[yk] for r in drawn] + list(box_y)
        else:
            xs = [r[xk] for r in drawn]
            ys = [r[yk] for r in drawn]

        x_pad = max((max(xs) - min(xs)) * 0.05, 10.0)
        y_pad = max((max(ys) - min(ys)) * 0.05, 10.0)
        ax.set_xlim(min(xs) - x_pad, max(xs) + x_pad)
        ax.set_ylim(min(ys) - y_pad, max(ys) + y_pad)
        ax.set_xlabel(xlabel, fontsize=12, fontweight='bold')
        ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
        title = f"True Neutrino Vertices: {level_name}, {apa}, {view_label}"
        if file_name:
            title += f" ({file_name})"
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=11)
        if legend_handles is None:
            legend_handles = ax.get_legend_handles_labels()

    legend_ax.axis('off')
    if legend_handles and legend_handles[0]:
        legend_ax.legend(*legend_handles, fontsize=16, loc='center', frameon=True,
                         title=f"True neutrino interactions: {len(drawn)}", title_fontsize=18,
                         labelspacing=1.1, borderpad=1.0)

    plt.tight_layout()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_dir / f"true_neutrino_vertices_{filename_prefix}_{apa}.png", dpi=100, bbox_inches='tight')
    plt.close()


def DrawNeutrinoVolumeCategory(vertex_records, output_dir, level_name, filename_prefix, apa, file_name=None,
                               volume_label="wire-readout sensitive box"):
    """
    Bar chart of true neutrino interactions split by whether their mc.json vertex
    falls inside the volume: In-volume vs Out-of-volume. Event/File/Job level
    alike (metadata.build_neutrino_vertex_records records can span any number of
    events).

    Only interactions whose true cluster SURVIVED all true selections are counted,
    so the two bars sum to the neutrino count in labels_aggregated /
    true_cluster_info.txt for the same level.

    This is a CLASSIFICATION of the neutrino sample, not a cut: nothing in the
    pipeline selects on the vertex. The energy selection stays deposit-based
    (apply_energy_cutoff on the summed sed point energies) exactly as before --
    an out-of-volume interaction whose daughter deposits inside the TPC is still
    a perfectly good cluster and is treated as one everywhere else.

    Parameters:
    - vertex_records: List of dicts from metadata.build_neutrino_vertex_records(),
        each with 'vertex_in_volume'
    - output_dir: Output directory
    - level_name: Label for the title (e.g. 'Event 9', 'File Level', 'Job Level')
    - filename_prefix: Suffix used in the output filename (e.g. 'event_9', 'file', 'job')
    - apa: APA identifier (label only, e.g. "Combined")
    - file_name: Optional input file name for title
    - volume_label: how the volume is described in the axis label
    """
    # SURVIVORS ONLY -- see DrawNeutrinoVertices for why, and
    # removed_true_neutrino_info.txt for what was dropped.
    surviving = [r for r in vertex_records if r.get('has_true_cluster')]
    if not surviving:
        return

    n_in  = sum(1 for r in surviving if r.get('vertex_in_volume') is True)
    n_out = sum(1 for r in surviving if r.get('vertex_in_volume') is False)

    fig, ax = plt.subplots(figsize=(10, 6))
    categories = ['In-volume\n(vertex inside)', 'Out-of-volume\n(vertex outside)']
    counts = [n_in, n_out]
    bars = ax.bar(categories, counts, width=0.4, color=['green', 'darkorange'], alpha=0.7,
                  edgecolor='black', linewidth=2)
    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height(), f'{int(count)}',
                ha='center', va='bottom', fontsize=16, fontweight='bold')

    ax.set_ylabel('Number of True Neutrino Interactions', fontsize=13, fontweight='bold')
    ax.set_xlabel(f'Interaction Vertex vs {volume_label}', fontsize=13, fontweight='bold')
    title = f'True Neutrino Interactions by Vertex Volume: {level_name}, {apa}'
    if file_name:
        title += f' ({file_name})'
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.tick_params(labelsize=12)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_dir / f'true_neutrino_vertex_volume_{filename_prefix}_{apa}.png',
                dpi=100, bbox_inches='tight')
    plt.close()


def DrawNeutrinoFlavor(vertex_records, output_dir, level_name, filename_prefix, apa, file_name=None,
                       volume_label="wire-readout sensitive box"):
    """
    Bar chart of neutrino FLAVOR (numu, nue, ... as named by mc.json's
    interaction-vertex node) counting IN-VOLUME, CUT-SURVIVING interactions only
    -- vertices outside the volume and interactions whose cluster the cuts
    removed are both excluded, so this describes the flavour composition of the
    in-detector sample that the rest of the pipeline actually evaluates.
    Event/File/Job level alike.

    Bars adapt to whatever flavours are present rather than assuming a fixed set,
    so a flavour absent from a given event/file simply has no bar (this dataset
    is overwhelmingly numu with a handful of nue).

    Parameters:
    - vertex_records: List of dicts from metadata.build_neutrino_vertex_records(),
        each with 'flavor' and 'vertex_in_volume'
    - output_dir: Output directory
    - level_name: Label for the title (e.g. 'Event 9', 'File Level', 'Job Level')
    - filename_prefix: Suffix used in the output filename (e.g. 'event_9', 'file', 'job')
    - apa: APA identifier (label only, e.g. "Combined")
    - file_name: Optional input file name for title
    - volume_label: how the volume is described in the title
    """
    # SURVIVORS ONLY, then in-volume -- see DrawNeutrinoVertices.
    in_volume = [r for r in vertex_records
                 if r.get('has_true_cluster') and r.get('vertex_in_volume') is True]
    if not in_volume:
        return

    flavor_counts = {}
    for r in in_volume:
        flavor = r.get('flavor') or 'unknown'
        flavor_counts[flavor] = flavor_counts.get(flavor, 0) + 1

    flavors = sorted(flavor_counts, key=lambda f: -flavor_counts[f])
    counts = [flavor_counts[f] for f in flavors]

    color_cycle = plt.rcParams['axes.prop_cycle'].by_key()['color']
    colors = [color_cycle[i % len(color_cycle)] for i in range(len(flavors))]

    fig, ax = plt.subplots(figsize=(max(8, 2.2 * len(flavors)), 6))
    # Default matplotlib bar width here (unlike the other neutrino bar charts):
    # with only a couple of flavours present, narrower bars made the 1-count nue
    # bar unreadable as a bar at all.
    bars = ax.bar(flavors, counts, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    # Percentage is of the IN-VOLUME sample plotted here (len(in_volume)), which is
    # what the bars are drawn from -- not of all interactions, and not of the
    # surviving total. The title states that sample size so the denominator is
    # never ambiguous.
    for bar, count in zip(bars, counts):
        pct = 100.0 * count / len(in_volume)
        ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height(),
                f'{int(count)} ({pct:.1f}%)',
                ha='center', va='bottom', fontsize=16, fontweight='bold')

    ax.set_ylabel('Number of True Neutrino Interactions', fontsize=13, fontweight='bold')
    ax.set_xlabel('Neutrino Flavor (mc.json)', fontsize=13, fontweight='bold')
    title = f'In-Volume True Neutrino Flavor: {level_name}, {apa}'
    if file_name:
        title += f' ({file_name})'
    ax.set_title(f'{title}\n(vertex inside the {volume_label}; {len(in_volume)} interactions)',
                 fontsize=14, fontweight='bold')
    ax.tick_params(labelsize=12)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_dir / f'true_neutrino_flavor_in_volume_{filename_prefix}_{apa}.png',
                dpi=100, bbox_inches='tight')
    plt.close()


def DrawNeutrinoBreakdown(vertex_records, output_dir, level_name, filename_prefix, apa,
                          file_name=None, energy_threshold=None):
    """
    Three stacked bars over EVERY mc.json interaction, each split by where the
    interaction vertex sits (in-volume vs out-of-volume). Event/File/Job level
    alike.

      1. Total true neutrinos          -- every interaction-vertex node in
                                          mc.json, deposits or not
      2. ... with any deposited energy -- produced true points in the active
                                          volume, i.e. a true cluster existed
                                          BEFORE any cut. Equals the neutrino
                                          cluster count SelectionAnalysis reports
                                          at "No cuts"
      3. Surviving the energy cut      -- its true cluster survived the true
                                          selections; the neutrino count in
                                          true_cluster_info.txt

    Stacked rather than side by side so each bar's height is the quantity of
    interest while the segments show what it is made of. Every segment carries
    its own count and each bar its total, so nothing has to be read off the axis.

    Bar 1 - bar 2 is the "no true deposits" category of
    removed_true_neutrino_info.txt; bar 2 - bar 3 is what the cuts removed
    (dominated by the energy cut). Bar 3's label names the energy threshold
    because that is what does essentially all of the work between 2 and 3 -- the
    geometric cuts are also applied but have been observed to remove nothing.

    'any deposited energy' needs precut_n_points on the records (pass
    clusters_true_precut to build_neutrino_vertex_records); without it bar 2
    collapses onto bar 3.

    Parameters:
    - vertex_records: List of dicts from metadata.build_neutrino_vertex_records(),
        each with 'vertex_in_volume' and 'has_true_cluster'
    - output_dir: Output directory
    - level_name: Label for the title (e.g. 'Event 9', 'File Level', 'Job Level')
    - filename_prefix: Suffix used in the output filename (e.g. 'event_9', 'file', 'job')
    - apa: APA identifier (label only, e.g. "Combined")
    - file_name: Optional input file name for title
    - energy_threshold: min_cluster_energy, named in bar 3's label; a generic
        label is used when None
    """
    if not vertex_records:
        return

    def _split(records):
        n_in = sum(1 for r in records if r.get('vertex_in_volume') is True)
        return n_in, len(records) - n_in

    def _deposited(record):
        return bool(record.get('has_true_cluster') or record.get('precut_n_points', 0) > 0)

    total_in, total_out         = _split(vertex_records)
    deposited_in, deposited_out = _split([r for r in vertex_records if _deposited(r)])
    surviving_in, surviving_out = _split([r for r in vertex_records if r.get('has_true_cluster')])

    energy_label = (f'Surviving neutrinos with true\nneutrino energy > {energy_threshold:g} MeV'
                    if energy_threshold is not None else
                    'Surviving neutrinos after\nthe true energy cut')

    IN_COLOR, OUT_COLOR = 'green', 'darkorange'
    categories = ['Total true neutrinos',
                  'Total true neutrinos with any\ndeposited energy in the detector',
                  energy_label]
    in_counts  = [total_in, deposited_in, surviving_in]
    out_counts = [total_out, deposited_out, surviving_out]

    # Narrow bars (half the matplotlib default): the bars carry three numbers
    # each, so the labels want the room more than the bars do.
    BAR_WIDTH = 0.4
    fig, ax = plt.subplots(figsize=(13, 7))
    bars_in  = ax.bar(categories, in_counts, width=BAR_WIDTH, color=IN_COLOR, alpha=0.8,
                      edgecolor='black', linewidth=2, label='vertex in volume')
    bars_out = ax.bar(categories, out_counts, width=BAR_WIDTH, bottom=in_counts, color=OUT_COLOR, alpha=0.8,
                      edgecolor='black', linewidth=2, label='vertex out of volume')

    # Segment values inside their own segment, each with its share OF THAT BAR --
    # the composition is the point of stacking, and it shifts sharply between the
    # bars (out-of-volume goes from two thirds of all interactions to a quarter of
    # the survivors). Bar totals sit above the bar as plain counts: the only
    # percentages shown are the in-volume/out-of-volume shares.
    bar_totals = [i + o for i, o in zip(in_counts, out_counts)]

    def _pct(count, denominator):
        return f'{100.0 * count / denominator:.1f}%' if denominator else 'n/a'

    for bar, count, bar_total in zip(bars_in, in_counts, bar_totals):
        if count > 0:
            ax.text(bar.get_x() + bar.get_width() / 2., count / 2.,
                    f'{count} ({_pct(count, bar_total)})',
                    ha='center', va='center', fontsize=16, fontweight='bold', color='white')
    for bar, count, base, bar_total in zip(bars_out, out_counts, in_counts, bar_totals):
        if count > 0:
            ax.text(bar.get_x() + bar.get_width() / 2., base + count / 2.,
                    f'{count} ({_pct(count, bar_total)})',
                    ha='center', va='center', fontsize=16, fontweight='bold', color='white')
    for bar, bar_total in zip(bars_in, bar_totals):
        ax.text(bar.get_x() + bar.get_width() / 2., bar_total, f'{bar_total}',
                ha='center', va='bottom', fontsize=18, fontweight='bold')

    ax.set_ylabel('Number of True Neutrino Interactions', fontsize=15, fontweight='bold')
    title = f'True Neutrino Breakdown: {level_name}, {apa}'
    if file_name:
        title += f' ({file_name})'
    ax.set_title(title, fontsize=16, fontweight='bold')
    ax.tick_params(labelsize=13)
    ax.grid(True, alpha=0.3, axis='y')
    # Headroom for the legend. The bars are non-increasing left to right by
    # construction (surviving subset of deposited subset of total), so the legend's
    # upper-right corner sits over the SHORTEST bar -- 1.35 keeps the tallest bar and
    # its total label below the legend box even in the worst case, where all three
    # bars are equal. 1.15 was enough for the bar tops but let the legend land on the
    # third bar's total label.
    ax.set_ylim(0, max(total_in + total_out, 1) * 1.35)
    ax.legend(fontsize=15, loc='upper right', framealpha=0.95)

    plt.tight_layout()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_dir / f'true_neutrino_breakdown_{filename_prefix}_{apa}.png',
                dpi=100, bbox_inches='tight')
    plt.close()


# ============================================================================
# EXTRA (UNMATCHED) RECO CLUSTER INVESTIGATION (additive)
# ============================================================================
# Categories match metadata.categorize_extra_reco_clusters() -- see its
# docstring for what each one means.
_EXTRA_RECO_CATEGORY_ORDER = ['matched_winner', 'fragment_of_neutrino', 'matched_cosmic_only', 'no_true_overlap']
_EXTRA_RECO_CATEGORY_COLORS = {
    'matched_winner':       'green',
    'fragment_of_neutrino': 'orange',
    'matched_cosmic_only':  'blue',
    'no_true_overlap':      'red',
}
_EXTRA_RECO_CATEGORY_LABELS = {
    'matched_winner':       'Matched (winner)',
    'fragment_of_neutrino': 'Fragment of neutrino',
    'matched_cosmic_only':  'Matched cosmic only',
    'no_true_overlap':      'No true overlap',
}


def DrawExtraRecoClusters(clusters_reco, categorized_rows, event, apa, output_dir, file_name=None):
    """
    Draw ONLY the "extra" (non-"matched_winner") reco clusters for one event,
    in XZ/YZ/XY projections side by side, colored by
    metadata.categorize_extra_reco_clusters() category -- the spatial
    counterpart to extra_reco_info.txt (writeinformation.write_extra_reco_info).
    True clusters and matched_winner reco clusters are deliberately NOT drawn,
    so the extra clusters stand alone rather than being lost against the rest
    of the event. Same view/axis conventions as draw_clustering_global_clusters
    above (Z on the x-axis for XZ/YZ).

    Parameters:
    - clusters_reco: dict {reco_cluster_id: points} for this event
    - categorized_rows: this event's rows from categorize_extra_reco_clusters()
    - event, apa, output_dir, file_name: same convention as the other event-level drawers

    Saved as extra_reco_clusters_event{event}_{apa}.png (one file, 3 panels).
    No-op (returns without writing) if the event has no extra reco cluster.
    """
    extra_reco_category = {r['reco_cluster_id']: r['category'] for r in categorized_rows
                            if r['category'] != 'matched_winner'}
    if not extra_reco_category:
        return

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # (view_label, x_col, y_col, xlim, ylim, xlabel, ylabel)
    views = [
        ("XZ", 2, 0, (0, 500), (-250, 250), "z [cm]", "x [cm]"),
        ("YZ", 2, 1, (0, 500), (-250, 250), "z [cm]", "y [cm]"),
        ("XY", 0, 1, (-250, 250), (-250, 250), "x [cm]", "y [cm]"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(20, 6.5))

    for col_idx, (view_label, x_col, y_col, xlim, ylim, xlabel, ylabel) in enumerate(views):
        ax = axes[col_idx]
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        title = f"Extra reco clusters: Event {event}, {apa}, {view_label}"
        if file_name:
            title += f" ({file_name})"
        ax.set_title(title, fontsize=11)

        for reco_cid, category in sorted(extra_reco_category.items()):
            points = np.array(clusters_reco[reco_cid])
            color = _EXTRA_RECO_CATEGORY_COLORS[category]
            ax.scatter(points[:, x_col], points[:, y_col], s=1, alpha=0.6, color=color)
            # Invisible zero-length line to carry the legend entry -- same
            # trick used by DrawTrueRecoClustersXZ/YZ/XY and
            # draw_clustering_global_clusters above -- so each cluster's ID is
            # readable directly off the plot, not just its category color.
            ax.plot([], [], color=color, label=f"Cluster {reco_cid:.0f} ({_EXTRA_RECO_CATEGORY_LABELS[category]})")
        ax.legend(fontsize=8, loc='upper right')

    plt.tight_layout()
    plt.savefig(output_dir / f"extra_reco_clusters_event{event}_{apa}.png", dpi=100, bbox_inches='tight')
    plt.close()


def DrawExtraRecoCategoryBreakdown(categorized_rows, n_true_neutrinos, output_dir, apa, level_name, filename_prefix,
                                    file_name=None):
    """
    Three bar charts stacked top to bottom -- event level, file level, or job
    level (same categorized_rows list works at any level, one event's rows or
    many events' concatenated together, same convention as the writers in
    writeinformation.py).

    TOP    : total true neutrino clusters vs. total reco clusters selected (beam
             window, post cuts) vs. how many of those actually form a 1-to-1
             true-reco pair (the "matched_winner" count, same quantity and same
             color as the middle panel's first bar) -- the "72 true neutrinos vs
             88 reco clusters" comparison that motivated this investigation,
             plus the pair count so equal true/reco totals don't read as "every
             true matched every reco".
    MIDDLE : those selected reco clusters split into just Matched (the 1-to-1
             winners) vs. Extra (everything else) -- the plain headline number
             the bottom panel then explains.
    BOTTOM : the Extra bucket broken down by metadata.categorize_extra_reco_clusters()
             reason (fragment_of_neutrino / matched_cosmic_only / no_true_overlap)
             -- WHY those reco clusters are "extra".

    Parameters:
    - categorized_rows: list of dicts from categorize_extra_reco_clusters() --
        one event's for the event-level copy, many events' concatenated for the
        file/job-level copy
    - n_true_neutrinos: count of true neutrino clusters over that same scope
        (the driver script counts clusters_true entries with
        cluster_id >= metadata.NEUTRINO_CLUSTER_ID_BASE)
    - output_dir, apa, level_name, filename_prefix, file_name: same convention
        as _draw_neutrino_cosmic_bar
    """
    if not categorized_rows and not n_true_neutrinos:
        return

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    num_events = len(set(r['event'] for r in categorized_rows)) if categorized_rows else 1
    n_matched_pairs = sum(1 for r in categorized_rows if r['category'] == 'matched_winner')
    n_extra = len(categorized_rows) - n_matched_pairs

    fig, (ax_top, ax_middle, ax_bottom) = plt.subplots(3, 1, figsize=(10, 17))

    # TOP: true neutrinos vs. total selected reco clusters vs. actual 1-to-1 pairs.
    # Violet and magenta are picked to sit clear of the bottom panel's
    # green/orange/blue/red category colors; the third bar deliberately REUSES
    # the middle/bottom panels' matched_winner green, since "Matched Pairs"
    # here and "Matched" there are the same quantity -- color follows the
    # entity, so the panels visually link on that one shared number.
    top_labels = ['True Neutrinos', 'Reco Clusters\n(selected)', 'Matched Pairs\n(1-to-1)']
    top_counts = [n_true_neutrinos, len(categorized_rows), n_matched_pairs]
    top_colors = ['#4a3aa7', '#e87ba4', _EXTRA_RECO_CATEGORY_COLORS['matched_winner']]
    bars_top = ax_top.bar(top_labels, top_counts, color=top_colors, alpha=0.85, edgecolor='black', linewidth=2)
    for bar, count in zip(bars_top, top_counts):
        height = bar.get_height()
        ax_top.text(bar.get_x() + bar.get_width() / 2., height, f'{int(count)}',
                    ha='center', va='bottom', fontsize=14, fontweight='bold')
    ax_top.set_ylabel('Count', fontsize=12, fontweight='bold')
    title_top = f'True Neutrinos vs Selected Reco - {level_name}, {num_events} events, {apa}'
    if file_name:
        title_top += f' ({file_name})'
    ax_top.set_title(title_top, fontsize=13, fontweight='bold')
    ax_top.grid(True, alpha=0.3, axis='y')

    # MIDDLE: matched vs. extra. Neutral gray for "Extra" -- reads as "explained
    # below" rather than any one of the bottom panel's specific reasons, and
    # stays clearly distinct from that panel's orange/blue/red (a gold/amber
    # here sat too close to the bottom panel's orange "Fragment of neutrino").
    middle_labels = ['Matched\n(winner)', 'Extra']
    middle_counts = [n_matched_pairs, n_extra]
    middle_colors = [_EXTRA_RECO_CATEGORY_COLORS['matched_winner'], '#898781']
    bars_middle = ax_middle.bar(middle_labels, middle_counts, color=middle_colors, alpha=0.85, edgecolor='black', linewidth=2)
    for bar, count in zip(bars_middle, middle_counts):
        height = bar.get_height()
        ax_middle.text(bar.get_x() + bar.get_width() / 2., height, f'{int(count)}',
                       ha='center', va='bottom', fontsize=14, fontweight='bold')
    ax_middle.set_ylabel('Number of Reco Clusters', fontsize=12, fontweight='bold')
    title_middle = f'Selected Reco: Matched vs Extra - {level_name}, {num_events} events, {apa}'
    if file_name:
        title_middle += f' ({file_name})'
    ax_middle.set_title(title_middle, fontsize=13, fontweight='bold')
    ax_middle.grid(True, alpha=0.3, axis='y')

    # BOTTOM: the Extra bucket broken down by reason (matched_winner excluded --
    # it's not "extra", and is already shown on its own in the middle panel).
    extra_categories = [cat for cat in _EXTRA_RECO_CATEGORY_ORDER if cat != 'matched_winner']
    bottom_counts = [sum(1 for r in categorized_rows if r['category'] == cat) for cat in extra_categories]
    bottom_labels = [_EXTRA_RECO_CATEGORY_LABELS[cat] for cat in extra_categories]
    bottom_colors = [_EXTRA_RECO_CATEGORY_COLORS[cat] for cat in extra_categories]
    bars_bottom = ax_bottom.bar(bottom_labels, bottom_counts, color=bottom_colors, alpha=0.7, edgecolor='black', linewidth=2)
    for bar, count in zip(bars_bottom, bottom_counts):
        height = bar.get_height()
        ax_bottom.text(bar.get_x() + bar.get_width() / 2., height, f'{int(count)}',
                       ha='center', va='bottom', fontsize=14, fontweight='bold')
    ax_bottom.set_ylabel('Number of Reco Clusters', fontsize=12, fontweight='bold')
    ax_bottom.set_xlabel('Reason', fontsize=12, fontweight='bold')
    title_bottom = f'Extra Reco Clusters by Reason - {level_name}, {num_events} events, {apa}'
    if file_name:
        title_bottom += f' ({file_name})'
    ax_bottom.set_title(title_bottom, fontsize=13, fontweight='bold')
    ax_bottom.grid(True, alpha=0.3, axis='y')
    plt.setp(ax_bottom.get_xticklabels(), rotation=15, ha='right')

    plt.tight_layout()
    plt.savefig(output_dir / f"extra_reco_category_breakdown_{filename_prefix}_{num_events}events_{apa}.png",
                dpi=100, bbox_inches='tight')
    plt.close()
