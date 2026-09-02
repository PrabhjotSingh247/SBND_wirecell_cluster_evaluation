"""
IMPURE RECO-TRUE PAIRS -- driven by
AnalysisDistributions/DrawRecoTrueClusters_Below_60pc_Purity.ipynb.

Every selected reco cluster whose match to a true cluster is less than 60% pure:
most of what it holds is not the true cluster it was paired with. Drawn in XZ, YZ
and XY with the true cluster above and the reco cluster below.

WHAT COUNTS

    pair_purity < LOW_PURITY_MAX   (0.60)
    category    != 'out_of_volume'

A purity cut and nothing else -- no completeness floor, no energy gate. That is
deliberate and it is what separates this population from Contamination_Clusters,
which takes the same purity bar AND requires completeness above 40%:

    Contamination_Clusters   purity < 60% AND completeness > 40%
    this                     purity < 60%

So this is a SUPERSET of the contaminated pairs. The extra ones are those the
completeness floor excluded: reco clusters that are mostly other charge AND found
little of the true cluster they were matched to. Those are matching failures
rather than contamination -- the picture shows two objects with little to do with
each other -- which is exactly why the contamination window excludes them, and
exactly why they are worth seeing on their own.

Out-of-volume pairs are excluded: that is a rejection category, and its purity is
not what this population is about.

A pair is required. A reco cluster that matched no true cluster (a cosmic
candidate) has no purity to be low, and treating a missing value as zero would
fill this directory with every cosmic in the sample.

NO SAMPLING. Every qualifying pair is drawn.
"""

from pathlib import Path

import numpy as np

from draw_saved_clusters import (
    _draw_row_panels, _TRUE_STYLE, _RECO_STYLE,
)
from draw_contamination_clusters import (
    _id_text, bee_event_url, load_bee_links, split_event_key,
)


# The selection. A purity bar and nothing else -- see the module docstring for
# why there is no completeness floor and no energy gate.
LOW_PURITY_MAX = 0.60

LOW_PURITY_DIR_NAME = 'pairs_below_60pc_purity'


def is_low_purity_pair(record, max_purity=LOW_PURITY_MAX):
    """
    True when this categorize_reco_clusters record is an impure pair.

    Requires an actual in-volume pair: a record with no true cluster (a cosmic
    candidate, or a reco cluster that matched nothing) has no purity to be low,
    and `or 0` on a missing value would quietly make it look like the least pure
    cluster in the sample.
    """
    if record is None or record.get('pair_true_cluster_id') is None:
        return False
    if record.get('category') == 'out_of_volume':
        return False
    purity = record.get('pair_purity')
    if purity is None:
        return False
    return purity < max_purity


def draw_low_purity_views(record, clusters_true, clusters_reco, output_root,
                          event_key, bee_url=None):
    """
    One impure pair, true cluster above and reco cluster below, in XZ/YZ/XY.

    The two rows share axes per column (see _draw_row_panels), which is the whole
    point for this population: the impurity is the part of the LOWER row that has
    no counterpart above it, and that reads only if both rows sit on one frame.

    Returns the path written, or None when the event's point clouds no longer
    hold one of the two clusters.
    """
    true_points = clusters_true.get(record['pair_true_cluster_id'])
    reco_points = clusters_reco.get(record['reco_cluster_id'])
    if true_points is None or reco_points is None:
        return None

    chunk, event = split_event_key(event_key)
    # Column 5 is the per-point true energy: the deposited energy AFTER the cuts,
    # the same quantity the truth-side stacks are filled with.
    true_energy = float(np.asarray(true_points)[:, 5].sum())
    legend_lines = [
        f"event {event_key}",
        f"{record.get('channel')}",
        f"purity {record['pair_purity']:.3f}",
        f"completeness {(record.get('pair_completeness') or 0):.3f}",
        f"true E {true_energy:.0f} MeV",
        f"reco E {(record.get('reco_energy_mev') or 0):.0f} MeV",
        f"true id {record['pair_true_cluster_id']:.0f}",
        f"reco id {record['reco_cluster_id']:.3f}",
    ]

    # Same filename convention as the contaminated pairs, so the two directories
    # can be read the same way: every number LABELLED, because they are bare
    # numbers otherwise and which is which is not recoverable from a name alone.
    name = (f"recotrue_clusters_{chunk}_event{event}"
            f"_recoID{_id_text(record['reco_cluster_id'])}"
            f"_trueID{_id_text(record['pair_true_cluster_id'])}.png")
    footer_note = ('bee-display', bee_url) if bee_url else None
    return _draw_row_panels(
        f"Below {LOW_PURITY_MAX:.0%} purity -- {record.get('channel')}",
        [("TRUE cluster", [(true_points, _TRUE_STYLE)]),
         ("RECO cluster", [(reco_points, _RECO_STYLE)])],
        # One sub-directory per chunk. The chunk is already in every filename, so
        # this adds no information -- it makes the directory browsable, since the
        # full sample puts every chunk's figures in one flat listing otherwise.
        Path(output_root) / LOW_PURITY_DIR_NAME / (chunk or 'unknown_chunk') / name,
        legend_lines,
        footer_note=footer_note)


