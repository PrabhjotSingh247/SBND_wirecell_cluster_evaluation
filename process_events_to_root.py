"""
Phase A of the processing/analysis split (see project plan / CLAUDE.md).

HighStatsEvaluation_MultiFile.ipynb currently redoes selections, KDTree efficiency/purity
matching, category classification, and metadata computation from scratch every time it's
run, plus draws ~10 plots per event - this is the reason a 10-file run takes >30 minutes,
which won't scale to hundreds of files. This script runs that same expensive, point-cloud-
dependent work exactly once per file/event/APA (same cut configuration and selection order
as the notebook), with NO plotting, and writes both the raw cluster point data and all
computed metadata into a single ROOT file via uproot. A later pass will rewire
analysis/plotting to read from this file instead of recomputing everything.

Usage:
    python process_events_to_root.py [--view 2view] [--file file1] [--apa APA0] [--out FILE.root]

Output: one .root file with six flat TTrees (column names, not nested branches - ROOT
branch names can't be dynamically named after runtime values like a file name or event
number, and a flat layout is what actually scales to hundreds of files):

  event_info group:
    true_points               one row per true-cluster point (post-selection)
    reco_points                one row per reco-cluster point
    true_points_before_deadarea  one row per point, pre-deadarea-cut, for clusters the
                                  dead-area cut actually affected (not the full dataset)

  metadata_info group:
    true_cluster_metadata     one row per true cluster (matched or not), incl. linearity,
                               category geometry (theta_xz/z_min/z_max/x_at_z_min/x_at_z_max),
                               dead-area before/after point counts, and matched_reco_ids
                               (jagged list of every reco cluster id this true cluster
                               matched, for cross-referencing into reco_cluster_metadata)
    reco_cluster_metadata     one row per reco cluster, incl. linearity
    true_reco_pair_metadata   one row per 1-to-1 matched true/reco pair
"""
import argparse
import contextlib
import io
import time
from datetime import datetime
from pathlib import Path

import awkward as ak
import numpy as np
import pandas as pd
import uproot

from readfiles import read_files_for_event
from selections import (
    apply_energy_cutoff, apply_min_true_points_cutoff, apply_min_reco_points_cutoff,
    apply_wire_readout_sensitive_yz_plane_cut_true, apply_wire_readout_sensitive_yz_plane_cut_reco,
    reassign_cluster_ID_true, reassign_cluster_ID_reco, GroupClustersByID,
    apply_deadarea_cut_true, apply_time_window_cut,
)
from cluster_category import cluster_category
from efficiency_purity_estimate import EvaluateEfficiency, EvaluatePurity
from clusterpairmatching import MatchTrueToReco1to1, MatchTruetoReco_OneToMany
from metadata import (
    add_metadata_true_clusters, add_metadata_reco_clusters,
    add_metadata_true_reco_pair_cluster, add_single_metadata,
)
from variable_pca_linearity import calculate_pca_linearity

# Same cut configuration and selection flags as HighStatsEvaluation_MultiFile.ipynb (cell 3),
# so this script reproduces identical selections/metrics, just without drawing.
RADIUS_EFFICIENCY        = 2
RADIUS_PURITY_XZ         = 2
RADIUS_PURITY_YZ         = 5
RADIUS_PURITY_XY         = 5
MIN_RECOPOINTS_THRESHOLD = 5
MIN_CLUSTER_ENERGY       = 100
MIN_TRUE_POINTS_CUTOFF   = 200
MIN_RECO_POINTS_CUTOFF   = 200

X_MIN, X_MAX = -250.0, 250.0
Y_MIN, Y_MAX = -200.0, 200.0
Z_MIN, Z_MAX = 0.15, 500.85

TIME_WINDOW_MIN = -205
TIME_WINDOW_MAX = 1508.5

APPLY_ENERGY_CUTOFF                        = True
APPLY_MIN_TRUE_POINTS_CUTOFF                = True
APPLY_MIN_RECO_POINTS_CUTOFF                = True
APPLY_WIRE_READOUT_SENSITIVE_XZ_PLANE_CUT   = True
APPLY_TIME_WINDOW_CUT                       = False
APPLY_DEADAREA_CUT                          = True


def find_all_input_directories(parent_dir):
    parent_dir = Path(parent_dir)
    return sorted(d for d in parent_dir.iterdir() if d.is_dir() and (d / "data").exists())


def detect_events_in_directory(input_dir):
    data_dir = Path(input_dir) / "data"
    events = []
    for item in data_dir.iterdir():
        if item.is_dir():
            try:
                events.append(int(item.name))
            except ValueError:
                pass
    return sorted(events)


