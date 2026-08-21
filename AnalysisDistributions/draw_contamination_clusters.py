"""
CONTAMINATED RECO-TRUE PAIRS -- driven by
AnalysisDistributions/DrawRecoTrueClusters.ipynb.

Every reco-true pair whose reco cluster picked up a substantial amount of charge
that does not belong to the true cluster it was matched to, drawn in XZ, YZ and
XY with the true cluster above and the reco cluster below.

WHAT COUNTS AS CONTAMINATION

    pair_purity       < CONTAMINATION_MAX_PURITY        (0.60)
    pair_completeness > CONTAMINATION_MIN_COMPLETENESS  (0.40)

Both bounds are needed and they say different things. Low purity alone is not
contamination -- a reco cluster that caught almost none of the true cluster is
low purity too, but that is a MATCHING failure and the picture shows two objects
that have little to do with each other. Requiring completeness above 40% keeps
the pairs where the reco cluster genuinely found the neutrino AND dragged in
something else: the true cluster is really there in the lower panel, with extra
charge around it. That is the population worth looking at one by one.

NO SAMPLING. Every qualifying pair is drawn -- unlike Saved_Clusters, which keeps
at most a few per completeness-purity cell. The point here is to look at all of
them, and on the full sample this is a few dozen figures.

BEE LINKS

Each figure prints the BEE event-display URL for its own event below the bottom
row of panels, where it covers no data. The URL is read from
bee_links_100_files_chunk.txt at the repository root. That file gives one set URL
per chunk, ending in '/event/list/'; the last segment is replaced by the event
number to address the event directly.

The URL is printed as TEXT, not as a link: PNG has no way to carry a hyperlink
(matplotlib's url= is honoured only by the vector backends), so a link drawn into
a raster figure would be a link that does not work. Printing it keeps the figure
honest about what it is -- the same URL is also written to bee_links.txt in the
output directory, where it can be clicked or copied without retyping.
"""

from pathlib import Path

import numpy as np

from draw_saved_clusters import (
    _draw_row_panels, _TRUE_STYLE, _RECO_STYLE,
)


# The contamination window. See the module docstring for why it is bounded on
# both sides rather than being a purity cut alone.
CONTAMINATION_MAX_PURITY = 0.60
CONTAMINATION_MIN_COMPLETENESS = 0.40

CONTAMINATION_DIR_NAME = 'Contamination_Clusters'

# Repository-root file mapping each chunk to its BEE set.
BEE_LINKS_FILENAME = 'bee_links_100_files_chunk.txt'


def load_bee_links(path):
    """
    {chunk name: BEE set URL} from bee_links_100_files_chunk.txt.

    The file is a comment header plus one 'chunk<N>  <events>  <url>' row per
    chunk. Blank lines and '#' comments are skipped; anything that is not three
    whitespace-separated fields is ignored rather than raised on, so a note added
    to the file by hand cannot stop a job.

    Returns {} if the file is missing -- the figures are still worth drawing
    without the links, and a missing links file should not cost a 20 minute run.
    """
    path = Path(path)
    if not path.exists():
        return {}
    links = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        fields = line.split()
        if len(fields) != 3 or not fields[2].startswith('http'):
            continue
        links[fields[0]] = fields[2]
    return links


def bee_event_url(set_url, event):
    """
    The per-EVENT BEE URL from a per-SET one: the trailing 'list' becomes the
    event number.

    '.../event/list/' -> '.../event/7/'

    Written as a replacement of the last non-empty path segment rather than a
    string replace of 'list', which would also corrupt a set id that happened to
    contain those four letters.
    """
    if not set_url:
        return None
    parts = set_url.rstrip('/').split('/')
    if not parts:
        return None
    parts[-1] = str(event)
    return '/'.join(parts) + '/'


def split_event_key(event_key):
    """
    'chunk3_57' -> ('chunk3', '57').

    The chunk name itself contains no underscore in this production, so the split
    is on the LAST one and the event number is whatever follows it. Returns
    (event_key, None) if there is nothing to split, so a caller still gets a
    usable label.
    """
    if event_key is None:
        return None, None
    text = str(event_key)
    if '_' not in text:
        return text, None
    chunk, event = text.rsplit('_', 1)
    return chunk, event


def _id_text(value):
    """
    A cluster id as it should appear in a FILENAME: '17' not '17.0', '-110.25'
    kept as is.

    Reco ids are rounded average x coordinates and so are floats that are usually
    but not always integral; true neutrino ids are large integers. '%g' prints
    both the way a person would write them, and keeps the filename free of the
    trailing '.0' that makes two names for one cluster.
    """
    if value is None:
        return 'none'
    return f"{float(value):g}"


def is_contamination_pair(record,
                          max_purity=CONTAMINATION_MAX_PURITY,
                          min_completeness=CONTAMINATION_MIN_COMPLETENESS):
    """
    True when this categorize_reco_clusters record is a contaminated pair.

    Requires an actual pair: a record with no true cluster (a cosmic candidate,
    or a reco cluster that matched nothing) has no purity to be low, and `or 0`
    on a missing value would quietly make it look like perfect contamination.
    """
    if record is None or record.get('pair_true_cluster_id') is None:
        return False
    purity = record.get('pair_purity')
    completeness = record.get('pair_completeness')
    if purity is None or completeness is None:
        return False
    return purity < max_purity and completeness > min_completeness


