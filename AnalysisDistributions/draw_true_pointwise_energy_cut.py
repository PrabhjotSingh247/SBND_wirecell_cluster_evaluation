"""
TRUE POINT-WISE ENERGY CUT -- what a per-point energy threshold does to a
reco-true pair.

The existing true-side energy cut (apply_energy_cutoff) is a CLUSTER cut: it
drops a true cluster whose TOTAL deposited energy is below a threshold. This
module asks a different question -- what if individual true POINTS below a
threshold were dropped instead, leaving the cluster but thinning it?

The answer matters because the true cluster carries a wide halo of very small
deposits (neutron captures and other stragglers far from the vertex), and those
points sit in the completeness denominator and in the purity match even though
no reconstruction could plausibly find them.

WHAT IS DRAWN

One figure per pair, four rows of XZ / YZ / XY sharing axes per column:

    row 1   RECO cluster, beam window                      (reference)
    row 2   TRUE cluster, no point-wise cut                completeness, purity
    row 3   TRUE cluster, per-point energy > 1 MeV         recomputed
    row 4   TRUE cluster, per-point energy > 2 MeV         recomputed

Rows 3 and 4 re-run EvaluateCompleteness and EvaluatePurity against the SAME
reco cluster with the thinned true cluster, so the printed metrics are the ones
the pipeline would have produced had the cut been in the chain -- not a
rescaling of the row-2 numbers.

Plus a second figure: the distribution of per-point deposited energy for that
true cluster, with the thresholds marked, which is what says whether 1 and 2 MeV
are the interesting places to cut.

THE PIPELINE HERE MIRRORS DrawRecoTrueClusters.ipynb and its constants are
copied from it (see below). It is a separate implementation, so it is CHECKED
rather than trusted: run_pair() compares the row-2 metrics against the values
the notebook recorded for the same pair and reports any disagreement.
"""

from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from readfiles import read_charge_light_files_for_event
from selections import (
    build_true_points_charge_light, reassign_cluster_ID_true_charge_light,
    GroupClustersByID, apply_wire_readout_sensitive_yz_plane_cut_true,
    Fiducial_X_MIN, Fiducial_X_MAX, Fiducial_Y_MIN,
    Fiducial_Y_MAX, Fiducial_Z_MIN, Fiducial_Z_MAX,
    apply_energy_cutoff,
)
from metadata import build_cluster_flash_metadata, build_img_cluster_flash_metadata
from completeness_purity_estimate import EvaluateCompleteness, EvaluatePurity
from DrawRecoTrueFlashes import BEAM_WINDOW_MIN_US, BEAM_WINDOW_MAX_US

# PIPELINE -- copied from DrawRecoTrueClusters.ipynb. Changing a value there and
# not here makes the two disagree, which is what the check in run_pair() catches.
RADIUS_COMPLETENESS      = 2
RADIUS_PURITY_XZ         = 3
RADIUS_PURITY_YZ         = 5
RADIUS_PURITY_XY         = 5
PURITY_MIN_PROJECTIONS   = 2
MIN_RECOPOINTS_THRESHOLD = 5
MIN_CLUSTER_ENERGY       = 100
FIDUCIAL = dict(x_min=Fiducial_X_MIN, x_max=Fiducial_X_MAX,
                y_min=Fiducial_Y_MIN, y_max=Fiducial_Y_MAX,
                z_min=Fiducial_Z_MIN, z_max=Fiducial_Z_MAX)

# The per-point thresholds this study is about, in MeV. Row 2 is the uncut
# cluster, so 0.0 leads the list and every later entry adds one row.
#
# 1e-3 and 2e-3 MeV, i.e. 1 and 2 keV. Measured on chunk0 event 1: the median
# per-point deposit is 0.078 MeV and only 26 of 7036 points exceed 1 MeV, so
# cutting at 1 MeV deletes the neutrino rather than thinning its halo. These
# thresholds sit in the sparse low tail, which is the part no reconstruction
# could find.
POINT_ENERGY_CUTS_MEV = [0.0, 1e-3, 2e-3]

TRUE_ENERGY_COLUMN = 5     # per-point deposited energy, MeV

