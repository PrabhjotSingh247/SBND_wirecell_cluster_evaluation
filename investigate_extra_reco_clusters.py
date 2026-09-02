"""
Standalone diagnostic script (not part of the main notebook pipeline): explains why
Evaluation_ChargeLightMatching_AfterBeamWindowCut.ipynb reports more reco clusters
surviving the beam-window cut than true neutrino clusters (e.g. 88 reco vs 72 true
neutrinos, job-wide). Every reco cluster is categorized via
metadata.categorize_extra_reco_clusters() into:
  - matched_winner        : the MatchTrueToReco1to1 winner for a true neutrino cluster (not "extra")
  - fragment_of_neutrino  : overlaps a neutrino true cluster but lost the 1-to-1 slot to another reco
  - matched_cosmic_only   : overlaps only cosmic true cluster(s)
  - no_true_overlap       : zero spatial overlap with anything (candidate for a charge-light
                             X-mis-assignment, diagnosed via nearest-true-cluster offset)

Writes event/file/job-level extra_reco_info.txt tables (writeinformation.write_extra_reco_info)
and event/file/job-level category-breakdown bar charts (DrawRecoTrueClusters.
DrawExtraRecoCategoryBreakdown -- true neutrinos vs. selected reco left, category split right),
plus per-event XZ/YZ/XY spatial plots (DrawRecoTrueClusters.DrawExtraRecoClusters) for every
event that has at least one non-matched_winner reco cluster.

Run directly: python investigate_extra_reco_clusters.py
Output: multi_file_plots_charge_light_matching/extra_reco_investigation_{timestamp}/
"""
import numpy as np
from datetime import datetime
from pathlib import Path

from readfiles import read_charge_light_files_for_event
from selections import (
    GroupClustersByID, build_true_points_charge_light,
    reassign_cluster_ID_true_charge_light, reassign_cluster_ID_reco,
    apply_energy_cutoff, apply_true_pointwise_energy_cutoff, apply_wire_readout_sensitive_yz_plane_cut_true,
    Fiducial_X_MIN, Fiducial_X_MAX, Fiducial_Y_MIN,
    Fiducial_Y_MAX, Fiducial_Z_MIN, Fiducial_Z_MAX,
    apply_wire_readout_sensitive_yz_plane_cut_reco,
    apply_deadarea_cut_true_charge_light,
)
from completeness_purity_estimate import EvaluateCompleteness, EvaluatePurity
from clusterpairmatching import MatchTrueToReco1to1
from metadata import (
    build_cluster_flash_metadata, build_img_cluster_flash_metadata, categorize_extra_reco_clusters,
    NEUTRINO_CLUSTER_ID_BASE,
)
from writeinformation import write_extra_reco_info
from DrawRecoTrueClusters import DrawExtraRecoClusters, DrawExtraRecoCategoryBreakdown
from DrawRecoTrueFlashes import BEAM_WINDOW_MIN_US, BEAM_WINDOW_MAX_US

# ============================================================================
# CONFIG -- same selection/beam-window-cut settings as
# Evaluation_ChargeLightMatching_AfterBeamWindowCut.ipynb (cells 4 and 6), so
# counts here are directly comparable to that notebook's job summary.
# ============================================================================
PARENT_DIR  = Path("Haiwang_files_charge_light_matching_MCP2025C_Fall_production_after_deadareacut")
TARGET_FILE = "all"   # "all" for every file subdirectory with a data/ folder, or "file0"/"file1"/...
EVENT_LOW   = None    # None = auto-detect from each file's data/ (all events present)
EVENT_HIGH  = None    # exclusive; None = auto-detect
OUTPUT_DIR  = Path("multi_file_plots_charge_light_matching/extra_reco_investigation")
APA_LABEL   = "Combined"

