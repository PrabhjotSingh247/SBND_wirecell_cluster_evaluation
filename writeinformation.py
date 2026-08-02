"""
Functions that WRITE human-readable information files (the .txt tables that sit
next to the plots). Kept separate from metadata.py, which builds the in-memory
records: metadata.py answers "what do we know about this cluster/interaction",
this module answers "how is that written to disk for a person to read".

Every writer here is level-agnostic -- pass one event's records for an
event-level file or a whole job's for the aggregated one -- and returns the Path
it wrote, or None when there was nothing to write.
"""
from pathlib import Path

def write_true_cluster_info(cluster_type_records, output_dir, filename="true_cluster_info.txt"):
    """
    Write true_cluster_info.txt: one row per event listing how many neutrinos
    it has.

    Level-agnostic -- pass ONE event's records for the event-level copy, or a
    whole file's/job's for the aggregated copy. The format is identical at
    every level (one row per distinct 'event' key found in the records), which
    is the point of having a single writer: the event-level file is a slice of
    the job-level one, byte for byte.

    reassign_cluster_ID_true_charge_light keeps each neutrino interaction as
    its own true cluster (99990+nu_idx), so counting neutrino clusters per
    event IS counting neutrinos per event -- no need to print nu_idx_values or
    repeat a row per interaction.

    There is no beam-window column: beam-window membership is a RECO-side
    quantity only (see build_true_cluster_type_records for why it cannot be
    stated for a true cluster, and write_reco_cluster_info for the reco-side
    counts).

    Parameters:
    - cluster_type_records: List of dicts from build_true_cluster_type_records(),
        each with 'event', 'is_neutrino'
    - output_dir: Directory to write into (created if missing)
    - filename: Output file name

    Returns:
        Path written, or None if there was nothing to write
    """
    if not cluster_type_records:
        return None

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / filename

    neutrino_counts_by_event = {}
    for r in cluster_type_records:
        if r['is_neutrino']:
            neutrino_counts_by_event[r['event']] = neutrino_counts_by_event.get(r['event'], 0) + 1

    with open(out_path, "w") as f:
        f.write(f"{'event':<20} {'num_neutrinos':>14}\n")
        for event_key in sorted(neutrino_counts_by_event):
            f.write(f"{event_key:<20} {neutrino_counts_by_event[event_key]:>14}\n")

        multi_neutrino_events = sorted((k, v) for k, v in neutrino_counts_by_event.items() if v > 1)
        f.write(f"\n{'='*60}\n")
        f.write(f"Events with more than one neutrino: {len(multi_neutrino_events)}\n")
        for event_key, count in multi_neutrino_events:
            f.write(f"  {event_key}: {count} neutrinos\n")

    return out_path

def write_reco_cluster_info(reco_beam_window_records, output_dir, filename="reco_cluster_info.txt"):
    """
    Write reco_cluster_info.txt: one row per event listing how many DISTINCT
    clustering-global clusters have a beam-window-matched flash.

    Level-agnostic, same as write_true_cluster_info above -- pass one event's
    record for the event-level copy, or the whole job's list for the
    aggregated one.

    This is the RECO-side proxy for "multiple neutrino-like activity in the
    beam spill" -- grouped by reco cluster + matched flash timing, NOT by true
    nu_idx (that's write_true_cluster_info's num_neutrinos column, which is
    ground truth). Beam-window membership is stated ONLY here, on the reco
    side, where the flash time is measured rather than inferred.

    Parameters:
    - reco_beam_window_records: List of dicts, each with 'file_name', 'event',
        'event_num', 'num_clusters_in_beam_window', 'cluster_ids'
    - output_dir: Directory to write into (created if missing)
    - filename: Output file name

    Returns:
        Path written, or None if there was nothing to write
    """
    if not reco_beam_window_records:
        return None

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / filename

    with open(out_path, "w") as f:
        f.write(f"{'event':<20} {'num_clusters_in_beam_window':>28} {'cluster_ids':<40}\n")
        for r in sorted(reco_beam_window_records, key=lambda r: (r['file_name'], r['event_num'])):
            ids_str = ",".join(f"{c:.0f}" for c in r['cluster_ids']) if r['cluster_ids'] else "-"
            f.write(f"{r['event']:<20} {r['num_clusters_in_beam_window']:>28} {ids_str:<40}\n")

        multi_cluster_events = sorted(
            (r['event'], r['num_clusters_in_beam_window'], r['cluster_ids'])
            for r in reco_beam_window_records if r['num_clusters_in_beam_window'] > 1
        )
        f.write(f"\n{'='*60}\n")
        f.write(f"Events with 2+ clusters in beam window: {len(multi_cluster_events)}\n")
        for event_key, count, cluster_ids in multi_cluster_events:
            ids_str = ",".join(f"{c:.0f}" for c in cluster_ids)
            f.write(f"  {event_key}: {count} clusters ({ids_str})\n")

    return out_path