# This study's own tree under multi_file_plots_charge_light_matching, with the
# usual combined_apa_<timestamp>/ run directory inside it and one sub-directory
# per chunk below that.
OUTPUT_TREE_NAME = 'True_Pointwise_Energy_Cut'

_VIEWS = [(2, 0, 'Z (cm)', 'X (cm)', 'XZ'),
          (2, 1, 'Z (cm)', 'Y (cm)', 'YZ'),
          (0, 1, 'X (cm)', 'Y (cm)', 'XY')]
_ZOOM_MARGIN = 0.15
_TRUE_STYLE = dict(color='tab:red',  marker='.', s=8, alpha=0.55)
_RECO_STYLE = dict(color='tab:blue', marker='.', s=8, alpha=0.55)
_TITLE_FONTSIZE = 15
_LABEL_FONTSIZE = 12
_LEGEND_FONTSIZE = 10


def load_event(base_dir, evt, file_name='chunk0', reco_id_field='cluster_id',
               true_source_sce=True):
    """
    One event through the same chain DrawRecoTrueClusters.ipynb uses, as far as
    (true clusters, beam-window reco clusters).

    Returns (clusters_true, clusters_reco_beam, event_key).
    """
    event_key = f"{file_name}_{evt}"
    result = read_charge_light_files_for_event(base_dir, evt)

    # TRUE SIDE. sed-sce_smear_readout when true_source_sce -- the variant
    # carrying the space-charge displacement clustering-global's reco also has.
    true_key = 'true_clustering_sce' if true_source_sce else 'true_clustering'
    if result.get(true_key) is None:
        raise RuntimeError(f"event {event_key}: {true_key} missing")
    x_t, y_t, z_t, id_t, q_t, real_id_t, e_t, nu_idx_t = result[true_key]
    # build_true_points_charge_light, NOT a raw column_stack: it produces the
    # standard 7-column shape where column 5 is the per-point energy. The
    # reader's own tuple is ordered differently, so stacking it directly would
    # silently put real_cluster_id where the energy is meant to be -- and this
    # whole study cuts on that column. real_id_t, not id_t: cluster_id is the
    # coarser grouping that can merge physically distinct tracks.
    true_points = build_true_points_charge_light(
        x_t, y_t, z_t, real_id_t, q_t, energy=e_t, nu_idx=nu_idx_t)
    true_points = reassign_cluster_ID_true_charge_light(true_points)
    true_points = apply_wire_readout_sensitive_yz_plane_cut_true(true_points)
    true_points = apply_energy_cutoff(true_points, MIN_CLUSTER_ENERGY)
    clusters_true = GroupClustersByID(true_points)

    # RECO SIDE: clustering-global, then the beam-window cut bridged through
    # img-global exactly as the notebook does it.
    x_c, y_c, z_c, id_clu, q_c, real_id_clu = result['clustering']
    reco_ids = id_clu if reco_id_field == 'cluster_id' else real_id_clu
    predicted_points = np.column_stack((x_c, y_c, z_c, reco_ids, q_c))

    flash_records = build_cluster_flash_metadata(
        result['op'], file_name, evt, "Combined", event_key)
    img_flash_records = build_img_cluster_flash_metadata(
        result['reco'], result['clustering'], flash_records,
        file_name, evt, "Combined", event_key)
    beam_ids = {float(r['clustering_cluster_id']) for r in img_flash_records
                if BEAM_WINDOW_MIN_US <= r['flash_time'] <= BEAM_WINDOW_MAX_US}
    if reco_id_field == 'cluster_id':
        real_to_coarse = {float(r): float(c) for r, c in zip(real_id_clu, id_clu)}
        beam_ids = {real_to_coarse[r] for r in beam_ids if r in real_to_coarse}

    if len(predicted_points) and beam_ids:
        ids = np.fromiter(beam_ids, dtype=float, count=len(beam_ids))
        predicted_points = predicted_points[np.isin(predicted_points[:, 3], ids)]
    else:
        predicted_points = predicted_points[:0]
    clusters_reco = GroupClustersByID(predicted_points) if len(predicted_points) else {}
    return clusters_true, clusters_reco, event_key