radius_completeness        = 2
radius_purity_xz         = 2
radius_purity_yz         = 5
radius_purity_xy         = 5
min_recopoints_threshold = 5
min_cluster_energy       = 100
min_true_point_energy    = 0.02   # MeV per true POINT -- see selections.py
x_min, x_max = Fiducial_X_MIN, Fiducial_X_MAX
y_min, y_max = Fiducial_Y_MIN, Fiducial_Y_MAX
z_min, z_max = Fiducial_Z_MIN, Fiducial_Z_MAX

b_draw_event_level_plots = True   # per-event XZ/YZ/XY plots for events with >=1 extra reco cluster


def find_input_files():
    """Same discovery rule as near_miss_investigation.py's find_input_files -- kept
    local since this script is standalone by design."""
    if TARGET_FILE != "all":
        return [TARGET_FILE]
    return [d.name for d in sorted(PARENT_DIR.iterdir())
            if d.is_dir() and (d / "data").is_dir()]


def find_events(file_name):
    """Same as near_miss_investigation.py's find_events -- event numbering is
    per-file, so a fixed range can't serve every file."""
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


def process_event(input_dir, file_name, evt):
    """
    Run one event through the same selection + beam-window-cut pipeline as
    Evaluation_ChargeLightMatching_AfterBeamWindowCut.ipynb's cell 6, then
    categorize every surviving reco cluster.

    Returns (clusters_true, clusters_reco, categorized_rows) or None if the
    event's files are missing.
    """
    result = read_charge_light_files_for_event(input_dir, evt)
    if result is None:
        return None

    event_key = f"{file_name}_{evt}"

    # --- True side (clustering-level: sed-smear, paired with clustering-global) ---
    x_true, y_true, z_true, id_true, q_true, real_id_true, e_true, nu_idx_true = result['true_clustering']
    true_points = build_true_points_charge_light(x_true, y_true, z_true, real_id_true, q_true,
                                                  energy=e_true, nu_idx=nu_idx_true)
    true_points = reassign_cluster_ID_true_charge_light(true_points)
    # POINT-wise first, so the cluster total the cluster cut tests is the
    # total of the points that survive. 0.01 MeV -- see selections.py.
    true_points = apply_true_pointwise_energy_cutoff(true_points, min_true_point_energy)
    true_points = apply_energy_cutoff(true_points, min_cluster_energy)
    true_points = apply_wire_readout_sensitive_yz_plane_cut_true(true_points)
    true_points = apply_deadarea_cut_true_charge_light(true_points, output_dir=None, event=evt, file_name=file_name)
    clusters_true = GroupClustersByID(true_points) if len(true_points) else {}

    # --- Reco side: beam-window cut on clustering-global, mirroring the notebook ---
    cluster_flash_records = build_cluster_flash_metadata(result['op'], file_name, evt, APA_LABEL, event_key=event_key)
    img_cluster_flash_records = build_img_cluster_flash_metadata(
        result['reco'], result['clustering'], cluster_flash_records, file_name, evt, APA_LABEL, event_key=event_key)
    clu_beam_window_ids = {float(r['clustering_cluster_id']) for r in img_cluster_flash_records
                            if BEAM_WINDOW_MIN_US <= r['flash_time'] <= BEAM_WINDOW_MAX_US}

    x_clu, y_clu, z_clu, id_clu, q_clu, real_id_clu = result['clustering']
    predicted_points = np.column_stack((x_clu, y_clu, z_clu, real_id_clu, q_clu))
    beam_ids_array = np.fromiter(clu_beam_window_ids, dtype=float, count=len(clu_beam_window_ids))
    predicted_points = predicted_points[np.isin(predicted_points[:, 3], beam_ids_array)]
    predicted_points = apply_wire_readout_sensitive_yz_plane_cut_reco(predicted_points)

    if len(predicted_points) == 0:
        clusters_reco = {}
    else:
        predicted_points = reassign_cluster_ID_reco(predicted_points)
        clusters_reco    = GroupClustersByID(predicted_points)

    completeness_results = EvaluateCompleteness(clusters_true, clusters_reco, event_key, radius_completeness, min_recopoints_threshold)
    purity_results      = EvaluatePurity(clusters_true, clusters_reco, event_key, radius_purity_xz, radius_purity_yz, radius_purity_xy)
    matched_pairs        = MatchTrueToReco1to1(completeness_results, purity_results)

    categorized_rows = categorize_extra_reco_clusters(clusters_true, clusters_reco, purity_results, matched_pairs,
                                                        file_name, evt, apa=APA_LABEL, event_key=event_key)

    return clusters_true, clusters_reco, categorized_rows


