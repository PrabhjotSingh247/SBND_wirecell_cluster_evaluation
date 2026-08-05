"""
Standalone diagnostic script (not part of the main notebook pipeline), and the
true-side mirror of investigate_extra_reco_clusters.py: that one explains why
Evaluation_ChargeLightMatching_AfterBeamWindowCut.ipynb reports MORE selected
reco clusters than true neutrinos (88 vs 72), this one explains why FEWER true
neutrinos than that find a reco match at all -- job-wide only 61 of the 72 true
neutrinos form a 1-to-1 pair, so 11 are unaccounted for.

Every true neutrino cluster is categorized via
metadata.categorize_unmatched_true_neutrinos() into:
  - matched                  : found its MatchTrueToReco1to1 reco partner (not a failure)
  - reco_outside_beam_window : a PRE-cut reco cluster overlaps it well enough to have
                                matched, but the beam-window cut removed it -- its
                                charge-light flash sits outside the window (the flash
                                offset separates "neutrino just outside the spill" from
                                "charge-light handed it a cosmic's flash")
  - reco_no_flash_match      : same, but charge-light matching attached NO flash at all,
                                so the beam-window filter dropped it for having no time
  - broken_or_sparse_reco    : reco charge DOES sit on the neutrino, but split into pieces
                                too sparse to clear the efficiency neighbor threshold
                                (the "highly scattered / broken neutrino" case)
  - no_reco_overlap          : not one reco point lands on it; nearest-reco offset
                                (dx-dominated => X-mis-assignment candidate) is reported

The diagnosis works by re-running the overlap test against the FULL
pre-beam-window-cut reco set, so each failure is attributed to the stage that
actually dropped it. Writes event/file/job-level unmatched_true_neutrino_info.txt
tables (writeinformation.write_unmatched_true_neutrino_info) and event/file/job-level
bar charts (DrawRecoTrueClusters.DrawUnmatchedTrueNeutrinoBreakdown -- true
neutrinos vs. selected reco vs. pairs on top, matched vs. not matched in the
middle, reasons on the bottom), plus per-event XZ/YZ/XY spatial plots
(DrawRecoTrueClusters.DrawUnmatchedTrueNeutrinos, cluster IDs in the legend) for
every event with at least one unmatched true neutrino.

Run directly: python investigate_unmatched_true_neutrinos.py
Output: multi_file_plots_charge_light_matching/unmatched_true_neutrino_investigation_{timestamp}/
"""
import numpy as np
from datetime import datetime
from pathlib import Path

from readfiles import read_charge_light_files_for_event
from selections import (
    GroupClustersByID, build_true_points_charge_light,
    reassign_cluster_ID_true_charge_light, reassign_cluster_ID_reco,
    apply_energy_cutoff, apply_wire_readout_sensitive_yz_plane_cut_true,
    apply_wire_readout_sensitive_yz_plane_cut_reco,
    apply_deadarea_cut_true_charge_light,
)
from efficiency_purity_estimate import EvaluateEfficiency, EvaluatePurity
from clusterpairmatching import MatchTrueToReco1to1
from metadata import (
    build_cluster_flash_metadata, build_img_cluster_flash_metadata,
    categorize_unmatched_true_neutrinos, NEUTRINO_CLUSTER_ID_BASE,
)
from writeinformation import write_unmatched_true_neutrino_info
from DrawRecoTrueClusters import DrawUnmatchedTrueNeutrinos, DrawUnmatchedTrueNeutrinoBreakdown
from DrawRecoTrueFlashes import (BEAM_WINDOW_MIN_US, BEAM_WINDOW_MAX_US,
                                  draw_unmatched_neutrino_flash_times)

# ============================================================================
# CONFIG -- same selection/beam-window-cut settings as
# Evaluation_ChargeLightMatching_AfterBeamWindowCut.ipynb (cells 4 and 6) and as
# investigate_extra_reco_clusters.py, so counts here are directly comparable to
# both that notebook's job summary and the extra-reco investigation.
# ============================================================================
PARENT_DIR  = Path("Haiwang_files_charge_light_matching_MCP2025C_Fall_production_after_deadareacut")
TARGET_FILE = "all"   # "all" for every file subdirectory with a data/ folder, or "file0"/"file1"/...
EVENT_LOW   = None    # None = auto-detect from each file's data/ (all events present)
EVENT_HIGH  = None    # exclusive; None = auto-detect
OUTPUT_DIR  = Path("multi_file_plots_charge_light_matching/unmatched_true_neutrino_investigation")
APA_LABEL   = "Combined"

radius_efficiency        = 2
radius_purity_xz         = 2
radius_purity_yz         = 5
radius_purity_xy         = 5
min_recopoints_threshold = 5
min_cluster_energy       = 100
x_min, x_max = -250.0, 250.0
y_min, y_max = -200.0, 200.0
z_min, z_max = 0.15, 500.85

