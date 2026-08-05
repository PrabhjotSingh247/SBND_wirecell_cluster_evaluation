"""
CHARGE-TO-ENERGY CALIBRATION FIT -- driven by EnergyReconstruction/EnergyFitting.ipynb.

Reads the 2D histogram EnergyReconstruction.ipynb wrote (true cluster energy vs
reco cluster charge, a TH2D in a .root file) and fits the energy-vs-charge
relation, so that a measured charge can be turned into an energy.

THE FIT

Three models, all CONSTRAINED TO PASS THROUGH THE ORIGIN -- zero collected
charge must mean zero deposited energy, so none of them has a constant term:

    linear      E(Q) = a*Q
    quadratic   E(Q) = a*Q + b*Q^2
    saturating  E(Q) = a*Q / (1 + c*Q)

The saturating form is the one with the right ASYMPTOTIC behaviour: it rises
linearly with slope a at small charge and flattens to a plateau of a/c at large
charge, which is what the data does. The quadratic reproduces the same bend by
curving over, but a downward-curving parabola eventually turns around and
predicts energy DECREASING with charge -- fine inside the fit window, nonsense
outside it.

Fitted by WEIGHTED LEAST SQUARES over the histogram's filled bins: each bin
contributes its (x_center, y_center) with weight = its count, i.e. every pair in
the bin counts once. Minimised quantity is  S = sum_i n_i * (y_i - f(x_i))^2.

Binning discretises both axes, which adds a quantisation spread of
bin_width/sqrt(12) to each coordinate (about 29 MeV on a 100 MeV y bin). That is
small next to the physical scatter, but it is why the goodness-of-fit below
floors the per-bin uncertainty at that value rather than trusting a column whose
entries all happen to land in one y bin.

GOODNESS OF FIT is measured on the PROFILE, not on the raw bins: for each x
column the weighted mean y and its standard error give a point with a real
uncertainty, and chi2/ndf against those points is a meaningful number. A chi2
built from raw bin scatter instead would just be measuring the width of the
energy distribution at fixed charge, which no smooth curve can ever fit.

COMPARING THE MODELS takes two different tools, because they are not all nested:

  - linear is nested in BOTH of the others (b=0 gives the quadratic back, c=0
    the saturating one), so an F-test on the drop in S says whether the second
    parameter is earned in each case.
  - quadratic and saturating are NOT nested in each other -- two different
    two-parameter families. They have the same parameter count, so their S and
    chi2/ndf are directly comparable, and the AIC ranks all three on one scale.

chi2/ndf answers a different question from either: whether a curve describes the
profile at all. A model can win every comparison and still fit badly.

ROOT I/O uses UPROOT, not PyROOT: the ROOT installations on this machine
conflict and PyROOT does not import, while uproot reads the same files with no
ROOT at all.
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Default name of the TH2 written by EnergyReconstruction.ipynb
# (draw_energy_reconstruction.ROOT_HIST_NAME).
DEFAULT_HIST_NAME = 'true_energy_vs_reco_charge'

# Font sizes, matching the other modules in this directory.
_AXIS_LABEL_FONTSIZE = 15
_TITLE_FONTSIZE      = 16
_TICK_LABEL_FONTSIZE = 13
_LEGEND_FONTSIZE     = 12
_STATS_BOX_FONTSIZE  = 11

_COLORMAP    = 'viridis'
_MODEL_STYLE = {
    'linear':     {'color': 'red',         'linestyle': '-',   'linewidth': 2.4},
    'quadratic':  {'color': 'deepskyblue', 'linestyle': '--',  'linewidth': 2.4},
    'saturating': {'color': 'orange',      'linestyle': '-.',  'linewidth': 2.4},
}

# The models on offer, all through the origin. n_params drives the F-test and
# the AIC; 'nested_in' records which richer models contain this one as a special
# case, which is what makes an F-test between them valid.
MODELS = {
    'linear':     {'param_names': ['a'],      'formula': 'E = a*Q',
                   'nested_in': ('quadratic', 'saturating')},
    'quadratic':  {'param_names': ['a', 'b'], 'formula': 'E = a*Q + b*Q^2',
                   'nested_in': ()},
    'saturating': {'param_names': ['a', 'c'], 'formula': 'E = a*Q / (1 + c*Q)',
                   'nested_in': ()},
}
ALL_MODELS = ('linear', 'quadratic', 'saturating')
_PROFILE_COLOR = 'black'

# Columns holding fewer entries than this are dropped from the PROFILE (and so
# from chi2/ndf): a mean built from one or two pairs carries no usable
# uncertainty. They still enter the least-squares fit itself, which weights by
# count and needs no per-column error.
MIN_ENTRIES_PER_PROFILE_COLUMN = 3


# ============================================================================
# INPUT
# ============================================================================

def read_hist2d(root_path, hist_name=DEFAULT_HIST_NAME):
    """
    Read a TH2 from a .root file into plain numpy arrays.

    Returns a dict: {counts (nx, ny), x_edges, y_edges, x_centers, y_centers,
    n_entries, path, hist_name}. counts is indexed [x, y], the same convention
    np.histogram2d and uproot's writer use.
    """
    import uproot

    root_path = Path(root_path)
    with uproot.open(root_path) as root_file:
        hist = root_file[hist_name]
        counts  = np.asarray(hist.values(), dtype=float)
        x_edges = np.asarray(hist.axes[0].edges(), dtype=float)
        y_edges = np.asarray(hist.axes[1].edges(), dtype=float)

    return {
        'counts':     counts,
        'x_edges':    x_edges,
        'y_edges':    y_edges,
        'x_centers':  (x_edges[:-1] + x_edges[1:]) / 2,
        'y_centers':  (y_edges[:-1] + y_edges[1:]) / 2,
        'n_entries':  float(counts.sum()),
        'path':       str(root_path),
        'hist_name':  hist_name,
    }


def rebin_hist2d(hist, x_factor=1, y_factor=1):
    """
    Merge neighbouring bins, x_factor of them along the charge axis and
    y_factor along the energy axis, returning a new histogram dict (the input
    is left untouched).

    Coarser bins put more pairs into each column, which is what the PROFILE
    needs: a column's mean energy is only as good as the number of pairs behind
    it, and the sparse high-charge tail has columns holding one or two. Merging
    trades resolution in charge for columns that carry a usable uncertainty.

    If the bin count is not divisible by the factor, the leftover bins are
    folded into the LAST group rather than dropped -- no entry is ever lost, and
    the final bin is simply wider than the others. Any function here that works
    from bin centers (hist2d_to_points, profile_points) treats that bin like any
    other; nothing assumes uniform width.
    """
    counts  = hist['counts']
    x_edges = hist['x_edges']
    y_edges = hist['y_edges']

    def _merge(values, factor, axis):
        if factor <= 1:
            return values
        n = values.shape[axis]
        n_groups = max(n // factor, 1)
        # Split at group boundaries, with everything past the last boundary
        # falling into the final group.
        boundaries = [i * factor for i in range(1, n_groups)]
        pieces = np.split(values, boundaries, axis=axis)
        return np.stack([piece.sum(axis=axis) for piece in pieces], axis=axis)

    def _merge_edges(edges, factor):
        if factor <= 1:
            return edges
        n = len(edges) - 1
        n_groups = max(n // factor, 1)
        kept = [edges[i * factor] for i in range(n_groups)]
        kept.append(edges[-1])          # last edge always survives -- see docstring
        return np.array(kept, dtype=float)

    new_counts  = _merge(_merge(counts, x_factor, axis=0), y_factor, axis=1)
    new_x_edges = _merge_edges(x_edges, x_factor)
    new_y_edges = _merge_edges(y_edges, y_factor)

    rebinned = dict(hist)
    rebinned.update({
        'counts':    new_counts,
        'x_edges':   new_x_edges,
        'y_edges':   new_y_edges,
        'x_centers': (new_x_edges[:-1] + new_x_edges[1:]) / 2,
        'y_centers': (new_y_edges[:-1] + new_y_edges[1:]) / 2,
        'n_entries': float(new_counts.sum()),
        'rebin':     (x_factor, y_factor),
    })
    return rebinned


def hist2d_to_points(hist, x_max=None, y_max=None, x_min=0.0, y_min=0.0):
    """
    Flatten the filled bins of a histogram into (x, y, weight) arrays, keeping
    only bins whose CENTER lies inside the fit window.

    Selecting on the center means a bin straddling the window edge is in or out
    as a whole -- no bin is ever counted twice or split, and the same rule
    applies to the plots, so what is drawn is exactly what was fitted.

    Returns (x, y, w) with one entry per filled bin; w is the bin count.
    """
    x_centers, y_centers = hist['x_centers'], hist['y_centers']
    counts = hist['counts']

    x_ok = np.ones_like(x_centers, dtype=bool)
    y_ok = np.ones_like(y_centers, dtype=bool)
    if x_min is not None:
        x_ok &= x_centers >= x_min
    if x_max is not None:
        x_ok &= x_centers <= x_max
    if y_min is not None:
        y_ok &= y_centers >= y_min
    if y_max is not None:
        y_ok &= y_centers <= y_max

    window = x_ok[:, None] & y_ok[None, :] & (counts > 0)
    ix, iy = np.nonzero(window)
    return x_centers[ix], y_centers[iy], counts[ix, iy]


# ============================================================================
# FITTING
# ============================================================================

def _design_matrix(x, degree):
    """
    Columns of the model, WITHOUT a constant term -- that is what forces the fit
    through the origin. degree=1 -> [x]; degree=2 -> [x, x^2].
    """
    if degree == 1:
        return np.column_stack([x])
    if degree == 2:
        return np.column_stack([x, x ** 2])
    raise ValueError(f"degree must be 1 (linear) or 2 (quadratic), got {degree}")


def fit_through_origin(x, y, weights, degree, model_name=None):
    """
    Weighted least-squares fit of y against x through the origin.

    Parameters:
    - x, y, weights: from hist2d_to_points() -- bin centers and bin counts
    - degree: 1 for E = a*Q, 2 for E = a*Q + b*Q^2
    - model_name: label for plots and tables (defaults to 'linear'/'quadratic')

    Returns a dict with:
        params, param_errors : fitted coefficients and their uncertainties, in
            the order [a] or [a, b]
        residual_sum_squares : S = sum n_i (y_i - f(x_i))^2, the minimised
            quantity -- the F-test compares this between models
        sigma                : sqrt(S / (n_entries - n_params)), the typical
            distance of a single pair from the curve, in MeV
        r_squared            : weighted fraction of the variance about ZERO that
            the model explains. Note it is about zero, not about the mean:
            these models have no constant term, so the mean is not a special
            value they could fall back on
        predict              : callable, the fitted curve
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    w = np.asarray(weights, dtype=float)

    if model_name is None:
        model_name = {1: 'linear', 2: 'quadratic'}[degree]

    design = _design_matrix(x, degree)
    n_params  = design.shape[1]
    n_entries = float(w.sum())
    if n_entries <= n_params:
        raise ValueError(f"{model_name} fit needs more than {n_params} entries, got {n_entries}")

    # Solve the weighted normal equations by scaling rows with sqrt(w): the
    # least-squares solution of the scaled system is the weighted solution of
    # the original, and lstsq handles the rank-deficient case gracefully.
    sqrt_w = np.sqrt(w)
    params, *_ = np.linalg.lstsq(design * sqrt_w[:, None], y * sqrt_w, rcond=None)

    predicted = design @ params
    residuals = y - predicted
    rss       = float(np.sum(w * residuals ** 2))

    # Common per-entry spread, estimated from the fit itself, then propagated
    # into the parameter errors through the weighted normal matrix.
    variance      = rss / (n_entries - n_params)
    normal_matrix = design.T @ (design * w[:, None])
    covariance    = variance * np.linalg.inv(normal_matrix)
    param_errors  = np.sqrt(np.diag(covariance))

    total_sum_squares = float(np.sum(w * y ** 2))       # about zero, see docstring
    r_squared = 1.0 - rss / total_sum_squares if total_sum_squares > 0 else float('nan')

    coefficients = params.copy()

    def predict(x_new, _coefficients=coefficients, _degree=degree):
        x_new = np.asarray(x_new, dtype=float)
        return _design_matrix(x_new, _degree) @ _coefficients

    return {
        'model':                model_name,
        'degree':               degree,
        'param_names':          ['a', 'b'][:n_params],
        'params':               params,
        'param_errors':         param_errors,
        'covariance':           covariance,
        'n_params':             n_params,
        'n_entries':            n_entries,
        'n_bins':               int(len(x)),
        'residual_sum_squares': rss,
        'sigma':                float(np.sqrt(variance)),
        'r_squared':            float(r_squared),
        'predict':              predict,
    }