def _none_to_nan(v):
    return v if v is not None else np.nan


def process_true_clusters(x, y, z, cid, q, e, t, apa, view):
    """Returns (clusters_true, deadarea_info). deadarea_info is {} unless the dead-area cut
    ran, in which case it's {"before": {cid: count}, "after": {cid: count},
    "pre_cut_points": {cid: full points array}} - the full pre-cut point clouds are only
    needed downstream for clusters the cut actually affected (before != after)."""
    points = np.column_stack([x, y, z, cid, q, e, t])
    points = reassign_cluster_ID_true(points)
    if APPLY_ENERGY_CUTOFF:
        points = apply_energy_cutoff(points, MIN_CLUSTER_ENERGY)
    if len(points) == 0:
        return {}, {}
    if APPLY_MIN_TRUE_POINTS_CUTOFF:
        points = apply_min_true_points_cutoff(points, MIN_TRUE_POINTS_CUTOFF)
    if len(points) == 0:
        return {}, {}
    if APPLY_WIRE_READOUT_SENSITIVE_XZ_PLANE_CUT:
        points = apply_wire_readout_sensitive_yz_plane_cut_true(
            points, X_MIN, X_MAX, Y_MIN, Y_MAX, Z_MIN, Z_MAX)
    if len(points) == 0:
        return {}, {}
    deadarea_info = {}
    if APPLY_DEADAREA_CUT:
        pre_cids, pre_counts = np.unique(points[:, 3], return_counts=True)
        before_counts = dict(zip(pre_cids, pre_counts))
        pre_cut_points = {c: points[points[:, 3] == c] for c in pre_cids}
        with contextlib.redirect_stdout(io.StringIO()):
            points = apply_deadarea_cut_true(points, apa, view_type=view, output_dir=None)
        if len(points) > 0:
            post_cids, post_counts = np.unique(points[:, 3], return_counts=True)
            after_counts = dict(zip(post_cids, post_counts))
        else:
            after_counts = {}
        deadarea_info = {"before": before_counts, "after": after_counts, "pre_cut_points": pre_cut_points}
    if len(points) == 0:
        return {}, deadarea_info
    if APPLY_TIME_WINDOW_CUT:
        points = apply_time_window_cut(points, TIME_WINDOW_MIN, TIME_WINDOW_MAX, apa)
    if len(points) == 0:
        return {}, deadarea_info
    return GroupClustersByID(points), deadarea_info


