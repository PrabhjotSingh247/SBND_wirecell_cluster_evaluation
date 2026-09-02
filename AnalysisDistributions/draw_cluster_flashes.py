"""
RECO CLUSTER FLASHES -- driven by
AnalysisDistributions/Draw_Cluster_Flashes.ipynb.

Flash time against number of clusters, for ALL reco clusters before any cut. This
is the population the beam-window selection is drawn FROM, so the window can be
seen against what it is cutting.

ONE FLASH PER CLUSTER -- one row per cluster, not one per (cluster, flash) match.

A cathode-crossing cluster is matched by one flash per APA, so an un-collapsed
plot counts it once per flash. Collapsing to one row each makes the count the
number of reco clusters the stacks in SignalBackground_Distributions.ipynb
report; without it the two disagree by however many flash-mates the coarse
grouping merged (137 vs 104 on chunk0).

HOW MUCH WAS COLLAPSED is still reported, in cluster_flashes.txt: both row counts
and their difference. That is the double-matching rate -- 229 of 1745 rows on
chunk0 -- which is worth knowing as a number even though the un-collapsed plot is
no longer drawn.

WHICH FLASH SURVIVES the collapse: an IN-BEAM-WINDOW flash in preference to any
other, because that is the flash the selection acts on -- a cluster is selected if
ANY of its flashes falls in the window. Ranking by matched points alone lost one
chunk0 cluster whose larger flash sat outside the window, making this plot
disagree with the stacks. Among equally in-window (or equally out-of-window)
flashes, the best supported wins.

WHY A SEPARATE MODULE. These plots used to come from
SignalBackground_Distributions.ipynb, where the collapse above sat inline in the
job-level cell. They describe the RECO INPUT -- what the beam-window cut is
choosing between -- rather than the signal/background composition that notebook
measures, and nothing else in it depends on them.

NO PAIRING NEEDED. Unlike every other population split out of that notebook,
these plots are built from the flash metadata alone: no completeness, no purity,
no 1-to-1 matching. The driving notebook can therefore leave
b_draw_selection_performance off and skip the most expensive part of the event
loop entirely.
"""

from pathlib import Path

from DrawRecoTrueFlashes import (BEAM_WINDOW_MIN_US, BEAM_WINDOW_MAX_US,
                                 draw_clustering_flashes)


CLUSTER_FLASHES_DIR_NAME = 'cluster_flashes'


def flash_rank(record):
    """
    Sort key deciding which flash represents a cluster: in-window first, then best
    supported. See the module docstring for why in-window wins over better
    supported rather than the other way round.
    """
    in_window = BEAM_WINDOW_MIN_US <= record['flash_time'] <= BEAM_WINDOW_MAX_US
    return (in_window, record.get('n_matched_points') or 0)


def one_flash_per_cluster(flash_records):
    """
    One record per (event, cluster), keeping the highest-ranked flash of each.

    A cathode-crossing cluster has one flash per APA; this is what turns the
    (cluster, flash) population into a per-CLUSTER one, so the count agrees with
    the number of reco clusters the stacks report.
    """
    best_by_cluster = {}
    for record in flash_records or []:
        key = (record['event'], record['clustering_cluster_id'])
        best = best_by_cluster.get(key)
        if best is None or flash_rank(record) > flash_rank(best):
            best_by_cluster[key] = record
    return list(best_by_cluster.values())


def draw_job_cluster_flashes(flash_records, output_root, apa="Combined",
                             level_name="Job Level", filename_prefix="job"):
    """
    The plot, into CLUSTER_FLASHES_DIR_NAME under output_root.

    Returns (n_pairs, n_clusters) -- rows before and after the collapse. Only the
    collapsed set is DRAWN; n_pairs is still returned because their difference is
    the double-matching rate, which cluster_flashes.txt reports.
    """
    if not flash_records:
        return 0, 0

    flash_dir = Path(output_root) / CLUSTER_FLASHES_DIR_NAME
    flash_dir.mkdir(parents=True, exist_ok=True)

    collapsed = one_flash_per_cluster(flash_records)
    draw_clustering_flashes(collapsed, flash_dir, apa, level_name,
                            f"{filename_prefix}_one_flash_per_cluster")
    return len(flash_records), len(collapsed)


def write_cluster_flash_info(n_pairs, n_clusters, output_root,
                             filename='cluster_flashes.txt'):
    """
    What was drawn and what was collapsed away, so the double-matching rate is a
    number on disc rather than something inferred from a plot that is no longer
    drawn.
    """
    output_root = Path(output_root) / CLUSTER_FLASHES_DIR_NAME
    output_root.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("=" * 78)
    lines.append("RECO CLUSTER FLASHES -- what was drawn")
    lines.append("=" * 78)
    lines.append("")
    lines.append("Flash time vs number of clusters, for ALL reco clusters before any cut --")
    lines.append("the population the beam-window selection is drawn FROM.")
    lines.append("")
    lines.append(f"  (cluster, flash) pairs seen   {n_pairs:8d} rows")
    lines.append(f"  DRAWN: one flash per cluster  {n_clusters:8d} rows")
    lines.append(f"  double-matched                {n_pairs - n_clusters:8d} rows")
    lines.append("")
    lines.append("Only the collapsed set is drawn. The difference is cathode-crossing")
    lines.append("clusters, matched by one flash per APA and so counted once per flash")
    lines.append("before the collapse. The one kept is an in-beam-window flash in preference")
    lines.append("to any other, because that is the flash the selection acts on -- so the")
    lines.append("drawn count is the number of reco clusters the stacks report.")
    lines.append("")
    lines.append(f"Beam window: {BEAM_WINDOW_MIN_US} to {BEAM_WINDOW_MAX_US} us.")
    lines.append("=" * 78)

    path = output_root / filename
    path.write_text("\n".join(lines) + "\n")
    return path