def draw_contamination_views(record, clusters_true, clusters_reco, output_root,
                             event_key, bee_url=None):
    """
    One contaminated pair, true cluster above and reco cluster below, in XZ/YZ/XY.

    The two rows share axes per column (see _draw_row_panels), which is the whole
    point for this population: contamination is extra reco charge sitting AROUND
    the true cluster, and that can only be seen if both rows are on one frame.

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
    in_volume = 'in-volume' if record.get('category') != 'out_of_volume' else 'OUT-of-volume'
    legend_lines = [
        f"event {event_key}",
        f"{record.get('channel')}",
        in_volume,
        f"purity {record['pair_purity']:.3f}",
        f"completeness {record['pair_completeness']:.3f}",
        f"true E {true_energy:.0f} MeV",
        f"reco E {(record.get('reco_energy_mev') or 0):.0f} MeV",
        f"true id {record['pair_true_cluster_id']:.0f}",
        f"reco id {record['reco_cluster_id']:.3f}",
    ]

    # Every number in the filename is LABELLED -- 'event18_recoID30_trueID99992',
    # not '18_30_99992'. They are bare numbers otherwise, and which is which is
    # not recoverable from a name alone once the file leaves this directory.
    name = (f"recotrue_clusters_{chunk}_event{event}"
            f"_recoID{_id_text(record['reco_cluster_id'])}"
            f"_trueID{_id_text(record['pair_true_cluster_id'])}.png")
    footer_note = ('bee-display', bee_url) if bee_url else None
    return _draw_row_panels(
        f"Contaminated reco-true pair -- {record.get('channel')}",
        [("TRUE cluster", [(true_points, _TRUE_STYLE)]),
         ("RECO cluster", [(reco_points, _RECO_STYLE)])],
        # One sub-directory per chunk. The chunk is already in every filename, so
        # this adds no information -- it makes the directory browsable, since the
        # full sample puts every chunk's figures in one flat listing otherwise.
        Path(output_root) / CONTAMINATION_DIR_NAME / (chunk or 'unknown_chunk') / name,
        legend_lines,
        footer_note=footer_note)


def save_event_contamination_views(selection_records, clusters_true, clusters_reco,
                                   output_root, event_key, bee_links=None,
                                   max_purity=CONTAMINATION_MAX_PURITY,
                                   min_completeness=CONTAMINATION_MIN_COMPLETENESS):
    """
    Every contaminated pair in ONE event.

    Called from inside the event loop because that is the only place the point
    clouds exist -- they are far too large to carry to job level.

    Returns a list of {path, event, chunk, ids, metrics, bee_url} for the index
    file, one per figure written.
    """
    chunk, event = split_event_key(event_key)
    bee_url = bee_event_url((bee_links or {}).get(chunk), event) if event else None

    written = []
    for record in selection_records or []:
        if not is_contamination_pair(record, max_purity, min_completeness):
            continue
        path = draw_contamination_views(record, clusters_true, clusters_reco,
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
    return written


def _relative_path(entry):
    """
    'chunk3/recotrue_clusters_chunk3_event57_recoID12_trueID99991.png' -- the
    path as it should appear in the index, relative to Contamination_Clusters.

    The figures live one directory per chunk, so the bare filename would no
    longer be something a reader can open from where the index sits.
    """
    path = Path(entry['path'])
    return f"{path.parent.name}/{path.name}"


def write_contamination_index(entries, output_root,
                              max_purity=CONTAMINATION_MAX_PURITY,
                              min_completeness=CONTAMINATION_MIN_COMPLETENESS,
                              filename='contamination_clusters.txt'):
    """
    The index: one row per figure, sorted by purity so the worst come first.

    Also writes bee_links.txt beside it -- filename and URL only, nothing else --
    because that is the file a reader can actually click a link out of. The URL
    is printed on each figure too, but a PNG cannot hold a working link.
    """
    output_root = Path(output_root) / CONTAMINATION_DIR_NAME
    output_root.mkdir(parents=True, exist_ok=True)
    entries = sorted(entries or [], key=lambda e: (e['purity'] is None, e['purity']))

    lines = []
    lines.append("=" * 104)
    lines.append("CONTAMINATED RECO-TRUE PAIRS -- index")
    lines.append("=" * 104)
    lines.append("")
    lines.append("EVERY pair -- no sampling -- with")
    lines.append(f"    purity       < {max_purity:.0%}")
    lines.append(f"    completeness > {min_completeness:.0%}")
    lines.append("")
    lines.append("Low purity alone would also catch pairs that simply matched the wrong")
    lines.append("object; requiring completeness above the floor keeps the ones where the")
    lines.append("reco cluster really did find the neutrino and then took in extra charge.")
    lines.append("")
    lines.append("Each figure has the true cluster on the top row and the reco cluster on")
    lines.append("the bottom, sharing axes per column, so the extra charge is visible as")
    lines.append("points the upper row does not have.")
    lines.append("")
    lines.append(f"{len(entries)} figure(s).")
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