def pair_metrics(clusters_true, clusters_reco, true_id, reco_id, event_key):
    """
    (completeness, purity) for ONE true/reco pair, from the same evaluators the
    pipeline uses and with the same radii.

    Both evaluators score every true cluster against every reco cluster, so the
    pair's entry is picked out of the full results rather than the evaluators
    being handed a single-cluster dict -- purity assigns each reco point to its
    NEAREST true cluster, so hiding the other true clusters would change it.
    """
    completeness = EvaluateCompleteness(clusters_true, clusters_reco, event_key,
                                        RADIUS_COMPLETENESS, MIN_RECOPOINTS_THRESHOLD)
    purity = EvaluatePurity(clusters_true, clusters_reco, event_key,
                            RADIUS_PURITY_XZ, RADIUS_PURITY_YZ, RADIUS_PURITY_XY,
                            min_projections=PURITY_MIN_PROJECTIONS)

    def pick(results, key):
        for r in results:
            if (float(r['true_cluster_id']) == float(true_id)
                    and float(r['reco_cluster_id']) == float(reco_id)):
                return r[key]
        return None

    # The key is 'completeness_energy_weighted', not 'completeness': the metric
    # is energy-weighted and the dict says so.
    return pick(completeness, 'completeness_energy_weighted'), pick(purity, 'purity')



def _energy_label(mev):
    """
    A threshold as a person would say it: '1 keV', not '0.001 MeV'.

    Everything else in this pipeline is in MeV, but these thresholds are three
    orders of magnitude below that and '0.001' invites a misread of where the
    decimal point is.
    """
    if mev >= 1.0:
        return f"{mev:g} MeV"
    if mev >= 1e-3:
        return f"{mev * 1e3:g} keV"
    return f"{mev * 1e6:g} eV"


def _cuts_tag(cuts):
    """
    Filename fragment naming the thresholds a figure was drawn at, e.g.
    'cuts_1keV_2keV'.

    Without it a second cut set overwrites the first: everything else in the
    stem is event and cluster ids, which do not change between them.
    """
    return 'cuts_' + '_'.join(_energy_label(c).replace(' ', '')
                              for c in cuts if c > 0)

def cut_true_points(points, min_point_energy_mev):
    """The true cluster keeping only points ABOVE min_point_energy_mev."""
    if points is None or not len(points) or min_point_energy_mev <= 0:
        return points
    points = np.asarray(points)
    return points[points[:, TRUE_ENERGY_COLUMN] > min_point_energy_mev]


def _draw_rows(rows, output_path, fig_title, header_lines):
    """
    len(rows) x 3 panels, one row per (row title, points, style, note).

    Axes are SHARED down each column, computed over EVERY point in the figure --
    including the uncut true cluster, which is the widest. That is deliberate:
    the point of rows 3 and 4 is which points disappeared, and on per-row limits
    a thinned cluster would simply re-zoom and look the same as the full one.
    """
    n = len(rows)
    fig, axes = plt.subplots(n, 3, figsize=(19, 5.0 * n), squeeze=False)
    everything = [np.asarray(p) for _, p, _, _ in rows if p is not None and len(p)]

    for col, (ix, iy, xlabel, ylabel, name) in enumerate(_VIEWS):
        lims = []
        for axis in (ix, iy):
            values = np.concatenate([p[:, axis] for p in everything]) if everything else None
            if values is None or not len(values):
                lims.append(None)
                continue
            lo, hi = values.min(), values.max()
            pad = max((hi - lo) * _ZOOM_MARGIN, 5.0)
            lims.append((lo - pad, hi + pad))

        for row, (row_title, points, style, note) in enumerate(rows):
            ax = axes[row][col]
            if points is not None and len(points):
                points = np.asarray(points)
                ax.scatter(points[:, ix], points[:, iy], **style)
            if lims[0]:
                ax.set_xlim(*lims[0])
            if lims[1]:
                ax.set_ylim(*lims[1])
            ax.set_xlabel(xlabel, fontsize=_LABEL_FONTSIZE, fontweight='bold')
            ax.set_ylabel(ylabel, fontsize=_LABEL_FONTSIZE, fontweight='bold')
            ax.set_title(f"{name} -- {row_title}", fontsize=_LABEL_FONTSIZE, fontweight='bold')
            ax.grid(True, linestyle='--', alpha=0.3)
            # The metrics go on the FIRST column only: they belong to the row,
            # not to the projection, and repeating them three times invites the
            # reader to look for a difference between the panels.
            if col == 0 and note:
                ax.text(0.02, 0.98, note, transform=ax.transAxes,
                        ha='left', va='top', fontsize=_LEGEND_FONTSIZE,
                        fontweight='bold', linespacing=1.5,
                        bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                                  edgecolor='gray', alpha=0.9))

    fig.suptitle(fig_title + "\n" + "   |   ".join(header_lines),
                 fontsize=_TITLE_FONTSIZE, fontweight='bold')
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=110, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    return output_path


