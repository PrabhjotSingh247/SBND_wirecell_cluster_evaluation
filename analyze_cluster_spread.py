"""
Phase 1 diagnostic for the "spread cluster" selection (see CLAUDE.md).

Some true/reco clusters contain many points but no coherent trajectory - they are
several disconnected blobs scattered over a large volume that happen to share one
cluster ID. This script does NOT remove anything. It walks the dataset, computes a
small set of per-cluster shape metrics (point count, PCA "linearity", bounding-box
diagonal), prints summary tables, and writes diagnostic plots so a removal threshold
can be chosen from real statistics instead of a single hand-picked event.

Usage:
    python analyze_cluster_spread.py [--view 2view] [--file file1] [--apa APA0]

Outputs (under spread_cluster_analysis/<timestamp>/), at Event-Level
(<file>/event_NNN/<APA>/), File-Level (<file>/file_level/<APA>/), and Job-Level
(job_level/<APA>/, aggregating every file/event processed in this run) - each APA
gets its own subdirectory at every level:
    *_linearity_bar_*.png                       (event-level only; true & reco)
    *_npoints_vs_energy_colz_*.png               (true: n_points vs energy, color=mean linearity)
    *_npoints_vs_energy_count_*.png              (true: n_points vs energy, color=#clusters)
    *_npoints_vs_charge_count_*.png              (reco: n_points vs charge, color=#clusters)
    *_npoints_vs_charge_colz_job_<APA>.png        (reco: n_points vs charge, color=mean linearity; job-level only)
    *_linearity_vs_completeness_*.png              (true cluster linearity vs. matched-reco completeness)
    flagged_true_clusters_*.txt                  (metadata table for flagged true clusters only)
    job_level/summary.txt                        (job start/end time and duration - not per-APA)
    <file>/event_NNN/<APA>/true_cluster_<id>_views_*.png   (XZ/YZ/XY views of each flagged true cluster)
    <file>/event_NNN/<APA>/reco_cluster_<id>_views_*.png   (XZ/YZ/XY views of each flagged reco cluster)
"""
import argparse
import contextlib
import io
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from readfiles import read_files_for_event
from selections import (
    apply_energy_cutoff, apply_true_pointwise_energy_cutoff, apply_min_true_points_cutoff, apply_min_reco_points_cutoff,
    apply_wire_readout_sensitive_yz_plane_cut_true, apply_wire_readout_sensitive_yz_plane_cut_reco,
    reassign_cluster_ID_true, reassign_cluster_ID_reco, GroupClustersByID,
    apply_deadarea_cut_true,
)
from completeness_purity_estimate import EvaluateCompleteness

# Same cut configuration as Evaluation_BeforeChargeLightMatching_BeforeBeamWindowCut.ipynb (cell 3), so the
# diagnostic reflects the cluster shapes a removal cut would actually see.
MIN_CLUSTER_ENERGY       = 10
MIN_TRUE_POINT_ENERGY = 0.02   # MeV per true POINT
MIN_TRUE_POINTS_CUTOFF   = 200
MIN_RECO_POINTS_CUTOFF   = 200
X_MIN, X_MAX = -250.0, 250.0
Y_MIN, Y_MAX = -200.0, 200.0
Z_MIN, Z_MAX = 0.15, 500.85
RADIUS_COMPLETENESS        = 2
MIN_RECOPOINTS_THRESHOLD = 5

# Candidate thresholds carried over from the single-event check (file1, event 1,
# APA0: true cluster -28 / reco -40 scored linearity 0.642 / 0.614 with 938 / 214
# points). Only used here to annotate plots and the "flagged" column - no points
# are removed by this script.
LINEARITY_THRESHOLD   = 0.8
MIN_POINTS_FOR_CHECK  = 50

NEUTRINO_CLUSTER_ID = 9999


def bin_edges(vmin, vmax, width):
    return np.arange(vmin, vmax + width, width)


# Zoomed bin edges for the 2D colz histograms - fixed range + bin width, per user request.
TRUE_NPOINTS_EDGES = bin_edges(0, 1000, 10)      # true clusters: 0-1000 points, 10 pts/bin
TRUE_ENERGY_EDGES = bin_edges(0, 500, 10)        # true clusters: 0-500 MeV, 10 MeV/bin
RECO_NPOINTS_EDGES = bin_edges(0, 1000, 10)      # reco clusters: 0-1000 points, 10 pts/bin
RECO_CHARGE_EDGES = bin_edges(0, 0.5e8, 0.1e7)   # reco clusters: 0-0.5e8 ADC, 0.1e7 ADC/bin
LINEARITY_EDGES = bin_edges(0, 1.0, 0.02)        # linearity: 0-1, 0.02/bin

# dataviz skill palette (references/palette.md), light mode
COLOR_REGULAR  = "#2a78d6"  # blue
COLOR_FLAGGED  = "#e34948"  # red
COLOR_NEUTRINO = "#4a3aa7"  # violet
COLOR_BLACK    = "#000000"
INK_PRIMARY    = "#0b0b0b"
INK_MUTED      = "#898781"
GRIDLINE       = "#e1e0d9"
SURFACE        = "#fcfcfb"
# Equivalent of ROOT's kTemperatureMap (dark blue -> cyan -> green -> yellow -> red)
# for the 2D colz histograms, where a single-hue ramp doesn't separate values well.
TEMPERATURE_CMAP = LinearSegmentedColormap.from_list(
    "temperature_map",
    ["#1a1a6e", "#0000ff", "#00c8ff", "#00ff00", "#ffff00", "#ff8c00", "#ff0000"])


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


