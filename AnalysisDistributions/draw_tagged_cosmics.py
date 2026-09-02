"""
COSMIC-TAGGER RESULTS -- driven by
AnalysisDistributions/SignalBackground_Distributions.ipynb.

Which reco clusters the cosmic taggers flagged, drawn in XZ, YZ and XY and listed
in a text file with enough identity to find each one again.

WHAT THE TAGGER FILES CONTAIN

Every <evt>-tagger_<name>.json of an event holds the SAME point cloud -- x, y, z,
q and real_cluster_id are identical between tagger_stm and tagger_tgm -- and only
the column named 'cluster_id' differs. That column is a FLAG: 1 where this tagger
tagged the point, 0 where it did not. On chunk0 event 73, tgm flags 4409 of 4418
points and stm flags none.

The cloud is not the whole event. On that event it is 4418 points against 45816
in clustering-global, covering one cosmic track region -- the candidate the
taggers were asked about.

HOW A TAGGED POINT IS TIED TO A RECO CLUSTER

By POSITION, nearest neighbour within MATCH_RADIUS_CM. Not by charge: the
tagger files carry a 'q' on a different scale from clustering-global's, and of
3698 exactly-coincident points on chunk0 event 73 only 3 had matching q -- the
ratio between them ranges over four orders of magnitude. Position is exact or
near enough to be: 3698 of 4418 points coincide to 1e-4 cm, and the worst
nearest-neighbour distance is 0.71 cm.

The match is done against the reco point cloud the notebook is already working
with, so a cluster is identified by the same id the rest of the pipeline uses --
whichever of cluster_id / real_cluster_id RECO_ID_FIELD selects. On chunk0 event
73 every tagged point lands in cluster 18, which is that event's cosmic
candidate, and the 9 UNtagged points in the same file land in a different real
cluster.

A CLUSTER IS TAGGED DIRECTLY when at least MIN_TAGGED_POINTS of its points are
flagged by at least one tagger. The floor exists because a nearest-neighbour
match across two point clouds will always find a few stragglers, and one stray
point is not a tagged cosmic.

...AND THEN THE TAG PROPAGATES ACROSS THE BEAM WINDOW.

If ANY in-beam cluster is tagged, EVERY in-beam cluster of that event is tagged.
This is not a convenience: SBND currently treats all activity inside the beam
window as a single interaction, and the reco grouping is flash-based, so two
clusters sharing a beam window cannot be told apart by anything the selection has
access to. Tagging one and keeping its neighbour would claim a distinction the
reconstruction cannot make.

THIS LOSES TRUE NEUTRINOS, and deliberately. A neutrino sharing a beam window
with a tagged cosmic is tagged with it, so a cut that removes tagged activity
removes that neutrino too. Measured on chunk0: 34 clusters tagged directly, 1
more by propagation -- and separately, 3 of the directly tagged clusters already
CONTAIN a true neutrino (>90% completeness each, at 10-39% purity), because the
coarse cluster_id grouping had already merged neutrino and cosmic into one
object. The propagation rule does not create that exposure; it makes the same
inability to separate in-beam activity explicit one level up.

Every entry records which way it was tagged -- tagged_directly True or False --
so the two populations stay separable in the output even though the flag does
not distinguish them.
"""

from pathlib import Path

import numpy as np

# The tagging itself lives in selections.py, beside apply_cosmic_tagger_cut which
# acts on its result: the cut and the pictures must agree about what is tagged,
# and two implementations would eventually disagree. This module only draws.
from selections import (
    COSMIC_TAG_MATCH_RADIUS_CM as MATCH_RADIUS_CM,
    COSMIC_TAG_MIN_POINTS as MIN_TAGGED_POINTS,
    tag_reco_clusters,
    tagged_tagger_points as tagged_points,
)
from draw_saved_clusters import _draw_panels, _RECO_STYLE
from draw_contamination_clusters import _id_text, bee_event_url, split_event_key


