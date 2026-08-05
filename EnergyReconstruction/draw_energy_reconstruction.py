"""
ENERGY RECONSTRUCTION plots for the charge-light matching pipeline -- driven by
EnergyReconstruction/EnergyReconstruction.ipynb.

The question this answers: how does a reco cluster's measured charge (ADC) map
onto the true energy of the neutrino that produced it? The plot is the 2D
distribution of true energy (y) against reco charge (x), one point per 1-to-1
matched true-reco pair.

WHICH PAIRS: only pairs whose TRUE side is a neutrino cluster, and only those
reconstructed well enough to be worth calibrating against -- efficiency above
EFFICIENCY_THRESHOLD_DEFAULT (0.8). A pair at 30% efficiency has most of its
true energy sitting in some other reco cluster (or in none), so its charge
cannot be expected to track its energy and it would only smear the relation.
The reco side of every pair is a SELECTED reco cluster by construction: the
pairing is done on the post-selection clusters_reco, so nothing that failed the
cuts can appear here.

WHICH TRUE CLUSTERS: the plot is drawn twice, over the neutrino pairs alone and
over every pair including cosmics -- see CLUSTER_SELECTIONS.

WHICH ENERGY: true_energy_MeV, the TRUE CLUSTER energy summed from the sed true
points. That is what the detector actually saw, and what every cut and
efficiency number in this pipeline uses, so it is the right target for a
charge-to-energy calibration. mc.json's 'Etot' (the INCIDENT neutrino energy) is
carried on each record and printed in the text table for reference, but is
deliberately NOT plotted: most of it may never be deposited in the active volume
at all, so a charge-vs-Etot plot mixes reconstruction together with the physics
of how much energy the interaction left behind (measured at 4% correlation,
against 62% for the cluster energy, on one test file).

At JOB level the histogram is also written to a .root file as a TH2D, so a later
analysis can pick up the binned distribution without re-running this pipeline.

This module is additive: it changes nothing in the existing pipeline modules and
only consumes records they already build (metadata.add_metadata_true_reco_pair_cluster,
metadata.build_neutrino_vertex_records).
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# reassign_cluster_ID_true_charge_light (selections.py) gives neutrino
# interaction nu_idx the true cluster_id 99990+nu_idx, so `true_cluster_id >=
# 99990` is exactly "this true cluster is a neutrino" and the remainder is its
# nu_idx -- an exact key, no spatial matching and no tolerance to tune. Kept
# here rather than imported from AnalysisDistributions_Reco_True/draw_variables.py
# so this directory stands on its own; selections.py is the source of truth for
# the scheme, and both copies must follow it.
NEUTRINO_CLUSTER_ID_BASE = 99990.0

# Minimum efficiency for a pair to enter the plots -- see the module docstring.
EFFICIENCY_THRESHOLD_DEFAULT = 0.8

# Bin widths for the 2D histogram. Same widths as the 1D distributions in
# AnalysisDistributions_Reco_True, so a projection of this plot is comparable to
# those. Neither axis has a fixed detector range to bin over, so the WIDTH is
# fixed and the range follows the data (see _bin_edges): a high-energy
# interaction gets its own bin instead of falling off the end of a fixed axis.
CHARGE_BIN_WIDTH_ADC = 2.0e6
ENERGY_BIN_WIDTH_MEV = 100.0

# Font sizes and marker styling, in one place so every plot here stays consistent
# (same values as AnalysisDistributions_Reco_True/draw_variables.py).
_AXIS_LABEL_FONTSIZE = 15
_TITLE_FONTSIZE      = 16
_TICK_LABEL_FONTSIZE = 13
_LEGEND_FONTSIZE     = 13
_STATS_BOX_FONTSIZE  = 11

_COLORMAP = 'viridis'

# The same plot over two TRUE-CLUSTER populations, each into its own
# subdirectory: (subdirectory, selection label for the title, neutrino_only).
# The neutrino set is a subset of the all-clusters set -- both are drawn from
# one record list, so the two can never be built on different pairings.
CLUSTER_SELECTIONS = [
    ('true_neutrino_clusters', 'true neutrino clusters',                True),
    ('all_true_clusters',      'all true clusters (neutrino + cosmic)',  False),
]

# Name of the TH2 written into the job-level ROOT file. Fixed rather than
# derived from the level/APA so downstream analysis can open any of these files
# and ask for the same key.
ROOT_HIST_NAME = 'true_energy_vs_reco_charge'


def nu_idx_from_true_cluster_id(true_cluster_id):
    """
    nu_idx of a true NEUTRINO cluster (99990+nu_idx -> nu_idx), or None if the
    cluster is cosmic (any avg-X-derived ID, always far below 99990).
    """
    if true_cluster_id is None:
        return None
    value = float(true_cluster_id)
    if value < NEUTRINO_CLUSTER_ID_BASE:
        return None
    return int(round(value - NEUTRINO_CLUSTER_ID_BASE))


# ============================================================================
# RECORD BUILDER
# ============================================================================

def build_matched_pair_energy_records(pair_metadata_list, vertex_records=None,
                                      efficiency_threshold=EFFICIENCY_THRESHOLD_DEFAULT,
                                      neutrino_only=True):
    """
    One record per 1-to-1 true-reco pair that survives the neutrino and
    efficiency selections -- the points of the 2D plots.

    The pairing is not recomputed here: it is read off the same
    clusterpairmatching.MatchTrueToReco1to1 ->
    metadata.add_metadata_true_reco_pair_cluster records the evaluation
    notebooks already produce, so a pair appears here if and only if the
    evaluation called that reco cluster the true neutrino's best match.

    Parameters:
    - pair_metadata_list: from metadata.add_metadata_true_reco_pair_cluster(),
        each with 'event', 'true_cluster_id', 'reco_cluster_id', 'efficiency',
        'purity', 'total_true_energy', 'total_reco_charge'
    - vertex_records: from metadata.build_neutrino_vertex_records(), joined by
        (event, nu_idx) -- an exact key -- to carry mc.json's Etot/Edep and the
        vertex_in_volume flag onto each record. None leaves those fields None,
        and the mc-energy variant of the plot then has nothing to draw.
    - efficiency_threshold: keep pairs with efficiency STRICTLY ABOVE this
        (0.8 = "more than 80% efficiency"). Pass 0 to keep every pair.
    - neutrino_only: keep only pairs whose true cluster is a neutrino

    Returns:
        List of dicts: {file_name, event, event_num, apa, nu_idx,
        true_cluster_id, reco_cluster_id, efficiency, purity,
        true_energy_MeV, reco_charge_ADC, mc_total_energy_MeV, mc_edep_MeV,
        vertex_in_volume}
    """
    if not pair_metadata_list:
        return []

    vertex_by_event_nu = {
        (r['event'], r['nu_idx']): r
        for r in (vertex_records or []) if r.get('nu_idx') is not None
    }

    records = []
    for pair in pair_metadata_list:
        nu_idx = nu_idx_from_true_cluster_id(pair.get('true_cluster_id'))
        if neutrino_only and nu_idx is None:
            continue

        efficiency = pair.get('efficiency', 0) or 0
        if efficiency <= efficiency_threshold:
            continue

        vertex = vertex_by_event_nu.get((pair['event'], nu_idx), {})
        records.append({
            'file_name':           pair.get('file_name'),
            'event':               pair['event'],
            'event_num':           pair.get('event_num'),
            'apa':                 pair.get('apa'),
            'nu_idx':              nu_idx,
            'true_cluster_id':     float(pair['true_cluster_id']),
            'reco_cluster_id':     float(pair['reco_cluster_id']),
            'efficiency':          float(efficiency),
            'purity':              float(pair.get('purity', 0) or 0),
            'true_energy_MeV':     float(pair.get('total_true_energy', 0) or 0),
            'reco_charge_ADC':     float(pair.get('total_reco_charge', 0) or 0),
            'mc_total_energy_MeV': vertex.get('mc_total_energy_MeV'),
            'mc_edep_MeV':         vertex.get('mc_edep_MeV'),
            'vertex_in_volume':    vertex.get('vertex_in_volume'),
        })
    return records


# ============================================================================
# DRAWING
# ============================================================================

def _bin_edges(values, bin_width):
    """
    Edges of bin_width, snapped OUTWARD to whole multiples of it, covering the
    data. Fixed width rather than a fixed range: neither axis here has a
    detector bound, so a fixed upper edge would silently drop the largest
    clusters -- exactly the ones a calibration most wants to see.
    """
    low  = np.floor(float(np.min(values)) / bin_width) * bin_width
    high = np.ceil(float(np.max(values)) / bin_width) * bin_width
    if high <= low:                      # every value in one bin
        high = low + bin_width
    return np.arange(low, high + bin_width / 2, bin_width)


def _stats_text(x_values, y_values, efficiency_threshold=None):
    """Entry count, per-axis mean/std, and the linear correlation between them."""
    x = np.asarray(x_values, dtype=float)
    y = np.asarray(y_values, dtype=float)
    lines = [f"pairs   = {len(x)}"]
    if efficiency_threshold is not None:
        lines.append(f"eff     > {efficiency_threshold:.2f}")
    lines.append(f"<charge>= {x.mean():.3g}")
    lines.append(f"<energy>= {y.mean():.1f}")
    # Pearson r needs two distinct values on each axis; a single pair, or a
    # degenerate axis, has no correlation to report rather than a misleading nan.
    if len(x) > 1 and x.std() > 0 and y.std() > 0:
        lines.append(f"corr r  = {np.corrcoef(x, y)[0, 1]:.3f}")
    else:
        lines.append("corr r  = n/a")
    return "\n".join(lines)


def _finish_axes(ax, xlabel, ylabel, title):
    """Labels, tick sizes and grid, at the module's font sizes."""
    ax.set_xlabel(xlabel, fontsize=_AXIS_LABEL_FONTSIZE, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=_AXIS_LABEL_FONTSIZE, fontweight='bold')
    ax.tick_params(axis='both', labelsize=_TICK_LABEL_FONTSIZE)
    ax.set_title(title, fontsize=_TITLE_FONTSIZE, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.3)


