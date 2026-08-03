"""
Standalone diagnostic script (not part of the main notebook pipeline): for each
true cluster in a chosen file/event range, finds its nearest reco cluster via
KDTree nearest-neighbor search (independent of EvaluateEfficiency's official
match, which requires >min_recopoints_threshold points within radius_efficiency),
to distinguish "true near-misses just outside the matching radius" from "no
nearby reco cluster at all" among EvaluateEfficiency's unmatched clusters.

Run directly: python near_miss_investigation.py
Output: multi_file_plots_charge_light_matching/near_miss_investigation_{TARGET_FILE}_events{EVENT_LOW}-{EVENT_HIGH-1}.txt
        (TARGET_FILE="all" / auto-detected events -> ..._allfiles_allevents.txt)
"""
import numpy as np
from datetime import datetime
from pathlib import Path
from scipy.spatial import KDTree

from readfiles import read_charge_light_files_for_event
from selections import (
    GroupClustersByID, build_true_points_charge_light,
    reassign_cluster_ID_true_charge_light, reassign_cluster_ID_reco,
    apply_energy_cutoff, apply_wire_readout_sensitive_yz_plane_cut_true,
    apply_wire_readout_sensitive_yz_plane_cut_reco,
    apply_deadarea_cut_true_charge_light,
)
from efficiency_purity_estimate import EvaluateEfficiency

# ============================================================================
# CONFIG -- same selection settings as Evaluation_ChargeLightMatching_BeforeBeamWindowCut.ipynb
# ============================================================================
PARENT_DIR    = Path("Haiwang_files_charge_light_matching_MCP2025C_Fall_production")
TARGET_FILE   = "all"   # "all" for every file subdirectory with a data/ folder, or "file0"/"file1"/...
EVENT_LOW     = None    # None = auto-detect from each file's data/ (all events present)
EVENT_HIGH    = None    # exclusive; None = auto-detect
OUTPUT_DIR    = Path("multi_file_plots_charge_light_matching")

radius_efficiency        = 2
min_recopoints_threshold = 5
min_cluster_energy       = 100
x_min, x_max = -250.0, 250.0
y_min, y_max = -200.0, 200.0
z_min, z_max = 0.15, 500.85


def find_input_files():
    """
    File subdirectories to run over: every subdirectory of PARENT_DIR that has
    a data/ folder when TARGET_FILE == "all", else just TARGET_FILE. Same
    discovery rule as the notebook's find_all_input_directories (kept local --
    this script is standalone by design and imports nothing from the notebook).
    """
    if TARGET_FILE != "all":
        return [TARGET_FILE]
    return [d.name for d in sorted(PARENT_DIR.iterdir())
            if d.is_dir() and (d / "data").is_dir()]


def find_events(file_name):
    """
    Event numbers to run for one file: EVENT_LOW..EVENT_HIGH-1 when both are
    set, else every numeric subdirectory of that file's data/ (event numbering
    is per-file, e.g. file6's events are 60-69, so a fixed range can't serve
    every file).
    """
    if EVENT_LOW is not None and EVENT_HIGH is not None:
        return list(range(EVENT_LOW, EVENT_HIGH))

    data_dir = PARENT_DIR / file_name / "data"
    if not data_dir.is_dir():
        return []
    events = []
    for item in data_dir.iterdir():
        if item.is_dir() and item.name.isdigit():
            events.append(int(item.name))
    return sorted(events)


