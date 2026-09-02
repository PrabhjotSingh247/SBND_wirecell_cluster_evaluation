"""
BADLY RECONSTRUCTED RECO-TRUE PAIRS -- driven by
AnalysisDistributions/DrawRecoTrueClusters.ipynb.

Every reco-true pair where the reco cluster found only a small part of the true
cluster it was matched to, drawn in XZ, YZ and XY with the true cluster above and
the reco cluster below.

WHAT COUNTS AS BADLY RECONSTRUCTED

    pair_completeness < LOW_COMPLETENESS_MAX             (0.60)
    reco_energy_mev   > LOW_COMPLETENESS_MIN_RECO_ENERGY (200 MeV)
    category          != 'out_of_volume'

The completeness bar is the definition; the reco-energy floor is what makes the
picture worth drawing. Below it a poorly reconstructed cluster is a handful of
points and the figure shows nothing, so the interesting failures are the ones
that reconstructed a SUBSTANTIAL cluster and still missed most of the true one.

The gate is on the RECO side rather than the true side because that is what the
lower panel actually contains. 200 MeV, measured rather than guessed: over the
full sample the 17 pairs below the completeness bar top out at 432 MeV of reco
energy, so anything near 500 empties the directory. Low completeness and a large
reco cluster are close to mutually exclusive by construction -- one pair is
521 MeV true against 7 MeV reco -- so this floor has to sit low to select
anything at all. Six of the 17 pass it on the full sample.

Out-of-volume pairs are excluded: that is a rejection category, and its
completeness is not what this population is about.

NO SAMPLING. Every qualifying pair is drawn -- the question these figures answer
("what does a badly reconstructed neutrino look like?") is not answered by one
example, and on the full sample this is a handful of figures.

WHY A SEPARATE MODULE, AND WHY HERE. These views used to be drawn by
draw_saved_clusters.py from SignalBackground_Distributions.ipynb, alongside the
completeness-purity grid. They never belonged there: that notebook draws
DISTRIBUTIONS, and a per-pair picture is what DrawRecoTrueClusters.ipynb exists
for. Moving them puts them beside Contamination_Clusters, whose population they
are the mirror image of -- contamination is a reco cluster that found the
neutrino and took in extra charge, this is one that missed most of it -- so the
two are drawn by the same notebook, in the same layout, and read side by side.

The BEE link handling, the event-key split and the id formatting are imported
from draw_contamination_clusters rather than copied: they are the same problems
with the same answers, and two copies would drift.
"""

from pathlib import Path

import numpy as np

from draw_saved_clusters import (
    _draw_row_panels, _TRUE_STYLE, _RECO_STYLE,
)
from draw_contamination_clusters import (
    _id_text, bee_event_url, load_bee_links, split_event_key,
)


# The selection. See the module docstring for why the energy floor is on the reco
# side and why it sits as low as it does.
LOW_COMPLETENESS_MAX = 0.60
LOW_COMPLETENESS_MIN_RECO_ENERGY_MEV = 200.0

LOW_COMPLETENESS_DIR_NAME = 'pairs_below_60pc_completeness'


def is_low_completeness_pair(record,
                             max_completeness=LOW_COMPLETENESS_MAX,
                             min_reco_energy=LOW_COMPLETENESS_MIN_RECO_ENERGY_MEV):
    """
    True when this categorize_reco_clusters record is a badly reconstructed pair.

    Requires an actual in-volume pair: a record with no true cluster (a cosmic
    candidate, or a reco cluster that matched nothing) has no completeness to be
    low, and `or 0` on a missing value would quietly make it look like the worst
    reconstruction in the sample.
    """
    if record is None or record.get('pair_true_cluster_id') is None:
        return False
    if record.get('category') == 'out_of_volume':
        return False
    completeness = record.get('pair_completeness')
    if completeness is None:
        return False
    return (completeness < max_completeness
            and (record.get('reco_energy_mev') or 0) > min_reco_energy)


