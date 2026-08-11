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
                                too sparse to clear the completeness neighbor threshold
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

SPLIT BY POPULATION. Every one of those outputs is written once per population,
at each level (see POPULATIONS below):

  <level>/                                                    all true neutrinos
  <level>/by_vertex_volume/in_volume/                         vertex in the box
  <level>/by_vertex_volume/out_volume/                        vertex outside it
  <level>/by_vertex_volume/in_volume/by_interaction_channel/  numu_CC, nue_CC, NC
                                                              (in-volume only)

Volume first, because the two fail differently: an out-of-volume interaction only
ever deposits the part of itself that leaked into the active volume, so "no reco
overlap" means something different there than for a vertex sitting in the middle
of the detector, and mixing them hides that. Then the in-volume neutrinos by
interaction channel, since those are the ones fully inside the detector -- a
failure there is a statement about reconstructing that channel rather than about
how much of the interaction happened to land inside.

Only the TRUE side is split. The reco set is never cut, so a category assignment
is identical in every copy (it IS the same row), and the selected-reco bar in the
top panel stays the whole beam-window reco population everywhere, since that is
what all of these neutrinos were matched against. There is deliberately no
reco-side version of this split: with no vertex reconstruction, a reco cluster has
no volume and no channel of its own.

Run directly: python investigate_unmatched_true_neutrinos.py
Output: multi_file_plots_charge_light_matching/unmatched_true_neutrino_investigation_{timestamp}/
"""
import numpy as np
from datetime import datetime
from pathlib import Path

from readfiles import read_charge_light_files_for_event, flatten_mc_tree
from selections import (
    GroupClustersByID, build_true_points_charge_light,
    reassign_cluster_ID_true_charge_light, reassign_cluster_ID_reco,
    apply_energy_cutoff, apply_wire_readout_sensitive_yz_plane_cut_true,
    apply_wire_readout_sensitive_yz_plane_cut_reco,
    apply_deadarea_cut_true_charge_light,
)
from completeness_purity_estimate import EvaluateCompleteness, EvaluatePurity
from clusterpairmatching import MatchTrueToReco1to1
from metadata import (
    build_cluster_flash_metadata, build_img_cluster_flash_metadata,
    categorize_unmatched_true_neutrinos, NEUTRINO_CLUSTER_ID_BASE,
    # The vertex-volume split: the vertex records give each interaction its
    # in/out-of-volume flag, build_neutrino_volume_map turns those into a
    # {(event, true cluster id) -> 'in'|'out'} lookup, and filter_records_by_label
    # selects one population's rows. The neutrino rows here carry the same
    # (event, true_cluster_id) key, so the same filter serves them unchanged.
    build_neutrino_vertex_records, build_neutrino_volume_map, build_neutrino_channel_map,
    filter_records_by_label, restrict_label_map,
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

radius_completeness        = 2
radius_purity_xz         = 2
radius_purity_yz         = 5
radius_purity_xy         = 5
min_recopoints_threshold = 5
min_cluster_energy       = 100
x_min, x_max = -250.0, 250.0
y_min, y_max = -200.0, 200.0
z_min, z_max = 0.15, 500.85

b_draw_event_level_plots = True   # per-event XZ/YZ/XY plots for events with >=1 unmatched true neutrino

# The populations every output is written for. 'all' keeps its outputs where they
# have always been (directly in the level's directory); the rest go in
# subdirectories, with the population named in the plot titles. Filenames are
# identical in all of them, so the same plot can be diffed between populations.
#
# Two axes, composed: WHERE the interaction happened (vertex in / out of the
# wire-readout sensitive box) and WHAT came out of it (numu CC / nue CC / NC, from
# metadata.classify_neutrino_interaction). The channel breakdown is done for the
# IN-VOLUME neutrinos: those are the ones fully inside the detector, so a failure
# there is a reconstruction statement about that channel rather than a statement
# about how much of the interaction happened to leak in.
#
# 'volume'/'channel' are the labels a row must carry to belong; None means that
# axis is not applied.
POPULATIONS = [
    {'key': 'all',        'volume': None, 'channel': None,
     'subdir': None,                                                        'label': None},
    {'key': 'in',         'volume': 'in',  'channel': None,
     'subdir': Path("by_vertex_volume/in_volume"),                          'label': 'vertex in volume'},
    {'key': 'out',        'volume': 'out', 'channel': None,
     'subdir': Path("by_vertex_volume/out_volume"),                         'label': 'vertex out of volume'},
    {'key': 'in_numu_CC', 'volume': 'in',  'channel': 'numu_CC',
     'subdir': Path("by_vertex_volume/in_volume/by_interaction_channel/numu_CC"),
     'label': 'vertex in volume, numu CC'},
    {'key': 'in_nue_CC',  'volume': 'in',  'channel': 'nue_CC',
     'subdir': Path("by_vertex_volume/in_volume/by_interaction_channel/nue_CC"),
     'label': 'vertex in volume, nue CC'},
    {'key': 'in_NC',      'volume': 'in',  'channel': 'NC',
     'subdir': Path("by_vertex_volume/in_volume/by_interaction_channel/NC"),
     'label': 'vertex in volume, NC'},
]


def population_rows(neutrino_rows, population, volume_map, channel_map):
    """
    The rows belonging to one population. Nothing is recategorized -- the rows
    were built once against the full reco set, this only selects which of them a
    given directory shows.
    """
    if population['channel'] is not None:
        # Channel labels restricted to this volume, so the two axes compose.
        composed = restrict_label_map(channel_map, volume_map, population['volume'])
        return filter_records_by_label(neutrino_rows, composed, population['channel'])
    if population['volume'] is not None:
        return filter_records_by_label(neutrino_rows, volume_map, population['volume'])
    return list(neutrino_rows)


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


def render_level_outputs(neutrino_rows, volume_map, channel_map, n_selected_reco, level_dir,
                         level_name, filename_prefix, file_name=None,
                         clusters_true=None, clusters_reco_all=None, event=None,
                         draw=True, always_write_breakdown=True):
    """
    Every output of one level (event, file or job), written once per vertex-volume
    population: all true neutrinos, then the in-volume and out-of-volume subsets.

    Nothing is recategorized -- the rows were built once against the full reco set
    and are only filtered here, so a neutrino's category is the same in whichever
    copy it appears in. n_selected_reco likewise stays the FULL beam-window reco
    count in every copy: that is the population all of these neutrinos were
    matched against, and scaling it per subset would invent a number the matching
    never used.

    Parameters:
    - neutrino_rows: categorize_unmatched_true_neutrinos() rows for this level
    - volume_map / channel_map: build_neutrino_volume_map() and
      build_neutrino_channel_map() output covering those rows
    - n_selected_reco: beam-window reco clusters at this level (top-panel bar)
    - level_dir: the level's output directory; 'all' writes here, the other two
      into subdirectories of it
    - level_name, filename_prefix, file_name: drawer conventions, unchanged
    - clusters_true / clusters_reco_all / event: event level only -- when given,
      the per-event XZ/YZ/XY spatial plot is drawn too
    - draw: False writes the text tables and skips the plots
    - always_write_breakdown: the breakdown chart is drawn even when nothing is
      unmatched (event level does this: "all matched" is a result worth seeing);
      the info table and spatial/flash plots still need >=1 unmatched row

    Returns {population key: number of unmatched rows in that population}.
    """
    unmatched_by_population = {}

    for population in POPULATIONS:
        pop_key = population['key']
        pop_rows = population_rows(neutrino_rows, population, volume_map, channel_map)
        unmatched_by_population[pop_key] = sum(1 for r in pop_rows if r['category'] != 'matched')

        # An empty subset means this level has no neutrino of that kind -- skip it
        # rather than create a directory of empty plots. The 'all' population is
        # never skipped: its directory is the level's own.
        if population['subdir'] is not None and not pop_rows:
            continue

        pop_dir = level_dir if population['subdir'] is None else level_dir / population['subdir']
        pop_level_name = level_name if not population['label'] else f"{level_name} ({population['label']})"

        if draw and (always_write_breakdown or unmatched_by_population[pop_key] > 0):
            DrawUnmatchedTrueNeutrinoBreakdown(pop_rows, n_selected_reco, pop_dir, APA_LABEL,
                                                pop_level_name, filename_prefix, file_name=file_name)

        if unmatched_by_population[pop_key] > 0:
            write_unmatched_true_neutrino_info(pop_rows, pop_dir)
            if draw:
                draw_unmatched_neutrino_flash_times(pop_rows, pop_dir, APA_LABEL,
                                                     pop_level_name, filename_prefix, file_name=file_name)
                if clusters_true is not None and event is not None:
                    # Full cluster dicts on purpose: the drawer indexes into them
                    # by the ids on the rows it was given.
                    DrawUnmatchedTrueNeutrinos(clusters_true, pop_rows, event, APA_LABEL, pop_dir,
                                                file_name=file_name, clusters_reco_all=clusters_reco_all)

    return unmatched_by_population


def process_event(input_dir, file_name, evt):
    """
    Run one event through the same selection + beam-window-cut pipeline as
    Evaluation_ChargeLightMatching_AfterBeamWindowCut.ipynb's cell 6, but keep
    the PRE-cut reco set alongside the post-cut one, then categorize every true
    neutrino cluster.

    Returns (clusters_true, clusters_reco, clusters_reco_all, neutrino_rows,
    vertex_records) or None if the event's files are missing.
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

    completeness_results = EvaluateCompleteness(clusters_true, clusters_reco, event_key, radius_completeness, min_recopoints_threshold)
    purity_results     = EvaluatePurity(clusters_true, clusters_reco, event_key, radius_purity_xz, radius_purity_yz, radius_purity_xy)
    matched_pairs      = MatchTrueToReco1to1(completeness_results, purity_results)

    neutrino_rows = categorize_unmatched_true_neutrinos(
        clusters_true, clusters_reco, clusters_reco_all, reco_provenance,
        clu_beam_window_ids, flash_times_by_real_id, matched_pairs,
        file_name, evt, apa=APA_LABEL, event_key=event_key,
        radius_completeness=radius_completeness, min_recopoints_threshold=min_recopoints_threshold)

    # --- Interaction vertices (mc.json), for the in/out-of-volume split ---
    # Same builder and same bounds as the evaluation notebook, so "in volume"
    # means exactly what it means there. The flag is copied onto each neutrino row
    # as well, so unmatched_true_neutrino_info.txt can show it per interaction
    # without the reader having to cross-reference another table.
    vertex_records = build_neutrino_vertex_records(
        flatten_mc_tree(result['mc']), clusters_true, file_name, evt, event_key,
        x_min=x_min, x_max=x_max, y_min=y_min, y_max=y_max, z_min=z_min, z_max=z_max)
    volume_by_cluster  = {r['cluster_id']: r['vertex_in_volume'] for r in vertex_records}
    channel_by_cluster = {r['cluster_id']: r['interaction_channel'] for r in vertex_records}
    for row in neutrino_rows:
        row['vertex_in_volume']    = volume_by_cluster.get(row['true_cluster_id'])
        row['interaction_channel'] = channel_by_cluster.get(row['true_cluster_id'])

    return clusters_true, clusters_reco, clusters_reco_all, neutrino_rows, vertex_records