def draw_point_energy_distribution(true_points, output_path, event_key, true_id,
                                   cuts=POINT_ENERGY_CUTS_MEV):
    """
    Per-point deposited energy for one true cluster, log-log.

    Log on BOTH axes because the distribution spans orders of magnitude in each
    -- the bulk of points sit far below 1 MeV while a few carry tens of MeV, and
    on linear axes the whole thing collapses into the first bin. The thresholds
    are drawn on it so what each one removes can be read directly, with the
    surviving fraction printed beside each.
    """
    energies = np.asarray(true_points)[:, TRUE_ENERGY_COLUMN]
    positive = energies[energies > 0]
    if not len(positive):
        return None

    fig, ax = plt.subplots(figsize=(11, 7))
    bins = np.logspace(np.log10(positive.min()), np.log10(positive.max()), 60)
    ax.hist(positive, bins=bins, histtype='step', color='tab:red', linewidth=1.8,
            label=f'true points ({len(energies)})')
    ax.set_xscale('log')
    ax.set_yscale('log')

    for cut, color in zip([c for c in cuts if c > 0], ('tab:blue', 'tab:green')):
        kept = int((energies > cut).sum())
        ax.axvline(cut, color=color, linestyle='--', linewidth=1.8,
                   label=f'> {_energy_label(cut)}: {kept} points '
                         f'({kept / len(energies) * 100:.1f}%), '
                         f'{energies[energies > cut].sum() / energies.sum() * 100:.1f}% of E')

    ax.set_xlabel('Per-point deposited energy (MeV)',
                  fontsize=_LABEL_FONTSIZE, fontweight='bold')
    ax.set_ylabel('True points', fontsize=_LABEL_FONTSIZE, fontweight='bold')
    ax.set_title(f'True point-wise deposited energy -- event {event_key}, '
                 f'true id {true_id:.0f}\n'
                 f'total {energies.sum():.0f} MeV in {len(energies)} points '
                 f'(median {np.median(energies):.3f} MeV)',
                 fontsize=_TITLE_FONTSIZE, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.set_axisbelow(True)
    ax.legend(fontsize=_LEGEND_FONTSIZE, framealpha=0.9)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    return output_path


def run_pair(base_dir, evt, true_id, reco_id, output_root, file_name='chunk0',
             cuts=POINT_ENERGY_CUTS_MEV, expected=None):
    """
    The whole study for one pair: the four-row figure, the energy distribution,
    and a text table of what each threshold did.

    `expected` is an optional (completeness, purity) the row-2 metrics must
    reproduce -- the notebook's own recorded values for this pair. It is checked
    rather than assumed, because the pipeline here is a second implementation of
    the notebook's and a silent drift between them would make every number on
    these figures wrong in a way no plot would reveal.

    Returns a dict of the paths written and the per-threshold rows.
    """
    clusters_true, clusters_reco, event_key = load_event(base_dir, evt, file_name)
    if true_id not in clusters_true:
        raise KeyError(f"true cluster {true_id} not in event {event_key} "
                       f"(have {sorted(clusters_true)})")
    if reco_id not in clusters_reco:
        raise KeyError(f"reco cluster {reco_id} not in beam window for {event_key} "
                       f"(have {sorted(clusters_reco)})")

    reco_points = clusters_reco[reco_id]
    full_true = np.asarray(clusters_true[true_id])
    total_energy = full_true[:, TRUE_ENERGY_COLUMN].sum()

    rows = [(f"RECO cluster (beam window), id {reco_id:g}",
             reco_points, _RECO_STYLE,
             f"reco points {len(reco_points)}")]
    table = []
    for cut in cuts:
        # The cut is applied to THIS cluster only, then the pair is rescored
        # against the same reco cluster. The other true clusters are left uncut:
        # the question is what dropping a neutrino's small deposits does to its
        # own metrics, and thinning everything at once would change which true
        # cluster each reco point is nearest and confound the two effects.
        thinned = cut_true_points(full_true, cut)
        variant = dict(clusters_true)
        variant[true_id] = thinned
        completeness, purity = pair_metrics(variant, clusters_reco, true_id,
                                            reco_id, event_key)
        kept_energy = np.asarray(thinned)[:, TRUE_ENERGY_COLUMN].sum() if len(thinned) else 0.0
        label = "no point cut" if cut <= 0 else f"per-point E > {_energy_label(cut)}"
        note = (f"{label}\n"
                f"completeness {completeness:.4f}\n" if completeness is not None
                else f"{label}\ncompleteness n/a\n")
        note += (f"purity {purity:.4f}\n" if purity is not None else "purity n/a\n")
        note += (f"points {len(thinned)} / {len(full_true)}\n"
                 f"E {kept_energy:.0f} / {total_energy:.0f} MeV")
        rows.append((f"TRUE cluster -- {label}", thinned, _TRUE_STYLE, note))
        table.append({'cut_mev': cut, 'completeness': completeness, 'purity': purity,
                      'n_points': len(thinned), 'n_points_total': len(full_true),
                      'energy_mev': float(kept_energy), 'energy_total_mev': float(total_energy)})

    warning = None
    if expected is not None:
        got = (table[0]['completeness'], table[0]['purity'])
        if any(a is None or abs(a - b) > 5e-4 for a, b in zip(got, expected)):
            warning = (f"row-2 metrics {got} do not reproduce the notebook's "
                       f"{expected} -- the pipeline in this module has drifted "
                       f"from DrawRecoTrueClusters.ipynb")

    # output_root is the run directory itself -- this study has its own tree,
    # multi_file_plots_charge_light_matching/True_Pointwise_Energy_Cut/, rather
    # than living under DrawRecoTrueClusters. One sub-directory per chunk below.
    out = Path(output_root) / file_name
    stem = (f"true_pointwise_energy_cut_{file_name}_event{evt}"
            f"_recoID{reco_id:g}_trueID{true_id:.0f}_{_cuts_tag(cuts)}")
    rows_path = _draw_rows(
        rows, out / f"{stem}.png",
        f"True point-wise energy cut -- event {event_key}",
        [f"true id {true_id:.0f}", f"reco id {reco_id:g}",
         f"true E {total_energy:.0f} MeV", f"{len(full_true)} true points"])
    dist_path = draw_point_energy_distribution(
        full_true, out / f"{stem}_point_energy.png", event_key, true_id, cuts)

    lines = [f"TRUE POINT-WISE ENERGY CUT -- event {event_key}, "
             f"true id {true_id:.0f}, reco id {reco_id:g}", ""]
    lines.append(f"  {'cut (MeV)':>10s}{'completeness':>14s}{'purity':>9s}"
                 f"{'points':>9s}{'% points':>10s}{'E (MeV)':>10s}{'% E':>8s}")
    for r in table:
        lines.append(
            f"  {r['cut_mev']:>10g}"
            f"{(r['completeness'] if r['completeness'] is not None else float('nan')):>14.4f}"
            f"{(r['purity'] if r['purity'] is not None else float('nan')):>9.4f}"
            f"{r['n_points']:>9d}{r['n_points'] / r['n_points_total'] * 100:>9.1f}%"
            f"{r['energy_mev']:>10.0f}{r['energy_mev'] / r['energy_total_mev'] * 100:>7.1f}%")
    if warning:
        lines += ["", "WARNING: " + warning]
    text_path = out / f"{stem}.txt"
    text_path.write_text("\n".join(lines) + "\n")

    return {'rows_figure': rows_path, 'distribution': dist_path,
            'table_file': text_path, 'table': table, 'warning': warning,
            'event_key': event_key}


# ============================================================================
# AGGREGATE OVER THE WHOLE SAMPLE
#
# The per-pair figures answer "what does this cut do to THIS neutrino". Choosing
# a threshold needs the other question -- what does the per-point energy spectrum
# look like across every neutrino in the sample, and where do the points a
# reconstruction cannot find actually sit. That is what this section builds.
# ============================================================================

# Log-spaced, spanning what the per-point energies actually cover (1e-6 to 10 MeV
# on chunk0). Fixed rather than derived per run so histograms from different runs
# can be added.
POINT_ENERGY_BINS = np.logspace(-6, 1, 141)

# A true point further than this from ANY point of its paired reco cluster is
# counted as unreconstructed -- the isolated dots. 5 cm is well outside the
# completeness match radius (2 cm), so a point beyond it was not merely missed by
# a hair.
ISOLATION_RADIUS_CM = 5.0


def accumulate_pair(true_points, reco_points, totals):
    """
    Add one true cluster's per-point energies into `totals`, split by whether
    each point is near its paired reco cluster.

    totals is a dict of arrays created by new_totals(); it is updated in place so
    a whole job can be accumulated without holding every point in memory (the
    full sample is ~10 million true points).
    """
    from scipy.spatial import cKDTree

    energies = np.asarray(true_points)[:, TRUE_ENERGY_COLUMN]
    totals['all'] += np.histogram(energies, bins=POINT_ENERGY_BINS)[0]
    totals['n_points'] += len(energies)
    totals['energy_mev'] += float(energies.sum())

    if reco_points is None or not len(reco_points):
        return totals
    distance, _ = cKDTree(np.asarray(reco_points)[:, :3]).query(
        np.asarray(true_points)[:, :3], k=1)
    isolated = distance > ISOLATION_RADIUS_CM
    totals['isolated'] += np.histogram(energies[isolated], bins=POINT_ENERGY_BINS)[0]
    totals['core'] += np.histogram(energies[~isolated], bins=POINT_ENERGY_BINS)[0]
    totals['n_isolated'] += int(isolated.sum())
    totals['n_core'] += int((~isolated).sum())
    totals['energy_isolated_mev'] += float(energies[isolated].sum())
    totals['energy_core_mev'] += float(energies[~isolated].sum())
    totals['n_pairs'] += 1
    return totals


def new_totals():
    """An empty accumulator for accumulate_pair()."""
    zeros = lambda: np.zeros(len(POINT_ENERGY_BINS) - 1, dtype=float)
    return {'all': zeros(), 'isolated': zeros(), 'core': zeros(),
            'n_points': 0, 'n_isolated': 0, 'n_core': 0, 'n_pairs': 0,
            'energy_mev': 0.0, 'energy_isolated_mev': 0.0, 'energy_core_mev': 0.0}


def draw_aggregate_point_energy(totals, output_path, label='all files'):
    """
    The per-point true energy spectrum over the whole sample, one line.

    Measured over 5.8M points: the points a paired reco cluster covers and the
    points it does not have the SAME spectrum, so splitting the line by that
    tells the reader nothing a single line does not. What the line does show is
    where the deposits actually sit, which is what any threshold has to be
    chosen against.
    """
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.stairs(totals['all'], POINT_ENERGY_BINS, color='black', linewidth=1.8)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('Per-point deposited energy (MeV)',
                  fontsize=_LABEL_FONTSIZE, fontweight='bold')
    ax.set_ylabel('True points', fontsize=_LABEL_FONTSIZE, fontweight='bold')
    ax.set_title(f"True point-wise deposited energy -- {label}\n"
                 f"{totals['n_pairs']:,} paired neutrino clusters, "
                 f"{totals['n_points']:,} points, {totals['energy_mev']:,.0f} MeV",
                 fontsize=_TITLE_FONTSIZE, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.set_axisbelow(True)

    fig.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    return output_path