TAGGED_COSMICS_DIR_NAME = 'TaggedCosmics'


def attach_tagged_cosmic_metadata(reco_var_records, tagged_by_cluster,
                                  id_field='cluster_id'):
    """
    Mark every reco cluster record the taggers flagged.

    Adds four fields to each record, on ALL of them so the schema does not
    depend on the outcome:

        tagged_cosmic     True/False
        tagged_by         list of tagger names, [] when untagged
        n_tagged_points   {tagger name: points flagged}, {} when untagged
        tagged_directly   True when a tagger flagged THIS cluster's points,
                          False when it was tagged because another cluster in
                          the same beam window was. None when untagged.

    tagged_cosmic does not distinguish the two -- that is the point of the
    propagation rule -- but tagged_directly keeps the distinction available for
    anything that wants to measure what the rule cost.

    Returns the number of records marked. Records are edited in place, which is
    what makes the flag travel with the cluster into every downstream plot and
    table built from them.
    """
    n_marked = 0
    for record in reco_var_records or []:
        entry = tagged_by_cluster.get(record.get(id_field))
        record['tagged_cosmic'] = entry is not None
        record['tagged_by'] = list(entry['taggers']) if entry else []
        record['n_tagged_points'] = dict(entry['n_tagged']) if entry else {}
        record['tagged_directly'] = entry['tagged_directly'] if entry else None
        if entry:
            n_marked += 1
    return n_marked


def draw_tagged_cluster_views(cluster_id, points, output_root, event_key,
                              detail, bee_url=None,
                              dir_name=TAGGED_COSMICS_DIR_NAME,
                              title="Tagged cosmic reco cluster",
                              name_prefix="tagged_cosmic"):
    """
    One tagged reco cluster in XZ, YZ and XY -- reco points only, since a tagged
    cosmic has no true neutrino counterpart to draw beside it.

    Returns the path written, or None when the cluster holds no points.
    """
    points = np.asarray(points, dtype=float)
    if not len(points):
        return None

    chunk, event = split_event_key(event_key)
    if detail.get('tagged_directly', True):
        tagger_text = ', '.join(f"{name} ({detail['n_tagged'][name]} pts)"
                                for name in detail['taggers'])
        tagger_text = f"tagged by {tagger_text}"
    else:
        # No tagger flagged this cluster: it shares a beam window with one that
        # was tagged, and in-beam activity cannot be separated. See the module
        # docstring.
        others = ', '.join(f"{cid:g}" for cid in detail.get('propagated_from', []))
        tagger_text = f"tagged by propagation (in-beam with reco {others})"
    legend_lines = [
        f"event {event_key}",
        tagger_text,
        f"reco id {cluster_id:.3f}",
        f"{detail['n_points']} points in cluster",
    ]
    if detail.get('flash_time') is not None:
        legend_lines.append(f"flash t {detail['flash_time']:.2f} us")
    if detail.get('reco_energy_mev') is not None:
        legend_lines.append(f"reco E {detail['reco_energy_mev']:.0f} MeV")

    name = (f"{name_prefix}_{chunk}_event{event}"
            f"_recoID{_id_text(cluster_id)}.png")
    footer_note = ('bee-display', bee_url) if bee_url else None
    return _draw_panels(
        title,
        [(points, _RECO_STYLE)],
        # One sub-directory per chunk, as for the other per-cluster populations.
        Path(output_root) / dir_name / (chunk or 'unknown_chunk') / name,
        legend_lines,
        footer_note=footer_note)