def saturating_model(x, a, c):
    """E = a*Q / (1 + c*Q): slope a at Q=0, plateau a/c as Q grows. Zero at zero."""
    return a * x / (1.0 + c * x)


def fit_saturating(x, y, weights, model_name='saturating'):
    """
    Weighted least-squares fit of the saturating form, which is non-linear in
    its parameters and so has to be solved iteratively (scipy.optimize.curve_fit)
    rather than by normal equations like the polynomials.

    curve_fit minimises sum(((y - f)/sigma)^2), so passing sigma = 1/sqrt(weight)
    minimises exactly the same weighted sum of squares as the polynomial fits --
    the three models are compared on one scale, not on two different ones.
    absolute_sigma=False then scales the covariance by the reduced chi2, i.e.
    estimates a common per-entry spread from the residuals, which is what
    fit_through_origin does analytically.

    The starting point is the linear fit's slope with c=0 -- the saturating model
    reduces to the linear one there, so the fit begins from a solution that is
    already reasonable and only has to bend it.
    """
    from scipy.optimize import curve_fit

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    w = np.asarray(weights, dtype=float)

    linear_start = fit_through_origin(x, y, w, degree=1)
    initial = [float(linear_start['params'][0]), 0.0]

    params, covariance = curve_fit(saturating_model, x, y, p0=initial,
                                   sigma=1.0 / np.sqrt(w), absolute_sigma=False,
                                   maxfev=20000)
    param_errors = np.sqrt(np.diag(covariance))

    residuals = y - saturating_model(x, *params)
    rss       = float(np.sum(w * residuals ** 2))
    n_entries = float(w.sum())
    n_params  = len(params)

    total_sum_squares = float(np.sum(w * y ** 2))       # about zero, see fit_through_origin
    r_squared = 1.0 - rss / total_sum_squares if total_sum_squares > 0 else float('nan')

    coefficients = params.copy()

    def predict(x_new, _coefficients=coefficients):
        return saturating_model(np.asarray(x_new, dtype=float), *_coefficients)

    return {
        'model':                model_name,
        'degree':               None,
        'param_names':          list(MODELS['saturating']['param_names']),
        'params':               params,
        'param_errors':         param_errors,
        'covariance':           covariance,
        'n_params':             n_params,
        'n_entries':            n_entries,
        'n_bins':               int(len(x)),
        'residual_sum_squares': rss,
        'sigma':                float(np.sqrt(rss / (n_entries - n_params))),
        'r_squared':            float(r_squared),
        'predict':              predict,
    }