def main():
    input_files = find_input_files()
    if not input_files:
        print(f"No input files found in {PARENT_DIR}")
        return

    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = OUTPUT_DIR / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    job_rows = []
    job_vertex_records = []
    job_selected_reco = 0
    events_processed = 0
    events_with_unmatched = 0

    for file_name in input_files:
        events = find_events(file_name)
        print(f"{file_name}: {len(events)} event(s) to process", flush=True)

        file_rows = []
        file_vertex_records = []
        file_selected_reco = 0
        file_output_dir = output_dir / file_name

        for evt in events:
            processed = process_event(PARENT_DIR / file_name, file_name, evt)
            if processed is None:
                continue
            clusters_true, clusters_reco, clusters_reco_all, neutrino_rows, vertex_records = processed

            file_rows.extend(neutrino_rows)
            job_rows.extend(neutrino_rows)
            file_vertex_records.extend(vertex_records)
            job_vertex_records.extend(vertex_records)
            file_selected_reco += len(clusters_reco)
            job_selected_reco  += len(clusters_reco)
            events_processed += 1

            n_unmatched = sum(1 for r in neutrino_rows if r['category'] != 'matched')
            event_volume_map = build_neutrino_volume_map(vertex_records)
            n_in  = sum(1 for r in neutrino_rows
                        if event_volume_map.get((r['event'], r['true_cluster_id'])) == 'in')
            print(f"  {file_name}_{evt}: {len(neutrino_rows)} true neutrino(s) "
                  f"({n_in} in volume, {len(neutrino_rows) - n_in} out), "
                  f"{len(clusters_reco)}/{len(clusters_reco_all)} reco in beam window, "
                  f"{n_unmatched} unmatched", flush=True)

            if n_unmatched > 0:
                events_with_unmatched += 1

            render_level_outputs(
                neutrino_rows, event_volume_map, build_neutrino_channel_map(vertex_records),
                len(clusters_reco),
                file_output_dir / f"event_{evt:03d}", "Event Level", file_name,
                file_name=file_name,
                clusters_true=clusters_true, clusters_reco_all=clusters_reco_all, event=evt,
                draw=b_draw_event_level_plots)

        if file_rows or file_selected_reco:
            render_level_outputs(
                file_rows, build_neutrino_volume_map(file_vertex_records),
                build_neutrino_channel_map(file_vertex_records), file_selected_reco,
                file_output_dir / "file_summary", "File Level", file_name, file_name=file_name)

    if job_rows or job_selected_reco:
        job_volume_map = build_neutrino_volume_map(job_vertex_records)
        render_level_outputs(job_rows, job_volume_map, build_neutrino_channel_map(job_vertex_records),
                             job_selected_reco, output_dir / "job_summary", "Job Level", "alljobs")

    categories = ['matched', 'reco_outside_beam_window', 'reco_no_flash_match', 'broken_or_sparse_reco',
                  'no_reco_overlap_x_shift', 'no_reco_overlap', 'unexplained']
    job_volume_map  = build_neutrino_volume_map(job_vertex_records)
    job_channel_map = build_neutrino_channel_map(job_vertex_records)
    rows_by_population = {p['key']: population_rows(job_rows, p, job_volume_map, job_channel_map)
                          for p in POPULATIONS}

    print(f"\n{'='*70}")
    print(f"Events processed: {events_processed} across {len(input_files)} file(s)")
    print(f"Events with >=1 unmatched true neutrino: {events_with_unmatched}")
    print(f"Total selected reco clusters (beam window, post cuts): {job_selected_reco}")
    print()
    # Same numbers as before, now with the two vertex-volume columns beside the
    # total. 'in' + 'out' can fall short of 'all' by any interaction with no
    # volume flag (no vertex in mc.json) -- none in the current dataset.
    columns = [(p['key'], p['label'] or 'all') for p in POPULATIONS]
    print(f"{'category':<26}" + "".join(f"{name:>30}" for _, name in columns))
    print(f"{'true neutrino clusters':<26}"
          + "".join(f"{len(rows_by_population[key]):>30}" for key, _ in columns))
    for cat in categories:
        print(f"  {cat + ':':<24}"
              + "".join(f"{sum(1 for r in rows_by_population[key] if r['category'] == cat):>30}"
                        for key, _ in columns))
    print(f"\nOutput written to: {output_dir}")
    for population in POPULATIONS:
        where = "<level>/" if population['subdir'] is None else f"<level>/{population['subdir']}/"
        print(f"  {(population['label'] or 'all true neutrinos'):<28}: {where}")


if __name__ == "__main__":
    main()