def flash_details(cluster_id, flash_records, id_field='clustering_cluster_id',
                  id_map=None):
    """
    The flashes bridged onto this reco cluster, as a list of
    {'flash_time', 'flash_index', 'n_matched_points'}, best supported first.

    A cluster can carry several (one per APA for a cathode crosser), so this
    returns all of them rather than picking one -- the text file prints the lot,
    which is what makes a tagged cluster's timing checkable afterwards.

    id_map, when given, translates each record's id before comparing:
    build_img_cluster_flash_metadata keys its records by REAL_CLUSTER_ID
    (deliberately -- see metadata.py), so a caller working in the coarse
    cluster_id namespace must pass {real id: coarse id} or nothing will match.
    """
    flashes = []
    for record in flash_records or []:
        record_id = record.get(id_field)
        if record_id is None:
            continue
        record_id = float(record_id)
        if id_map is not None:
            record_id = id_map.get(record_id, record_id)
        if record_id != float(cluster_id):
            continue
        flashes.append({
            'flash_time':       record.get('flash_time'),
            'flash_index':      record.get('flash_index'),
            'n_matched_points': record.get('n_matched_points'),
        })
    return sorted(flashes, key=lambda f: -(f['n_matched_points'] or 0))


def save_event_tagged_cosmics(taggers, clusters_reco, output_root, event_key,
                              flash_records=None, reco_var_records=None,
                              id_field='cluster_id', bee_links=None,
                              flash_id_map=None,
                              match_radius=MATCH_RADIUS_CM,
                              min_tagged_points=MIN_TAGGED_POINTS):
    """
    Tag, draw and describe every tagged reco cluster in ONE event.

    Returns (entries, tagged_by_cluster): one entry per figure written, and the
    raw tagging result so the caller can attach it to its own records.

    flash_id_map is passed straight to flash_details -- see there for why the
    coarse-id caller needs it.

    clusters_reco should be the BEAM-WINDOW survivors: a tagged cosmic outside
    the window was already going to be cut, so the ones worth drawing are the ones
    the selection would otherwise have kept.
    """
    tagged_by_cluster = tag_reco_clusters(taggers, clusters_reco,
                                          match_radius=match_radius,
                                          min_tagged_points=min_tagged_points)
    if not tagged_by_cluster:
        return [], {}

    chunk, event = split_event_key(event_key)
    bee_url = bee_event_url((bee_links or {}).get(chunk), event) if event else None
    energy_by_id = {r.get(id_field): r.get('reco_energy_mev')
                    for r in reco_var_records or []}

    entries = []
    for cluster_id, detail in sorted(tagged_by_cluster.items()):
        flashes = flash_details(cluster_id, flash_records, id_map=flash_id_map)
        detail = dict(detail)
        detail['flash_time'] = flashes[0]['flash_time'] if flashes else None
        detail['reco_energy_mev'] = energy_by_id.get(cluster_id)
        path = draw_tagged_cluster_views(cluster_id, clusters_reco[cluster_id],
                                         output_root, event_key, detail,
                                         bee_url=bee_url)
        if path is None:
            continue
        entries.append({
            'path':            path,
            'event_key':       event_key,
            'chunk':           chunk,
            'event':           event,
            'reco_cluster_id': cluster_id,
            'taggers':         detail['taggers'],
            'n_tagged':        detail['n_tagged'],
            'n_points':        detail['n_points'],
            'tagged_directly': detail.get('tagged_directly', True),
            'propagated_from': detail.get('propagated_from', []),
            'reco_energy_mev': detail['reco_energy_mev'],
            'flashes':         flashes,
            'bee_url':         bee_url,
        })
    return entries, tagged_by_cluster


def _relative_path(entry):
    path = Path(entry['path'])
    return f"{path.parent.name}/{path.name}"