def draw_true_energy_vs_reco_charge(records, output_dir, level_name, filename_prefix, apa,
                                    file_name=None, selection_label='true neutrino clusters',
                                    filename_tag='true_cluster_energy',
                                    efficiency_threshold=EFFICIENCY_THRESHOLD_DEFAULT,
                                    write_text_table=True, write_root=False):
    """
    The 2D histogram of true cluster energy (y) against reco cluster charge (x),
    one entry per selected 1-to-1 pair. Level-agnostic: pass one event's
    records, one file's, or the whole job's -- the output has the same shape
    either way, which is what makes an event-level plot a slice of the
    job-level one.

    Empty bins are left blank (cmin=1) rather than drawn as the colormap's
    zero, so an occupied bin holding one pair is distinguishable from one
    holding none.

    Parameters:
    - records: from build_matched_pair_energy_records(), optionally narrowed to
        the neutrino pairs by select_neutrino_pair_records() -- this function
        applies no selection of its own
    - output_dir: output directory (created if missing)
    - level_name: title label ('Event 3', 'File Level', 'Job Level')
    - filename_prefix: filename suffix ('event_3', 'file', 'job')
    - apa: APA label (e.g. 'Combined')
    - file_name: optional input file name for the title
    - selection_label: which true-cluster population these pairs are, for the title
    - filename_tag: stem of the output filenames
    - efficiency_threshold: shown in the title and stats box only; the cut
        itself was applied by build_matched_pair_energy_records
    - write_text_table: also write the pair-by-pair table behind the histogram
    - write_root: also write the histogram to a .root file as a TH2D, for
        downstream analysis. Used at job level, where the histogram is the whole
        job's statistics; see _write_hist2d_root.

    An empty selection is NOT silently skipped: the text table is still written
    with a "0 pairs" note, so an empty directory always means the code did not
    run rather than the selection being genuinely empty.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if write_text_table:
        _write_pair_energy_info(records, output_dir, level_name, selection_label,
                                efficiency_threshold, file_name, filename_tag)

    if not records:
        print(f"  [draw_energy_reconstruction] {filename_tag} / {selection_label} / {level_name}: "
              f"0 pairs -- no plot drawn")
        return

    x = np.array([r['reco_charge_ADC'] for r in records], dtype=float)
    y = np.array([r['true_energy_MeV'] for r in records], dtype=float)

    title = f'True Energy vs Reco Charge: {level_name}, {apa}'
    if file_name:
        title += f' ({file_name})'
    title += f'\n1-to-1 pairs, {selection_label}, efficiency > {efficiency_threshold:.0%}'

    x_label = 'Reco cluster charge [ADC]'
    y_label = 'True cluster energy [MeV]'

    x_edges = _bin_edges(x, CHARGE_BIN_WIDTH_ADC)
    y_edges = _bin_edges(y, ENERGY_BIN_WIDTH_MEV)

    fig, ax = plt.subplots(figsize=(10, 7))
    counts, x_edges, y_edges, mesh = ax.hist2d(x, y, bins=[x_edges, y_edges], cmap=_COLORMAP, cmin=1)
    colorbar = fig.colorbar(mesh, ax=ax)
    colorbar.set_label('Number of pairs', fontsize=_AXIS_LABEL_FONTSIZE, fontweight='bold')
    colorbar.ax.tick_params(labelsize=_TICK_LABEL_FONTSIZE)
    _finish_axes(ax, x_label, y_label, title)
    ax.text(0.98, 0.02, _stats_text(x, y, efficiency_threshold), transform=ax.transAxes,
            fontsize=_STATS_BOX_FONTSIZE, family='monospace', ha='right', va='bottom',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    fig.savefig(output_dir / f'{filename_tag}_vs_reco_charge_hist2d_{filename_prefix}_{apa}.png',
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)

    if write_root:
        # cmin=1 leaves EMPTY bins as NaN in what ax.hist2d returns -- fine for
        # the image (they render blank), wrong for a histogram meant to be read
        # back and analysed, where an empty bin is a zero. Rebin cleanly rather
        # than patching the NaNs, so the counts written are unambiguous.
        root_counts, _, _ = np.histogram2d(x, y, bins=[x_edges, y_edges])
        _write_hist2d_root(root_counts, x_edges, y_edges,
                           output_dir / f'{filename_tag}_vs_reco_charge_hist2d_{filename_prefix}_{apa}.root',
                           x_label, y_label, title)


def _write_hist2d_root(counts, x_edges, y_edges, path, x_label, y_label, title):
    """
    Write the 2D histogram to a .root file as a TH2D named ROOT_HIST_NAME, so
    downstream analysis can pick the calibration up from the binned distribution
    without re-running this pipeline.

    Written with UPROOT, not PyROOT: the ROOT installations on this machine
    conflict and PyROOT does not import, while uproot needs no ROOT at all and
    produces a file ROOT reads normally. The tuple (counts, x_edges, y_edges) is
    uproot's writable-histogram form; counts is indexed [x, y], matching
    np.histogram2d's output.

    Import is local to this function so the rest of the module -- every PNG and
    every text table -- still works in an environment without uproot installed.
    """
    import uproot

    path = Path(path)
    with uproot.recreate(path) as root_file:
        root_file[ROOT_HIST_NAME] = (counts, x_edges, y_edges)
    print(f"  [draw_energy_reconstruction] wrote TH2D '{ROOT_HIST_NAME}' "
          f"({counts.shape[0]}x{counts.shape[1]} bins, {int(counts.sum())} entries) to {path}")
    return path


def select_neutrino_pair_records(records):
    """
    Keep only the pairs whose TRUE side is a neutrino cluster. nu_idx is None on
    a cosmic record (see nu_idx_from_true_cluster_id), so this is an exact
    split of the all-clusters population, not a re-derivation of it.
    """
    return [r for r in (records or []) if r.get('nu_idx') is not None]


def draw_all_energy_reconstruction_plots(records, output_dir, level_name, filename_prefix, apa,
                                         file_name=None,
                                         efficiency_threshold=EFFICIENCY_THRESHOLD_DEFAULT,
                                         write_root=False):
    """
    Draw the 2D histogram for both true-cluster populations of ONE aggregation
    level, each into its own subdirectory of output_dir:

      true_neutrino_clusters/  pairs whose true side is a neutrino cluster
      all_true_clusters/       every pair, neutrino and cosmic alike

    Both come from the SAME records list -- the neutrino set is a subset,
    selected here -- so the two plots can never end up built on different
    pairings or different cuts.

    Called identically at event, file and job level; pass write_root=True at job
    level to also write each histogram as a TH2D.
    """
    output_dir = Path(output_dir)
    for dirname, selection_label, neutrino_only in CLUSTER_SELECTIONS:
        selected = select_neutrino_pair_records(records) if neutrino_only else records
        draw_true_energy_vs_reco_charge(
            selected, output_dir / dirname, level_name, filename_prefix, apa,
            file_name=file_name, selection_label=selection_label,
            efficiency_threshold=efficiency_threshold, write_root=write_root)


def _write_pair_energy_info(records, output_dir, level_name, selection_label,
                            efficiency_threshold, file_name, filename_tag):
    """
    {filename_tag}_vs_reco_charge.txt: one row per pair behind the histogram, so
    the entries can be checked cluster by cluster instead of only read off a
    plot. mc.json's Etot rides along as a reference column -- it is NOT what is
    plotted (see the module docstring on why the cluster energy is).
    Written at every level from the same function, so an event-level table is
    that event's slice of the job-level one in the same format.
    """
    path = Path(output_dir) / f'{filename_tag}_vs_reco_charge.txt'
    columns = [('event', 15), ('nu_idx', 8), ('true_cluster_id', 17), ('reco_cluster_id', 17),
               ('efficiency', 12), ('purity', 10), ('reco_charge_ADC', 18),
               ('true_energy_MeV', 18), ('mc_Etot_MeV', 14), ('vertex_in_volume', 18)]

    with open(path, 'w') as f:
        f.write(f'# true energy vs reco charge -- {level_name}\n')
        f.write(f'# y axis: true_energy_MeV (true cluster energy, summed from the sed points)\n')
        f.write(f'# x axis: reco_charge_ADC (matched reco cluster charge)\n')
        f.write(f'# selection: 1-to-1 matched pairs, {selection_label}, '
                f'efficiency > {efficiency_threshold}\n')
        if file_name:
            f.write(f'# file: {file_name}\n')
        f.write(f'# pairs: {len(records)}\n')
        f.write(''.join(name.ljust(width) for name, width in columns) + '\n')
        for record in sorted(records, key=lambda r: (str(r['event']), r['true_cluster_id'])):
            values = [
                str(record['event']), str(record['nu_idx']),
                f"{record['true_cluster_id']:.0f}", f"{record['reco_cluster_id']:.3f}",
                f"{record['efficiency']:.4f}", f"{record['purity']:.4f}",
                f"{record['reco_charge_ADC']:.2f}",
                f"{record['true_energy_MeV']:.2f}",
                'n/a' if record.get('mc_total_energy_MeV') is None else f"{record['mc_total_energy_MeV']:.1f}",
                str(record.get('vertex_in_volume')),
            ]
            f.write(''.join(v.ljust(width) for v, (_, width) in zip(values, columns)) + '\n')
    return path