def save_event_low_purity_views(selection_records, clusters_true, clusters_reco,
                                output_root, event_key, bee_links=None,
                                max_purity=LOW_PURITY_MAX):
    """
    Every impure pair in ONE event.

    Called from inside the event loop because that is the only place the point
    clouds exist -- they are far too large to carry to job level.

    Returns (entries, n_in_volume_pairs): one entry per figure written, and how
    many in-volume pairs the event held in total. The second is the denominator
    that makes the first readable -- "3 impure of 4 pairs" and "3 of 40" are very
    different statements about the reconstruction.
    """
    chunk, event = split_event_key(event_key)
    bee_url = bee_event_url((bee_links or {}).get(chunk), event) if event else None

    written, n_in_volume_pairs = [], 0
    for record in selection_records or []:
        # The denominator: in-volume pairs, the same population the purity bar is
        # applied to.
        if (record.get('pair_true_cluster_id') is not None
                and record.get('category') != 'out_of_volume'
                and record.get('pair_purity') is not None):
            n_in_volume_pairs += 1
        if not is_low_purity_pair(record, max_purity):
            continue
        path = draw_low_purity_views(record, clusters_true, clusters_reco,
                                     output_root, event_key, bee_url=bee_url)
        if path is None:
            continue
        true_points = clusters_true.get(record['pair_true_cluster_id'])
        written.append({
            'path':            path,
            'true_energy_mev': (float(np.asarray(true_points)[:, 5].sum())
                                if true_points is not None else None),
            'event_key':       event_key,
            'chunk':           chunk,
            'event':           event,
            'channel':         record.get('channel'),
            'category':        record.get('category'),
            'reco_cluster_id': record.get('reco_cluster_id'),
            'true_cluster_id': record.get('pair_true_cluster_id'),
            'purity':          record.get('pair_purity'),
            'completeness':    record.get('pair_completeness'),
            'reco_energy_mev': record.get('reco_energy_mev'),
            'bee_url':         bee_url,
        })
    return written, n_in_volume_pairs


def _relative_path(entry):
    """
    'chunk3/recotrue_clusters_chunk3_event57_recoID12_trueID99991.png' -- the
    path as it should appear in the index, relative to the directory it sits in.

    The figures live one directory per chunk, so the bare filename would no
    longer be something a reader can open from where the index sits.
    """
    path = Path(entry['path'])
    return f"{path.parent.name}/{path.name}"


def write_low_purity_index(entries, output_root, n_in_volume_pairs=None,
                           max_purity=LOW_PURITY_MAX,
                           filename='pairs_below_60pc_purity.txt'):
    """
    The index: one row per figure, worst purity first.

    Also writes bee_links.txt beside it -- filename and URL only, nothing else --
    because that is the file a reader can actually click a link out of. The URL
    is printed on each figure too, but a PNG cannot hold a working link.

    n_in_volume_pairs, if given, is how many in-volume pairs the job held; it is
    reported next to the figure count so the impure fraction is on the page
    rather than left to be worked out.
    """
    output_root = Path(output_root) / LOW_PURITY_DIR_NAME
    output_root.mkdir(parents=True, exist_ok=True)
    entries = sorted(entries or [], key=lambda e: (e['purity'] is None, e['purity']))

    lines = []
    lines.append("=" * 104)
    lines.append("IMPURE RECO-TRUE PAIRS -- index")
    lines.append("=" * 104)
    lines.append("")
    lines.append("EVERY in-volume pair -- no sampling -- with")
    lines.append(f"    purity < {max_purity:.0%}")
    lines.append("")
    lines.append("A purity bar and nothing else: no completeness floor, no energy gate. This")
    lines.append("is therefore a SUPERSET of Contamination_Clusters, which takes the same bar")
    lines.append("AND requires completeness above 40%. The extra pairs here are the ones that")
    lines.append("floor excluded -- mostly other charge AND little of the true cluster they")
    lines.append("were matched to, which is a matching failure rather than contamination.")
    lines.append("")
    lines.append("Each figure has the true cluster on the top row and the reco cluster on")
    lines.append("the bottom, sharing axes per column, so the impurity is visible as points")
    lines.append("the upper row does not have.")
    lines.append("")
    if n_in_volume_pairs is None:
        lines.append(f"{len(entries)} figure(s).")
    else:
        fraction = (f" of {n_in_volume_pairs} in-volume pair(s) "
                    f"({len(entries) / n_in_volume_pairs:.0%})") if n_in_volume_pairs else ""
        lines.append(f"{len(entries)} figure(s){fraction}.")
    lines.append("")
    lines.append("-" * 104)
    lines.append(f"  {'event':<14s}{'channel':>9s}{'purity':>9s}{'compl':>8s}"
                 f"{'true E':>9s}{'reco E':>9s}{'reco id':>11s}{'true id':>10s}  file")
    lines.append("-" * 104)
    for entry in entries:
        lines.append(
            f"  {str(entry['event_key']):<14s}{str(entry['channel']):>9s}"
            f"{(entry['purity'] or 0):>9.3f}{(entry['completeness'] or 0):>8.3f}"
            f"{(entry['true_energy_mev'] or 0):>9.0f}{(entry['reco_energy_mev'] or 0):>9.0f}"
            f"{_id_text(entry['reco_cluster_id']):>11s}"
            f"{_id_text(entry['true_cluster_id']):>10s}  {_relative_path(entry)}")

    index_path = output_root / filename
    index_path.write_text("\n".join(lines) + "\n")

    link_lines = ["# BEE event display, one per figure. The same URL is printed on the",
                  "# figure itself, where it cannot be clicked -- PNG has no hyperlinks.",
                  ""]
    for entry in entries:
        if entry.get('bee_url'):
            link_lines.append(f"{_relative_path(entry)}  {entry['bee_url']}")
    (output_root / 'bee_links.txt').write_text("\n".join(link_lines) + "\n")
    return index_path