b_draw_event_level_plots = True   # per-event XZ/YZ/XY plots for events with >=1 unmatched true neutrino


def find_input_files():
    """Same discovery rule as investigate_extra_reco_clusters.py's find_input_files --
    kept local since this script is standalone by design."""
    if TARGET_FILE != "all":
        return [TARGET_FILE]
    return [d.name for d in sorted(PARENT_DIR.iterdir())
            if d.is_dir() and (d / "data").is_dir()]


def find_events(file_name):
    """Same as investigate_extra_reco_clusters.py's find_events -- event numbering
    is per-file, so a fixed range can't serve every file."""
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


def group_reco_with_provenance(predicted_points):
    """
    reassign_cluster_ID_reco() + GroupClustersByID() in one pass, additionally
    returning where each grouped cluster came from.

    Needed because this investigation has to compare the PRE- and POST-beam-window-cut
    reco sets cluster by cluster, and reassign_cluster_ID_reco replaces the raw
    real_cluster_id with the cluster's rounded mean X -- which discards exactly
    the ID the beam-window cut and the flash records are keyed on. The grouping
    itself is unchanged from the notebook's path: the beam-window cut removes
    WHOLE clusters (it filters on real_cluster_id), so a surviving cluster
    contains the same points, and therefore gets the same mean-X ID, whether the
    cut is applied before or after this grouping.

    Args:
        predicted_points: Nx5 array [x, y, z, real_cluster_id, q], already
            YZ-plane-cut

    Returns:
        (clusters, provenance) -- clusters is {mean_x_id: [point, ...]} exactly as
        GroupClustersByID would return it, provenance is {mean_x_id: [real_cluster_id, ...]}
        (more than one only in the rare case of two raw clusters whose mean X
        agrees to 3 decimals, which the notebook's path would also merge).
    """
    by_real_id = {}
    for point in predicted_points:
        by_real_id.setdefault(point[3], []).append(point)

    clusters, provenance = {}, {}
    for real_id, points in by_real_id.items():
        points = np.array(points)
        new_id = round(float(np.mean(points[:, 0])), 3)
        points[:, 3] = new_id
        clusters.setdefault(new_id, []).extend(list(points))
        provenance.setdefault(new_id, []).append(real_id)
    return clusters, provenance