def fit_model(x, y, weights, model):
    """
    Fit one named model from MODELS -- the single entry point the notebook uses,
    so adding a model here is the only change needed to have it fitted,
    compared, plotted and tabulated everywhere.
    """
    if model == 'linear':
        fit = fit_through_origin(x, y, weights, degree=1, model_name='linear')
    elif model == 'quadratic':
        fit = fit_through_origin(x, y, weights, degree=2, model_name='quadratic')
    elif model == 'saturating':
        fit = fit_saturating(x, y, weights)
    else:
        raise ValueError(f"unknown model {model!r}; known models: {sorted(MODELS)}")
    fit.setdefault('param_names', list(MODELS[model]['param_names']))
    return fit


def akaike_information_criterion(fit):
    """
    AIC for a least-squares fit with a common unknown spread:

        AIC = N * ln(S / N) + 2 * p

    The one yardstick that ranks NON-nested models -- quadratic against
    saturating, which no F-test can compare -- by trading goodness of fit
    against parameter count. Only DIFFERENCES between models on the same data
    mean anything; a gap of more than about 10 is decisive, under 2 is noise.

    Added to `fit` in place as 'aic' and returned.
    """
    n_entries = fit['n_entries']
    aic = float(n_entries * np.log(fit['residual_sum_squares'] / n_entries) + 2 * fit['n_params'])
    fit['aic'] = aic
    return aic


def rank_fits(fits):
    """
    Rank fits by AIC (lowest first), with each model's gap to the best.

    Returns {'ranking': [(model, aic, delta_aic), ...], 'best': model_name}.
    Read it beside each fit's chi2/ndf: the AIC says which of these curves is
    the best of the three, not that the best one is any good.
    """
    for fit in fits:
        if 'aic' not in fit:
            akaike_information_criterion(fit)
    ordered = sorted(fits, key=lambda f: f['aic'])
    best_aic = ordered[0]['aic']
    return {
        'ranking': [(f['model'], f['aic'], f['aic'] - best_aic) for f in ordered],
        'best':    ordered[0]['model'],
    }