def write_tagged_cosmics_info(entries, output_root, n_events_with_taggers=None,
                              n_beam_window_clusters=None,
                              filename='tagged_cosmics.txt'):
    """
    One block per tagged cluster: which taggers flagged it and how many points,
    the reco id, the chunk and event, the cluster size and energy, and every
    flash bridged onto it.

    A block rather than a table row because the flash list is variable length --
    a cathode-crossing cluster carries one per APA -- and truncating it would
    lose the timing this file exists to record.
    """
    output_root = Path(output_root) / TAGGED_COSMICS_DIR_NAME
    output_root.mkdir(parents=True, exist_ok=True)
    entries = sorted(entries or [], key=lambda e: (str(e['chunk']), int(e['event'] or 0)))

    lines = []
    lines.append("=" * 96)
    lines.append("TAGGED COSMIC RECO CLUSTERS")
    lines.append("=" * 96)
    lines.append("")
    lines.append("Reco clusters the cosmic taggers flagged, AFTER the beam-window cut: these")
    lines.append("are background the selection would otherwise have kept. A cluster is tagged")
    lines.append(f"DIRECTLY when at least {MIN_TAGGED_POINTS} of its points are flagged by at least one tagger,")
    lines.append(f"matched by position within {MATCH_RADIUS_CM} cm -- NOT by charge, which is on a different")
    lines.append("scale in the tagger files than in the clustering output.")
    lines.append("")
    lines.append("THE TAG THEN PROPAGATES ACROSS THE BEAM WINDOW: if any in-beam cluster is")
    lines.append("tagged, every in-beam cluster of that event is. SBND treats all activity")
    lines.append("inside the beam window as a single interaction and the reco grouping is")
    lines.append("flash-based, so two clusters sharing a window cannot be told apart by")
    lines.append("anything the selection can see. This DOES tag true neutrinos that share a")
    lines.append("window with a cosmic, and a cut removing tagged activity removes them too.")
    lines.append("")
    summary = f"{len(entries)} tagged cluster(s)"
    if n_beam_window_clusters:
        summary += (f" of {n_beam_window_clusters} that survived the beam-window cut "
                    f"({len(entries) / n_beam_window_clusters:.0%})")
    if n_events_with_taggers is not None:
        summary += f", over {n_events_with_taggers} event(s) with tagger files"
    lines.append(summary + ".")
    lines.append("")
    n_direct = sum(1 for e in entries if e.get('tagged_directly'))
    lines.append(f"    {n_direct} tagged directly by a tagger")
    lines.append(f"    {len(entries) - n_direct} tagged by propagation across the beam window")
    lines.append("")
    by_tagger = {}
    for entry in entries:
        if not entry.get('tagged_directly'):
            continue
        by_tagger.setdefault(', '.join(entry['taggers']), 0)
        by_tagger[', '.join(entry['taggers'])] += 1
    if by_tagger:
        lines.append("Of the directly tagged, by tagger:")
        for names, count in sorted(by_tagger.items()):
            lines.append(f"    {names:<16s} {count}")
        lines.append("")

    for entry in entries:
        lines.append("-" * 96)
        lines.append(f"  {entry['chunk']}   event {entry['event']}   "
                     f"reco id {_id_text(entry['reco_cluster_id'])}")
        if entry.get('tagged_directly'):
            lines.append(f"    tagged by       : "
                         + ", ".join(f"{name} ({entry['n_tagged'][name]} points)"
                                     for name in entry['taggers']))
        else:
            others = ', '.join(f"{cid:g}" for cid in entry.get('propagated_from', []))
            lines.append(f"    tagged by       : PROPAGATION -- no tagger flagged this")
            lines.append(f"                      cluster; it shares the beam window with "
                         f"reco {others}")
        lines.append(f"    cluster points  : {entry['n_points']}")
        if entry.get('reco_energy_mev') is not None:
            lines.append(f"    reco energy     : {entry['reco_energy_mev']:.1f} MeV")
        if entry['flashes']:
            for n, flash in enumerate(entry['flashes']):
                time = flash['flash_time']
                lines.append(f"    flash {n}         : "
                             f"t = {time:.3f} us" if time is not None else
                             f"    flash {n}         : t = n/a")
                lines.append(f"                      index {flash['flash_index']}, "
                             f"{flash['n_matched_points']} matched points")
        else:
            lines.append("    flash           : none bridged onto this cluster")
        lines.append(f"    figure          : {_relative_path(entry)}")
        if entry.get('bee_url'):
            lines.append(f"    bee display     : {entry['bee_url']}")
    lines.append("-" * 96)

    path = output_root / filename
    path.write_text("\n".join(lines) + "\n")
    return path