def linearity_and_bbox(xyz):
    """PCA linearity = lambda_1 / sum(lambda) of the 3D covariance matrix.
    1.0 = points lie on a single line/curve direction, lower = scattered in
    multiple directions. bbox_diag = bounding-box diagonal length in cm."""
    bbox_diag = float(np.linalg.norm(xyz.max(axis=0) - xyz.min(axis=0)))
    if len(xyz) < 3:
        return 1.0, bbox_diag
    centered = xyz - xyz.mean(axis=0)
    eigvals = np.clip(np.linalg.eigvalsh(np.cov(centered.T)), 0, None)
    total = eigvals.sum()
    linearity = float(eigvals.max() / total) if total > 0 else 1.0
    return linearity, bbox_diag


def process_true_clusters(x, y, z, cid, q, e, t):
    points = np.column_stack([x, y, z, cid, q, e, t])
    points = reassign_cluster_ID_true(points)
    # POINT-wise first, so the cluster total the cluster cut tests is the
    # total of the points that survive. 0.01 MeV -- see selections.py.
    points = apply_true_pointwise_energy_cutoff(points, MIN_TRUE_POINT_ENERGY)
    points = apply_energy_cutoff(points, MIN_CLUSTER_ENERGY)
    if len(points) == 0:
        return {}
    points = apply_min_true_points_cutoff(points, MIN_TRUE_POINTS_CUTOFF)
    if len(points) == 0:
        return {}
    points = apply_wire_readout_sensitive_yz_plane_cut_true(
        points, X_MIN, X_MAX, Y_MIN, Y_MAX, Z_MIN, Z_MAX)
    if len(points) == 0:
        return {}
    with contextlib.redirect_stdout(io.StringIO()):
        points = apply_deadarea_cut_true(points, apa="APA0", view_type="2view")
    if len(points) == 0:
        return {}
    return GroupClustersByID(points)