def main():
    input_files = find_input_files()
    if not input_files:
        print(f"No input files found in {PARENT_DIR}")
        return

    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = OUTPUT_DIR / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    job_rows = []
    job_true_neutrinos = 0
    events_processed = 0
    events_with_extra = 0

    for file_name in input_files:
        events = find_events(file_name)
        print(f"{file_name}: {len(events)} event(s) to process", flush=True)

        file_rows = []
        file_true_neutrinos = 0
        file_output_dir = output_dir / file_name

        for evt in events:
            processed = process_event(PARENT_DIR / file_name, file_name, evt)
            if processed is None:
                continue
            clusters_true, clusters_reco, categorized_rows = processed

            n_true_neutrinos = sum(1 for cid in clusters_true if cid >= NEUTRINO_CLUSTER_ID_BASE)

            file_rows.extend(categorized_rows)
            job_rows.extend(categorized_rows)
            file_true_neutrinos += n_true_neutrinos
            job_true_neutrinos  += n_true_neutrinos
            events_processed += 1

            n_extra = sum(1 for r in categorized_rows if r['category'] != 'matched_winner')
            print(f"  {file_name}_{evt}: {len(clusters_true)} true ({n_true_neutrinos} neutrino), "
                  f"{len(clusters_reco)} reco, {n_extra} extra", flush=True)

            event_output_dir = file_output_dir / f"event_{evt:03d}"
            if b_draw_event_level_plots:
                DrawExtraRecoCategoryBreakdown(categorized_rows, n_true_neutrinos, event_output_dir, APA_LABEL,
                                                "Event Level", file_name, file_name=file_name)

            if n_extra > 0:
                events_with_extra += 1
                write_extra_reco_info(categorized_rows, event_output_dir)
                if b_draw_event_level_plots:
                    DrawExtraRecoClusters(clusters_reco, categorized_rows, evt, APA_LABEL,
                                           event_output_dir, file_name=file_name)

        if file_rows or file_true_neutrinos:
            file_summary_dir = file_output_dir / "file_summary"
            write_extra_reco_info(file_rows, file_summary_dir)
            DrawExtraRecoCategoryBreakdown(file_rows, file_true_neutrinos, file_summary_dir, APA_LABEL,
                                            "File Level", file_name, file_name=file_name)

    if job_rows or job_true_neutrinos:
        job_summary_dir = output_dir / "job_summary"
        write_extra_reco_info(job_rows, job_summary_dir)
        DrawExtraRecoCategoryBreakdown(job_rows, job_true_neutrinos, job_summary_dir, APA_LABEL, "Job Level", "alljobs")

    n_winner   = sum(1 for r in job_rows if r['category'] == 'matched_winner')
    n_fragment = sum(1 for r in job_rows if r['category'] == 'fragment_of_neutrino')
    n_cosmic   = sum(1 for r in job_rows if r['category'] == 'matched_cosmic_only')
    n_noover   = sum(1 for r in job_rows if r['category'] == 'no_true_overlap')

    print(f"\n{'='*70}")
    print(f"Events processed: {events_processed} across {len(input_files)} file(s)")
    print(f"Events with >=1 extra reco cluster: {events_with_extra}")
    print(f"Total reco clusters (beam window, post cuts): {len(job_rows)}")
    print(f"  matched_winner:       {n_winner}")
    print(f"  fragment_of_neutrino: {n_fragment}")
    print(f"  matched_cosmic_only:  {n_cosmic}")
    print(f"  no_true_overlap:      {n_noover}")
    print(f"Output written to: {output_dir}")


if __name__ == "__main__":
    main()