def process_reco_clusters(x, y, z, cid, q):
    points = np.column_stack([x, y, z, cid, q])
    if APPLY_MIN_RECO_POINTS_CUTOFF:
        points = apply_min_reco_points_cutoff(points, MIN_RECO_POINTS_CUTOFF)
    if len(points) == 0:
        return {}
    if APPLY_WIRE_READOUT_SENSITIVE_XZ_PLANE_CUT:
        points = apply_wire_readout_sensitive_yz_plane_cut_reco(
            points, X_MIN, X_MAX, Y_MIN, Y_MAX, Z_MIN, Z_MAX)
    if len(points) == 0:
        return {}
    points = reassign_cluster_ID_reco(points)
    return GroupClustersByID(points)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--view", default="2view", choices=["2view", "3view"])
    parser.add_argument("--file", default=None, help="Restrict to one file dir (e.g. file1), for quick testing")
    parser.add_argument("--apa", default=None, choices=["APA0", "APA1"], help="Restrict to one APA (default: both)")
    parser.add_argument("--out", default=None, help="Output .root path (default: processed_events/<timestamp>.root)")
    args = parser.parse_args()

    start_time = datetime.now()
    start_clock = time.monotonic()
    print(f"Job started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    parent_dir = Path(args.view)
    apa_list = [args.apa] if args.apa is not None else ["APA0", "APA1"]

    if args.out is not None:
        out_path = Path(args.out)
    else:
        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        out_dir = Path("processed_events")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{timestamp}.root"

    input_directories = find_all_input_directories(parent_dir)
    if args.file is not None:
        input_directories = [d for d in input_directories if d.name == args.file]
    print(f"Found {len(input_directories)} file directories under {parent_dir}")
    print(f"APA(s) to process: {apa_list}")
    print(f"Output file: {out_path}")

    # Point-level accumulators (event_info group) - list of per-column numpy arrays,
    # concatenated once at the end for speed.
    true_points_cols = {k: [] for k in
                         ["file", "event", "apa", "true_cluster_id", "x", "y", "z", "q_true", "energy", "time"]}
    reco_points_cols = {k: [] for k in
                        ["file", "event", "apa", "reco_cluster_id", "x", "y", "z", "charge"]}
    # Pre-deadarea-cut points, written only for clusters the cut actually affected.
    true_points_before_deadarea_cols = {k: [] for k in
                         ["file", "event", "apa", "true_cluster_id", "x", "y", "z", "q_true", "energy", "time"]}

    # Metadata accumulators (metadata_info group) - one row (dict) per cluster/pair.
    true_cluster_metadata_list = []
    reco_cluster_metadata_list = []
    true_reco_pair_metadata_list = []

    total_events_processed = 0

    for apa in apa_list:
        for input_dir in input_directories:
            file_name = input_dir.name
            events = detect_events_in_directory(input_dir)
            print(f"\nFILE {file_name} ({apa}): {len(events)} events")

            for evt in events:
                result = read_files_for_event(input_dir, evt, apa)
                if result is None:
                    continue
                (x_true, y_true, z_true, id_true, q_true, e_true, t_true,
                 x_pred, y_pred, z_pred, id_pred, q_pred) = result

                clusters_true = {}
                deadarea_info = {}
                if len(x_true) > 0:
                    clusters_true, deadarea_info = process_true_clusters(
                        x_true, y_true, z_true, id_true, q_true, e_true, t_true, apa, args.view)

                clusters_reco = {}
                if len(x_pred) > 0:
                    clusters_reco = process_reco_clusters(x_pred, y_pred, z_pred, id_pred, q_pred)

                if not clusters_true:
                    continue

                event_key = f"{file_name}_{evt}"

                # ---- raw point clouds (event_info) ----
                for true_cid, points in clusters_true.items():
                    points = np.array(points)
                    n = len(points)
                    true_points_cols["file"].extend([file_name] * n)
                    true_points_cols["event"].extend([evt] * n)
                    true_points_cols["apa"].extend([apa] * n)
                    true_points_cols["true_cluster_id"].append(np.full(n, true_cid))
                    true_points_cols["x"].append(points[:, 0])
                    true_points_cols["y"].append(points[:, 1])
                    true_points_cols["z"].append(points[:, 2])
                    true_points_cols["q_true"].append(points[:, 4])
                    true_points_cols["energy"].append(points[:, 5])
                    true_points_cols["time"].append(points[:, 6])

                for reco_cid, points in clusters_reco.items():
                    points = np.array(points)
                    n = len(points)
                    reco_points_cols["file"].extend([file_name] * n)
                    reco_points_cols["event"].extend([evt] * n)
                    reco_points_cols["apa"].extend([apa] * n)
                    reco_points_cols["reco_cluster_id"].append(np.full(n, reco_cid))
                    reco_points_cols["x"].append(points[:, 0])
                    reco_points_cols["y"].append(points[:, 1])
                    reco_points_cols["z"].append(points[:, 2])
                    reco_points_cols["charge"].append(points[:, 4])

                # ---- pre-deadarea-cut points, for clusters the cut affected ----
                before_counts = deadarea_info.get("before", {})
                after_counts = deadarea_info.get("after", {})
                pre_cut_points = deadarea_info.get("pre_cut_points", {})
                for cid_, pre_points in pre_cut_points.items():
                    if before_counts.get(cid_) == after_counts.get(cid_):
                        continue  # not affected by the dead-area cut
                    n = len(pre_points)
                    true_points_before_deadarea_cols["file"].extend([file_name] * n)
                    true_points_before_deadarea_cols["event"].extend([evt] * n)
                    true_points_before_deadarea_cols["apa"].extend([apa] * n)
                    true_points_before_deadarea_cols["true_cluster_id"].append(np.full(n, cid_))
                    true_points_before_deadarea_cols["x"].append(pre_points[:, 0])
                    true_points_before_deadarea_cols["y"].append(pre_points[:, 1])
                    true_points_before_deadarea_cols["z"].append(pre_points[:, 2])
                    true_points_before_deadarea_cols["q_true"].append(pre_points[:, 4])
                    true_points_before_deadarea_cols["energy"].append(pre_points[:, 5])
                    true_points_before_deadarea_cols["time"].append(pre_points[:, 6])

                # ---- category classification (needs point clouds -> must run here) ----
                cluster_category_results = cluster_category(clusters_true, output_dir=None, event=evt, apa=apa, file_name=file_name)

                # ---- KDTree efficiency/purity matching (the expensive part) ----
                efficiency_results = EvaluateEfficiency(
                    clusters_true, clusters_reco, event_key,
                    radius_efficiency=RADIUS_EFFICIENCY, min_recopoints_threshold=MIN_RECOPOINTS_THRESHOLD)
                purity_results = EvaluatePurity(
                    clusters_true, clusters_reco, event_key,
                    radius_purity_xz=RADIUS_PURITY_XZ, radius_purity_yz=RADIUS_PURITY_YZ, radius_purity_xy=RADIUS_PURITY_XY)

                # ---- PCA linearity per cluster (needs point clouds) ----
                true_linearity_lookup = {
                    (file_name, event_key, apa, cid): calculate_pca_linearity(pts)
                    for cid, pts in clusters_true.items()
                }
                reco_linearity_lookup = {
                    (file_name, event_key, apa, cid): calculate_pca_linearity(pts)
                    for cid, pts in clusters_reco.items()
                }

                # ---- metadata (cheap - built from the results above) ----
                event_true_metadata = add_metadata_true_clusters(
                    efficiency_results, cluster_category_results,
                    file_name=file_name, event=evt, apa=apa, view=args.view, event_key=event_key)
                add_single_metadata(event_true_metadata, "linearity", true_linearity_lookup)

                # Dead-area before/after point counts (all true clusters in this event).
                before_lookup = {(file_name, event_key, apa, c): n for c, n in before_counts.items()}
                after_lookup = {(file_name, event_key, apa, c): n for c, n in after_counts.items()}
                add_single_metadata(event_true_metadata, "n_points_before_deadarea", before_lookup, default=None)
                add_single_metadata(event_true_metadata, "n_points_after_deadarea", after_lookup, default=None)

                # Category geometry, for reproducing DrawTrueClusterCategories without
                # recomputing cluster_category() from raw points at analysis time.
                is_neutrino_lookup   = {(file_name, event_key, apa, c): bool(info["is_neutrino"]) for c, info in cluster_category_results.items()}
                theta_xz_lookup      = {(file_name, event_key, apa, c): _none_to_nan(info["theta_xz"]) for c, info in cluster_category_results.items()}
                z_min_lookup         = {(file_name, event_key, apa, c): _none_to_nan(info["z_min"]) for c, info in cluster_category_results.items()}
                z_max_lookup         = {(file_name, event_key, apa, c): _none_to_nan(info["z_max"]) for c, info in cluster_category_results.items()}
                x_at_z_min_lookup    = {(file_name, event_key, apa, c): _none_to_nan(info["x_at_z_min"]) for c, info in cluster_category_results.items()}
                x_at_z_max_lookup    = {(file_name, event_key, apa, c): _none_to_nan(info["x_at_z_max"]) for c, info in cluster_category_results.items()}
                add_single_metadata(event_true_metadata, "is_neutrino", is_neutrino_lookup, default=False)
                add_single_metadata(event_true_metadata, "theta_xz", theta_xz_lookup, default=np.nan)
                add_single_metadata(event_true_metadata, "z_min", z_min_lookup, default=np.nan)
                add_single_metadata(event_true_metadata, "z_max", z_max_lookup, default=np.nan)
                add_single_metadata(event_true_metadata, "x_at_z_min", x_at_z_min_lookup, default=np.nan)
                add_single_metadata(event_true_metadata, "x_at_z_max", x_at_z_max_lookup, default=np.nan)

                # Full one-to-many match set (every reco cluster id a true cluster matched,
                # not just the 1-to-1 best), with the exact per-pair efficiency and purity -
                # so DrawTrueClusterWithMatchedReco and the heatmaps can be reproduced from
                # metadata alone at analysis time, without the aggregate approximation.
                matched_true_reco_clusters = MatchTruetoReco_OneToMany(purity_results, efficiency_results)
                matched_reco_ids_lookup = {
                    (file_name, event_key, apa, m["true_cluster_id"]):
                        [rc["reco_cluster_id"] for rc in m["matched_reco_clusters"]]
                    for m in matched_true_reco_clusters
                }
                matched_reco_efficiencies_lookup = {
                    (file_name, event_key, apa, m["true_cluster_id"]):
                        [rc["efficiency_energy_weighted"] for rc in m["matched_reco_clusters"]]
                    for m in matched_true_reco_clusters
                }
                add_single_metadata(event_true_metadata, "matched_reco_ids", matched_reco_ids_lookup, default=None)
                add_single_metadata(event_true_metadata, "matched_reco_efficiencies", matched_reco_efficiencies_lookup, default=None)

                true_cluster_metadata_list.extend(event_true_metadata)

                # Reco-centric inversion of the same one-to-many match set: for each reco
                # cluster, every true cluster it matched and that pair's exact purity.
                reco_matches = {}
                for m in matched_true_reco_clusters:
                    for rc in m["matched_reco_clusters"]:
                        reco_matches.setdefault(rc["reco_cluster_id"], []).append((m["true_cluster_id"], rc["purity"]))
                matched_true_ids_lookup = {
                    (file_name, event_key, apa, rid): [t[0] for t in matches]
                    for rid, matches in reco_matches.items()
                }
                matched_true_purities_lookup = {
                    (file_name, event_key, apa, rid): [t[1] for t in matches]
                    for rid, matches in reco_matches.items()
                }

                event_reco_metadata = add_metadata_reco_clusters(
                    purity_results, file_name=file_name, event=evt, apa=apa, view=args.view, event_key=event_key)
                add_single_metadata(event_reco_metadata, "linearity", reco_linearity_lookup,
                                    key_fields=("file_name", "event", "apa", "reco_cluster_id"))
                add_single_metadata(event_reco_metadata, "matched_true_ids", matched_true_ids_lookup, default=None,
                                    key_fields=("file_name", "event", "apa", "reco_cluster_id"))
                add_single_metadata(event_reco_metadata, "matched_true_purities", matched_true_purities_lookup, default=None,
                                    key_fields=("file_name", "event", "apa", "reco_cluster_id"))
                reco_cluster_metadata_list.extend(event_reco_metadata)

                matched_pairs = MatchTrueToReco1to1(efficiency_results, purity_results)
                event_pair_metadata = add_metadata_true_reco_pair_cluster(
                    matched_pairs, cluster_category_results,
                    file_name=file_name, event=evt, apa=apa, view=args.view, event_key=event_key)
                true_reco_pair_metadata_list.extend(event_pair_metadata)

                total_events_processed += 1
                print(f"  event {evt}: {len(clusters_true)} true, {len(clusters_reco)} reco clusters")

    print(f"\nTotal events processed: {total_events_processed}")

    # ---- concatenate point-level columns into flat numpy arrays ----
    def finalize_points(cols, id_col):
        if not cols[id_col]:
            return {k: np.array([]) for k in cols}
        out = {}
        for k, v in cols.items():
            if k in ("file", "event", "apa"):
                out[k] = np.array(v)
            else:
                out[k] = np.concatenate(v)
        return out

    true_points_data = finalize_points(true_points_cols, "true_cluster_id")
    reco_points_data = finalize_points(reco_points_cols, "reco_cluster_id")
    true_points_before_deadarea_data = finalize_points(true_points_before_deadarea_cols, "true_cluster_id")

    print(f"true_points rows: {len(true_points_data['true_cluster_id'])}")
    print(f"reco_points rows: {len(reco_points_data['reco_cluster_id'])}")
    print(f"true_points_before_deadarea rows: {len(true_points_before_deadarea_data['true_cluster_id'])}")
    print(f"true_cluster_metadata rows: {len(true_cluster_metadata_list)}")
    print(f"reco_cluster_metadata rows: {len(reco_cluster_metadata_list)}")
    print(f"true_reco_pair_metadata rows: {len(true_reco_pair_metadata_list)}")

    def to_columns(metadata_list):
        # Plain dict-of-arrays, not a DataFrame passed directly - uproot would otherwise
        # also write the DataFrame's RangeIndex as a spurious extra "index" branch.
        if not metadata_list:
            return {}
        df = pd.DataFrame(metadata_list)
        out = {}
        for col in df.columns:
            # list-valued columns (e.g. matched_reco_ids) are jagged - need an awkward
            # Array, not a plain numpy array of Python list objects, for uproot to write them.
            if df[col].apply(lambda v: isinstance(v, list)).any():
                out[col] = ak.Array([v if isinstance(v, list) else [] for v in df[col]])
            else:
                out[col] = df[col].to_numpy()
        return out

    # ---- write everything to one ROOT file ----
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with uproot.recreate(out_path) as f:
        f["true_points"] = true_points_data
        f["reco_points"] = reco_points_data
        f["true_points_before_deadarea"] = true_points_before_deadarea_data
        f["true_cluster_metadata"] = to_columns(true_cluster_metadata_list)
        f["reco_cluster_metadata"] = to_columns(reco_cluster_metadata_list)
        f["true_reco_pair_metadata"] = to_columns(true_reco_pair_metadata_list)

    elapsed = time.monotonic() - start_clock
    print(f"\nWrote {out_path} in {elapsed/60:.2f} min")


if __name__ == "__main__":
    main()