def profile_points(x, y, weights, y_bin_width, min_entries=MIN_ENTRIES_PER_PROFILE_COLUMN):
    """
    Collapse the 2D distribution into one point per x column: the weighted mean
    y and the standard error of that mean.

    The uncertainty is floored at the y-axis quantisation, y_bin_width/sqrt(12),
    divided by sqrt(n): a column whose entries all land in a single y bin has
    zero measured spread, which is an artefact of the binning rather than an
    infinitely precise measurement, and would otherwise dominate chi2.

    Returns (x_column, mean_y, error_on_mean, n_per_column), each an array over
    the columns holding at least min_entries entries.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    w = np.asarray(weights, dtype=float)

    quantisation_sigma = y_bin_width / np.sqrt(12.0)

    columns, means, errors, counts = [], [], [], []
    for x_value in np.unique(x):
        in_column = x == x_value
        n = float(w[in_column].sum())
        if n < min_entries:
            continue
        y_column, w_column = y[in_column], w[in_column]
        mean = float(np.average(y_column, weights=w_column))
        # Population variance about that mean, then the standard error.
        variance = float(np.average((y_column - mean) ** 2, weights=w_column))
        error    = np.sqrt(max(variance, quantisation_sigma ** 2) / n)
        columns.append(float(x_value))
        means.append(mean)
        errors.append(float(error))
        counts.append(n)

    return (np.array(columns), np.array(means), np.array(errors), np.array(counts))


def chi_square_against_profile(fit, profile, min_entries=MIN_ENTRIES_PER_PROFILE_COLUMN):
    """
    chi2 and chi2/ndf of a fit against the profile points -- the goodness-of-fit
    number to quote. See the module docstring for why the profile, and not the
    raw bin scatter, is the right thing to test against.

    Adds the results to `fit` in place (chi2, ndf, chi2_per_ndf,
    n_profile_points) and returns it.
    """
    x_column, mean_y, error_y, _ = profile
    if len(x_column) <= fit['n_params']:
        fit.update({'chi2': float('nan'), 'ndf': 0, 'chi2_per_ndf': float('nan'),
                    'n_profile_points': int(len(x_column))})
        return fit

    residuals = mean_y - fit['predict'](x_column)
    chi2 = float(np.sum((residuals / error_y) ** 2))
    ndf  = int(len(x_column) - fit['n_params'])
    fit.update({'chi2': chi2, 'ndf': ndf, 'chi2_per_ndf': chi2 / ndf,
                'n_profile_points': int(len(x_column))})
    return fit


def compare_fits(simpler_fit, richer_fit):
    """
    F-test between two NESTED fits (linear inside quadratic): does the extra
    parameter reduce the residual sum of squares by more than chance?

        F = ((S_simple - S_rich) / (p_rich - p_simple)) / (S_rich / (N - p_rich))

    Returns {f_statistic, p_value, delta_params, preferred, reason}. p_value is
    None if scipy is unavailable -- the F statistic itself is still reported, and
    the chi2/ndf comparison stands on its own.

    'preferred' names the model this test favours at the 5% level; the caller
    should read it together with each model's chi2/ndf rather than on its own.
    """
    delta_params = richer_fit['n_params'] - simpler_fit['n_params']
    dof_residual = richer_fit['n_entries'] - richer_fit['n_params']

    numerator   = (simpler_fit['residual_sum_squares'] - richer_fit['residual_sum_squares']) / delta_params
    denominator = richer_fit['residual_sum_squares'] / dof_residual
    f_statistic = float(numerator / denominator) if denominator > 0 else float('inf')

    p_value = None
    try:
        from scipy import stats
        p_value = float(stats.f.sf(f_statistic, delta_params, dof_residual))
    except Exception:
        pass

    if p_value is not None:
        prefer_richer = p_value < 0.05
        reason = (f"F={f_statistic:.2f}, p={p_value:.3g} "
                  f"({'below' if prefer_richer else 'above'} 0.05)")
    else:
        prefer_richer = f_statistic > 4.0        # rough 5% threshold at large ndf
        reason = f"F={f_statistic:.2f} (scipy unavailable, no exact p-value)"

    return {
        'simpler':      simpler_fit['model'],
        'richer':       richer_fit['model'],
        'f_statistic':  f_statistic,
        'p_value':      p_value,
        'delta_params': delta_params,
        'preferred':    richer_fit['model'] if prefer_richer else simpler_fit['model'],
        'reason':       reason,
    }


def format_model(fit):
    """One-line human-readable form of the fitted model, e.g. 'E = 3.85e-05*Q'."""
    a = fit['params'][0]
    if fit['model'] == 'saturating':
        c = fit['params'][1]
        return f"E = {a:.4g}*Q / (1 {'+' if c >= 0 else '-'} {abs(c):.4g}*Q)"
    text = f"E = {a:.4g}*Q"
    if fit['model'] == 'quadratic':
        b = fit['params'][1]
        text += f" {'+' if b >= 0 else '-'} {abs(b):.4g}*Q^2"
    return text


def saturation_plateau(fit):
    """
    The energy the saturating model tends to as charge grows without bound,
    a/c -- the physical content of its second parameter. None for the other
    models, and None if c <= 0 (a fitted curve that never turns over).
    """
    if fit['model'] != 'saturating':
        return None
    a, c = fit['params']
    return float(a / c) if c > 0 else None


# ============================================================================
# DRAWING
# ============================================================================

def _finish_axes(ax, xlabel, ylabel, title, legend=True):
    ax.set_xlabel(xlabel, fontsize=_AXIS_LABEL_FONTSIZE, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=_AXIS_LABEL_FONTSIZE, fontweight='bold')
    ax.tick_params(axis='both', labelsize=_TICK_LABEL_FONTSIZE)
    ax.set_title(title, fontsize=_TITLE_FONTSIZE, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.3)
    if legend:
        ax.legend(fontsize=_LEGEND_FONTSIZE, loc='upper left', framealpha=0.9)


def _fit_label(fit):
    parameters = ", ".join(
        f"{name} = {value:.4g} ± {error:.2g}"
        for name, value, error in zip(fit['param_names'], fit['params'], fit['param_errors']))
    label = (f"{fit['model']}: {parameters}\n"
             f"    χ²/ndf = {fit.get('chi2_per_ndf', float('nan')):.2f}, "
             f"σ = {fit['sigma']:.0f} MeV")
    plateau = saturation_plateau(fit)
    if plateau is not None:
        label += f", plateau = {plateau:.0f} MeV"
    return label


def draw_fit(hist, fits, output_dir, profile=None, x_max=None, y_max=None,
             x_min=0.0, y_min=0.0, filename='energy_calibration_fit.png',
             title='Charge-to-Energy Calibration Fit', extrapolate_to=None,
             file_label=None):
    """
    The 2D histogram with every fitted curve drawn over it, plus the profile
    points the goodness-of-fit was measured against.

    Axis limits are the FIT WINDOW, so what is shown is what was fitted --
    unless extrapolate_to is given, in which case the x axis runs out to that
    value and the curves continue as dashed lines beyond the window, showing
    where each model would take a charge it was never fitted on.

    Parameters:
    - hist: from read_hist2d()
    - fits: list of fit dicts from fit_through_origin() (after
        chi_square_against_profile, so the labels can quote chi2/ndf)
    - output_dir: output directory (created if missing)
    - profile: (x, mean, error, n) from profile_points(); drawn as black points
    - x_min/x_max/y_min/y_max: the fit window, drawn as the axis range and, when
        extrapolating, marked with a dashed boundary
    - extrapolate_to: draw out to this x value with the curves dashed past x_max
    - file_label: extra line under the title, e.g. which ROOT file this came from
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    counts, x_edges, y_edges = hist['counts'], hist['x_edges'], hist['y_edges']
    # Blank the empty bins so an occupied bin holding one pair is
    # distinguishable from an empty one, as in the source plot.
    masked = np.ma.masked_where(counts <= 0, counts)

    # A config with no upper bound (the full-range fit) leaves x_max/y_max None;
    # fall back to the histogram's own extent so the axes still have a limit.
    x_hi = extrapolate_to if extrapolate_to is not None else x_max
    if x_hi is None:
        x_hi = float(x_edges[-1])
    y_hi = y_max if y_max is not None else float(y_edges[-1])
    if extrapolate_to is not None and y_max is not None:
        # The curves climb past the window when extrapolated; leave room for them.
        curve_max = max(float(np.max(fit['predict'](np.array([x_hi])))) for fit in fits)
        y_hi = max(y_max, curve_max) * 1.05

    fig, ax = plt.subplots(figsize=(11, 7.5))
    mesh = ax.pcolormesh(x_edges, y_edges, masked.T, cmap=_COLORMAP)
    colorbar = fig.colorbar(mesh, ax=ax)
    colorbar.set_label('Number of pairs', fontsize=_AXIS_LABEL_FONTSIZE, fontweight='bold')
    colorbar.ax.tick_params(labelsize=_TICK_LABEL_FONTSIZE)

    if profile is not None:
        x_column, mean_y, error_y, _ = profile
        ax.errorbar(x_column, mean_y, yerr=error_y, fmt='o', markersize=5,
                    color=_PROFILE_COLOR, ecolor=_PROFILE_COLOR, elinewidth=1.4,
                    capsize=3, label='profile (mean energy per charge bin)')

    x_curve = np.linspace(x_min or 0.0, x_hi, 400)
    for fit in fits:
        style = _MODEL_STYLE.get(fit['model'], {'color': 'white', 'linestyle': '-', 'linewidth': 2.0})
        inside = x_curve <= (x_max if x_max is not None else x_hi)
        ax.plot(x_curve[inside], fit['predict'](x_curve[inside]), label=_fit_label(fit), **style)
        if extrapolate_to is not None and (~inside).any():
            dashed = dict(style, linestyle=':')
            ax.plot(x_curve[~inside], fit['predict'](x_curve[~inside]), **dashed)

    if extrapolate_to is not None and x_max is not None:
        ax.axvline(x_max, color='white', linestyle='--', linewidth=1.5)
        ax.text(x_max, ax.get_ylim()[1], ' fit window ', color='white', fontsize=10,
                ha='right', va='top', rotation=90)

    ax.set_xlim(x_min or 0.0, x_hi)
    ax.set_ylim(y_min or 0.0, y_hi)

    full_title = title
    if file_label:
        full_title += f'\n{file_label}'
    _finish_axes(ax, 'Reco cluster charge [ADC]', 'True cluster energy [MeV]', full_title)

    fig.savefig(output_dir / filename, dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    return output_dir / filename


def draw_residuals(fits, profile, output_dir, filename='energy_calibration_residuals.png',
                   title='Fit Residuals (profile - fit)', file_label=None):
    """
    Profile-minus-fit residuals against charge, one series per model, with the
    profile's own error bars. This is where a wrong shape shows up: a linear fit
    that is really quadratic leaves a curved trend here even when its chi2/ndf
    looks tolerable.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    x_column, mean_y, error_y, _ = profile

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.axhline(0.0, color='grey', linewidth=1.2)
    for fit in fits:
        style = _MODEL_STYLE.get(fit['model'], {'color': 'black'})
        residuals = mean_y - fit['predict'](x_column)
        ax.errorbar(x_column, residuals, yerr=error_y, fmt='o', markersize=5,
                    color=style['color'], ecolor=style['color'], elinewidth=1.2, capsize=3,
                    label=(f"{fit['model']}: χ²/ndf = {fit.get('chi2_per_ndf', float('nan')):.2f}, "
                           f"RMS = {np.sqrt(np.mean(residuals ** 2)):.0f} MeV"))

    full_title = title
    if file_label:
        full_title += f'\n{file_label}'
    _finish_axes(ax, 'Reco cluster charge [ADC]', 'Energy residual [MeV]', full_title)

    fig.savefig(output_dir / filename, dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    return output_dir / filename


def write_fit_results(fits, comparisons, hist, window, output_dir, filename='fit_results.txt',
                      ranking=None):
    """
    The numbers behind the plots: the window, each model's parameters and
    goodness of fit, the F-tests between the nested pairs, the AIC ranking
    across all three, and a plain verdict.

    - comparisons: list of compare_fits() results (or a single one)
    - ranking: rank_fits() result; computed here if not given
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename

    lines = []
    lines.append("=" * 78)
    lines.append("CHARGE-TO-ENERGY CALIBRATION FIT")
    lines.append("=" * 78)
    lines.append(f"Input file : {hist['path']}")
    lines.append(f"Histogram  : {hist['hist_name']}  "
                 f"({hist['counts'].shape[0]}x{hist['counts'].shape[1]} bins, "
                 f"{hist['n_entries']:.0f} entries in total)")
    lines.append("")
    lines.append("Fit window (bins selected by their center):")
    lines.append(f"  charge: {window['x_min']:.4g} to {window['x_max']:.4g} ADC")
    lines.append(f"  energy: {window['y_min']:.4g} to {window['y_max']:.4g} MeV")
    lines.append(f"  entries in window: {window['n_entries']:.0f} "
                 f"({window['n_bins']} filled bins)")
    lines.append("")
    lines.append("All models are constrained to pass through the origin:")
    for model in ALL_MODELS:
        if any(fit['model'] == model for fit in fits):
            lines.append(f"  {model:<11s}{MODELS[model]['formula']}")
    lines.append("")
    for fit in fits:
        lines.append("-" * 78)
        lines.append(f"{fit['model'].upper()}:  {format_model(fit)}")
        lines.append("-" * 78)
        for name, value, error in zip(fit['param_names'], fit['params'], fit['param_errors']):
            lines.append(f"  {name} = {value:.6g} +/- {error:.3g}")
        if fit['params'][0] != 0:
            lines.append(f"  1/a = {1.0 / fit['params'][0]:.6g} ADC per MeV "
                         f"(slope at zero charge)")
        plateau = saturation_plateau(fit)
        if plateau is not None:
            lines.append(f"  plateau a/c = {plateau:.1f} MeV (energy as charge -> infinity)")
        if fit['model'] == 'quadratic' and fit['params'][1] < 0:
            turnover = -fit['params'][0] / (2 * fit['params'][1])
            lines.append(f"  TURNS OVER at Q = {abs(turnover):.4g} ADC -- beyond that this model "
                         f"predicts energy DECREASING with charge")
        lines.append(f"  residual sum of squares = {fit['residual_sum_squares']:.6g}")
        lines.append(f"  sigma (single pair)     = {fit['sigma']:.2f} MeV")
        lines.append(f"  R^2 (about zero)        = {fit['r_squared']:.5f}")
        lines.append(f"  chi2/ndf vs profile     = {fit.get('chi2', float('nan')):.2f} / "
                     f"{fit.get('ndf', 0)} = {fit.get('chi2_per_ndf', float('nan')):.3f}"
                     f"  ({fit.get('n_profile_points', 0)} profile points)")
        lines.append("")

    if isinstance(comparisons, dict):
        comparisons = [comparisons]
    if ranking is None:
        ranking = rank_fits(fits)

    lines.append("-" * 78)
    lines.append("MODEL COMPARISON")
    lines.append("-" * 78)
    lines.append("F-tests (valid only between NESTED models -- linear sits inside both of")
    lines.append("the others; quadratic and saturating are separate families and cannot be")
    lines.append("compared this way):")
    for comparison in comparisons:
        lines.append(f"  {comparison['simpler']} vs {comparison['richer']}: {comparison['reason']}"
                     f"  ->  prefers {comparison['preferred']}")
    lines.append("")
    lines.append("AIC ranking (lower is better; ranks all three, nested or not):")
    for model, aic, delta in ranking['ranking']:
        marker = '  <-- best' if delta == 0 else ''
        lines.append(f"  {model:<11s} AIC = {aic:12.2f}   dAIC = {delta:8.2f}{marker}")
    lines.append("  (dAIC under 2 is noise, over 10 is decisive)")
    lines.append("")
    lines.append("chi2/ndf against the profile (is the curve any good at all?):")
    for fit in fits:
        lines.append(f"  {fit['model']:<11s} chi2/ndf = {fit.get('chi2_per_ndf', float('nan')):.3f}"
                     f"   sigma = {fit['sigma']:.1f} MeV")
    best_by_chi2 = min(fits, key=lambda f: abs(f.get('chi2_per_ndf', float('inf')) - 1.0))
    lines.append(f"  closest to 1: {best_by_chi2['model']}")
    lines.append("")
    lines.append("VERDICT")
    lines.append(f"  best by AIC:      {ranking['best']}")
    lines.append(f"  best by chi2/ndf: {best_by_chi2['model']}")
    lines.append("")
    lines.append("These answer different questions. AIC and the F-tests rank the candidates")
    lines.append("against each other; chi2/ndf says whether the winner actually describes the")
    lines.append("profile. A model can win every comparison and still fit badly. And a model")
    lines.append("that fits inside the window can still be nonsense outside it -- see the")
    lines.append("turnover note above, and the extrapolated plot.")
    lines.append("=" * 78)

    with open(path, 'w') as f:
        f.write("\n".join(lines) + "\n")
    return path


# ============================================================================
# APPLYING A MODEL: reco energy, and how well it reproduces the true energy
# ============================================================================
# Each fitted model IS an energy estimator: feed it a cluster's charge and it
# returns that cluster's reconstructed energy. The two functions below turn a
# fit into exactly that, and then ask how good it is -- first as a 2D picture of
# reco against true energy, then as the 1D distribution of the fractional error
# (reco - true)/true, which is the number a resolution is quoted from.
#
# Both work from the same binned entries the fit used, so a pair enters the
# resolution at its bin's center rather than at its own charge and energy. The
# 100 MeV energy bins put a floor of about 29 MeV (bin/sqrt(12)) on any width
# measured this way -- negligible against the widths seen here, but it is why
# these numbers should not be quoted below the few-percent level.

# Bin width for the true-vs-reco energy plots, in MeV. Matches the energy
# binning of the source histogram, so a projection of that plot and this one are
# on the same footing.
ENERGY_BIN_WIDTH_MEV = 100.0

# Binning for the (reco - true)/true distribution. The range is generous enough
# to contain the tails of a badly-performing model rather than silently clipping
# them into the edge bins, where they would distort the Gaussian fit. The bin
# count is deliberately coarse (0.33 wide): the inputs are binned, so this ratio
# takes preferred values and comes out combed, and finer bins resolve that comb
# rather than the distribution -- which is what the Gaussian then has to fit.
#
# CAUTION at this width: the fitted core sigma is about 0.21, i.e. SMALLER THAN
# ONE BIN. A Gaussian cannot measure a width the binning does not resolve, so
# the sigma quoted here is a statement about the binning as much as about the
# data. Compare models at a width where the core spans several bins before
# concluding anything from it.
RESOLUTION_RANGE = (-1.5, 2.5)
RESOLUTION_N_BINS = 12


def _edges_around_values(values, fallback_width):
    """
    Bin edges placed at the MIDPOINTS between the distinct values present, with
    the outer two extended by half the adjacent spacing.

    This exists because of the gaps. Reco energy is not a continuous quantity
    here: it is a model evaluated at the CENTER of each charge bin, so it takes
    only as many distinct values as there are charge columns -- about a dozen
    over this window. Binning those on a uniform 100 MeV grid leaves empty
    columns wherever consecutive predictions are further apart than one bin
    (near zero charge the model climbs ~190 MeV per charge bin, so every other
    bin came out empty), and packs several into one bin where the model
    flattens. The gaps were an artefact of that mismatch, not a feature of the
    data.

    Midpoint edges give each distinct prediction its own bin, so the picture
    shows the population rather than the grid. The bins are then of UNEVEN
    width, and the colour scale is counts per bin, not a density -- which is the
    honest thing to show for a variable that only takes discrete values.
    """
    unique_values = np.unique(np.asarray(values, dtype=float))
    if len(unique_values) == 1:
        half = fallback_width / 2.0
        return np.array([unique_values[0] - half, unique_values[0] + half])

    midpoints = (unique_values[:-1] + unique_values[1:]) / 2.0
    first = unique_values[0] - (midpoints[0] - unique_values[0])
    last  = unique_values[-1] + (unique_values[-1] - midpoints[-1])
    return np.concatenate(([first], midpoints, [last]))


def _bin_edges(values, bin_width):
    """
    Edges of bin_width covering the data, snapped OUTWARD to whole multiples of
    it. Fixed width, data-driven range: the same choice made for the charge and
    energy axes of the source histogram, so these plots bin the same way it does.
    """
    low  = np.floor(float(np.min(values)) / bin_width) * bin_width
    high = np.ceil(float(np.max(values)) / bin_width) * bin_width
    if high <= low:
        high = low + bin_width
    return np.arange(low, high + bin_width / 2, bin_width)


def gaussian(x, amplitude, mean, sigma):
    """Plain Gaussian, the form fitted to the (reco - true)/true distribution."""
    return amplitude * np.exp(-0.5 * ((x - mean) / sigma) ** 2)


def resolution_values(fit, x, y):
    """
    Fractional energy error (reco - true)/true for every entry, with reco energy
    predicted from the charge by this fit.

    Returns (values, reco_energy). Entries with true energy <= 0 would divide by
    zero; none exist in these histograms (the lowest bin center is half a bin
    above zero), but they are dropped rather than assumed away -- see the mask
    returned by the caller if this ever changes.
    """
    reco_energy = fit['predict'](x)
    with np.errstate(divide='ignore', invalid='ignore'):
        values = (reco_energy - y) / y
    return values, reco_energy


def _seed_from_peak(counts, centers):
    """
    Starting values for the Gaussian, taken from the PEAK of the distribution
    rather than from its overall mean and spread.

    The distribution of (reco - true)/true is combed by the input binning -- reco
    energy comes from a handful of discrete charge bins, true energy from
    discrete energy bins, so their ratio takes preferred values -- and it has
    long one-sided tails. Seeding a fit with the overall mean and standard
    deviation of that shape starts it far from the peak and lets it converge on a
    broad, flat curve that describes nothing (seen in practice: sigma 0.86 on a
    distribution whose core is 6 times narrower).

    Width is seeded from the full width at half maximum, which is a property of
    the peak alone and is not moved by the tails.
    """
    peak_index = int(np.argmax(counts))
    peak_center = float(centers[peak_index])
    half_max = counts[peak_index] / 2.0

    above = np.nonzero(counts >= half_max)[0]
    if len(above) >= 2:
        bin_width = float(centers[1] - centers[0])
        fwhm = float(centers[above[-1]] - centers[above[0]]) + bin_width
        sigma_seed = fwhm / 2.355
    else:
        sigma_seed = float(centers[-1] - centers[0]) / 10.0

    return float(counts[peak_index]), peak_center, max(sigma_seed, 1e-3)


def fit_gaussian_to_resolution(values, weights, bin_range=RESOLUTION_RANGE,
                               n_bins=RESOLUTION_N_BINS, refit_within_sigma=2.0,
                               max_iterations=5, min_bins_in_window=None):
    """
    Fit a Gaussian to the CORE of the binned (reco - true)/true distribution.

    Seeded from the peak (see _seed_from_peak) and then refitted ITERATIVELY
    within mean +/- refit_within_sigma * sigma until the window stops moving.
    One pass is not enough: the first window is only as good as its seed, and a
    seed pulled off-peak by the tails takes the fit with it. Iterating lets the
    window walk onto the core and settle there, which is the usual practice for
    quoting a resolution.

    The tails are real and are drawn on the plot; the quoted sigma deliberately
    describes the core only, and raw_mean/raw_std beside it describe the whole
    distribution without any fit.

    Returns a dict with mean, sigma and amplitude (each with an error), the
    chi2/ndf of the final fit, the bin contents so the caller can draw exactly
    what was fitted, 'fit_range' (the window the numbers came from) and
    'n_iterations'.
    """
    from scipy.optimize import curve_fit

    counts, edges = np.histogram(values, bins=n_bins, range=bin_range, weights=weights)
    centers = (edges[:-1] + edges[1:]) / 2

    # Description of the whole distribution, tails included, needing no fit.
    inside = (values >= bin_range[0]) & (values <= bin_range[1])
    raw_mean = float(np.average(values[inside], weights=weights[inside]))
    raw_std  = float(np.sqrt(np.average((values[inside] - raw_mean) ** 2, weights=weights[inside])))

    seed = _seed_from_peak(counts, centers)

    def _fit(mask, p0):
        # Poisson errors on the bin counts; empty bins carry no information and
        # would give a zero error, so they are excluded rather than floored.
        use = mask & (counts > 0)
        if use.sum() < 4:
            return None
        errors = np.sqrt(counts[use])
        try:
            params, covariance = curve_fit(gaussian, centers[use], counts[use], sigma=errors,
                                           absolute_sigma=True, p0=p0, maxfev=20000)
        except (RuntimeError, ValueError):
            return None
        if not np.isfinite(covariance).all() or params[2] == 0:
            return None
        residuals = counts[use] - gaussian(centers[use], *params)
        chi2 = float(np.sum((residuals / errors) ** 2))
        ndf  = int(use.sum() - len(params))
        return {'params': params, 'errors': np.sqrt(np.diag(covariance)),
                'chi2': chi2, 'ndf': ndf,
                'chi2_per_ndf': chi2 / ndf if ndf > 0 else float('nan'),
                'n_bins_used': int(use.sum())}

    # First pass over a window set by the SEED, not over everything: starting
    # from the full range is what let the tails dominate.
    bin_width = float(centers[1] - centers[0])
    if min_bins_in_window is None:
        min_bins_in_window = max(5, n_bins // 4)
    minimum_half_width = min_bins_in_window * bin_width / 2.0

    def _window_around(mean, sigma):
        half_width = max(refit_within_sigma * abs(sigma), minimum_half_width)
        return (mean - half_width, mean + half_width)

    amplitude_seed, mean_seed, sigma_seed = seed
    window = _window_around(mean_seed, sigma_seed)
    result, n_iterations = None, 0

    for iteration in range(max_iterations):
        mask = (centers >= window[0]) & (centers <= window[1])
        attempt = _fit(mask, [amplitude_seed, mean_seed, sigma_seed])
        if attempt is None:
            break
        result, n_iterations = attempt, iteration + 1
        amplitude_seed, mean_seed, sigma_seed = attempt['params']
        sigma_seed = abs(sigma_seed)
        new_window = _window_around(mean_seed, sigma_seed)
        # Settled once the window stops moving by more than 1% of its width.
        if abs(new_window[0] - window[0]) + abs(new_window[1] - window[1]) < 0.01 * (window[1] - window[0]):
            window = new_window
            break
        window = new_window

    output = {
        'counts': counts, 'edges': edges, 'centers': centers,
        'raw_mean': raw_mean, 'raw_std': raw_std,
        'n_entries': float(weights.sum()), 'fit_range': (float(window[0]), float(window[1])),
        'converged': result is not None, 'n_iterations': n_iterations,
        'seed': {'amplitude': seed[0], 'mean': seed[1], 'sigma': seed[2]},
    }
    if result is None:
        output.update({'amplitude': float('nan'), 'mean': float('nan'), 'sigma': float('nan'),
                       'amplitude_error': float('nan'), 'mean_error': float('nan'),
                       'sigma_error': float('nan'), 'chi2': float('nan'), 'ndf': 0,
                       'chi2_per_ndf': float('nan')})
        return output

    amplitude, mean, sigma = result['params']
    amplitude_error, mean_error, sigma_error = result['errors']
    output.update({
        'amplitude': float(amplitude), 'mean': float(mean), 'sigma': float(abs(sigma)),
        'amplitude_error': float(amplitude_error), 'mean_error': float(mean_error),
        'sigma_error': float(sigma_error),
        'chi2': result['chi2'], 'ndf': result['ndf'], 'chi2_per_ndf': result['chi2_per_ndf'],
        'n_bins_used': result['n_bins_used'],
    })
    return output


def draw_reco_vs_true_energy(fit, x, y, weights, output_dir, file_label=None,
                             filename=None, title=None, bin_width=ENERGY_BIN_WIDTH_MEV):
    """
    2D histogram of TRUE cluster energy (y) against RECO cluster energy (x),
    where the reco energy is this model's prediction from the cluster's charge.

    The dashed diagonal is reco = true, i.e. a perfect estimator. How the
    population sits relative to that line is the whole content of the plot:
    parallel to it but offset means a bias, splayed away from it at one end
    means the model has the wrong shape there.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    _, reco_energy = resolution_values(fit, x, y)

    # x: one bin per distinct prediction (see _edges_around_values -- a uniform
    # grid leaves gaps, because reco energy takes only a dozen discrete values).
    # y: the true energies already sit on the source histogram's 100 MeV grid,
    # so a uniform grid of that width has no gaps to leave.
    x_edges = _edges_around_values(reco_energy, bin_width)
    y_edges = _bin_edges(y, bin_width)

    counts, _, _ = np.histogram2d(reco_energy, y, bins=[x_edges, y_edges], weights=weights)
    masked = np.ma.masked_where(counts <= 0, counts)

    fig, ax = plt.subplots(figsize=(10, 7.5))
    mesh = ax.pcolormesh(x_edges, y_edges, masked.T, cmap=_COLORMAP)
    colorbar = fig.colorbar(mesh, ax=ax)
    colorbar.set_label('Number of pairs', fontsize=_AXIS_LABEL_FONTSIZE, fontweight='bold')
    colorbar.ax.tick_params(labelsize=_TICK_LABEL_FONTSIZE)

    limit = max(float(x_edges[-1]), float(y_edges[-1]))
    ax.plot([0, limit], [0, limit], color='white', linestyle='--', linewidth=2,
            label='reco = true')

    fractional = (reco_energy - y) / y
    stats = (f"pairs   = {weights.sum():.0f}\n"
             f"model   = {fit['model']}\n"
             f"mean    = {np.average(fractional, weights=weights):+.3f}\n"
             f"std     = {np.sqrt(np.average((fractional - np.average(fractional, weights=weights)) ** 2, weights=weights)):.3f}")
    ax.text(0.98, 0.02, stats, transform=ax.transAxes, fontsize=_STATS_BOX_FONTSIZE,
            family='monospace', ha='right', va='bottom',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.85))

    ax.set_xlim(0, limit)
    ax.set_ylim(0, limit)
    full_title = title or f'True vs Reco Energy -- {fit["model"]} model\n{format_model(fit)}'
    if file_label:
        full_title += f'\n{file_label}'
    _finish_axes(ax, 'Reco cluster energy [MeV]', 'True cluster energy [MeV]', full_title)

    path = output_dir / (filename or f'true_vs_reco_energy_{fit["model"]}.png')
    fig.savefig(path, dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    return path


def draw_energy_resolution(fit, x, y, weights, output_dir, file_label=None,
                           filename=None, title=None, **gaussian_kwargs):
    """
    The (reco - true)/true distribution for one model, with the Gaussian fitted
    to its core drawn over it.

    Returns the fit_gaussian_to_resolution() result, so the caller can rank the
    models on the numbers rather than by eye. The shaded band marks the range
    the quoted Gaussian was actually fitted over -- everything outside it is
    tail that the width deliberately does not describe.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    values, _ = resolution_values(fit, x, y)
    gauss = fit_gaussian_to_resolution(values, weights, **gaussian_kwargs)

    counts, edges, centers = gauss['counts'], gauss['edges'], gauss['centers']

    fig, ax = plt.subplots(figsize=(10, 6.5))
    ax.hist(centers, bins=edges, weights=counts, histtype='step',
            color='black', linewidth=1.8, label='(reco - true)/true')
    ax.plot(centers, counts, linestyle='none', marker='o', markersize=4, color='black')

    if gauss['converged']:
        low, high = gauss['fit_range']
        ax.axvspan(low, high, color='gold', alpha=0.18, label='Gaussian fit range')
        fine = np.linspace(edges[0], edges[-1], 500)
        ax.plot(fine, gaussian(fine, gauss['amplitude'], gauss['mean'], gauss['sigma']),
                color='red', linewidth=2.2,
                label=(f"Gaussian: μ = {gauss['mean']:+.4f} ± {gauss['mean_error']:.4f}\n"
                       f"          σ = {gauss['sigma']:.4f} ± {gauss['sigma_error']:.4f}\n"
                       f"          χ²/ndf = {gauss['chi2_per_ndf']:.2f}"))
    ax.axvline(0.0, color='grey', linewidth=1.2, linestyle=':')

    stats = (f"pairs = {gauss['n_entries']:.0f}\n"
             f"mean  = {gauss['raw_mean']:+.3f}\n"
             f"std   = {gauss['raw_std']:.3f}")
    ax.text(0.98, 0.98, stats, transform=ax.transAxes, fontsize=_STATS_BOX_FONTSIZE,
            family='monospace', ha='right', va='top',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.85))

    full_title = title or f'Energy Resolution -- {fit["model"]} model\n{format_model(fit)}'
    if file_label:
        full_title += f'\n{file_label}'
    # Legend BELOW the axes, not inside them: the Gaussian's label runs to three
    # lines and the peak sits wherever the model's bias puts it, so any in-axes
    # corner is one model away from being covered.
    _finish_axes(ax, '(reco - true) / true', 'Number of pairs', full_title, legend=False)
    ax.legend(fontsize=_LEGEND_FONTSIZE, loc='upper center', bbox_to_anchor=(0.5, -0.18),
              ncol=3, framealpha=0.9)
    # Headroom so the stats box in the top corner clears the peak as well.
    _, y_top = ax.get_ylim()
    ax.set_ylim(0, y_top * 1.25)

    path = output_dir / (filename or f'energy_resolution_{fit["model"]}.png')
    fig.savefig(path, dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)

    gauss['model'] = fit['model']
    gauss['path'] = str(path)
    return gauss


def write_resolution_results(resolutions, fits, output_dir, filename='resolution_results.txt'):
    """
    One table ranking the models by how well they actually estimate energy:
    the Gaussian bias (mean) and resolution (sigma) of each model's
    (reco - true)/true distribution, beside the raw mean and spread that need no
    fit to be valid.

    The ranking is by |bias| and by sigma separately, because they are different
    failures: a biased-but-narrow estimator can be corrected by a scale factor,
    a wide one cannot.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename

    by_model = {fit['model']: fit for fit in fits}

    lines = []
    lines.append("=" * 88)
    lines.append("ENERGY RESOLUTION -- (reco - true)/true, per calibration model")
    lines.append("=" * 88)
    lines.append("Reco energy is each model's prediction from the cluster's charge; true energy is")
    lines.append("the true cluster energy. Gaussian mu/sigma come from a fit to the CORE of the")
    lines.append("distribution (refitted within +/-2 sigma), so long tails do not inflate the")
    lines.append("quoted width -- raw mean/std below describe the whole distribution, tails and all.")
    lines.append("")
    header = [('model', 12), ('pairs', 9), ('gauss_mean', 14), ('gauss_sigma', 15),
              ('chi2/ndf', 12), ('raw_mean', 12), ('raw_std', 12)]
    lines.append(''.join(name.ljust(width) for name, width in header))
    for resolution in resolutions:
        row = [resolution['model'], f"{resolution['n_entries']:.0f}",
               f"{resolution['mean']:+.4f}", f"{resolution['sigma']:.4f}",
               f"{resolution['chi2_per_ndf']:.2f}",
               f"{resolution['raw_mean']:+.4f}", f"{resolution['raw_std']:.4f}"]
        lines.append(''.join(v.ljust(width) for v, (_, width) in zip(row, header)))
    lines.append("")

    # Only fits that actually converged can be ranked; a failed fit carries nan,
    # and min() over nan silently returns whichever entry it saw first.
    converged = [r for r in resolutions if r.get('converged') and np.isfinite(r['sigma'])]
    if converged:
        smallest_bias  = min(converged, key=lambda r: abs(r['mean']))
        smallest_sigma = min(converged, key=lambda r: r['sigma'])
        lines.append(f"Smallest |bias|  : {smallest_bias['model']}  (mu = {smallest_bias['mean']:+.4f})")
        lines.append(f"Smallest sigma   : {smallest_sigma['model']}  (sigma = {smallest_sigma['sigma']:.4f})")
    else:
        lines.append("No Gaussian fit converged -- nothing to rank.")
    # Compared by model name: these dicts hold numpy arrays, and `in` on them
    # tries an elementwise comparison and raises.
    converged_models = {r['model'] for r in converged}
    failed = [r['model'] for r in resolutions if r['model'] not in converged_models]
    if failed:
        lines.append(f"Gaussian fit did NOT converge for: {', '.join(failed)}")
    lines.append("")
    lines.append("The two need not agree, and they fail differently: a biased but narrow")
    lines.append("estimator can be fixed with a scale factor, a wide one cannot.")
    lines.append("")
    lines.append("Models fitted:")
    for model, fit in by_model.items():
        lines.append(f"  {model:<12s} {format_model(fit)}")
    lines.append("=" * 88)

    with open(path, 'w') as f:
        f.write("\n".join(lines) + "\n")
    return path