def write_neutrino_vertex_info(vertex_records, output_dir, filename="true_neutrino_info.txt",
                               volume_label="wire-readout sensitive box"):
    """
    Everything known about each true neutrino interaction, one row per
    interaction, from build_neutrino_vertex_records().

    cluster_energy_MeV (from the sed true points) is the energy used everywhere
    else in the pipeline; mc_Etot/mc_Edep are mc.json reference values that no
    cut uses -- the header says so, so a reader can't mistake one for the other.
    """
    if not vertex_records:
        return None

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / filename

    def _fmt(value, spec):
        return format(value, spec) if value is not None else "n/a"

    with open(out_path, "w") as f:
        f.write(f"{'='*150}\n")
        f.write("TRUE NEUTRINO INTERACTIONS (one row per interaction, from mc.json interaction-vertex nodes)\n")
        f.write(f"{'='*150}\n")
        f.write("vertex_x/y/z  : interaction vertex from mc.json (cm, same frame as the true points)\n")
        f.write(f"in_volume     : vertex inside the {volume_label}\n")
        f.write("cluster_energy: TRUE cluster energy summed from the sed true points -- the energy used\n")
        f.write("                for evaluation and the energy cut everywhere in this pipeline\n")
        f.write("mc_Etot/mc_Edep: mc.json reference energies (incident neutrino total / mc-side deposited).\n")
        f.write("                NOT used for any cut or evaluation -- shown for cross-reference only\n")
        f.write("has_cluster   : whether this interaction produced a true cluster that survived the cuts\n")
        f.write(f"{'='*150}\n\n")

        f.write(f"{'event':<12} {'nu_idx':>6} {'flavor':<8} {'cluster_id':>11} "
                f"{'vertex_x':>10} {'vertex_y':>10} {'vertex_z':>10} {'in_volume':>10} "
                f"{'cluster_energy':>15} {'n_points':>9} {'mc_Etot':>10} {'mc_Edep':>10} {'has_cluster':>12}\n")
        for r in sorted(vertex_records, key=lambda r: (r['file_name'], r['event_num'], r['nu_idx'] or 0)):
            f.write(
                f"{r['event']:<12} {str(r['nu_idx']):>6} {str(r['flavor']):<8} "
                f"{_fmt(r['cluster_id'], '.0f'):>11} "
                f"{_fmt(r['vertex_x'], '.2f'):>10} {_fmt(r['vertex_y'], '.2f'):>10} {_fmt(r['vertex_z'], '.2f'):>10} "
                f"{str(r['vertex_in_volume']):>10} "
                f"{_fmt(r['cluster_energy_MeV'], '.2f'):>15} {r['n_true_points']:>9} "
                f"{_fmt(r['mc_total_energy_MeV'], '.1f'):>10} {_fmt(r['mc_edep_MeV'], '.1f'):>10} "
                f"{str(r['has_true_cluster']):>12}\n")

        n_total    = len(vertex_records)
        n_in       = sum(1 for r in vertex_records if r['vertex_in_volume'] is True)
        n_out      = sum(1 for r in vertex_records if r['vertex_in_volume'] is False)
        n_cluster  = sum(1 for r in vertex_records if r['has_true_cluster'])
        n_in_clu   = sum(1 for r in vertex_records if r['vertex_in_volume'] is True and r['has_true_cluster'])
        n_out_clu  = sum(1 for r in vertex_records if r['vertex_in_volume'] is False and r['has_true_cluster'])

        f.write(f"\n{'='*150}\n")
        f.write(f"Total true neutrino interactions: {n_total}\n")
        f.write(f"  vertex IN  volume: {n_in:>5}   (with a true cluster: {n_in_clu})\n")
        f.write(f"  vertex OUT volume: {n_out:>5}   (with a true cluster: {n_out_clu})\n")
        f.write(f"  produced a true cluster: {n_cluster} / {n_total}\n")
        f.write("Note: an OUT-of-volume interaction can still produce a true cluster -- a daughter\n")
        f.write("particle entering the active volume deposits there even though the vertex is outside.\n")

    return out_path