def draw_low_completeness_views(record, clusters_true, clusters_reco, output_root,
                                event_key, bee_url=None):
    """
    One badly reconstructed pair, true cluster above and reco cluster below, in
    XZ/YZ/XY.

    The two rows share axes per column (see _draw_row_panels), which is the whole
    point for this population: what was missed is the part of the upper row that
    has no counterpart below it, and that reads only if both rows sit on one
    frame.

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
        f"completeness {record['pair_completeness']:.3f}",
        f"purity {(record.get('pair_purity') or 0):.3f}",
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
        f"Below {LOW_COMPLETENESS_MAX:.0%} completeness -- {record.get('channel')}",
        [("TRUE cluster", [(true_points, _TRUE_STYLE)]),
         ("RECO cluster", [(reco_points, _RECO_STYLE)])],
        # One sub-directory per chunk. The chunk is already in every filename, so
        # this adds no information -- it makes the directory browsable, since the
        # full sample puts every chunk's figures in one flat listing otherwise.
        Path(output_root) / LOW_COMPLETENESS_DIR_NAME / (chunk or 'unknown_chunk') / name,
        legend_lines,
        footer_note=footer_note)


def save_event_low_completeness_views(selection_records, clusters_true, clusters_reco,
                                      output_root, event_key, bee_links=None,
                                      max_completeness=LOW_COMPLETENESS_MAX,
                                      min_reco_energy=LOW_COMPLETENESS_MIN_RECO_ENERGY_MEV):
    """
    Every badly reconstructed pair in ONE event.

    Called from inside the event loop because that is the only place the point
    clouds exist -- they are far too large to carry to job level.

    Returns (entries, n_below_bar): one entry per figure written, and how many
    pairs fell below the completeness bar BEFORE the reco-energy floor. The
    second number is what tells a reader whether an empty directory means "the
    reconstruction is fine" or "the floor is too high" -- on the full sample the
    two are 6 and 17, so the difference is not a detail.
    """
    chunk, event = split_event_key(event_key)
    bee_url = bee_event_url((bee_links or {}).get(chunk), event) if event else None

    written, n_below_bar = [], 0
    for record in selection_records or []:
        # Counted before the energy floor, and on the same in-volume pairs the
        # selection itself applies to.
        if (record.get('pair_true_cluster_id') is not None
                and record.get('category') != 'out_of_volume'
                and (record.get('pair_completeness') is not None)
                and record['pair_completeness'] < max_completeness):
            n_below_bar += 1
        if not is_low_completeness_pair(record, max_completeness, min_reco_energy):
            continue
        path = draw_low_completeness_views(record, clusters_true, clusters_reco,
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
    return written, n_below_bar


def _relative_path(entry):
    """
    'chunk3/recotrue_clusters_chunk3_event57_recoID12_trueID99991.png' -- the
    path as it should appear in the index, relative to the directory it sits in.

    The figures live one directory per chunk, so the bare filename would no
    longer be something a reader can open from where the index sits.
    """
    path = Path(entry['path'])
    return f"{path.parent.name}/{path.name}"


def write_low_completeness_index(entries, output_root, n_below_bar=None,
                                 max_completeness=LOW_COMPLETENESS_MAX,
                                 min_reco_energy=LOW_COMPLETENESS_MIN_RECO_ENERGY_MEV,
                                 filename='pairs_below_60pc_completeness.txt'):
    """
    The index: one row per figure, sorted by completeness so the worst come first.

    Also writes bee_links.txt beside it -- filename and URL only, nothing else --
    because that is the file a reader can actually click a link out of. The URL
    is printed on each figure too, but a PNG cannot hold a working link.

    n_below_bar, if given, is how many pairs sat below the completeness bar before
    the reco-energy floor; it is reported next to the figure count so an empty or
    short directory is readable as a statement about the floor rather than about
    the reconstruction.
    """
    output_root = Path(output_root) / LOW_COMPLETENESS_DIR_NAME
    output_root.mkdir(parents=True, exist_ok=True)
    entries = sorted(entries or [],
                     key=lambda e: (e['completeness'] is None, e['completeness']))

    lines = []
    lines.append("=" * 104)
    lines.append("BADLY RECONSTRUCTED RECO-TRUE PAIRS -- index")
    lines.append("=" * 104)
    lines.append("")
    lines.append("EVERY in-volume pair -- no sampling -- with")
    lines.append(f"    completeness < {max_completeness:.0%}")
    lines.append(f"    reco energy  > {min_reco_energy:.0f} MeV")
    lines.append("")
    lines.append("The completeness bar is the definition; the reco-energy floor is what makes")
    lines.append("the picture worth drawing. Below it a badly reconstructed cluster is a")
    lines.append("handful of points and the figure shows nothing, so what is kept are the")
    lines.append("failures that reconstructed a substantial cluster and still missed most of")
    lines.append("the true one. It is a hard cut: low completeness and a large reco cluster")
    lines.append("are close to mutually exclusive, so far fewer pairs pass it than sit below")
    lines.append("the bar.")
    lines.append("")
    lines.append("Each figure has the true cluster on the top row and the reco cluster on")
    lines.append("the bottom, sharing axes per column, so what was missed is visible as")
    lines.append("points the lower row does not have.")
    lines.append("")
    if n_below_bar is None:
        lines.append(f"{len(entries)} figure(s).")
    else:
        lines.append(f"{len(entries)} figure(s), from {n_below_bar} pair(s) below the "
                     f"{max_completeness:.0%} bar.")
    lines.append("")
    lines.append("-" * 104)
    lines.append(f"  {'event':<14s}{'channel':>9s}{'compl':>9s}{'purity':>8s}"
                 f"{'true E':>9s}{'reco E':>9s}{'reco id':>11s}{'true id':>10s}  file")
    lines.append("-" * 104)
    for entry in entries:
        lines.append(
            f"  {str(entry['event_key']):<14s}{str(entry['channel']):>9s}"
            f"{(entry['completeness'] or 0):>9.3f}{(entry['purity'] or 0):>8.3f}"
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