def find_near_miss_rows(clusters_true, clusters_reco, matched_true_cids, evt, file_name):
    """
    For every true cluster, KDTree-search every reco cluster in the same event
    to find the reco cluster with the single smallest point-to-point distance
    to any of the true cluster's points (min_dist) -- NOT necessarily the
    cluster EvaluateEfficiency officially matched. mean_nn_dist is the mean
    nearest-neighbor distance across ALL of the true cluster's points to that
    same nearest reco cluster. offset_dx/dy/dz = mean(true_point -
    nearest_reco_point) over the true cluster's points.

    Returns a list of row dicts, one per true cluster.
    """
    reco_trees = {cid: KDTree(np.array(pts)[:, :3]) for cid, pts in clusters_reco.items()}

    rows = []
    for true_id, true_pts in clusters_true.items():
        true_pts = np.array(true_pts)
        true_xyz = true_pts[:, :3]
        is_neutrino = bool(true_pts[0, 4] > 0)

        best_reco_id, best_min_dist = None, np.inf
        for reco_id, tree in reco_trees.items():
            dists, _ = tree.query(true_xyz)
            d = dists.min()
            if d < best_min_dist:
                best_min_dist, best_reco_id = d, reco_id

        if best_reco_id is None:
            continue

        tree = reco_trees[best_reco_id]
        dists, idx = tree.query(true_xyz)
        nearest_reco_pts = np.array(clusters_reco[best_reco_id])[idx, :3]
        offset = (true_xyz - nearest_reco_pts).mean(axis=0)

        rows.append({
            'file': file_name,
            'evt': evt,
            'true_id': true_id,
            'is_neutrino': is_neutrino,
            'matched': true_id in matched_true_cids,
            'nearest_reco': best_reco_id,
            'min_dist': best_min_dist,
            'mean_nn_dist': dists.mean(),
            'dx': offset[0], 'dy': offset[1], 'dz': offset[2],
            'n_true_pts': len(true_pts),
            'energy_MeV': true_pts[:, 5].sum(),
        })
    return rows


def write_unmatched_table(f, title, rows):
    f.write(f"\n{'='*100}\n")
    f.write(f"{title}\n")
    f.write(f"{'='*100}\n")
    unmatched = sorted((r for r in rows if not r['matched']), key=lambda r: r['min_dist'])
    if not unmatched:
        f.write("(none)\n")
        return unmatched

    # 'file' column added for multi-file runs -- event numbering is per-file, so
    # evt alone no longer identifies a row once more than one file is included.
    f.write(f"{'file':<8} {'evt':>4} {'true_id':>10} {'nearest_reco':>12} {'min_dist_cm':>11} {'mean_nn_cm':>10} "
            f"{'dx_cm':>8} {'dy_cm':>8} {'dz_cm':>8} {'n_true_pts':>10} {'energy_MeV':>10}\n")
    for r in unmatched:
        f.write(f"{r['file']:<8} {r['evt']:>4} {r['true_id']:>10.2f} {r['nearest_reco']:>12.2f} {r['min_dist']:>11.2f} "
                f"{r['mean_nn_dist']:>10.2f} {r['dx']:>8.2f} {r['dy']:>8.2f} {r['dz']:>8.2f} "
                f"{r['n_true_pts']:>10} {r['energy_MeV']:>10.2f}\n")
    return unmatched


