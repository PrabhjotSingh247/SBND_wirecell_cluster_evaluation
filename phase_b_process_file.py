"""
Phase B per-file worker (see project plan): runs the Event-Level + File-Level plotting
pipeline for ONE file, so Evaluation_BeforeChargeLightMatching_BeforeBeamWindowCut_FromROOT.ipynb can dispatch one of these per
CPU core via concurrent.futures.ProcessPoolExecutor instead of processing files serially.

Profiling Phase B on a single file (8 events) showed its runtime is ~70% matplotlib
rendering (PNG encoding + layout - print_figure/savefig), not KDTree/pandas work - so
parallelizing across files (not individual plot calls) gives a near-linear speedup bounded
by CPU core count, without touching any drawing code. Job-Level plots stay serial in the
notebook itself since they need every file's results first (a real aggregation barrier),
but that's a small, fixed-size cost that doesn't scale with event count the way Event-Level
plotting does.

Each worker opens its own RootEventStore (uproot file handles aren't safely shareable
across process boundaries) and writes its own PNGs directly to disk (safe - different
files/directories, no shared state) but can't write into the single shared output ROOT
histogram file directly for the same reason, so ROOT-histogram writes are recorded as
plain dicts in `histogram_records` (kind "th1"/"th2"/"th1_counts" plus the save_th*() args)
for the caller to replay against the single shared output file after every worker returns.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless backend - required when rendering from a subprocess

import numpy as np

from root_reconstruction import RootEventStore
from completeness_purity_draw import (
    plot_completeness_heatmap, plot_purity_heatmap,
    DrawCompletenessVsTrueEnergyPerEvent, DrawCompletenessVsTrueEnergyPerFile,
    DrawClusterCompletenessVsTrueEnergyPerEvent, DrawClusterCompletenessVsTrueEnergyPerFile,
    DrawCompletenessVsTrueEnergy_MatchedPairs_PerEvent, DrawCompletenessVsTrueEnergy_MatchedPairs_PerFile,
    DrawPurityVsRecoChargePerEvent, DrawPurityVsRecoChargePerFile,
    DrawCompletenessVsPurity_MatchedPairs,
)
from DrawRecoTrueClusters import (
    DrawTrueRecoClustersXZ, DrawTrueRecoClustersYZ, DrawTrueRecoClustersXY,
    DrawTrueClusterWithMatchedReco, DrawLabels, DrawLabelPerFile,
    DrawTrueRecoMatchMultiplicity, DrawTrueClusterCategories,
    DrawPointsBeforeAfterDeadArea, DrawTrueClusterWithDeadArea,
)


def completeness_results_per_cluster_like(true_rows):
    """One row per true cluster - exact (matches what DrawCompletenessVsTrueEnergyPerEvent/
    PerFile/PerJob re-aggregate to internally anyway)."""
    results = []
    for r in true_rows:
        matched_ids = r.get("matched_reco_ids")
        reco_id = 8888 if matched_ids is None or len(matched_ids) == 0 else matched_ids[0]
        results.append({
            "event": r["event"], "true_cluster_id": r["true_cluster_id"], "reco_cluster_id": reco_id,
            "completeness_energy_weighted": r.get("total_completeness", 0),
            "total_true_cluster_energy": r.get("total_true_energy", 0),
        })
    return results


def _matched_ids(r):
    """r['matched_reco_ids'] is a numpy array once read back from ROOT - `or []` on it
    raises ValueError (ambiguous truth value), so check None explicitly instead."""
    v = r.get("matched_reco_ids")
    return [] if v is None else list(v)


def completeness_results_pairs_like(true_rows, matched_pairs):
    matched_true_ids = {p["true_cluster_id"] for p in matched_pairs}
    results = [{"true_cluster_id": p["true_cluster_id"], "reco_cluster_id": p["reco_cluster_id"],
                "completeness_energy_weighted": p["completeness_energy_weighted"]} for p in matched_pairs]
    for r in true_rows:
        if r["true_cluster_id"] not in matched_true_ids:
            results.append({"true_cluster_id": r["true_cluster_id"], "reco_cluster_id": 8888,
                             "completeness_energy_weighted": 0})
    return results


def purity_results_pairs_like(reco_rows, matched_pairs):
    matched_reco_ids = {p["reco_cluster_id"] for p in matched_pairs}
    results = [{"true_cluster_id": p["true_cluster_id"], "reco_cluster_id": p["reco_cluster_id"],
                "purity": p["purity"]} for p in matched_pairs]
    for r in reco_rows:
        if r["reco_cluster_id"] not in matched_reco_ids:
            results.append({"true_cluster_id": 8888, "reco_cluster_id": r["reco_cluster_id"], "purity": -0.1})
    return results


_DEADAREA_CACHE = {}


def load_deadarea_polygons(view, apa):
    """Dead-area polygons are static per-APA detector geometry, not event data - load fresh
    from disk exactly as apply_deadarea_cut_true does, same as the original notebook."""
    key = (view, apa)
    if key not in _DEADAREA_CACHE:
        deadarea_base = Path("Deadareas")
        sub = "2viewactive_2viewdead" if view == "2view" else "3viewactive_1viewdead"
        fname = "0-channel-deadarea-apa0-face0.json" if apa == "APA0" else "0-channel-deadarea-apa1-face0.json"
        with open(deadarea_base / sub / fname) as f:
            _DEADAREA_CACHE[key] = json.load(f)
    return _DEADAREA_CACHE[key]


def process_one_file(root_path, file_name, apa, view, file_output_dir, root_file_dir, target_event=None):
    """
    Runs Event-Level plotting for every event in `file_name`/`apa` (or just `target_event`
    if given), then this file's own File-Level summary plotting. Safe to run in its own
    process - opens an independent RootEventStore and only touches its own output
    directory, never the shared output ROOT histogram file.

    Returns a dict: file_true_rows/file_reco_rows/file_pair_metadata_list (for the caller's
    Job-Level aggregation), histogram_records (deferred ROOT-histogram writes for the
    caller to replay), and total_events_processed.
    """
    store = RootEventStore(root_path)
    file_output_dir = Path(file_output_dir)
    file_output_dir.mkdir(parents=True, exist_ok=True)

    file_true_rows, file_reco_rows, file_pair_metadata_list = [], [], []
    histogram_records = []
    total_events_processed = 0

    for evt in store.events_for_file(file_name, apa):
        if target_event is not None and evt != target_event:
            continue

        event_output_dir = file_output_dir / f"event_{evt:03d}"
        event_output_dir.mkdir(parents=True, exist_ok=True)
        PLOTDIR_EVT = event_output_dir
        root_event_dir = f"{root_file_dir}/event_{evt:03d}"

        completeness_dir = event_output_dir / "completeness"
        purity_dir = event_output_dir / "purity"
        completeness_dir.mkdir(parents=True, exist_ok=True)
        purity_dir.mkdir(parents=True, exist_ok=True)

        eff_vs_purity_incl_dir = event_output_dir / "true_reco_matched_pair_completeness_purity_including_unmatched_true_clusters"
        eff_vs_purity_excl_dir = event_output_dir / "true_reco_matched_pair_completeness_purity_excluding_unmatched_true_clusters"
        eff_vs_purity_incl_dir.mkdir(parents=True, exist_ok=True)
        eff_vs_purity_excl_dir.mkdir(parents=True, exist_ok=True)

        completeness_2d1d_imaging_dir = completeness_dir / "completeness_2d_1d_imaging_level"
        completeness_2d1d_clustering_dir = completeness_dir / "completeness_2d_1d_clusteringlevel"
        completeness_2d1d_clustering_pairs_only_dir = completeness_dir / "completeness_2d_1d_clusteringlevel_true_reco_pairs_only"
        completeness_2d1d_imaging_dir.mkdir(parents=True, exist_ok=True)
        completeness_2d1d_clustering_dir.mkdir(parents=True, exist_ok=True)
        completeness_2d1d_clustering_pairs_only_dir.mkdir(parents=True, exist_ok=True)

        clusters_true = store.clusters_true(file_name, evt, apa)
        clusters_reco = store.clusters_reco(file_name, evt, apa)
        if not clusters_true:
            continue

        true_rows = store.true_cluster_rows(file_name, evt, apa)
        reco_rows = store.reco_cluster_rows(file_name, evt, apa)
        pair_rows = store.pair_rows(file_name, evt, apa)
        cluster_category_results = store.cluster_category_results(file_name, evt, apa)

        file_true_rows.extend(true_rows)
        file_reco_rows.extend(reco_rows)
        file_pair_metadata_list.extend(pair_rows)

        # ---- true/reco spatial views + category + dead-area debug plots ----
        DrawTrueRecoClustersXZ(clusters_true, clusters_reco, evt, apa, PLOTDIR_EVT, file_name)
        DrawTrueRecoClustersYZ(clusters_true, clusters_reco, evt, apa, PLOTDIR_EVT, file_name)
        DrawTrueRecoClustersXY(clusters_true, clusters_reco, evt, apa, PLOTDIR_EVT, file_name)
        DrawLabels(clusters_true, evt, apa, PLOTDIR_EVT, file_name)
        DrawTrueClusterCategories(cluster_category_results, clusters_true, PLOTDIR_EVT, event=evt, apa=apa, file_name=file_name)

        before_counts, after_counts = store.deadarea_before_after_counts(file_name, evt, apa)
        DrawPointsBeforeAfterDeadArea(before_counts, after_counts, evt, apa, PLOTDIR_EVT, file_name)
        affected_ids = [cid for cid in before_counts if before_counts.get(cid) != after_counts.get(cid)]
        if affected_ids:
            deadarea_polygons = load_deadarea_polygons(view, apa)
            for cid in affected_ids:
                full_pts = store.pre_deadarea_points_for_cluster(file_name, evt, apa, cid)
                if full_pts is not None:
                    DrawTrueClusterWithDeadArea(full_pts, deadarea_polygons, cid, evt, apa, PLOTDIR_EVT, file_name)

        # ---- heatmaps (exact per-pair values) ----
        matched_pairs = store.matched_pairs_exact(file_name, evt, apa)
        plot_completeness_heatmap(completeness_results_pairs_like(true_rows, matched_pairs), evt, apa, completeness_dir, file_name)
        plot_purity_heatmap(purity_results_pairs_like(reco_rows, matched_pairs), evt, apa, purity_dir, file_name)

        # ---- true cluster with matched reco clusters (exact per-pair values) ----
        for matched_info in store.matched_info_list(file_name, evt, apa):
            DrawTrueClusterWithMatchedReco(matched_info, clusters_true, clusters_reco, completeness_dir, evt, apa, file_name)

        # ---- completeness vs true energy ----
        eff_like = completeness_results_per_cluster_like(true_rows)
        DrawCompletenessVsTrueEnergyPerEvent(eff_like, completeness_2d1d_imaging_dir, evt, apa, file_name, cluster_category_results=cluster_category_results)
        DrawClusterCompletenessVsTrueEnergyPerEvent(pair_rows, completeness_2d1d_clustering_dir, evt, apa, file_name, all_true_metadata_list=true_rows)
        DrawCompletenessVsTrueEnergy_MatchedPairs_PerEvent(pair_rows, completeness_2d1d_clustering_pairs_only_dir, evt, apa, file_name)

        # ---- purity vs reco charge ----
        DrawPurityVsRecoChargePerEvent(pair_rows, purity_dir, evt, apa, file_name)
        DrawCompletenessVsPurity_MatchedPairs(pair_rows, eff_vs_purity_incl_dir, f'Event {evt}', apa, file_name, all_true_metadata_list=true_rows)
        DrawCompletenessVsPurity_MatchedPairs(pair_rows, eff_vs_purity_excl_dir, f'Event {evt}', apa, file_name, all_true_metadata_list=None)

        DrawTrueRecoMatchMultiplicity(true_rows, event_output_dir, apa, f'Event {evt}', f'event_{evt}', file_name=file_name)

        # ---- mirrored ROOT histograms, deferred for the parent process to write ----
        energies_evt = np.array([r["total_true_energy"] for r in true_rows])
        effs_evt = np.array([r["total_completeness"] for r in true_rows])
        histogram_records.append({"kind": "th2", "dir": f"{root_event_dir}/completeness", "name": "completeness_vs_true_energy_2d",
                                   "x": energies_evt, "y": effs_evt, "xbins": 50, "ybins": 50})
        if pair_rows:
            charges_evt = np.array([r["total_reco_charge"] for r in pair_rows])
            purities_evt = np.array([r["purity"] for r in pair_rows])
            histogram_records.append({"kind": "th2", "dir": f"{root_event_dir}/purity", "name": "purity_vs_reco_charge_2d",
                                       "x": charges_evt, "y": purities_evt, "xbins": 50, "ybins": 50})
            histogram_records.append({"kind": "th2", "dir": f"{root_event_dir}/true_reco_matched_pair_completeness_purity",
                                       "name": "completeness_vs_purity",
                                       "x": np.array([r["completeness"] for r in pair_rows]), "y": purities_evt,
                                       "xbins": 50, "ybins": 50})

        total_events_processed += 1

    # ====================================================================
    # FILE-LEVEL AGGREGATION
    # ====================================================================
    if file_true_rows:
        agg_output_dir = file_output_dir / "file_summary"
        agg_output_dir.mkdir(parents=True, exist_ok=True)
        root_file_summary_dir = f"{root_file_dir}/file_summary"

        file_completeness_2d1d_imaging_dir = agg_output_dir / "completeness" / "completeness_2d_1d_imaging_level"
        file_completeness_2d1d_clustering_dir = agg_output_dir / "completeness" / "completeness_2d_1d_clusteringlevel"
        file_completeness_2d1d_clustering_pairs_only_dir = agg_output_dir / "completeness" / "completeness_2d_1d_clusteringlevel_true_reco_pairs_only"
        file_completeness_2d1d_imaging_dir.mkdir(parents=True, exist_ok=True)
        file_completeness_2d1d_clustering_dir.mkdir(parents=True, exist_ok=True)
        file_completeness_2d1d_clustering_pairs_only_dir.mkdir(parents=True, exist_ok=True)

        file_purity_summary_dir = agg_output_dir / "purity"
        file_purity_summary_dir.mkdir(parents=True, exist_ok=True)

        file_eff_vs_purity_incl_dir = agg_output_dir / "true_reco_matched_pair_completeness_purity_including_unmatched_true_clusters"
        file_eff_vs_purity_excl_dir = agg_output_dir / "true_reco_matched_pair_completeness_purity_excluding_unmatched_true_clusters"
        file_eff_vs_purity_incl_dir.mkdir(parents=True, exist_ok=True)
        file_eff_vs_purity_excl_dir.mkdir(parents=True, exist_ok=True)

        file_eff_like = completeness_results_per_cluster_like(file_true_rows)
        file_energies, file_effs = DrawCompletenessVsTrueEnergyPerFile(
            file_eff_like, file_completeness_2d1d_imaging_dir, apa, file_name, file_metadata_list=file_true_rows) or ([], [])
        DrawClusterCompletenessVsTrueEnergyPerFile(file_pair_metadata_list, file_completeness_2d1d_clustering_dir, apa, file_name, all_true_metadata_list=file_true_rows)
        DrawCompletenessVsTrueEnergy_MatchedPairs_PerFile(file_pair_metadata_list, file_completeness_2d1d_clustering_pairs_only_dir, apa, file_name)
        DrawPurityVsRecoChargePerFile(file_pair_metadata_list, file_purity_summary_dir, apa, file_name)
        DrawCompletenessVsPurity_MatchedPairs(file_pair_metadata_list, file_eff_vs_purity_incl_dir, 'File Level', apa, file_name, all_true_metadata_list=file_true_rows)
        DrawCompletenessVsPurity_MatchedPairs(file_pair_metadata_list, file_eff_vs_purity_excl_dir, 'File Level', apa, file_name, all_true_metadata_list=None)
        DrawLabelPerFile(file_true_rows, agg_output_dir, apa, file_name)
        DrawTrueRecoMatchMultiplicity(file_true_rows, agg_output_dir, apa, 'File Level', 'file', file_name=file_name)

        if file_energies is not None and len(file_energies):
            histogram_records.append({"kind": "th1", "dir": f"{root_file_summary_dir}/completeness",
                                       "name": "completeness_vs_true_energy_1d_file", "values": np.array(file_effs), "bins": 20})
        neutrino_n = sum(1 for r in file_true_rows if r["cluster_type"] == "neutrino")
        cosmic_n = sum(1 for r in file_true_rows if r["cluster_type"] == "cosmic")
        histogram_records.append({"kind": "th1_counts", "dir": root_file_summary_dir,
                                   "name": "true_clusters_by_type_file", "counts": [neutrino_n, cosmic_n]})

    return {
        "file_name": file_name,
        "file_true_rows": file_true_rows,
        "file_reco_rows": file_reco_rows,
        "file_pair_metadata_list": file_pair_metadata_list,
        "histogram_records": histogram_records,
        "total_events_processed": total_events_processed,
    }