def write_removed_neutrino_info(vertex_records, output_dir, filename="removed_true_neutrino_info.txt"):
    """
    The true neutrino interactions that did NOT survive the true selections --
    everything the plots leave out, kept so the losses can be studied rather
    than silently disappearing.

    Requires build_neutrino_vertex_records() to have been given
    clusters_true_precut/min_cluster_energy; without them precut_energy_MeV and
    removal_reason are blank and this file can only say that the interaction is
    missing, not why.

    Grouped and summarised by removal_reason, since the categories call for
    different responses: "no true deposits" is a genuinely invisible interaction
    (nothing to recover), while "below energy cut" is a threshold choice and
    "removed by geometric cuts" is a fiducial/dead-area effect.
    """
    removed = [r for r in vertex_records if not r.get('has_true_cluster')]
    if not removed:
        return None

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / filename

    def _fmt(value, spec):
        return format(value, spec) if value is not None else "n/a"

    n_total = len(vertex_records)
    with open(out_path, "w") as f:
        f.write(f"{'='*140}\n")
        f.write("TRUE NEUTRINO INTERACTIONS REMOVED BY THE TRUE SELECTIONS\n")
        f.write(f"{'='*140}\n")
        f.write("These interactions exist in mc.json but have no true cluster left after the cuts, so they\n")
        f.write("are EXCLUDED from every true-neutrino plot (vertices, vertex-volume, flavor). Listed here\n")
        f.write("so the losses stay visible and can be revisited.\n\n")
        f.write("precut_energy / precut_points: the cluster BEFORE any cut -- what the interaction actually\n")
        f.write("                deposited in the active volume, summed from the sed true points\n")
        f.write("removal_reason: which stage is responsible (see below)\n")
        f.write("mc_Etot/mc_Edep: mc.json reference energies, not used by any cut\n")
        f.write(f"{'='*140}\n\n")

        f.write(f"{'event':<12} {'nu_idx':>6} {'flavor':<8} {'in_volume':>10} "
                f"{'vertex_x':>10} {'vertex_y':>10} {'vertex_z':>10} "
                f"{'precut_energy':>14} {'precut_points':>14} {'mc_Etot':>9} {'mc_Edep':>9}  removal_reason\n")
        for r in sorted(removed, key=lambda r: (r['file_name'], r['event_num'], r['nu_idx'] or 0)):
            f.write(
                f"{r['event']:<12} {str(r['nu_idx']):>6} {str(r['flavor']):<8} {str(r['vertex_in_volume']):>10} "
                f"{_fmt(r['vertex_x'], '.2f'):>10} {_fmt(r['vertex_y'], '.2f'):>10} {_fmt(r['vertex_z'], '.2f'):>10} "
                f"{_fmt(r.get('precut_energy_MeV'), '.2f'):>14} {r.get('precut_n_points', 0):>14} "
                f"{_fmt(r['mc_total_energy_MeV'], '.1f'):>9} {_fmt(r['mc_edep_MeV'], '.1f'):>9}"
                f"  {r.get('removal_reason') or 'n/a'}\n")

        by_category = {}
        for r in removed:
            by_category.setdefault(r.get('removal_category') or 'unknown', []).append(r)

        n_surviving = n_total - len(removed)
        f.write(f"\n{'='*140}\n")
        f.write("REMOVAL SUMMARY BY REASON\n")
        f.write(f"{'='*140}\n")
        f.write(f"{'reason':<28} {'removed':>9} {'% of removed':>13} {'% of all':>10} "
                f"{'vertex_in':>10} {'vertex_out':>11}\n")
        f.write(f"{'-'*140}\n")
        for category, group in sorted(by_category.items(), key=lambda kv: -len(kv[1])):
            n_in = sum(1 for r in group if r['vertex_in_volume'] is True)
            f.write(f"{category:<28} {len(group):>9} "
                    f"{100.0 * len(group) / len(removed):>12.1f}% {100.0 * len(group) / n_total:>9.1f}% "
                    f"{n_in:>10} {len(group) - n_in:>11}\n")
        f.write(f"{'-'*140}\n")
        n_in_all = sum(1 for r in removed if r['vertex_in_volume'] is True)
        f.write(f"{'TOTAL REMOVED':<28} {len(removed):>9} {100.0:>12.1f}% "
                f"{100.0 * len(removed) / n_total:>9.1f}% {n_in_all:>10} {len(removed) - n_in_all:>11}\n\n")
        f.write(f"True neutrino interactions in mc.json: {n_total}\n")
        f.write(f"  removed by the true selections:     {len(removed)}\n")
        f.write(f"  surviving (and therefore plotted):  {n_surviving}\n\n")
        f.write("Cross-check against the cluster-level counts: interactions minus 'no true deposits'\n")
        f.write("is the neutrino cluster count BEFORE any cut, and subtracting 'below energy cut'\n")
        f.write("leaves the count after it -- the same two numbers SelectionAnalysis reports.\n")

        # What lowering the threshold would recover -- the actionable half of
        # "understand what we can do for those neutrinos".
        energy_removed = [r for r in removed
                          if r.get('removal_category') == 'below energy cut'
                          and r.get('precut_energy_MeV') is not None]
        if energy_removed:
            energies = sorted(r['precut_energy_MeV'] for r in energy_removed)
            f.write(f"\n{'='*140}\n")
            f.write("DEPOSITED ENERGY OF THE INTERACTIONS LOST TO THE ENERGY CUT\n")
            f.write("(how many would come back if the threshold moved -- deposited energy from the sed points)\n")
            f.write(f"{'='*140}\n")
            f.write(f"{'energy range [MeV]':<22} {'count':>7} {'cumulative':>12}   (cumulative = recovered if the cut moved to the upper edge)\n")
            edges = [0, 10, 25, 50, 75, 100]
            cumulative = 0
            for low, high in zip(edges[:-1], edges[1:]):
                n = sum(1 for e in energies if low <= e < high)
                cumulative += n
                f.write(f"{f'{low} - {high}':<22} {n:>7} {cumulative:>12}\n")
            f.write(f"\nmin {energies[0]:.1f} MeV, median {energies[len(energies)//2]:.1f} MeV, "
                    f"max {energies[-1]:.1f} MeV, over {len(energies)} interactions\n")

    return out_path