def main():
    input_files = find_input_files()
    if not input_files:
        print(f"No input files found in {PARENT_DIR}")
        return

    all_rows = []
    events_processed = 0
    for file_name in input_files:
        events = find_events(file_name)
        print(f"{file_name}: {len(events)} event(s) to process", flush=True)

        for evt in events:
            result = read_charge_light_files_for_event(PARENT_DIR / file_name, evt)
            if result is None:
                continue

            x_true, y_true, z_true, id_true, q_true, real_id_true, e_true, nu_idx_true = result['true_clustering']
            true_points = build_true_points_charge_light(x_true, y_true, z_true, id_true, q_true, energy=e_true, nu_idx=nu_idx_true)
            true_points = reassign_cluster_ID_true_charge_light(true_points)
            true_points = apply_energy_cutoff(true_points, min_cluster_energy)
            true_points = apply_wire_readout_sensitive_yz_plane_cut_true(true_points, x_min, x_max, y_min, y_max, z_min, z_max)
            true_points = apply_deadarea_cut_true_charge_light(true_points, output_dir=None, event=evt, file_name=file_name)
            if len(true_points) == 0:
                continue
            clusters_true = GroupClustersByID(true_points)

            x_clu, y_clu, z_clu, id_clu, q_clu, real_id_clu = result['clustering']
            predicted_points = np.column_stack((x_clu, y_clu, z_clu, real_id_clu, q_clu))
            predicted_points = apply_wire_readout_sensitive_yz_plane_cut_reco(predicted_points, x_min, x_max, y_min, y_max, z_min, z_max)
            predicted_points = reassign_cluster_ID_reco(predicted_points)
            clusters_reco = GroupClustersByID(predicted_points)

            event_key = f"{file_name}_{evt}"
            efficiency_results = EvaluateEfficiency(clusters_true, clusters_reco, event_key, radius_efficiency, min_recopoints_threshold)
            matched_true_cids = {e['true_cluster_id'] for e in efficiency_results if e['reco_cluster_id'] != 8888}

            event_rows = find_near_miss_rows(clusters_true, clusters_reco, matched_true_cids, evt, file_name)
            all_rows.extend(event_rows)
            events_processed += 1
            print(f"  {event_key}: {len(clusters_true)} true, {len(clusters_reco)} reco, "
                  f"{sum(1 for r in event_rows if not r['matched'])} unmatched", flush=True)

    cosmic_rows   = [r for r in all_rows if not r['is_neutrino']]
    neutrino_rows = [r for r in all_rows if r['is_neutrino']]

    # Filename/heading describe whatever was actually run: the single-file fixed
    # range keeps its original name, an all-files auto-detected run gets one
    # combined file (rows carry a 'file' column to stay distinguishable).
    if TARGET_FILE == "all" or EVENT_LOW is None or EVENT_HIGH is None:
        scope_tag  = f"{'allfiles' if TARGET_FILE == 'all' else TARGET_FILE}_allevents"
        scope_desc = (f"{len(input_files)} file(s) ({', '.join(input_files)}), "
                      f"all {events_processed} event(s) found")
    else:
        scope_tag  = f"{TARGET_FILE}_events{EVENT_LOW}-{EVENT_HIGH-1}"
        scope_desc = f"{TARGET_FILE} events {EVENT_LOW}-{EVENT_HIGH-1}"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"near_miss_investigation_{scope_tag}.txt"
    with open(out_path, "w") as f:
        f.write(f"{'='*100}\n")
        f.write(f"Generated by: near_miss_investigation.py ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n")
        f.write(f"NEAR-MISS INVESTIGATION: true clusters vs their nearest reco cluster, "
                f"{scope_desc} ({PARENT_DIR})\n")
        f.write(f"{'='*100}\n\n")
        f.write("Context: for each true cluster, 'nearest_reco' is the reco cluster with the smallest\n"
                "single point-to-point distance to any of the true cluster's points (min_dist), found via\n"
                "KDTree nearest-neighbor search against every reco cluster in the same event -- NOT\n"
                "necessarily the cluster EvaluateEfficiency officially matched. Only UNMATCHED true\n"
                "clusters are listed below (matched clusters align to ~0.01-0.1cm and aren't informative\n"
                "here); mean_nn_dist is the mean nearest-neighbor distance across ALL of the true cluster's\n"
                "points to that same nearest reco cluster (large mean_nn_dist despite tiny min_dist = the\n"
                "true cluster only partially/tangentially overlaps that reco cluster). offset_dx/dy/dz =\n"
                "mean(true_point - nearest_reco_point) over the true cluster's points, i.e. signed direction\n"
                "of the residual gap.\n\n")
        f.write(f"Pipeline settings: radius_efficiency={radius_efficiency}cm, "
                f"min_recopoints_threshold={min_recopoints_threshold}, energy cutoff={min_cluster_energy} MeV,\n"
                f"wire-readout + dead-area cuts applied, reco clusters grouped by real_cluster_id then\n"
                f"reassign_cluster_ID_reco (avg-X relabeling); true clusters via\n"
                f"reassign_cluster_ID_true_charge_light (99990+nu_idx for neutrino, avg-X for cosmic).\n")

        unmatched_cosmic   = write_unmatched_table(f, "UNMATCHED COSMIC CLUSTERS (sorted by min_dist to nearest reco cluster, ascending)", cosmic_rows)
        unmatched_neutrino = write_unmatched_table(f, "UNMATCHED NEUTRINO CLUSTERS (sorted by min_dist to nearest reco cluster, ascending)", neutrino_rows)

        f.write(f"\n{'='*100}\n")
        f.write(f"Events processed: {events_processed} across {len(input_files)} file(s)\n")
        f.write(f"Total true clusters checked: {len(all_rows)} ({len(cosmic_rows)} cosmic, {len(neutrino_rows)} neutrino)\n")
        f.write(f"Cosmic:   unmatched {len(unmatched_cosmic)} / {len(cosmic_rows)}\n")
        f.write(f"Neutrino: unmatched {len(unmatched_neutrino)} / {len(neutrino_rows)}\n")

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