def process_event(input_dir, file_name, evt):
    """
    Run one event through the same selection + beam-window-cut pipeline as
    Evaluation_ChargeLightMatching_AfterBeamWindowCut.ipynb's cell 6, but keep
    the PRE-cut reco set alongside the post-cut one, then categorize every true
    neutrino cluster.

    Returns (clusters_true, clusters_reco, clusters_reco_all, neutrino_rows) or
    None if the event's files are missing.
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
    true_points = apply_energy_cutoff(true_points, min_cluster_energy)
    true_points = apply_wire_readout_sensitive_yz_plane_cut_true(true_points, x_min, x_max, y_min, y_max, z_min, z_max)
    true_points = apply_deadarea_cut_true_charge_light(true_points, output_dir=None, event=evt, file_name=file_name)
    clusters_true = GroupClustersByID(true_points) if len(true_points) else {}

    # --- Reco side: flash association first, so the beam-window cut can be
    # applied as a SELECTION over the full set rather than as a filter that
    # throws the rejected clusters away -- those rejects are the evidence this
    # investigation needs.
    cluster_flash_records = build_cluster_flash_metadata(result['op'], file_name, evt, APA_LABEL, event_key=event_key)
    img_cluster_flash_records = build_img_cluster_flash_metadata(
        result['reco'], result['clustering'], cluster_flash_records, file_name, evt, APA_LABEL, event_key=event_key)
    clu_beam_window_ids = {float(r['clustering_cluster_id']) for r in img_cluster_flash_records
                            if BEAM_WINDOW_MIN_US <= r['flash_time'] <= BEAM_WINDOW_MAX_US}
    flash_times_by_real_id = {}
    for r in img_cluster_flash_records:
        flash_times_by_real_id.setdefault(float(r['clustering_cluster_id']), []).append(r['flash_time'])

    x_clu, y_clu, z_clu, id_clu, q_clu, real_id_clu = result['clustering']
    predicted_points = np.column_stack((x_clu, y_clu, z_clu, real_id_clu, q_clu))
    predicted_points = apply_wire_readout_sensitive_yz_plane_cut_reco(predicted_points, x_min, x_max, y_min, y_max, z_min, z_max)

    if len(predicted_points) == 0:
        clusters_reco_all, reco_provenance, clusters_reco = {}, {}, {}
    else:
        clusters_reco_all, reco_provenance = group_reco_with_provenance(predicted_points)
        clusters_reco = {cid: points for cid, points in clusters_reco_all.items()
                          if any(rid in clu_beam_window_ids for rid in reco_provenance[cid])}

    efficiency_results = EvaluateEfficiency(clusters_true, clusters_reco, event_key, radius_efficiency, min_recopoints_threshold)
    purity_results     = EvaluatePurity(clusters_true, clusters_reco, event_key, radius_purity_xz, radius_purity_yz, radius_purity_xy)
    matched_pairs      = MatchTrueToReco1to1(efficiency_results, purity_results)

    neutrino_rows = categorize_unmatched_true_neutrinos(
        clusters_true, clusters_reco, clusters_reco_all, reco_provenance,
        clu_beam_window_ids, flash_times_by_real_id, matched_pairs,
        file_name, evt, apa=APA_LABEL, event_key=event_key,
        radius_efficiency=radius_efficiency, min_recopoints_threshold=min_recopoints_threshold)

    return clusters_true, clusters_reco, clusters_reco_all, neutrino_rows


def main():
    input_files = find_input_files()
    if not input_files:
        print(f"No input files found in {PARENT_DIR}")
        return

    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = OUTPUT_DIR / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    job_rows = []
    job_selected_reco = 0
    events_processed = 0
    events_with_unmatched = 0

    for file_name in input_files:
        events = find_events(file_name)
        print(f"{file_name}: {len(events)} event(s) to process", flush=True)

        file_rows = []
        file_selected_reco = 0
        file_output_dir = output_dir / file_name

        for evt in events:
            processed = process_event(PARENT_DIR / file_name, file_name, evt)
            if processed is None:
                continue
            clusters_true, clusters_reco, clusters_reco_all, neutrino_rows = processed

            file_rows.extend(neutrino_rows)
            job_rows.extend(neutrino_rows)
            file_selected_reco += len(clusters_reco)
            job_selected_reco  += len(clusters_reco)
            events_processed += 1

            n_unmatched = sum(1 for r in neutrino_rows if r['category'] != 'matched')
            print(f"  {file_name}_{evt}: {len(neutrino_rows)} true neutrino(s), "
                  f"{len(clusters_reco)}/{len(clusters_reco_all)} reco in beam window, "
                  f"{n_unmatched} unmatched", flush=True)

            event_output_dir = file_output_dir / f"event_{evt:03d}"
            if b_draw_event_level_plots:
                DrawUnmatchedTrueNeutrinoBreakdown(neutrino_rows, len(clusters_reco), event_output_dir, APA_LABEL,
                                                    "Event Level", file_name, file_name=file_name)

            if n_unmatched > 0:
                events_with_unmatched += 1
                write_unmatched_true_neutrino_info(neutrino_rows, event_output_dir)
                if b_draw_event_level_plots:
                    DrawUnmatchedTrueNeutrinos(clusters_true, neutrino_rows, evt, APA_LABEL, event_output_dir,
                                                file_name=file_name, clusters_reco_all=clusters_reco_all)
                    draw_unmatched_neutrino_flash_times(neutrino_rows, event_output_dir, APA_LABEL,
                                                         "Event Level", file_name, file_name=file_name)

        if file_rows or file_selected_reco:
            file_summary_dir = file_output_dir / "file_summary"
            write_unmatched_true_neutrino_info(file_rows, file_summary_dir)
            DrawUnmatchedTrueNeutrinoBreakdown(file_rows, file_selected_reco, file_summary_dir, APA_LABEL,
                                                "File Level", file_name, file_name=file_name)
            draw_unmatched_neutrino_flash_times(file_rows, file_summary_dir, APA_LABEL,
                                                 "File Level", file_name, file_name=file_name)

    if job_rows or job_selected_reco:
        job_summary_dir = output_dir / "job_summary"
        write_unmatched_true_neutrino_info(job_rows, job_summary_dir)
        DrawUnmatchedTrueNeutrinoBreakdown(job_rows, job_selected_reco, job_summary_dir, APA_LABEL, "Job Level", "alljobs")
        draw_unmatched_neutrino_flash_times(job_rows, job_summary_dir, APA_LABEL, "Job Level", "alljobs")

    n_matched = sum(1 for r in job_rows if r['category'] == 'matched')
    categories = ['reco_outside_beam_window', 'reco_no_flash_match', 'broken_or_sparse_reco',
                  'no_reco_overlap_x_shift', 'no_reco_overlap', 'unexplained']

    print(f"\n{'='*70}")
    print(f"Events processed: {events_processed} across {len(input_files)} file(s)")
    print(f"Events with >=1 unmatched true neutrino: {events_with_unmatched}")
    print(f"Total true neutrino clusters: {len(job_rows)}")
    print(f"Total selected reco clusters (beam window, post cuts): {job_selected_reco}")
    print(f"  matched:                  {n_matched}")
    for cat in categories:
        print(f"  {cat + ':':<26}{sum(1 for r in job_rows if r['category'] == cat)}")
    print(f"Output written to: {output_dir}")


if __name__ == "__main__":
    main()
