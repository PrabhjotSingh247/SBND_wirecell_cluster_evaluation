"""
ENERGY RECONSTRUCTION VALIDATION -- driven by
EnergyReconstruction/EnergyReconstructionValidation.ipynb.

Applies the charge-to-energy calibrations fitted by EnergyFitting.ipynb to the
selected reco clusters and asks whether the resulting RECO ENERGY distribution
looks like the TRUE ENERGY distribution of the true neutrino clusters. The fit
said how well each model describes the pairs it was fitted on; this asks the
downstream question -- does the calibrated energy spectrum come out right.

THE THREE CALIBRATIONS are the models EnergyFitting.ipynb fitted, in the same
forms, all through the origin:

    linear      E(Q) = a*Q
    quadratic   E(Q) = a*Q + b*Q^2
    saturating  E(Q) = a*Q / (1 + c*Q)

Their parameters are NOT re-fitted here -- they are passed in from the notebook,
which records which fit run produced them. Refitting would make this a fit
notebook rather than a validation of one.

TWO POPULATIONS ARE COMPARED, and they are not the same objects:
  - reco: every selected reco cluster surviving the beam-window cut, calibrated
    to an energy. Cosmic and neutrino alike -- there is no truth information on
    the reco side to separate them with.
  - true: the true NEUTRINO clusters, at their true energy.
A difference between the two spectra is therefore not by itself a calibration
failure; the reco side contains in-spill cosmic clusters that have no
counterpart on the true side. Read the comparison for the SHAPE of the
neutrino-dominated bulk, not for a bin-by-bin match.

NOTE ON PROVENANCE: the calibrations were fitted on the BEFORE-beam-window-cut
sample (all true clusters, cosmic-dominated, over a wide charge range), and are
applied here to the AFTER-cut, neutrino-dominated one. That is the point of the
exercise -- a calibration is only useful if it transfers -- but it does mean a
mismatch here can come from the transfer rather than from the model's shape.

DRAWING is delegated to AnalysisDistributions/draw_variables.py, the
same module behind the Reco_Distributions.ipynb plots, so these come out in
identical style (step line for reco, points with sqrt(N) uncertainties for true,
same fonts, same stats box, same text tables) rather than being a second
implementation that drifts from it. The notebook puts that directory on sys.path.
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from draw_variables import (
    draw_cluster_variable_distributions, draw_reco_true_comparison,
    select_true_neutrino_records, nu_idx_from_true_cluster_id,
    select_matched_pair_records, VERSION_DIRNAME,
)
# Private helpers from the same module, imported deliberately: the side-by-side
# panel below has to draw the reco and true curves ITSELF (three overlays in one
# figure is not something draw_reco_true_comparison can express), and reusing
# these keeps it pixel-identical to the single-model plots instead of being a
# second implementation of the same style that drifts from them.
from draw_variables import (
    _plot_histogram, _legend_handle, _finish_axes, _bin_edges, _values_for,
    _COMPARISON_STYLE, _TITLE_FONTSIZE, _LEGEND_FONTSIZE,
)

# Energy binning for every plot here, MeV. Matches the energy binning of the
# histogram the calibrations were fitted from.
ENERGY_BIN_WIDTH_MEV = 100.0

# Calibration parameters, in the order the model's formula takes them:
#   linear     (a,)
#   quadratic  (a, b)
#   saturating (a, c)
# These are DEFAULTS -- the notebook passes its own, recording which fit run they
# came from. Keeping a set here means the module can be exercised on its own.
DEFAULT_MODEL_PARAMS = {
    'linear':     (2.91499e-05,),
    'quadratic':  (4.66830e-05, -5.63991e-13),
    'saturating': (5.47869e-05, 3.02913e-08),
}

ALL_MODELS = ('linear', 'quadratic', 'saturating')

# Where each model's plots go, and how it is labelled on them.
MODEL_DIRNAME = {model: f'{model}_fit' for model in ALL_MODELS}

# One colour and line style per calibration, for the figures that put all three
# on one axes. Distinct in BOTH, so the models stay separable where two of them
# land on the same bins -- which they routinely do, quadratic and saturating
# being nearly identical over the populated range.
MODEL_OVERLAY_STYLE = {
    'linear':     {'color': 'red',       'linestyle': ':',  'linewidth': 2.4,
                   'draw_line': True, 'draw_markers': False, 'draw_errors': False},
    'quadratic':  {'color': 'royalblue', 'linestyle': '--', 'linewidth': 2.2,
                   'draw_line': True, 'draw_markers': False, 'draw_errors': False},
    'saturating': {'color': 'seagreen',  'linestyle': '-',  'linewidth': 2.0,
                   'draw_line': True, 'draw_markers': False, 'draw_errors': False},
}

def reco_energy_from_charge(charge, model, params):
    """
    Reco energy (MeV) from reco cluster charge (ADC), for one calibration model.

    The three forms are written out here rather than imported from
    fit_energy_calibration so that this module depends only on the fitted
    NUMBERS, not on the fitting code: the parameters are what the fit produced,
    and the formula is what it fitted.
    """
    charge = np.asarray(charge, dtype=float)
    if model == 'linear':
        (a,) = params
        return a * charge
    if model == 'quadratic':
        a, b = params
        return a * charge + b * charge ** 2
    if model == 'saturating':
        a, c = params
        return a * charge / (1.0 + c * charge)
    raise ValueError(f"unknown model {model!r}; known models: {ALL_MODELS}")


def format_model(model, params):
    """One-line human-readable form of a calibration, for titles and tables."""
    if model == 'linear':
        return f"E = {params[0]:.4g}*Q"
    if model == 'quadratic':
        a, b = params
        return f"E = {a:.4g}*Q {'+' if b >= 0 else '-'} {abs(b):.4g}*Q^2"
    if model == 'saturating':
        a, c = params
        return f"E = {a:.4g}*Q / (1 {'+' if c >= 0 else '-'} {abs(c):.4g}*Q)"
    raise ValueError(f"unknown model {model!r}")


def energy_variable_spec(key, label, bin_width=ENERGY_BIN_WIDTH_MEV):
    """
    One entry of draw_variables' variable-spec format:
    (record key, axis label, unit, fixed range, bin count, bin width).

    Fixed WIDTH with a data-driven range, not a fixed range: energy has no upper
    bound to bin against, and a fixed top edge would silently drop the most
    energetic clusters.
    """
    return [(key, label, 'MeV', None, None, bin_width)]


# ============================================================================
# RECORD PREPARATION
# ============================================================================

def add_reco_energy(reco_records, model, params):
    """
    Copy reco cluster records with the calibrated energy attached.

    Adds two keys holding the same number: 'reco_energy' (what the reco-side
    plots histogram) and 'energy_MeV' (the COMMON key the reco-vs-true
    comparison bins both sides on -- the two sides call their energy different
    things, and draw_reco_true_comparison overlays one key).

    The input records are not modified: each model produces its own copy, so the
    three calibrations can be drawn from one set of clusters without any of them
    seeing another's numbers.
    """
    energies = reco_energy_from_charge([r['total_charge'] for r in reco_records], model, params) \
        if reco_records else np.array([])

    prepared = []
    for record, energy in zip(reco_records, energies):
        prepared.append(dict(record, reco_energy=float(energy), energy_MeV=float(energy)))
    return prepared


def add_true_energy_key(true_records):
    """
    Copy true cluster records with 'energy_MeV' set from 'total_energy', so the
    comparison can bin both sides on one key. Nothing is recomputed -- this is
    the same true cluster energy every other plot in the pipeline uses.
    """
    return [dict(record, energy_MeV=float(record['total_energy'])) for record in (true_records or [])]


# ============================================================================
# DRAWING
# ============================================================================

def draw_all_energy_validation_plots(reco_records, true_records, output_dir,
                                     level_name, filename_prefix, apa,
                                     file_name=None, model_params=None,
                                     bin_width=ENERGY_BIN_WIDTH_MEV,
                                     reco_population='all selected reco clusters',
                                     true_population='all true neutrino clusters (in and out of volume)'):
    """
    Every plot of ONE aggregation level, into output_dir:

      reco/<model>_fit/          calibrated reco energy of all selected reco
                                 clusters, one directory per calibration
      true/all_true_neutrinos/   true energy of the true neutrino clusters
      reco_true_comparison/<model>_fit/
                                 the two overlaid in the same bins, one
                                 directory per calibration
      reco_true_comparison/      all three side by side in one figure, on
                                 shared axes

    Called identically at event, file and job level -- just pass that level's
    records, exactly as draw_variables' own orchestrator does.

    Parameters:
    - reco_records: from draw_variables.build_reco_cluster_variable_records()
        (all selected reco clusters; the beam-window cut is applied upstream)
    - true_records: from draw_variables.build_true_cluster_variable_records();
        the neutrino selection is applied HERE, so the caller passes everything
    - model_params: {model: params}; defaults to DEFAULT_MODEL_PARAMS
    """
    output_dir = Path(output_dir)
    model_params = model_params or DEFAULT_MODEL_PARAMS

    true_neutrinos = select_true_neutrino_records(true_records)
    true_for_comparison = add_true_energy_key(true_neutrinos)

    # ---- reco: one calibrated energy spectrum per model ----
    for model in ALL_MODELS:
        params = model_params[model]
        prepared = add_reco_energy(reco_records, model, params)
        # Label 'Cluster energy', not 'Reco cluster energy': the drawer already
        # prefixes the title with the side ('Reco ...'). The formula goes on its
        # own line of the selection label rather than inline, which otherwise
        # runs the title off the figure.
        draw_cluster_variable_distributions(
            prepared, output_dir / 'reco' / MODEL_DIRNAME[model],
            level_name, filename_prefix, apa, file_name=file_name, kind='reco',
            selection_label=(f'{reco_population}, {model} calibration\n'
                             f'{format_model(model, params)}'),
            variables=energy_variable_spec('reco_energy', 'Cluster energy', bin_width))

    # ---- true: the neutrino energy spectrum, once (no calibration involved) ----
    draw_cluster_variable_distributions(
        true_neutrinos, output_dir / 'true' / 'all_true_neutrinos',
        level_name, filename_prefix, apa, file_name=file_name, kind='true',
        selection_label=true_population,
        variables=energy_variable_spec('total_energy', 'Cluster true energy', bin_width))

    # ---- comparison: calibrated reco energy against true neutrino energy ----
    for model in ALL_MODELS:
        params = model_params[model]
        prepared = add_reco_energy(reco_records, model, params)
        draw_reco_true_comparison(
            prepared, true_for_comparison,
            output_dir / 'reco_true_comparison' / MODEL_DIRNAME[model],
            level_name, filename_prefix, apa, file_name=file_name,
            reco_label=f'reco ({model})',
            true_label='true',
            variables=energy_variable_spec('energy_MeV', 'Cluster energy', bin_width))

    # ---- all three calibrations on one axes, in reco/ ----
    draw_reco_models_overlay(
        reco_records, output_dir / 'reco', level_name, filename_prefix, apa,
        file_name=file_name, model_params=model_params, bin_width=bin_width,
        population_label=reco_population)

    # ---- the same three comparisons side by side, on shared axes ----
    draw_energy_comparison_panel(
        reco_records, true_records, output_dir / 'reco_true_comparison',
        level_name, filename_prefix, apa, file_name=file_name,
        model_params=model_params, bin_width=bin_width)


def draw_reco_models_overlay(reco_records, output_dir, level_name, filename_prefix, apa,
                             file_name=None, model_params=None,
                             bin_width=ENERGY_BIN_WIDTH_MEV, population_label=None,
                             filename=None):
    """
    All three calibrated reco spectra on ONE axes, one colour and line style per
    calibration -- the same clusters, priced three ways.

    One set of bin edges for all three, pooled from every model's energies, so a
    difference between the curves is a difference between the calibrations and
    not between their binnings.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model_params = model_params or DEFAULT_MODEL_PARAMS

    energies_by_model = {
        model: [r['reco_energy'] for r in add_reco_energy(reco_records, model, model_params[model])]
        for model in ALL_MODELS
    }
    pooled = [e for energies in energies_by_model.values() for e in energies]
    if not pooled:
        print(f"  [draw_energy_validation] reco model overlay / {level_name}: "
              f"0 clusters -- no figure drawn")
        return None
    edges = _bin_edges(pooled, None, None, bin_width)

    fig, ax = plt.subplots(figsize=(11, 6.5))
    handles, labels = [], []
    # Drawn back to front: solid first, then dashed, then dotted. Two
    # calibrations can land on identical bins -- quadratic and saturating
    # routinely do over the populated range -- and a solid line drawn last
    # covers the dashes underneath it, making one curve look simply absent.
    # With the broken styles on top, the overlap reads as agreement.
    for model in reversed(ALL_MODELS):
        values = energies_by_model[model]
        if not values:
            continue
        style = MODEL_OVERLAY_STYLE[model]
        _plot_histogram(ax, values, edges, marker='o', **style)
        handles.append(_legend_handle(ax, dict(style, marker='o')))
        labels.append(f'{model}: N={len(values)}, mean={np.mean(values):.0f} MeV\n'
                      f'    {format_model(model, model_params[model])}')
    # Legend back in ALL_MODELS order, whatever order the curves were drawn in.
    handles, labels = handles[::-1], labels[::-1]

    title = f'Reco Cluster Energy, all calibrations: {level_name}, {apa}'
    if file_name:
        title += f' ({file_name})'
    if population_label:
        title = f'{population_label}\n{title}'
    ax.set_xlim(edges[0], edges[-1])
    _finish_axes(ax, 'Reco cluster energy [MeV]', title=title, legend=True,
                 legend_handles=handles, legend_labels=labels,
                 legend_fontsize=_LEGEND_FONTSIZE - 1)

    path = output_dir / (filename or f'reco_energy_all_models_{filename_prefix}_{apa}.png')
    fig.savefig(path, dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    return path


def draw_energy_comparison_panel(reco_records, true_records, output_dir,
                                 level_name, filename_prefix, apa, file_name=None,
                                 model_params=None, bin_width=ENERGY_BIN_WIDTH_MEV,
                                 filename=None):
    """
    All three calibrations side by side in ONE figure: three panels, each the
    calibrated reco spectrum overlaid on the same true neutrino spectrum.

    The panels share BOTH axes and one set of bin edges, computed from every
    model's energies and the true energies pooled together. That is the whole
    point of the figure -- three separately-scaled panels would let a model look
    better or worse than its neighbour purely through its axis range, and the
    question here is which calibration lands closest to the same fixed truth.

    The per-model plots in the subdirectories are unchanged and remain the ones
    to read numbers off; this is for the comparison at a glance.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model_params = model_params or DEFAULT_MODEL_PARAMS

    true_neutrinos = select_true_neutrino_records(true_records)
    true_energies = [r['total_energy'] for r in true_neutrinos]
    reco_by_model = {
        model: [r['reco_energy'] for r in add_reco_energy(reco_records, model, model_params[model])]
        for model in ALL_MODELS
    }

    pooled = list(true_energies) + [e for energies in reco_by_model.values() for e in energies]
    if not pooled:
        print(f"  [draw_energy_validation] comparison panel / {level_name}: "
              f"0 clusters on either side -- no figure drawn")
        return None
    edges = _bin_edges(pooled, None, None, bin_width)

    fig, axes = plt.subplots(1, len(ALL_MODELS), figsize=(7 * len(ALL_MODELS), 6),
                             sharex=True, sharey=True)
    axes = np.atleast_1d(axes)

    for ax, model in zip(axes, ALL_MODELS):
        params = model_params[model]
        handles, labels = [], []
        # true (solid) drawn first, reco (dotted) on top -- same reason as the
        # single-model comparisons: the broken line has to stay visible where
        # the two coincide.
        for label, values, style in (
                ('true (all neutrinos)', true_energies, _COMPARISON_STYLE['true']),
                (f'reco ({model})', reco_by_model[model], _COMPARISON_STYLE['reco'])):
            if not values:
                continue
            _plot_histogram(ax, values, edges, **style)
            handles.append(_legend_handle(ax, style))
            labels.append(f'{label}: N={len(values)}, mean={np.mean(values):.0f}')
        handles, labels = handles[::-1], labels[::-1]      # legend: reco, then true
        # Same as the single-model comparisons: axis spans exactly the bins, so
        # an energy axis starts at 0 rather than in negative padding.
        ax.set_xlim(edges[0], edges[-1])
        _finish_axes(ax, 'Cluster energy [MeV]', title=f'{model}\n{format_model(model, params)}',
                     legend=True, legend_fontsize=_LEGEND_FONTSIZE - 1,
                     legend_handles=handles, legend_labels=labels,
                     title_fontsize=_TITLE_FONTSIZE - 2)

    # Headroom, applied ONCE. _finish_axes stretches the y range by a fixed
    # fraction to keep the legend clear of the curves, but these axes are shared:
    # three calls compounded that stretch on the same limit and left the panels
    # sitting in the bottom third of the canvas. Set it here from the tallest bin
    # across every panel instead.
    tallest = max(
        [np.histogram(values, bins=edges)[0].max()
         for values in list(reco_by_model.values()) + [true_energies] if len(values)] or [1])
    axes[0].set_ylim(0, tallest * 1.45)

    suptitle = f'Reco vs True Cluster Energy, all calibrations: {level_name}, {apa}'
    if file_name:
        suptitle += f' ({file_name})'
    fig.suptitle(suptitle, fontsize=_TITLE_FONTSIZE + 1, fontweight='bold')
    fig.tight_layout()

    path = output_dir / (filename or f'reco_true_energy_all_models_{filename_prefix}_{apa}.png')
    fig.savefig(path, dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    return path


def draw_energy_validation_versions(reco_records, true_records, pair_metadata_list,
                                    output_dir, level_name, filename_prefix, apa,
                                    file_name=None, model_params=None,
                                    bin_width=ENERGY_BIN_WIDTH_MEV):
    """
    Draw every plot family TWICE, for the two populations, into
    output_dir/<version>/ -- see VERSION_DIRNAME:

      all_true_all_selected_reco_clusters/
          every selected reco cluster against every true neutrino cluster. The
          two sides are different objects: the reco side holds in-spill cosmic
          clusters with no true counterpart, and the true side holds neutrinos
          that were never reconstructed. Their counts need not agree.

      pair_true_reco_clusters/
          only the 1-to-1 matched pairs whose true side is a neutrino -- the
          same physical objects seen twice. Counts agree, and a bin-by-bin
          difference is the calibration getting that cluster's energy wrong
          rather than the two samples containing different things.

    The second is the sharper test of a calibration; the first is what the
    experiment actually has, since nothing selects pairs without truth.
    """
    output_dir = Path(output_dir)

    draw_all_energy_validation_plots(
        reco_records, true_records, output_dir / VERSION_DIRNAME['all'],
        level_name, filename_prefix, apa, file_name=file_name,
        model_params=model_params, bin_width=bin_width)

    paired_reco, paired_true = select_matched_pair_records(
        reco_records, true_records, pair_metadata_list)
    draw_all_energy_validation_plots(
        paired_reco, paired_true, output_dir / VERSION_DIRNAME['pairs'],
        level_name, filename_prefix, apa, file_name=file_name,
        model_params=model_params, bin_width=bin_width,
        reco_population='1-to-1 matched reco clusters (true side is a neutrino)',
        true_population='1-to-1 matched true neutrino clusters')
    return {'all': (reco_records, true_records), 'pairs': (paired_reco, paired_true)}


def write_calibration_summary(model_params, output_dir, source_note=None,
                              filename='calibrations_used.txt'):
    """
    Record which calibration each plot was drawn with, beside the plots.

    Without this the three reco directories are three spectra with no statement
    of what separates them, and the parameters live only in the notebook that
    produced them.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename

    lines = ["=" * 78, "CHARGE-TO-ENERGY CALIBRATIONS USED", "=" * 78]
    if source_note:
        lines.append(f"Source: {source_note}")
    lines.append("")
    for model in ALL_MODELS:
        params = model_params[model]
        lines.append(f"{model:<12s} {format_model(model, params)}")
        lines.append(f"             params = {tuple(float(p) for p in params)}")
    lines.append("")
    lines.append("Applied to the total charge (ADC) of every selected reco cluster.")
    lines.append("=" * 78)

    with open(path, 'w') as f:
        f.write("\n".join(lines) + "\n")
    return path