def process_reco_clusters(x, y, z, cid, q):
    points = np.column_stack([x, y, z, cid, q])
    points = apply_min_reco_points_cutoff(points, MIN_RECO_POINTS_CUTOFF)
    if len(points) == 0:
        return {}
    points = apply_wire_readout_sensitive_yz_plane_cut_reco(
        points, X_MIN, X_MAX, Y_MIN, Y_MAX, Z_MIN, Z_MAX)
    if len(points) == 0:
        return {}
    points = reassign_cluster_ID_reco(points)
    return GroupClustersByID(points)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--view", default="2view", choices=["2view", "3view"])
    parser.add_argument("--ghosting", dest="ghosting", action="store_true", default=True)
    parser.add_argument("--no-ghosting", dest="ghosting", action="store_false")
    parser.add_argument("--file", default=None, help="Restrict to one file dir (e.g. file1), for quick testing")
    parser.add_argument("--apa", default=None, choices=["APA0", "APA1"], help="Restrict to one APA (default: both)")
    args = parser.parse_args()

    start_time = datetime.now()
    start_clock = time.monotonic()
    print(f"Job started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    parent_dir = Path(args.view)
    apa_list = [args.apa] if args.apa is not None else ["APA0", "APA1"]

    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    out_dir = Path("spread_cluster_analysis") / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    input_directories = find_all_input_directories(parent_dir)
    if args.file is not None:
        input_directories = [d for d in input_directories if d.name == args.file]
    print(f"Found {len(input_directories)} file directories under {parent_dir}")

    true_rows = []
    reco_rows = []
    completeness_rows = []
    flagged_true_xyz = {}  # (file, event, apa, cluster_id) -> xyz points, for the per-cluster view plots
    flagged_reco_xyz = {}  # same, for reco clusters

    for input_dir in input_directories:
        file_name = input_dir.name
        events = detect_events_in_directory(input_dir)
        print(f"  {file_name}: {len(events)} events")

        for evt in events:
            for apa in apa_list:
                result = read_files_for_event(input_dir, evt, apa)
                if result is None:
                    continue
                (x_true, y_true, z_true, id_true, q_true, e_true, t_true,
                 x_pred, y_pred, z_pred, id_pred, q_pred) = result

                true_clusters = {}
                true_shape_by_id = {}
                if len(x_true) > 0:
                    true_clusters = process_true_clusters(
                        x_true, y_true, z_true, id_true, q_true, e_true, t_true)
                    for cluster_id, points in true_clusters.items():
                        points = np.array(points)
                        xyz = points[:, :3]
                        linearity, bbox_diag = linearity_and_bbox(xyz)
                        is_neutrino = abs(cluster_id - NEUTRINO_CLUSTER_ID) < 1e-6
                        # No neutrino exemption here - this is the Phase 1 diagnostic, testing
                        # whether the metric itself would catch the neutrino cluster, not the
                        # (separate, not-yet-written) removal cut where 9999 must be preserved.
                        flagged = (len(points) >= MIN_POINTS_FOR_CHECK
                                   and linearity < LINEARITY_THRESHOLD)
                        true_shape_by_id[cluster_id] = {
                            "linearity": linearity, "is_neutrino": is_neutrino, "flagged": flagged,
                        }
                        true_rows.append({
                            "file": file_name, "event": evt, "apa": apa,
                            "cluster_id": cluster_id, "n_points": len(points),
                            "energy": float(points[:, 5].sum()),
                            "linearity": linearity, "bbox_diag": bbox_diag,
                            "is_neutrino": is_neutrino, "flagged": flagged,
                        })
                        if flagged:
                            flagged_true_xyz[(file_name, evt, apa, cluster_id)] = xyz.copy()

                reco_clusters = {}
                if len(x_pred) > 0:
                    reco_clusters = process_reco_clusters(x_pred, y_pred, z_pred, id_pred, q_pred)
                    for cluster_id, points in reco_clusters.items():
                        points = np.array(points)
                        xyz = points[:, :3]
                        linearity, bbox_diag = linearity_and_bbox(xyz)
                        reco_flagged = (len(points) >= MIN_POINTS_FOR_CHECK
                                        and linearity < LINEARITY_THRESHOLD)
                        reco_rows.append({
                            "file": file_name, "event": evt, "apa": apa,
                            "cluster_id": cluster_id, "n_points": len(points),
                            "charge": float(points[:, 4].sum()),
                            "linearity": linearity, "bbox_diag": bbox_diag,
                            "flagged": reco_flagged,
                        })
                        if reco_flagged:
                            flagged_reco_xyz[(file_name, evt, apa, cluster_id)] = xyz.copy()

                if true_clusters:
                    eff_results = EvaluateCompleteness(
                        true_clusters, reco_clusters, evt,
                        radius_completeness=RADIUS_COMPLETENESS,
                        min_recopoints_threshold=MIN_RECOPOINTS_THRESHOLD)
                    for row in eff_results:
                        shape = true_shape_by_id.get(row["true_cluster_id"])
                        if shape is None:
                            continue
                        completeness_rows.append({
                            "file": file_name, "event": evt, "apa": apa,
                            "true_cluster_id": row["true_cluster_id"],
                            "reco_cluster_id": row["reco_cluster_id"],
                            "completeness": row["completeness_energy_weighted"],
                            "linearity": shape["linearity"],
                            "is_neutrino": shape["is_neutrino"],
                            "flagged": shape["flagged"],
                        })

    true_df = pd.DataFrame(true_rows)
    reco_df = pd.DataFrame(reco_rows)
    completeness_df = pd.DataFrame(completeness_rows)
    print(f"\nProcessed {len(true_df)} true cluster rows, {len(reco_df)} reco cluster rows, "
          f"{len(completeness_df)} true-to-reco completeness matches")

    # Join flagged true-cluster matches with their true/reco cluster metadata, for
    # the flagged-cluster .txt reports. reco_cluster_id == 8888 (unmatched) simply
    # won't be found in reco_df, so those rows keep NaN reco columns.
    if not completeness_df.empty:
        flagged_metadata_df = completeness_df[completeness_df["flagged"]].copy()
        true_lookup = true_df.set_index(["file", "event", "apa", "cluster_id"])[["n_points", "energy"]]
        true_lookup = true_lookup.rename(columns={"n_points": "n_true_points", "energy": "true_energy"})
        flagged_metadata_df = flagged_metadata_df.join(
            true_lookup, on=["file", "event", "apa", "true_cluster_id"])

        reco_lookup = reco_df.set_index(["file", "event", "apa", "cluster_id"])[["n_points", "charge"]]
        reco_lookup = reco_lookup.rename(columns={"n_points": "n_reco_points", "charge": "reco_charge"})
        flagged_metadata_df = flagged_metadata_df.join(
            reco_lookup, on=["file", "event", "apa", "reco_cluster_id"])
    else:
        flagged_metadata_df = pd.DataFrame(columns=FLAGGED_METADATA_COLUMNS)

    # Cross-lookups (file, event, apa, cluster_id) -> list of matched cluster IDs on
    # the other side, for labeling the flagged-cluster view plots. Excludes 8888
    # (the unmatched sentinel).
    true_match_lookup = {}
    reco_match_lookup = {}
    if not completeness_df.empty:
        matched = completeness_df[completeness_df["reco_cluster_id"] != 8888]
        for _, r in matched.iterrows():
            true_key = (r["file"], r["event"], r["apa"], r["true_cluster_id"])
            true_match_lookup.setdefault(true_key, []).append(r["reco_cluster_id"])
            reco_key = (r["file"], r["event"], r["apa"], r["reco_cluster_id"])
            reco_match_lookup.setdefault(reco_key, []).append(r["true_cluster_id"])

    # Per true cluster: how many distinct reco clusters it matched (0, 1, or >1),
    # for the linearity-vs-energy-by-match-count plots below.
    def _n_reco_matches(row):
        key = (row["file"], row["event"], row["apa"], row["cluster_id"])
        return len(true_match_lookup.get(key, []))

    true_df["n_reco_matches"] = true_df.apply(_n_reco_matches, axis=1)
    true_df["match_category"] = np.select(
        [true_df["n_reco_matches"] == 0, true_df["n_reco_matches"] == 1],
        ["zero", "one"], default="multiple")

    neutrino_df = true_df[true_df["is_neutrino"]].sort_values("linearity")
    if len(neutrino_df) > 0:
        print(f"\nNeutrino cluster (9999) linearity across {len(neutrino_df)} events: "
              f"min={neutrino_df['linearity'].min():.3f}, "
              f"mean={neutrino_df['linearity'].mean():.3f}, "
              f"max={neutrino_df['linearity'].max():.3f}")
        n_below = (neutrino_df["linearity"] < LINEARITY_THRESHOLD).sum()
        print(f"  Neutrino clusters below the candidate threshold ({LINEARITY_THRESHOLD}): {n_below}")

    candidates_true = true_df[(~true_df["is_neutrino"]) & (true_df["n_points"] >= MIN_POINTS_FOR_CHECK)]
    top_true = candidates_true.sort_values("linearity").head(15)
    print(f"\nTop 15 lowest-linearity TRUE clusters (n_points >= {MIN_POINTS_FOR_CHECK}, excl. neutrino):")
    print(top_true.to_string(index=False))

    candidates_reco = reco_df[reco_df["n_points"] >= MIN_POINTS_FOR_CHECK]
    top_reco = candidates_reco.sort_values("linearity").head(15)
    print(f"\nTop 15 lowest-linearity RECO clusters (n_points >= {MIN_POINTS_FOR_CHECK}):")
    print(top_reco.to_string(index=False))

    # Event-Level: one set of plots per (file, event, apa)
    for (file_name, evt, apa), true_group in true_df.groupby(["file", "event", "apa"]):
        evt_dir = out_dir / file_name / f"event_{int(evt):03d}" / apa
        evt_dir.mkdir(parents=True, exist_ok=True)
        tag = f"{file_name}_{apa}_event{int(evt)}"
        plot_linearity_bar(true_group, id_col="cluster_id",
                            title=f"True cluster linearity - {file_name}, event {evt}, {apa}",
                            out_path=evt_dir / f"true_cluster_linearity_bar_{tag}.png")
        plot_2d_hist_colz(true_group, x_col="n_points", y_col="energy", agg="mean", z_col="linearity",
                           x_bins=TRUE_NPOINTS_EDGES, y_bins=TRUE_ENERGY_EDGES,
                           x_label="Number of points", y_label="Cluster energy [MeV]",
                           title=f"True clusters: n_points vs energy (color=linearity) - {file_name}, event {evt}, {apa}",
                           out_path=evt_dir / f"true_cluster_npoints_vs_energy_colz_{tag}.png")
        plot_2d_hist_colz(true_group, x_col="n_points", y_col="energy", agg="count",
                           x_bins=TRUE_NPOINTS_EDGES, y_bins=TRUE_ENERGY_EDGES,
                           x_label="Number of points", y_label="Cluster energy [MeV]",
                           title=f"True clusters: n_points vs energy (color=#clusters) - {file_name}, event {evt}, {apa}",
                           out_path=evt_dir / f"true_cluster_npoints_vs_energy_count_{tag}.png")
        plot_2d_hist_colz(true_group, x_col="linearity", y_col="energy", agg="count",
                           x_bins=LINEARITY_EDGES, y_bins=TRUE_ENERGY_EDGES,
                           x_label="PCA linearity", y_label="Cluster energy [MeV]",
                           title=f"True clusters: linearity vs energy (color=#clusters) - {file_name}, event {evt}, {apa}",
                           out_path=evt_dir / f"true_cluster_linearity_vs_energy_count_{tag}.png")
        for _, row in true_group[true_group["flagged"]].iterrows():
            key = (file_name, evt, apa, row["cluster_id"])
            xyz = flagged_true_xyz.get(key)
            if xyz is None:
                continue
            reco_ids = true_match_lookup.get(key, [])
            reco_label = "_".join(f"{r:.0f}" for r in reco_ids) if reco_ids else "unmatched"
            info = f"n_points={int(row['n_points'])}   energy={row['energy']:.2f} MeV   linearity={row['linearity']:.3f}"
            plot_cluster_three_views(
                xyz, info=info,
                title=(f"True cluster {row['cluster_id']:.0f} with reco {reco_label} - "
                       f"{file_name}, event {evt}, {apa}"),
                out_path=evt_dir / f"true_cluster_{row['cluster_id']:.0f}_with_reco_{reco_label}_views_{tag}.png")
    for (file_name, evt, apa), reco_group in reco_df.groupby(["file", "event", "apa"]):
        evt_dir = out_dir / file_name / f"event_{int(evt):03d}" / apa
        evt_dir.mkdir(parents=True, exist_ok=True)
        tag = f"{file_name}_{apa}_event{int(evt)}"
        plot_linearity_bar(reco_group, id_col="cluster_id",
                            title=f"Reco cluster linearity - {file_name}, event {evt}, {apa}",
                            out_path=evt_dir / f"reco_cluster_linearity_bar_{tag}.png")
        plot_2d_hist_colz(reco_group, x_col="n_points", y_col="charge", agg="count",
                           x_bins=RECO_NPOINTS_EDGES, y_bins=RECO_CHARGE_EDGES,
                           x_label="Number of points", y_label="Reco cluster charge [ADC]",
                           title=f"Reco clusters: n_points vs charge (color=#clusters) - {file_name}, event {evt}, {apa}",
                           out_path=evt_dir / f"reco_cluster_npoints_vs_charge_count_{tag}.png")
        for _, row in reco_group[reco_group["flagged"]].iterrows():
            key = (file_name, evt, apa, row["cluster_id"])
            xyz = flagged_reco_xyz.get(key)
            if xyz is None:
                continue
            true_ids = reco_match_lookup.get(key, [])
            true_label = "_".join(f"{t:.0f}" for t in true_ids) if true_ids else "unmatched"
            info = f"n_points={int(row['n_points'])}   charge={row['charge']:.2f} ADC   linearity={row['linearity']:.3f}"
            plot_cluster_three_views(
                xyz, info=info,
                title=(f"Reco cluster {row['cluster_id']:.0f} with true {true_label} - "
                       f"{file_name}, event {evt}, {apa}"),
                out_path=evt_dir / f"reco_cluster_{row['cluster_id']:.0f}_with_true_{true_label}_views_{tag}.png")
    if not completeness_df.empty:
        for (file_name, evt, apa), eff_group in completeness_df.groupby(["file", "event", "apa"]):
            evt_dir = out_dir / file_name / f"event_{int(evt):03d}" / apa
            evt_dir.mkdir(parents=True, exist_ok=True)
            tag = f"{file_name}_{apa}_event{int(evt)}"
            plot_linearity_vs_completeness_scatter(
                eff_group, title=f"True cluster linearity vs. completeness - {file_name}, event {evt}, {apa}",
                out_path=evt_dir / f"true_cluster_linearity_vs_completeness_{tag}.png")
            flagged_group = flagged_metadata_df[
                (flagged_metadata_df["file"] == file_name) & (flagged_metadata_df["event"] == evt)
                & (flagged_metadata_df["apa"] == apa)]
            write_flagged_metadata_txt(
                flagged_group, title=f"Flagged true clusters - {file_name}, event {evt}, {apa}",
                out_path=evt_dir / f"flagged_true_clusters_{tag}.txt")

    # File-Level: colz plots (+ linearity vs completeness scatter, + flagged metadata
    # .txt) per (file, apa), aggregating all events in that file. (No bar chart at
    # this level - too many bars across events to be readable/meaningful.)
    for (file_name, apa), true_group in true_df.groupby(["file", "apa"]):
        file_dir = out_dir / file_name / "file_level" / apa
        file_dir.mkdir(parents=True, exist_ok=True)
        tag = f"{file_name}_{apa}"
        plot_2d_hist_colz(true_group, x_col="n_points", y_col="energy", agg="mean", z_col="linearity",
                           x_bins=TRUE_NPOINTS_EDGES, y_bins=TRUE_ENERGY_EDGES,
                           x_label="Number of points", y_label="Cluster energy [MeV]",
                           title=f"True clusters: n_points vs energy (color=linearity) - {file_name}, all events, {apa}",
                           out_path=file_dir / f"true_cluster_npoints_vs_energy_colz_{tag}.png")
        plot_2d_hist_colz(true_group, x_col="n_points", y_col="energy", agg="count",
                           x_bins=TRUE_NPOINTS_EDGES, y_bins=TRUE_ENERGY_EDGES,
                           x_label="Number of points", y_label="Cluster energy [MeV]",
                           title=f"True clusters: n_points vs energy (color=#clusters) - {file_name}, all events, {apa}",
                           out_path=file_dir / f"true_cluster_npoints_vs_energy_count_{tag}.png")
        plot_2d_hist_colz(true_group, x_col="linearity", y_col="energy", agg="count",
                           x_bins=LINEARITY_EDGES, y_bins=TRUE_ENERGY_EDGES,
                           x_label="PCA linearity", y_label="Cluster energy [MeV]",
                           title=f"True clusters: linearity vs energy (color=#clusters) - {file_name}, all events, {apa}",
                           out_path=file_dir / f"true_cluster_linearity_vs_energy_count_{tag}.png")
        reco_group = reco_df[(reco_df["file"] == file_name) & (reco_df["apa"] == apa)]
        plot_2d_hist_colz(reco_group, x_col="n_points", y_col="charge", agg="count",
                           x_bins=RECO_NPOINTS_EDGES, y_bins=RECO_CHARGE_EDGES,
                           x_label="Number of points", y_label="Reco cluster charge [ADC]",
                           title=f"Reco clusters: n_points vs charge (color=#clusters) - {file_name}, all events, {apa}",
                           out_path=file_dir / f"reco_cluster_npoints_vs_charge_count_{tag}.png")
        if not completeness_df.empty:
            eff_group = completeness_df[(completeness_df["file"] == file_name) & (completeness_df["apa"] == apa)]
            plot_linearity_vs_completeness_scatter(
                eff_group, title=f"True cluster linearity vs. completeness - {file_name}, all events, {apa}",
                out_path=file_dir / f"true_cluster_linearity_vs_completeness_{tag}.png")
        flagged_group = flagged_metadata_df[
            (flagged_metadata_df["file"] == file_name) & (flagged_metadata_df["apa"] == apa)]
        write_flagged_metadata_txt(
            flagged_group, title=f"Flagged true clusters - {file_name}, all events, {apa}",
            out_path=file_dir / f"flagged_true_clusters_{tag}.txt")

    # Job-Level: aggregating all files/events in this run, per apa (each apa's
    # plots go under job_level/<APA>/). Includes both the count and
    # linearity-colored versions of the true/reco 2D histograms.
    job_base_dir = out_dir / "job_level"
    job_base_dir.mkdir(parents=True, exist_ok=True)
    for apa, true_group in true_df.groupby("apa"):
        job_dir = job_base_dir / apa
        job_dir.mkdir(parents=True, exist_ok=True)
        plot_2d_hist_colz(true_group, x_col="n_points", y_col="energy", agg="mean", z_col="linearity",
                           x_bins=TRUE_NPOINTS_EDGES, y_bins=TRUE_ENERGY_EDGES,
                           x_label="Number of points", y_label="Cluster energy [MeV]",
                           title=f"True clusters: n_points vs energy (color=linearity) - all files, all events, {apa}",
                           out_path=job_dir / f"true_cluster_npoints_vs_energy_colz_job_{apa}.png")
        plot_2d_hist_colz(true_group, x_col="n_points", y_col="energy", agg="count",
                           x_bins=TRUE_NPOINTS_EDGES, y_bins=TRUE_ENERGY_EDGES,
                           x_label="Number of points", y_label="Cluster energy [MeV]",
                           title=f"True clusters: n_points vs energy (color=#clusters) - all files, all events, {apa}",
                           out_path=job_dir / f"true_cluster_npoints_vs_energy_count_job_{apa}.png")
        plot_2d_hist_colz(true_group, x_col="linearity", y_col="energy", agg="count",
                           x_bins=LINEARITY_EDGES, y_bins=TRUE_ENERGY_EDGES,
                           x_label="PCA linearity", y_label="Cluster energy [MeV]",
                           title=f"True clusters: linearity vs energy (color=#clusters) - all files, all events, {apa}",
                           out_path=job_dir / f"true_cluster_linearity_vs_energy_count_job_{apa}.png")
        neutrino_group = true_group[true_group["is_neutrino"]]
        cosmic_group = true_group[~true_group["is_neutrino"]]
        for label, group in [("neutrino", neutrino_group), ("cosmic", cosmic_group)]:
            plot_linearity_vs_energy_by_match_count(
                group, y_max=500,
                title=(f"True {label} cluster linearity vs. energy, by reco match count (zoomed) - "
                       f"all files, all events, {apa}"),
                out_path=job_dir / f"true_{label}_cluster_linearity_vs_energy_by_match_zoomed_job_{apa}.png")
            plot_linearity_vs_energy_by_match_count(
                group, y_max=None,
                title=(f"True {label} cluster linearity vs. energy, by reco match count (full range) - "
                       f"all files, all events, {apa}"),
                out_path=job_dir / f"true_{label}_cluster_linearity_vs_energy_by_match_full_job_{apa}.png")
            # Same plots again, but one category at a time - easier to read than all
            # three overlaid.
            cat_descriptions = {"zero": "0 reco clusters", "one": "1 reco cluster", "multiple": ">1 reco clusters"}
            for cat, cat_desc in cat_descriptions.items():
                plot_linearity_vs_energy_by_match_count(
                    group, y_max=500, only_categories=[cat],
                    title=(f"True {label} cluster linearity vs. energy, matched to {cat_desc} "
                           f"(zoomed) - all files, all events, {apa}"),
                    out_path=job_dir / f"true_{label}_cluster_linearity_vs_energy_by_match_{cat}_zoomed_job_{apa}.png")
                plot_linearity_vs_energy_by_match_count(
                    group, y_max=None, only_categories=[cat],
                    title=(f"True {label} cluster linearity vs. energy, matched to {cat_desc} "
                           f"(full range) - all files, all events, {apa}"),
                    out_path=job_dir / f"true_{label}_cluster_linearity_vs_energy_by_match_{cat}_full_job_{apa}.png")
    for apa, reco_group in reco_df.groupby("apa"):
        job_dir = job_base_dir / apa
        job_dir.mkdir(parents=True, exist_ok=True)
        plot_2d_hist_colz(reco_group, x_col="n_points", y_col="charge", agg="mean", z_col="linearity",
                           x_bins=RECO_NPOINTS_EDGES, y_bins=RECO_CHARGE_EDGES,
                           x_label="Number of points", y_label="Reco cluster charge [ADC]",
                           title=f"Reco clusters: n_points vs charge (color=linearity) - all files, all events, {apa}",
                           out_path=job_dir / f"reco_cluster_npoints_vs_charge_colz_job_{apa}.png")
        plot_2d_hist_colz(reco_group, x_col="n_points", y_col="charge", agg="count",
                           x_bins=RECO_NPOINTS_EDGES, y_bins=RECO_CHARGE_EDGES,
                           x_label="Number of points", y_label="Reco cluster charge [ADC]",
                           title=f"Reco clusters: n_points vs charge (color=#clusters) - all files, all events, {apa}",
                           out_path=job_dir / f"reco_cluster_npoints_vs_charge_count_job_{apa}.png")
    if not completeness_df.empty:
        for apa, eff_group in completeness_df.groupby("apa"):
            job_dir = job_base_dir / apa
            job_dir.mkdir(parents=True, exist_ok=True)
            plot_linearity_vs_completeness_scatter(
                eff_group, title=f"True cluster linearity vs. completeness - all files, all events, {apa}",
                out_path=job_dir / f"true_cluster_linearity_vs_completeness_job_{apa}.png")
    for apa in apa_list:
        job_dir = job_base_dir / apa
        job_dir.mkdir(parents=True, exist_ok=True)
        if not flagged_metadata_df.empty:
            apa_group = flagged_metadata_df[flagged_metadata_df["apa"] == apa]
            neutrino_flagged = apa_group[apa_group["is_neutrino"]]
            cosmic_flagged = apa_group[~apa_group["is_neutrino"]]
        else:
            neutrino_flagged = flagged_metadata_df
            cosmic_flagged = flagged_metadata_df
        write_flagged_metadata_txt(
            neutrino_flagged, title=f"Flagged neutrino true clusters - all files, all events, {apa}",
            out_path=job_dir / f"flagged_neutrino_true_clusters_job_{apa}.txt")
        write_flagged_metadata_txt(
            cosmic_flagged, title=f"Flagged cosmic true clusters - all files, all events, {apa}",
            out_path=job_dir / f"flagged_cosmic_true_clusters_job_{apa}.txt")

    print(f"\nAll outputs written to {out_dir}/")

    end_time = datetime.now()
    elapsed = time.monotonic() - start_clock
    print(f"\nJob started at  {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Job finished at {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total duration: {elapsed:.1f} s ({elapsed/60:.2f} min)")
    write_summary_txt(start_time, end_time, elapsed, job_base_dir / "summary.txt")


def plot_linearity_bar(df, id_col, title, out_path, composite_event_label=False):
    """Bar chart of linearity per cluster, one bar per cluster ID (or per
    event:cluster_id at File-Level, since IDs can repeat across events), each bar
    annotated 'flagged'/'unflagged' and colored accordingly."""
    if len(df) == 0:
        print(f"No rows to plot for {out_path}, skipping.")
        return

    df = df.copy()
    if composite_event_label:
        df["event_cluster_label"] = df.apply(
            lambda r: f"e{int(r['event'])}:{r['cluster_id']:.1f}", axis=1)
        df = df.sort_values(["event", "cluster_id"])
        labels = df["event_cluster_label"].tolist()
    else:
        df = df.sort_values("cluster_id")
        labels = [f"{cid:.2f}" for cid in df["cluster_id"]]

    n = len(df)
    fig, ax = plt.subplots(figsize=(max(7, 0.3 * n), 5.5), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)

    x = np.arange(n)
    colors = [COLOR_FLAGGED if f else COLOR_REGULAR for f in df["flagged"]]
    ax.bar(x, df["linearity"], color=colors, width=0.7)

    for xi, (val, flagged) in enumerate(zip(df["linearity"], df["flagged"])):
        ax.text(xi, val + 0.015, "flagged" if flagged else "unflagged",
                 ha="center", va="bottom", rotation=90, fontsize=6,
                 color=COLOR_FLAGGED if flagged else INK_MUTED)

    ax.axhline(LINEARITY_THRESHOLD, color=INK_MUTED, linestyle="--", linewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=90, fontsize=7, color=INK_MUTED)
    ax.set_ylim(0, 1.2)
    ax.set_ylabel("PCA linearity", color=INK_PRIMARY)
    ax.set_xlabel("Event:Cluster ID" if composite_event_label else "Cluster ID", color=INK_PRIMARY)
    ax.set_title(title, color=INK_PRIMARY, fontsize=11)
    ax.tick_params(colors=INK_MUTED)
    for spine in ax.spines.values():
        spine.set_color(GRIDLINE)
    ax.grid(True, axis="y", color=GRIDLINE, linewidth=0.8)
    ax.set_axisbelow(True)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved {out_path}")


def plot_2d_hist_colz(df, x_col, y_col, title, out_path, x_label, y_label,
                       agg="mean", z_col="linearity", x_bins=20, y_bins=20):
    """Rectangular 2D histogram (x_col vs y_col) where each bin's color (z) is
    either the mean of z_col (agg='mean', e.g. linearity - a ROOT-COLZ-style TH2
    of a per-cluster value) or the number of clusters falling in the bin
    (agg='count' - a ROOT-COLZ-style TH2 population plot). Linear axes,
    NaN/empty bins left blank. x_bins/y_bins may be an int bin count or an
    explicit array of bin edges (use edges to both zoom the axis range and set
    a fixed bin width - points outside the edges are simply not counted)."""
    if len(df) == 0:
        print(f"No rows to plot for {out_path}, skipping.")
        return

    x = df[x_col].to_numpy()
    y = df[y_col].to_numpy()
    counts, xedges, yedges = np.histogram2d(x, y, bins=[x_bins, y_bins])

    if agg == "count":
        z_grid = np.where(counts > 0, counts, np.nan)
        vmin, vmax = 0, None
        cbar_label = "Number of clusters"
    else:
        z = df[z_col].to_numpy()
        sums, _, _ = np.histogram2d(x, y, bins=[xedges, yedges], weights=z)
        with np.errstate(invalid="ignore", divide="ignore"):
            z_grid = np.where(counts > 0, sums / counts, np.nan)
        vmin, vmax = 0, 1
        cbar_label = f"Mean {z_col}"

    fig, ax = plt.subplots(figsize=(8, 6), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)

    pcm = ax.pcolormesh(xedges, yedges, z_grid.T, cmap=TEMPERATURE_CMAP, vmin=vmin, vmax=vmax)
    cbar = fig.colorbar(pcm, ax=ax)
    cbar.set_label(cbar_label, color=INK_PRIMARY)
    cbar.ax.yaxis.set_tick_params(color=INK_MUTED)
    plt.setp(cbar.ax.get_yticklabels(), color=INK_MUTED)

    ax.set_xlim(xedges[0], xedges[-1])
    ax.set_ylim(yedges[0], yedges[-1])
    ax.set_xlabel(x_label, color=INK_PRIMARY)
    ax.set_ylabel(y_label, color=INK_PRIMARY)
    ax.set_title(title, color=INK_PRIMARY, fontsize=11)
    ax.tick_params(colors=INK_MUTED)
    for spine in ax.spines.values():
        spine.set_color(GRIDLINE)
    ax.set_axisbelow(True)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved {out_path}")


def plot_cluster_three_views(xyz, info, title, out_path):
    """Draw one flagged cluster (true or reco) in XZ (left), YZ (middle), XY
    (right) - Z on the x-axis for the XZ/YZ panels, matching the convention used
    elsewhere in this project (e.g. DrawRecoTrueClusters.py). `info` is the
    preformatted metadata line (n_points/energy-or-charge/linearity)."""
    x, y, z = xyz[:, 0], xyz[:, 1], xyz[:, 2]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), facecolor=SURFACE)
    panels = [(axes[0], z, x, "Z [cm]", "X [cm]", "XZ"),
              (axes[1], z, y, "Z [cm]", "Y [cm]", "YZ"),
              (axes[2], x, y, "X [cm]", "Y [cm]", "XY")]
    for ax, px, py, xlabel, ylabel, name in panels:
        ax.set_facecolor(SURFACE)
        ax.scatter(px, py, s=8, alpha=0.6, color=COLOR_FLAGGED, edgecolors="none")
        ax.set_xlabel(xlabel, color=INK_PRIMARY)
        ax.set_ylabel(ylabel, color=INK_PRIMARY)
        ax.set_title(name, color=INK_PRIMARY, fontsize=11)
        ax.tick_params(colors=INK_MUTED)
        for spine in ax.spines.values():
            spine.set_color(GRIDLINE)
        ax.grid(True, color=GRIDLINE, linewidth=0.8)
        ax.set_axisbelow(True)

    fig.suptitle(f"{title}\n{info}", color=INK_PRIMARY, fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved {out_path}")


def plot_linearity_vs_completeness_scatter(df, title, out_path):
    """Scatter of true-cluster linearity (x) vs its energy-weighted completeness (y)
    matching to reco clusters (one point per true-to-reco match, from
    EvaluateCompleteness; unmatched true clusters appear at completeness=0)."""
    if len(df) == 0:
        print(f"No rows to plot for {out_path}, skipping.")
        return

    fig, ax = plt.subplots(figsize=(8, 6), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)

    # Neutrino takes priority in the drawing/legend categories: a flagged neutrino
    # cluster is drawn once, as neutrino (violet), not also as flagged (red).
    regular_mask = (~df["flagged"]) & (~df["is_neutrino"])
    flagged_mask = df["flagged"] & (~df["is_neutrino"])
    ax.scatter(df.loc[regular_mask, "linearity"], df.loc[regular_mask, "completeness"],
               s=18, alpha=0.5, color=COLOR_REGULAR, edgecolors="none", label="True cluster match")
    ax.scatter(df.loc[flagged_mask, "linearity"], df.loc[flagged_mask, "completeness"],
               s=28, alpha=0.85, color=COLOR_FLAGGED, edgecolors="none",
               label=f"Flagged (linearity<{LINEARITY_THRESHOLD})")
    ax.scatter(df.loc[df["is_neutrino"], "linearity"], df.loc[df["is_neutrino"], "completeness"],
               s=32, alpha=0.9, color=COLOR_NEUTRINO, edgecolors="none",
               label="Neutrino cluster (9999)")

    ax.axvline(LINEARITY_THRESHOLD, color=INK_MUTED, linestyle="--", linewidth=1)
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.05)
    ax.set_xlabel("PCA linearity", color=INK_PRIMARY)
    ax.set_ylabel("Completeness (energy-weighted match to reco)", color=INK_PRIMARY)
    ax.set_title(title, color=INK_PRIMARY, fontsize=11)
    ax.tick_params(colors=INK_MUTED)
    for spine in ax.spines.values():
        spine.set_color(GRIDLINE)
    ax.grid(True, color=GRIDLINE, linewidth=0.8)
    ax.set_axisbelow(True)
    legend = ax.legend(frameon=False, loc="upper left", fontsize=15, markerscale=3)
    for text in legend.get_texts():
        text.set_color(INK_PRIMARY)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved {out_path}")


