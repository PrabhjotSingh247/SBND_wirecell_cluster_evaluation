"""
Cluster-level VARIABLE DISTRIBUTIONS (reco and true) for the charge-light
matching pipeline -- driven by AnalysisDistributions_Reco_True/Reco_Distributions.ipynb.

This module is additive: it adds no behaviour to, and changes nothing in, the
existing evaluation modules. It takes the SAME post-selection objects the
evaluation notebook already builds (clusters_reco / clusters_true dicts, 1-to-1
pair metadata, true cluster-type records, neutrino vertex records) and turns
them into per-cluster records with one number per variable, then histograms
them.

Variables per RECO cluster: avg_x, avg_y, avg_z (the cluster's mean position,
cm), flash_time (us, the bridged optical flash time of that cluster) and
total_charge (ADC).
Variables per TRUE cluster: avg_x, avg_y, avg_z and total_energy (MeV, summed
from the true points -- the same quantity the energy cut and every completeness
plot use). There is deliberately no true-side flash_time: true clusters carry
no flash and no time (build_true_points_charge_light fills the time column with
zeros). See metadata.build_true_cluster_type_records for why beam/flash timing
stays a reco-side quantity.

FLASH TIME AND THE RECO CLUSTER ID NAMESPACE (the one subtle part):
the evaluation pipeline relabels reco clusters via
selections.reassign_cluster_ID_reco (cluster_id := round(mean(x), 3)), which
destroys clustering-global's real_cluster_id -- the namespace
metadata.build_img_cluster_flash_metadata's flash records are keyed in. So the
flash time cannot be looked up from clusters_reco after the fact.
build_reco_flash_time_lookup() below is given the points array as it was JUST
BEFORE that relabelling and reproduces the same round(mean(x), 3) key, which
maps each real_cluster_id onto the id the rest of the pipeline uses.

NEUTRINO SELECTION uses the cluster ID, not the 'cluster_type' string:
reassign_cluster_ID_true_charge_light gives neutrino interaction nu_idx the
true cluster_id 99990+nu_idx, so `true_cluster_id >= 99990` is exactly "this
true cluster is a neutrino" and `true_cluster_id - 99990` is its nu_idx --
an exact key with no reliance on how any downstream record spelled the type.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pathlib import Path

from DrawRecoTrueFlashes import BEAM_WINDOW_MIN_US, BEAM_WINDOW_MAX_US

# reassign_cluster_ID_true_charge_light's neutrino cluster-ID base: neutrino
# interaction nu_idx becomes cluster_id 99990+nu_idx (99991, 99992, ...).
NEUTRINO_CLUSTER_ID_BASE = 99990.0

# (record key, axis label, unit, fixed range or None for auto, number of bins).
# The fixed x/y/z ranges are the wire-readout sensitive box the fiducial cut
# already applied (x_min..z_max in the notebook), so every histogram covers the
# full allowed volume and two selections are directly comparable bin by bin.
# flash_time is auto-ranged instead: with the beam-window cut on, every entry
# sits inside a 1.6 us window and a fixed wide range would put all of them in
# one bin.
#
# The spatial variables are binned in fixed 50 cm bins: several of these
# selections hold only a handful of clusters per run, and finer bins spread
# them one-per-bin so the histogram carries no shape at all. Change
# SPATIAL_BIN_WIDTH_CM alone to rebin all three -- the bin COUNTS are derived
# from it, so the fixed ranges above stay exact multiples of the width and no
# bin ever straddles a volume boundary.
SPATIAL_BIN_WIDTH_CM = 50.0

X_RANGE_CM = (-250.0, 250.0)
Y_RANGE_CM = (-200.0, 200.0)
Z_RANGE_CM = (0.0, 500.0)


def _n_bins_for(value_range, bin_width):
    """Number of bins of bin_width covering value_range (at least one)."""
    return max(int(round((value_range[1] - value_range[0]) / bin_width)), 1)


# True cluster energy and reco cluster charge have no fixed detector range to
# bin over the way the spatial variables do -- a cosmic or a high-energy
# interaction can sit far above the typical value, and a fixed upper edge would
# silently drop it. They are binned at a FIXED BIN WIDTH over whatever range the
# data occupies instead (see _bin_edges): the width is the physically meaningful
# choice, and the range follows the sample.
ENERGY_BIN_WIDTH_MEV = 100.0     # true cluster energy
CHARGE_BIN_WIDTH_ADC = 2.0e6     # reco cluster charge -- deliberately coarse

# Variable specs: (record key, axis label, unit, fixed range or None, number of
# bins or None, fixed bin width or None). Give a spec EITHER a fixed range plus
# a bin count, OR a bin width -- see _bin_edges for how each is turned into bin
# edges.
SPATIAL_VARIABLE_SPECS = [
    ('avg_x', 'Average X of cluster', 'cm', X_RANGE_CM, _n_bins_for(X_RANGE_CM, SPATIAL_BIN_WIDTH_CM), None),
    ('avg_y', 'Average Y of cluster', 'cm', Y_RANGE_CM, _n_bins_for(Y_RANGE_CM, SPATIAL_BIN_WIDTH_CM), None),
    ('avg_z', 'Average Z of cluster', 'cm', Z_RANGE_CM, _n_bins_for(Z_RANGE_CM, SPATIAL_BIN_WIDTH_CM), None),
]

RECO_VARIABLE_SPECS = SPATIAL_VARIABLE_SPECS + [
    ('flash_time',   'Flash time',           'us',  None, 80,   None),
    ('total_charge', 'Cluster reco charge',  'ADC', None, None, CHARGE_BIN_WIDTH_ADC),
]

TRUE_VARIABLE_SPECS = SPATIAL_VARIABLE_SPECS + [
    ('total_energy', 'Cluster true energy', 'MeV', None, None, ENERGY_BIN_WIDTH_MEV),
]

# Per-side drawing style. Colour identifies the side everywhere: reco red, true
# black.
#
# NO statistical error bars are drawn (draw_errors=False everywhere). The reco
# and true histograms are built from the SAME events -- the same interactions
# seen two ways -- so their bin counts are not independent Poisson draws, and
# sqrt(N) bars would suggest an independence the two sides do not have. The
# machinery is still in _plot_histogram for a case where it is warranted.
#
# _KIND_STYLE is for a plot showing ONE population on its own (the reco/ and
# true/ set directories): each is a step line, since nothing else shares the axes.
_KIND_STYLE = {
    'reco': {'color': 'red',   'linestyle': ':', 'linewidth': 2.2, 'marker': 'o',
             'draw_line': True, 'draw_markers': False, 'draw_errors': False},
    'true': {'color': 'black', 'linestyle': '-', 'linewidth': 1.8, 'marker': 'o',
             'draw_line': True, 'draw_markers': False, 'draw_errors': False},
}

# _COMPARISON_STYLE is for the reco-vs-true overlay, where the two are drawn on
# the SAME axes: both are step lines, reco red and dotted, true black and solid.
# The two coincide bin-for-bin wherever reconstruction worked, so the SOLID one
# is drawn first and the broken one on top of it (see _draw_onto) -- otherwise
# the last line drawn simply erases the other and one curve looks absent.
_COMPARISON_STYLE = {
    'reco': dict(_KIND_STYLE['reco']),
    'true': {'color': 'black', 'linestyle': '-', 'linewidth': 2.0, 'marker': 'o',
             'draw_line': True, 'draw_markers': False, 'draw_errors': False},
}

_KIND_COLOR = {kind: style['color'] for kind, style in _KIND_STYLE.items()}

# Font sizes, in one place so every plot in this module stays consistent.
_AXIS_LABEL_FONTSIZE   = 15
_TITLE_FONTSIZE        = 16
_TICK_LABEL_FONTSIZE   = 13
_LEGEND_FONTSIZE       = 13
_STATS_BOX_FONTSIZE    = 11

# One definition of the error-bar look, shared by the bars drawn on the plot and
# by the legend key that stands for them, so the two can't drift apart.
_ERROR_BAR_KWARGS = dict(elinewidth=1.4, capsize=4, capthick=1.4)

# Headroom above the tallest bin, as a fraction of it. The legend and the stats
# box sit inside the axes, so the y-axis is extended to keep them clear of the
# curve rather than letting them land on top of it.
_Y_HEADROOM = 0.45


def _cluster_key(cluster_id):
    """
    Hashable key for a reco cluster ID. reassign_cluster_ID_reco rounds to 3
    decimals, so both sides of every comparison here are the same rounded
    value -- rounding again just makes that explicit rather than relying on
    two float paths landing on identical bits.
    """
    return round(float(cluster_id), 3)


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
# RECORD BUILDERS
# ============================================================================

def build_reco_flash_time_lookup(predicted_points, cluster_flash_records, prefer_beam_window=True):
    """
    Map each reco cluster onto its bridged optical flash time, keyed by the
    cluster ID the evaluation pipeline uses AFTER reassign_cluster_ID_reco.

    Parameters:
    - predicted_points: the Nx5 reco points array [x, y, z, real_cluster_id, q]
        exactly as it is handed to selections.reassign_cluster_ID_reco -- i.e.
        after every reco-side cut (beam window, fiducial, min points) and
        before the relabelling. Column 3 must still be clustering-global's
        real_cluster_id, which is the namespace cluster_flash_records is keyed
        in; passing an already-relabelled array silently matches nothing.
    - cluster_flash_records: output of metadata.build_img_cluster_flash_metadata()
        for this event, each with 'clustering_cluster_id', 'flash_index', 'flash_time'
    - prefer_beam_window: when a cluster has several distinct flash matches,
        prefer the in-beam-window one(s). A cluster that survived the
        beam-window cut has an in-window flash by construction, so this picks
        the flash the cut selected on rather than an unrelated second match.

    Returns:
        {reassigned_reco_cluster_id: flash_time}. Clusters with no flash match
        are simply absent (same convention as the flash metadata builders) --
        build_reco_cluster_variable_records stores flash_time=None for those.
    """
    if predicted_points is None or len(predicted_points) == 0:
        return {}

    # real_cluster_id -> distinct flash times (deduplicated by flash_index: one
    # clustering cluster can map to several img clusters sharing ONE flash).
    times_by_real_id = {}
    seen = set()
    for record in (cluster_flash_records or []):
        real_id = float(record['clustering_cluster_id'])
        key = (real_id, record['flash_index'])
        if key in seen:
            continue
        seen.add(key)
        times_by_real_id.setdefault(real_id, []).append(float(record['flash_time']))

    predicted_points = np.asarray(predicted_points)
    real_ids = predicted_points[:, 3]

    # Two different real_cluster_ids can round to the SAME avg-X key, in which
    # case reassign_cluster_ID_reco genuinely merges them into one reco cluster
    # downstream -- so their flash times are pooled here and resolved together.
    candidate_times = {}
    for real_id in np.unique(real_ids):
        mask = real_ids == real_id
        reassigned_id = _cluster_key(np.mean(predicted_points[mask, 0]))
        candidate_times.setdefault(reassigned_id, []).extend(times_by_real_id.get(float(real_id), []))

    flash_time_by_reco_id = {}
    for reassigned_id, times in candidate_times.items():
        if not times:
            continue
        if prefer_beam_window:
            in_window = [t for t in times if BEAM_WINDOW_MIN_US <= t <= BEAM_WINDOW_MAX_US]
            if in_window:
                times = in_window
        # Mean only ever averages genuinely distinct flashes of one cluster
        # (or of clusters merged by the avg-X key above); the common case is a
        # single value, where the mean is that value.
        flash_time_by_reco_id[reassigned_id] = float(np.mean(times))

    return flash_time_by_reco_id


def build_reco_cluster_variable_records(clusters_reco, file_name, event, event_key=None,
                                        apa="Combined", flash_time_by_reco_id=None):
    """
    One record per SELECTED reco cluster, holding the variables to histogram.

    Parameters:
    - clusters_reco: dict {cluster_id: points}, points columns [x, y, z, cluster_id, charge],
        post-selection and post reassign_cluster_ID_reco -- i.e. the very same
        dict the completeness/purity evaluation runs on, so these distributions
        describe exactly the clusters that evaluation scored.
    - file_name, event, event_key, apa: identification, as elsewhere in the pipeline
    - flash_time_by_reco_id: output of build_reco_flash_time_lookup(); None
        leaves every flash_time None (the flash_time histogram is then skipped)

    Returns:
        List of dicts: {file_name, event, event_num, apa, reco_cluster_id,
        n_points, total_charge, avg_x, avg_y, avg_z, flash_time}
    """
    if event_key is None:
        event_key = f"{file_name}_{event}"
    if not clusters_reco:
        return []

    flash_time_by_reco_id = flash_time_by_reco_id or {}

    records = []
    for cluster_id, points in clusters_reco.items():
        points = np.asarray(points)
        if len(points) == 0:
            continue
        records.append({
            'file_name':       file_name,
            'event':           event_key,
            'event_num':       event,
            'apa':             apa,
            'reco_cluster_id': float(cluster_id),
            'n_points':        int(len(points)),
            'total_charge':    float(points[:, 4].sum()),
            'avg_x':           float(points[:, 0].mean()),
            'avg_y':           float(points[:, 1].mean()),
            'avg_z':           float(points[:, 2].mean()),
            'flash_time':      flash_time_by_reco_id.get(_cluster_key(cluster_id)),
        })
    return records


def build_true_cluster_variable_records(clusters_true, file_name, event, event_key=None,
                                        apa="Combined", vertex_records=None):
    """
    One record per SELECTED true cluster, holding the variables to histogram.

    Parameters:
    - clusters_true: dict {cluster_id: points}, points columns
        [x, y, z, cluster_id, q_true, energy, time], post-selection and post
        reassign_cluster_ID_true_charge_light (neutrino clusters at 99990+nu_idx)
    - file_name, event, event_key, apa: identification, as elsewhere
    - vertex_records: output of metadata.build_neutrino_vertex_records() for this
        event. Used only to carry each neutrino cluster's vertex_in_volume flag
        onto its record (joined by nu_idx, an exact key -- no spatial matching);
        None leaves vertex_in_volume None and select_true_neutrino_records()
        can then not apply an in-volume selection.

    Returns:
        List of dicts: {file_name, event, event_num, apa, true_cluster_id,
        is_neutrino, nu_idx, n_points, total_energy, avg_x, avg_y, avg_z,
        vertex_in_volume}
    """
    if event_key is None:
        event_key = f"{file_name}_{event}"
    if not clusters_true:
        return []

    in_volume_by_nu_idx = {
        r['nu_idx']: r.get('vertex_in_volume')
        for r in (vertex_records or []) if r.get('nu_idx') is not None
    }

    records = []
    for cluster_id, points in clusters_true.items():
        points = np.asarray(points)
        if len(points) == 0:
            continue
        nu_idx = nu_idx_from_true_cluster_id(cluster_id)
        records.append({
            'file_name':        file_name,
            'event':            event_key,
            'event_num':        event,
            'apa':              apa,
            'true_cluster_id':  float(cluster_id),
            'is_neutrino':      nu_idx is not None,
            'nu_idx':           nu_idx,
            'n_points':         int(len(points)),
            'total_energy':     float(points[:, 5].sum()),
            'avg_x':            float(points[:, 0].mean()),
            'avg_y':            float(points[:, 1].mean()),
            'avg_z':            float(points[:, 2].mean()),
            'vertex_in_volume': in_volume_by_nu_idx.get(nu_idx) if nu_idx is not None else None,
        })
    return records


# ============================================================================
# SELECTORS -- each takes and returns a list of the records above, so they
# compose: select_records_in_single_neutrino_events(
#     select_reco_records_matched_to_true_neutrino(...), ...)
# ============================================================================

# The two populations every plot family can be drawn for, and their directories.
# 'all'   -- every selected reco cluster and every true cluster. The two sides
#            are different objects: the reco side holds clusters with no true
#            counterpart, the true side holds clusters that were never
#            reconstructed, and their counts need not agree.
# 'pairs' -- only the 1-to-1 matched true-reco pairs whose true side is a
#            neutrino: the same physical objects seen twice, so a difference
#            between the sides is a reconstruction effect rather than a
#            difference of population.
VERSION_DIRNAME = {
    'all':   'all_true_all_selected_reco_clusters',
    'pairs': 'pair_true_reco_clusters',
}


def select_matched_pair_records(reco_records, true_records, pair_metadata_list):
    """
    Narrow both sides to the 1-to-1 matched pairs whose TRUE side is a neutrino
    cluster: the reco clusters that were matched, and the true clusters they
    were matched to.

    The pairing is not recomputed here -- it is read off the same
    clusterpairmatching.MatchTrueToReco1to1 ->
    metadata.add_metadata_true_reco_pair_cluster records the notebooks already
    produce, so a cluster appears here if and only if the evaluation put it in a
    pair.

    Both sides are keyed on (event, cluster_id), so a cluster is kept only if
    THAT event's pairing contains it -- an id repeating across events cannot
    pull in the wrong cluster.

    Returns (reco_subset, true_subset). Their lengths agree up to the rare case
    of one reco cluster being the best match for two different true clusters,
    which MatchTrueToReco1to1 permits (it deduplicates on the true side only).
    """
    reco_keys, true_keys = set(), set()
    for pair in (pair_metadata_list or []):
        if nu_idx_from_true_cluster_id(pair.get('true_cluster_id')) is None:
            continue                                   # cosmic true cluster
        reco_keys.add((pair['event'], _cluster_key(pair['reco_cluster_id'])))
        true_keys.add((pair['event'], _cluster_key(pair['true_cluster_id'])))

    reco_subset = [r for r in (reco_records or [])
                   if (r['event'], _cluster_key(r['reco_cluster_id'])) in reco_keys]
    true_subset = [r for r in (true_records or [])
                   if (r['event'], _cluster_key(r['true_cluster_id'])) in true_keys]
    return reco_subset, true_subset


def select_true_neutrino_records(true_records, nu_idx=None, in_volume_only=False,
                                 out_of_volume_only=False):
    """
    Keep only true NEUTRINO clusters, optionally of one interaction index and/or
    on one side of the volume boundary.

    in_volume_only=True requires vertex_in_volume to be exactly True, and
    out_of_volume_only=True requires it to be exactly False -- records where it
    is None (built without vertex_records, or an interaction with no vertex) are
    dropped by both rather than being assumed to fall on either side. Leaving
    both False keeps every neutrino cluster, which is the in-volume set and the
    out-of-volume set combined, plus any such unknown-vertex cluster.
    """
    if in_volume_only and out_of_volume_only:
        raise ValueError("in_volume_only and out_of_volume_only are mutually exclusive; "
                         "leave both False to keep in-volume and out-of-volume neutrinos together")

    selected = [r for r in (true_records or []) if r['is_neutrino']]
    if nu_idx is not None:
        selected = [r for r in selected if r['nu_idx'] == nu_idx]
    if in_volume_only:
        selected = [r for r in selected if r.get('vertex_in_volume') is True]
    if out_of_volume_only:
        selected = [r for r in selected if r.get('vertex_in_volume') is False]
    return selected


# ============================================================================
# DRAWING
# ============================================================================

def _values_for(records, key):
    """Non-None values of one variable (flash_time is None for unflashed clusters)."""
    return [r[key] for r in records if r.get(key) is not None]


def _bin_edges(values, fixed_range, n_bins, bin_width=None):
    """
    Bin edges for one variable, from its spec:

    - fixed range + bin count: the same edges for every selection and every
      level, so two histograms of that variable are directly comparable
    - fixed bin width: edges of that width, snapped OUTWARD to whole multiples
      of it, covering the data. The width is comparable across selections; the
      range follows the sample, so an unusually large value gets its own bin
      instead of falling off the end of a fixed range
    - neither: a 5%-padded data range split into n_bins, with a guard for the
      all-identical-value case
    """
    if fixed_range is not None:
        return np.linspace(fixed_range[0], fixed_range[1], n_bins + 1)

    if bin_width:
        low  = np.floor(float(np.min(values)) / bin_width) * bin_width
        high = np.ceil(float(np.max(values)) / bin_width) * bin_width
        # A width-binned variable here is a physical magnitude -- an energy, a
        # charge -- that starts at zero, and zero is a meaningful end of its
        # axis rather than an arbitrary edge. Start the axis there whenever the
        # data is non-negative, so two selections with different minima are
        # binned identically and neither begins part-way up its own range.
        # (Anything with negative values keeps the snapped data range.)
        if low > 0:
            low = 0.0
        if high <= low:                      # every value in one bin
            high = low + bin_width
        return np.arange(low, high + bin_width / 2, bin_width)

    low, high = float(np.min(values)), float(np.max(values))
    if high <= low:
        pad = abs(low) * 0.05 or 0.5
        low, high = low - pad, high + pad
    else:
        pad = (high - low) * 0.05
        low, high = low - pad, high + pad
    return np.linspace(low, high, n_bins + 1)


def _plot_histogram(ax, values, edges, color, label=None, linestyle='-', linewidth=1.2,
                    marker='o', draw_line=True, draw_markers=True, draw_errors=False):
    """
    Draw a 1D histogram as a step OUTLINE, as POINTS at the bin centers, or as
    both -- never as filled bars. Several of these selections hold only a
    handful of clusters, where filled bars read as a few isolated blocks;
    outline and points both keep the shape of the distribution (including the
    empty bins between entries) visible, and let two populations be overlaid on
    one axis without one hiding the other.

    Binning always goes through ax.hist, whichever style is drawn: with
    draw_line=False the step is drawn at zero linewidth purely to produce the
    counts, so the points sit on exactly the bins ax.hist made. There is never
    a second, independently binned copy of the data that could drift out of
    step with the line.

    The label goes on whichever element is visible, so the legend key matches
    what the plot actually shows -- a line swatch for a line, a marker for
    points.

    draw_errors adds a statistical uncertainty bar per bin: sqrt(N) on a bin
    holding N clusters, i.e. a relative uncertainty of 1/sqrt(N) -- the Poisson
    error on a count. Empty bins get no bar (sqrt(0) = 0, nothing to draw).
    """
    counts, edges, _ = ax.hist(values, bins=edges, histtype='step', color=color,
                               linewidth=linewidth if draw_line else 0,
                               linestyle=linestyle,
                               label=label if draw_line else None)
    centers = (edges[:-1] + edges[1:]) / 2
    if draw_errors:
        filled = counts > 0
        ax.errorbar(centers[filled], counts[filled], yerr=np.sqrt(counts[filled]),
                    fmt='none', ecolor=color, **_ERROR_BAR_KWARGS)
    if draw_markers:
        ax.plot(centers, counts, linestyle='none', marker=marker, markersize=6,
                color=color, markerfacecolor=color, markeredgecolor=color,
                label=None if draw_line else label)
    return counts


def _legend_handle(ax, style):
    """
    Proxy artist standing for one side in the legend, matching how that side is
    actually drawn.

    Without this, matplotlib takes its key straight from the artist: a step
    histogram is a Polygon, whose key is a filled BOX outline -- nothing like
    the dotted line on the plot -- and a points-with-uncertainties side keyed
    off its markers shows a bare point with no error bar. Both are drawn here
    instead: a plain line for a line, a point WITH its error bar for points.

    The proxy carries no data, so it adds nothing to the axes; the errorbar
    variant has to be created on the axes (rather than constructed standalone)
    because only ax.errorbar builds the container the legend renders.
    """
    color = style['color']
    if style['draw_line']:
        return Line2D([], [], color=color, linestyle=style['linestyle'], linewidth=style['linewidth'])
    if style.get('draw_errors'):
        return ax.errorbar([], [], yerr=[], fmt=style['marker'], color=color, ecolor=color,
                           markersize=6, linestyle='none', **_ERROR_BAR_KWARGS)
    return Line2D([], [], color=color, marker=style['marker'], linestyle='none', markersize=6)


def _finish_axes(ax, xlabel, ylabel='Number of Clusters', title=None, legend=False,
                 title_fontsize=_TITLE_FONTSIZE, axis_label_fontsize=_AXIS_LABEL_FONTSIZE,
                 legend_fontsize=_LEGEND_FONTSIZE, legend_handles=None, legend_labels=None):
    """
    Common finishing for every axes here: labels, tick sizes, grid, y range and
    legend.

    The y-axis starts at 0 (counts are never negative and the curve should sit
    on the axis) and is extended by _Y_HEADROOM above the tallest bin, so the
    legend and the stats box -- both anchored to the top of the axes -- have
    room of their own instead of landing on the distribution.

    Pass legend_handles/legend_labels (from _legend_handle) to key the legend on
    proxies instead of on the plotted artists; without them the legend is built
    the default way, from whatever carries a label.
    """
    ax.set_xlabel(xlabel, fontsize=axis_label_fontsize, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=axis_label_fontsize, fontweight='bold')
    ax.tick_params(axis='both', labelsize=_TICK_LABEL_FONTSIZE)
    if title:
        ax.set_title(title, fontsize=title_fontsize, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.3)

    _, y_top = ax.get_ylim()
    ax.set_ylim(0, y_top * (1 + _Y_HEADROOM) if y_top > 0 else 1)

    if legend:
        # upper LEFT, opposite the stats box in the upper right, so the two
        # never collide with each other either.
        legend_args = ([legend_handles, legend_labels] if legend_handles is not None else [])
        ax.legend(*legend_args, fontsize=legend_fontsize, loc='upper left', framealpha=0.9)


def _stats_text(values):
    values = np.asarray(values, dtype=float)
    return (f"entries = {len(values)}\n"
            f"mean    = {values.mean():.3f}\n"
            f"std     = {values.std():.3f}\n"
            f"min     = {values.min():.3f}\n"
            f"max     = {values.max():.3f}")


def draw_cluster_variable_distributions(records, output_dir, level_name, filename_prefix, apa,
                                        file_name=None, kind="reco", selection_label=None,
                                        variables=None, write_text_table=True):
    """
    1D histograms of the per-cluster variables, one PNG per variable plus one
    overview PNG with every variable side by side. Level-agnostic: pass one
    event's records, one file's, or the whole job's -- the shape of the output
    is identical, which is what makes an event-level plot a slice of the
    job-level one.

    Parameters:
    - records: from build_reco_cluster_variable_records() or
        build_true_cluster_variable_records(), optionally passed through the
        selectors above
    - output_dir: output directory (created if missing) -- one directory per
        selection, so the same filenames never collide between selections
    - level_name: title label ('Event 3', 'File Level', 'Job Level')
    - filename_prefix: filename suffix ('event_3', 'file', 'job')
    - apa: APA label (e.g. 'Combined')
    - file_name: optional input file name for the title
    - kind: 'reco' or 'true' -- picks the default variable list and the color
    - selection_label: which selection these records are ('all selected reco
        clusters', '1-to-1 matched to true neutrino', ...); goes in the title
        and the text table header so a plot is readable on its own
    - variables: override the (key, label, unit, range, n_bins) spec list
    - write_text_table: also write {kind}_cluster_variables.txt, one row per
        cluster, so the numbers behind the histograms can be checked directly

    An empty selection is NOT silently skipped: the text table is still written
    with a "0 clusters" note, so an empty directory always means the code did
    not run rather than the selection being genuinely empty.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if variables is None:
        variables = RECO_VARIABLE_SPECS if kind == "reco" else TRUE_VARIABLE_SPECS
    style = _KIND_STYLE.get(kind, _KIND_STYLE['reco'])

    id_key = 'reco_cluster_id' if kind == "reco" else 'true_cluster_id'

    if write_text_table:
        _write_cluster_variable_info(records, output_dir, kind, id_key, variables,
                                     level_name, selection_label, file_name)

    if not records:
        print(f"  [draw_variables] {kind} / {selection_label or 'unlabelled'} / {level_name}: "
              f"0 clusters -- no histogram drawn")
        return

    title_suffix = f'{level_name}, {apa}'
    if file_name:
        title_suffix += f' ({file_name})'
    if selection_label:
        title_suffix = f'{selection_label}\n{title_suffix}'

    # One PNG per variable.
    for key, label, unit, fixed_range, n_bins, bin_width in variables:
        values = _values_for(records, key)
        if not values:
            continue
        edges = _bin_edges(values, fixed_range, n_bins, bin_width)

        fig, ax = plt.subplots(figsize=(10, 6))
        _plot_histogram(ax, values, edges, **style)
        has_legend = key == 'flash_time'
        if has_legend:
            ax.axvspan(BEAM_WINDOW_MIN_US, BEAM_WINDOW_MAX_US, color='gold', alpha=0.25, label='beam-window')
        # Axis spans exactly the bins, with none of matplotlib's default padding:
        # for a variable that starts at zero (an energy, a charge) the padding put
        # the axis into negative values the quantity cannot take. Variables with a
        # fixed range are unaffected -- the edges ARE that range.
        ax.set_xlim(edges[0], edges[-1])
        _finish_axes(ax, f'{label} [{unit}]',
                     title=f'{kind.capitalize()} {label}: {title_suffix}', legend=has_legend)
        ax.text(0.98, 0.98, _stats_text(values), transform=ax.transAxes,
                fontsize=_STATS_BOX_FONTSIZE, family='monospace', ha='right', va='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        fig.savefig(output_dir / f'{kind}_{key}_{filename_prefix}_{apa}.png',
                    dpi=100, bbox_inches='tight', pad_inches=0.3)
        plt.close(fig)

    # Overview: every variable in one figure, for scanning a selection at a
    # glance. Skipped for a single variable, where it would be a second copy of
    # the plot just written rather than an overview of anything.
    n_vars = len(variables)
    if n_vars < 2:
        return

    n_cols = 2 if n_vars > 1 else 1
    n_rows = int(np.ceil(n_vars / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(8 * n_cols, 5 * n_rows), squeeze=False)
    for ax_idx, (key, label, unit, fixed_range, n_bins, bin_width) in enumerate(variables):
        ax = axes[ax_idx // n_cols][ax_idx % n_cols]
        values = _values_for(records, key)
        if not values:
            ax.text(0.5, 0.5, f'no {key} values', transform=ax.transAxes, ha='center', va='center')
            ax.set_axis_off()
            continue
        panel_edges = _bin_edges(values, fixed_range, n_bins, bin_width)
        _plot_histogram(ax, values, panel_edges, **style)
        if key == 'flash_time':
            ax.axvspan(BEAM_WINDOW_MIN_US, BEAM_WINDOW_MAX_US, color='gold', alpha=0.25)
        ax.set_xlim(panel_edges[0], panel_edges[-1])
        _finish_axes(ax, f'{label} [{unit}]', title=label)
        ax.text(0.98, 0.98, _stats_text(values), transform=ax.transAxes,
                fontsize=_STATS_BOX_FONTSIZE, family='monospace', ha='right', va='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    for ax_idx in range(n_vars, n_rows * n_cols):
        axes[ax_idx // n_cols][ax_idx % n_cols].set_axis_off()

    fig.suptitle(f'{kind.capitalize()} Cluster Variables: {title_suffix}',
                 fontsize=_TITLE_FONTSIZE + 2, fontweight='bold')
    fig.tight_layout()
    fig.savefig(output_dir / f'{kind}_cluster_variables_{filename_prefix}_{apa}.png',
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)


def draw_reco_true_comparison(reco_records, true_records, output_dir, level_name, filename_prefix, apa,
                              file_name=None, reco_label="reco (all selected clusters)",
                              true_label="true (all neutrinos)", variables=None, write_text_table=True):
    """
    Overlay the reco and true spatial distributions on shared axes: avg X, avg
    Y and avg Z of the two populations in the same bins, one PNG per variable
    plus an overview PNG.

    Only the spatial variables are compared -- there is no true-side flash
    time, so nothing to overlay it against.

    Both sides are drawn as RAW COUNTS, not normalised to each other: the
    difference in how many clusters each population has is itself part of what
    the comparison shows (e.g. every selected reco cluster vs one true cluster
    per neutrino interaction). Read the shapes against each other by eye and
    the entry counts off the legend; normalising would hide the second half of
    that.

    Parameters:
    - reco_records / true_records: the two populations to overlay, already
        selected (this function applies no selection of its own)
    - output_dir, level_name, filename_prefix, apa, file_name: as in
        draw_cluster_variable_distributions()
    - reco_label / true_label: legend labels, naming which selection each side is
    - variables: override the spec list (spatial variables by default)
    - write_text_table: also write reco_true_comparison.txt with each side's
        entries/mean/std/min/max per variable
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if variables is None:
        variables = SPATIAL_VARIABLE_SPECS

    # Overlay styles (_COMPARISON_STYLE, not _KIND_STYLE): reco a red dotted
    # step line, true black points with sqrt(N) uncertainties -- see that
    # constant for why true is drawn as points here but as a line on its own.
    sides = [
        (reco_label, reco_records, _COMPARISON_STYLE['reco']),
        (true_label, true_records, _COMPARISON_STYLE['true']),
    ]

    if write_text_table:
        with open(output_dir / 'reco_true_comparison.txt', 'w') as f:
            f.write(f'# reco vs true cluster variable comparison -- {level_name}\n')
            f.write(f'# reco: {reco_label}\n')
            f.write(f'# true: {true_label}\n')
            if file_name:
                f.write(f'# file: {file_name}\n')
            columns = [('variable', 14), ('side', 8), ('entries', 10),
                       ('mean', 14), ('std', 14), ('min', 14), ('max', 14)]
            f.write(''.join(name.ljust(width) for name, width in columns) + '\n')
            for key, label, unit, fixed_range, n_bins, bin_width in variables:
                for side_label, records, *_ in sides:
                    values = _values_for(records, key)
                    side = 'reco' if records is reco_records else 'true'
                    if not values:
                        row = [key, side, '0', 'n/a', 'n/a', 'n/a', 'n/a']
                    else:
                        values = np.asarray(values, dtype=float)
                        row = [key, side, str(len(values)), f'{values.mean():.3f}',
                               f'{values.std():.3f}', f'{values.min():.3f}', f'{values.max():.3f}']
                    f.write(''.join(v.ljust(width) for v, (_, width) in zip(row, columns)) + '\n')

    if not reco_records and not true_records:
        print(f"  [draw_variables] reco-true comparison / {level_name}: "
              f"0 clusters on both sides -- no histogram drawn")
        return

    title_suffix = f'{level_name}, {apa}'
    if file_name:
        title_suffix += f' ({file_name})'

    def _draw_onto(ax, key, label, unit, fixed_range, n_bins, bin_width, title, legend_fontsize):
        # Both sides share one set of edges so the two curves are bin-for-bin
        # comparable; the shared edges come from the spec's fixed range, or
        # from the two populations pooled when a variable has none.
        pooled = _values_for(reco_records, key) + _values_for(true_records, key)
        if not pooled:
            return False
        edges = _bin_edges(pooled, fixed_range, n_bins, bin_width)
        # Legend keys come from _legend_handle proxies, not from the plotted
        # artists: matplotlib would key the reco step histogram as a filled box
        # and the true side as a bare point, neither of which is what the plot
        # shows.
        handles, labels = [], []
        # Drawn back to front -- true (solid) first, reco (dotted) on top -- so
        # that where the two agree exactly the broken line stays visible over
        # the solid one instead of being covered by it.
        for side_label, records, side_style in reversed(sides):
            values = _values_for(records, key)
            if not values:
                continue
            _plot_histogram(ax, values, edges, **side_style)
            handles.append(_legend_handle(ax, side_style))
            labels.append(f'{side_label}: N={len(values)}, mean={np.mean(values):.1f}')
        # Legend back in reco-then-true order, whatever order they were drawn in.
        handles, labels = handles[::-1], labels[::-1]
        # The x axis spans exactly the bins, with none of matplotlib's default
        # padding: for a variable that starts at zero (an energy, a charge) the
        # padding put the axis into negative values that the quantity cannot
        # take. Variables with a fixed range keep it -- the edges ARE that range.
        ax.set_xlim(edges[0], edges[-1])
        # No stats box on these axes -- the entry count and mean of each side
        # are in its legend label -- so the legend takes the upper left and the
        # headroom _finish_axes adds keeps it off the curves.
        _finish_axes(ax, f'{label} [{unit}]', title=title, legend=True, legend_fontsize=legend_fontsize,
                     legend_handles=handles, legend_labels=labels)
        return True

    # One PNG per variable.
    for key, label, unit, fixed_range, n_bins, bin_width in variables:
        fig, ax = plt.subplots(figsize=(10, 6))
        if not _draw_onto(ax, key, label, unit, fixed_range, n_bins, bin_width,
                          f'Reco vs True {label}: {title_suffix}', _LEGEND_FONTSIZE):
            plt.close(fig)
            continue
        fig.savefig(output_dir / f'reco_true_{key}_{filename_prefix}_{apa}.png',
                    dpi=100, bbox_inches='tight', pad_inches=0.3)
        plt.close(fig)

    # Overview: all compared variables in one figure. Skipped for a single
    # variable -- see the note in draw_cluster_variable_distributions.
    n_vars = len(variables)
    if n_vars < 2:
        return

    n_cols = 2 if n_vars > 1 else 1
    n_rows = int(np.ceil(n_vars / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(8 * n_cols, 5 * n_rows), squeeze=False)
    for ax_idx, (key, label, unit, fixed_range, n_bins, bin_width) in enumerate(variables):
        ax = axes[ax_idx // n_cols][ax_idx % n_cols]
        if not _draw_onto(ax, key, label, unit, fixed_range, n_bins, bin_width, label, _LEGEND_FONTSIZE - 1):
            ax.text(0.5, 0.5, f'no {key} values', transform=ax.transAxes, ha='center', va='center')
            ax.set_axis_off()
    for ax_idx in range(n_vars, n_rows * n_cols):
        axes[ax_idx // n_cols][ax_idx % n_cols].set_axis_off()

    fig.suptitle(f'Reco vs True Cluster Variables: {title_suffix}',
                 fontsize=_TITLE_FONTSIZE + 2, fontweight='bold')
    fig.tight_layout()
    fig.savefig(output_dir / f'reco_true_cluster_variables_{filename_prefix}_{apa}.png',
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)


def draw_all_reco_true_variable_sets(reco_records, true_records, output_dir,
                                     level_name, filename_prefix, apa, file_name=None,
                                     reco_label='all selected reco clusters',
                                     true_label='all true neutrino clusters (in and out of volume)'):
    """
    Draw ONE reco population, ONE true population and their comparison for a
    single aggregation level:

      reco/                  every record in reco_records
      true/                  the NEUTRINO clusters among true_records, in and
                             out of volume together
      reco_true_comparison/  the two overlaid in the same bins

    Deliberately one selection per side. Earlier versions split the reco side
    five ways (matched-to-neutrino, single-neutrino events, nu_idx=2, nu_idx=1
    in volume) and the true side three (in volume, out of volume, both), which
    made it easy to compare two directories that did not describe the same
    clusters. The population being drawn is now named once, by the directory
    this is called into -- see draw_all_reco_true_variable_sets_versions.

    Called identically at event, file and job level.
    """
    output_dir = Path(output_dir)

    draw_cluster_variable_distributions(
        reco_records, output_dir / 'reco', level_name, filename_prefix, apa,
        file_name=file_name, kind='reco', selection_label=reco_label)

    true_neutrinos = select_true_neutrino_records(true_records)
    draw_cluster_variable_distributions(
        true_neutrinos, output_dir / 'true', level_name, filename_prefix, apa,
        file_name=file_name, kind='true', selection_label=true_label)

    draw_reco_true_comparison(
        reco_records, true_neutrinos, output_dir / 'reco_true_comparison',
        level_name, filename_prefix, apa, file_name=file_name,
        reco_label=f'reco ({reco_label})', true_label=f'true ({true_label})')


def draw_all_reco_true_variable_sets_versions(reco_records, true_records, pair_metadata_list,
                                              output_dir, level_name, filename_prefix, apa,
                                              file_name=None):
    """
    Draw the reco / true / comparison tree TWICE, once per population, into
    output_dir/<version>/ -- see VERSION_DIRNAME.

      all_true_all_selected_reco_clusters/
          every selected reco cluster against every true neutrino cluster (in
          and out of volume together). What the experiment actually has:
          nothing selects pairs without truth. The two sides are different
          objects and their counts need not agree.

      pair_true_reco_clusters/
          the reco clusters that were 1-to-1 matched to a true neutrino, and
          the true neutrino clusters they were matched to. The same physical
          objects seen twice, so a bin-by-bin difference is a reconstruction
          effect rather than the two samples containing different things.

    One selection per side in each, so any two directories being compared
    describe the same clusters.
    """
    output_dir = Path(output_dir)

    draw_all_reco_true_variable_sets(
        reco_records, true_records, output_dir / VERSION_DIRNAME['all'],
        level_name, filename_prefix, apa, file_name=file_name)

    paired_reco, paired_true = select_matched_pair_records(
        reco_records, true_records, pair_metadata_list)
    draw_all_reco_true_variable_sets(
        paired_reco, paired_true, output_dir / VERSION_DIRNAME['pairs'],
        level_name, filename_prefix, apa, file_name=file_name,
        reco_label='reco clusters of 1-to-1 true-reco pairs',
        true_label='true neutrino clusters of 1-to-1 true-reco pairs')

    return {'all': (reco_records, true_records), 'pairs': (paired_reco, paired_true)}


def _write_cluster_variable_info(records, output_dir, kind, id_key, variables,
                                 level_name, selection_label, file_name):
    """
    {kind}_cluster_variables.txt: one row per cluster behind the histograms,
    plus a header naming the selection. Written at every level from the same
    function, so an event-level table is that event's slice of the job-level
    one in the same format.
    """
    path = Path(output_dir) / f'{kind}_cluster_variables.txt'
    # total_charge / total_energy are columns in their own right AND histogrammed
    # variables; listed once each, in the fixed position, rather than twice.
    always_key = 'total_charge' if kind == "reco" else 'total_energy'
    variable_keys = [key for key, *_ in variables if key != always_key]

    columns = [('event', 15), (id_key, 18), ('n_points', 11)]
    columns += [('total_charge', 16)] if kind == "reco" else [('total_energy_MeV', 18)]
    columns += [(key, 14) for key in variable_keys]
    if kind == "true":
        columns += [('nu_idx', 9), ('vertex_in_volume', 18)]

    with open(path, 'w') as f:
        f.write(f'# {kind} cluster variables -- {level_name}\n')
        f.write(f'# selection: {selection_label or "all"}\n')
        if file_name:
            f.write(f'# file: {file_name}\n')
        f.write(f'# clusters: {len(records)}\n')
        f.write(''.join(name.ljust(width) for name, width in columns) + '\n')
        for record in sorted(records, key=lambda r: (str(r['event']), r[id_key])):
            values = [str(record['event']), f"{record[id_key]:.3f}", str(record['n_points'])]
            values += [f"{record['total_charge']:.2f}"] if kind == "reco" else [f"{record['total_energy']:.2f}"]
            values += [('n/a' if record.get(key) is None else f"{record[key]:.3f}") for key in variable_keys]
            if kind == "true":
                values += [str(record['nu_idx']), str(record.get('vertex_in_volume'))]
            f.write(''.join(v.ljust(width) for v, (_, width) in zip(values, columns)) + '\n')
    return path