def draw_tagged_neutrino_match_bar(entries, output_root,
                                   dir_name=TAGGED_COSMICS_DIR_NAME,
                                   filename='tagged_neutrino_match.png'):
    """
    How much SIGNAL the taggers are sitting on: tagged clusters that matched an
    IN-VOLUME true neutrino, against those that did not, split by how each came
    to be tagged.

    IN-VOLUME ONLY. An out-of-volume neutrino is a rejection category -- the
    selection does not want it either -- so counting one as signal lost to the
    tagger would overstate the cost. The caller decides this when it fills in
    matched_true_neutrino.

    The clusters here are the ones selections.apply_cosmic_tagger_cut removes, so
    this is the signal cost of that cut -- measured where the tagging is studied
    rather than where it is applied.

    Two bars because the question has two answers, stacked by cause because the
    interesting follow-up is whether the neutrino losses come from clusters a
    tagger actually flagged (the coarse grouping had already merged neutrino and
    cosmic) or from propagation across the beam window (the neutrino was a
    bystander). Those are different problems with different fixes, and one bar
    would hide the difference.

    entries need 'matched_true_neutrino' and 'tagged_directly'; see
    save_event_tagged_cosmics and the notebook that fills the first in.
    """
    import matplotlib.pyplot as plt

    output_root = Path(output_root) / dir_name
    output_root.mkdir(parents=True, exist_ok=True)
    entries = entries or []

    groups = ['No in-volume neutrino match', 'Matched an in-volume neutrino']
    # Fixed order, never cycled: blue is always "tagger flagged it", orange always
    # "propagated". Validated as a categorical pair -- normal-vision dE 35.7, and
    # 25.0 / 33.6 / 34.3 under protan / deutan / tritan.
    causes = [('tagged directly by a tagger', '#1f77b4', True),
              ('tagged by propagation',        '#ff7f0e', False)]

    counts = {(g, direct): 0 for g in groups for _, _, direct in causes}
    for entry in entries:
        group = groups[1] if entry.get('matched_true_neutrino') else groups[0]
        counts[(group, bool(entry.get('tagged_directly')))] += 1

    fig, ax = plt.subplots(figsize=(9, 6))
    bottoms = [0, 0]
    for label, colour, direct in causes:
        values = [counts[(g, direct)] for g in groups]
        ax.bar(groups, values, bottom=bottoms, color=colour, label=label,
               width=0.55, edgecolor='white', linewidth=2)
        for n, (value, base) in enumerate(zip(values, bottoms)):
            if value:
                ax.text(n, base + value / 2, str(value), ha='center', va='center',
                        fontsize=13, fontweight='bold', color='white')
        bottoms = [b + v for b, v in zip(bottoms, values)]

    for n, total in enumerate(bottoms):
        ax.text(n, total, f" {total} ", ha='center', va='bottom',
                fontsize=14, fontweight='bold')

    ax.set_ylabel('Tagged reco clusters', fontsize=13, fontweight='bold')
    ax.set_title('Cosmic taggers: what they tagged\n'
                 f'{sum(bottoms)} in-beam cluster(s) tagged, '
                 f'{bottoms[1]} of them matched an in-volume true neutrino',
                 fontsize=14, fontweight='bold')
    ax.tick_params(axis='both', labelsize=12)
    ax.legend(fontsize=11, framealpha=0.9)
    # Recessive grid, and headroom for the total labels.
    ax.grid(True, axis='y', linestyle='--', alpha=0.3)
    ax.set_axisbelow(True)
    ax.set_ylim(0, max(bottoms + [1]) * 1.18)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)

    path = output_root / filename
    fig.savefig(path, dpi=150, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    return path