def plot_linearity_vs_energy_by_match_count(df, title, out_path, y_max=None, only_categories=None):
    """Scatter of true-cluster linearity (x) vs true-cluster energy (y), one point
    per true cluster, colored by how many reco clusters it matched: 0 (unmatched),
    exactly 1, or more than 1 (fragmented on the reco side). Pass only_categories
    (a subset of {"zero", "one", "multiple"}) to draw just one category at a time -
    the y-axis range still reflects the full incoming df, so single-category plots
    stay comparable to the combined one."""
    if len(df) == 0:
        print(f"No rows to plot for {out_path}, skipping.")
        return

    fig, ax = plt.subplots(figsize=(8, 6), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)

    categories = [
        ("zero", COLOR_FLAGGED, "Matched to 0 reco clusters"),
        ("one", COLOR_BLACK, "Matched to 1 reco cluster"),
        ("multiple", COLOR_REGULAR, "Matched to >1 reco clusters"),
    ]
    if only_categories is not None:
        categories = [c for c in categories if c[0] in only_categories]
    for cat, color, label in categories:
        mask = df["match_category"] == cat
        ax.scatter(df.loc[mask, "linearity"], df.loc[mask, "energy"],
                   s=18, alpha=0.6, color=color, edgecolors="none", label=label)

    ax.axvline(LINEARITY_THRESHOLD, color=INK_MUTED, linestyle="--", linewidth=1)
    ax.set_xlim(-0.02, 1.02)
    if y_max is not None:
        ax.set_ylim(0, y_max)
    else:
        ax.set_ylim(0, df["energy"].max() * 1.05)
    ax.set_xlabel("PCA linearity", color=INK_PRIMARY)
    ax.set_ylabel("Cluster energy [MeV]", color=INK_PRIMARY)
    ax.set_title(title, color=INK_PRIMARY, fontsize=11)
    ax.tick_params(colors=INK_MUTED)
    for spine in ax.spines.values():
        spine.set_color(GRIDLINE)
    ax.grid(True, color=GRIDLINE, linewidth=0.8)
    ax.set_axisbelow(True)
    legend = ax.legend(frameon=False, loc="upper left", fontsize=15, markerscale=3)
    for text in legend.get_texts():
        text.set_color(INK_PRIMARY)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved {out_path}")


FLAGGED_METADATA_COLUMNS = [
    "file", "event", "true_cluster_id", "reco_cluster_id", "completeness", "linearity",
    "n_true_points", "true_energy", "n_reco_points", "reco_charge",
]


def write_flagged_metadata_txt(df, title, out_path):
    """Plain-text table of flagged true clusters (one row per true-to-reco match,
    unmatched clusters show blank reco columns)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        f.write(f"{title}\n")
        f.write(f"Flagged = linearity < {LINEARITY_THRESHOLD} and n_true_points >= {MIN_POINTS_FOR_CHECK}\n\n")
        if len(df) == 0:
            f.write("No flagged true clusters.\n")
        else:
            f.write(df[FLAGGED_METADATA_COLUMNS].to_string(index=False))
            f.write("\n")
    print(f"Saved {out_path}")


def write_summary_txt(start_time, end_time, elapsed, out_path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        f.write(f"Job started at  {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Job finished at {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total duration: {elapsed:.1f} s ({elapsed/60:.2f} min)\n")
    print(f"Saved {out_path}")


if __name__ == "__main__":
    main()
