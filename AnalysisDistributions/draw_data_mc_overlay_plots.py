#!/usr/bin/env python3
"""
Data/MC overlay plots -- POT-normalize the NuMuCC (BNB Light) MC sample and
the off-beam data to the on-beam data's POT, then compare against on-beam
data. Reads the "All selected reco" TH1D each job already wrote (the same
histogram drawn as the black closure outline / data points in that job's own
figures), rather than re-running any selection.

Run at all three bin widths the source jobs wrote (200, 100 and 50 MeV), each
into its own subdirectory of OUT_DIR so the widths don't overwrite each other:
  Data_MC_Overlay_Plots/200MeV/...
  Data_MC_Overlay_Plots/100MeV/...
  Data_MC_Overlay_Plots/50MeV/...

Inputs (today's r3-nuecc/r3-mc-cv/data runs), per bin width W:
  MC (NuMuCC)   selection_performance_histograms_{W}MeV.root : selection_AfterBeamWindowCut_{W}MeV/all_selected_reco
  Off-beam data selected_reco_histograms_{W}MeV.root         : selection_AfterBeamWindowCut_{W}MeV/all_selected_reco
  On-beam data  selected_reco_histograms_{W}MeV.root         : selection_AfterBeamWindowCut_{W}MeV/all_selected_reco

POT / gates (given):
  POT_MC       = 4.535236e17
  POT_DataOn   = 4.941240e17
  gates_off    = 4.983220e5
  gates_on     = 1.030330e5
  POT_off = POT_DataOn * (gates_off / gates_on)   -- off-beam has no POT of its own,
  only gates, so its POT-equivalent is derived by scaling on-beam's POT by the
  gate-count ratio between the two data streams.

Scale factors:
  MC_scale  = POT_DataOn / POT_MC        -- MC "All selected reco" x MC_scale
  off_scale = POT_DataOn / POT_off = gates_on / gates_off  -- off-beam x off_scale
  on-beam data needs no scaling -- it defines the POT everything else is normalized to.
"""
import uproot
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, MaxNLocator
from pathlib import Path

# ============================================================================
# INPUTS
# ============================================================================
REPO = Path("/Users/prabhjotsingh/Experiments/SBND/WireCell_Reconstruction")
AD = REPO / "AnalysisDistributions"

MC_DIR = (AD / "multi_file_plots_charge_light_matching/Signal_Background_Distributions_BeforeCosmicTagger"
          "/NuMuCC_Sample/combined_apa_20260922_104834"
          "/job_summary/selection_reco")
OFFBEAM_DIR = (AD / "multi_file_plots_charge_light_matching/Signal_Background_Distributions_BeforeCosmicTagger_Data_OffBeam"
               "/combined_apa_20260922_115302"
               "/job_summary/selection_reco")
ONBEAM_DIR = (AD / "multi_file_plots_charge_light_matching/Signal_Background_Distributions_BeforeCosmicTagger_Data_OnBeam"
              "/combined_apa_20260922_115507"
              "/job_summary/selection_reco")

OUT_ROOT = AD / "multi_file_plots_charge_light_matching/Data_MC_Overlay_Plots"

POT_MC     = 4.535236e17
POT_DATAON = 4.941240e17
GATES_OFF  = 4.983220e5
GATES_ON   = 1.030330e5
POT_OFF    = POT_DATAON * (GATES_OFF / GATES_ON)

MC_SCALE  = POT_DATAON / POT_MC
OFF_SCALE = POT_DATAON / POT_OFF   # == GATES_ON / GATES_OFF

# ============================================================================
# STYLE -- matching draw_selection_performance.py / draw_signal_background.py
# ============================================================================
_AXIS_LABEL_FONTSIZE = 15
_TITLE_FONTSIZE      = 16
_TICK_LABEL_FONTSIZE = 13
_LEGEND_FONTSIZE      = 22  # doubled from the codebase default (11) for readability
_Y_HEADROOM_LINEAR   = 0.45
ENERGY_AXIS_TICK_MEV = 500.0
PLOT_X_MAX_MEV       = 3000.0

# All bins from here up are merged into one overflow bin, drawn filling the
# rest of the visible axis (threshold to PLOT_X_MAX_MEV) -- see
# merge_overflow's docstring for why (its true [threshold, 5000] span put the
# bin's own data point off the visible axis).
OVERFLOW_THRESHOLD_MEV = 1400.0

_TOTAL_STYLE  = dict(color='black', linestyle='-', linewidth=2.0)
_DATA_COLOR   = 'black'
_MC_COLOR     = 'tab:blue'
_OFF_COLOR    = 'lightgray'

# Same component list/colors/labels as SELECTION_COMPONENTS in
# draw_selection_performance.py (copied rather than imported -- that module's
# import chain reaches a notebook-only dependency (DrawRecoTrueFlashes) that
# isn't on the path for a standalone script). 'pinned' components keep a fixed
# stack position (declaration order, reversed, on top); the rest are stacked
# free, smallest-count first, below the pinned ones -- same rule
# order_components_for_stack uses.
MC_COMPONENTS = [
    {'key': 'high_signal_numu_CC', 'label': r'Candidate $\nu_\mu$ CC in-volume, Signal',
     'color': 'tab:blue',   'legend_rank': 0, 'pinned': True},
    {'key': 'high_signal_NC',      'label': 'Candidate NC in-volume, Signal',
     'color': 'tab:green',  'legend_rank': 1, 'pinned': True},
    {'key': 'high_signal_nue_CC',  'label': r'Candidate $\nu_e$ CC in-volume, Signal',
     'color': 'tab:orange', 'legend_rank': 2, 'pinned': True},
    {'key': 'contaminated',        'label': 'Contamination+Incomplete',
     'color': 'tab:cyan',   'legend_rank': 3, 'pinned': True},
    {'key': 'out_of_volume',       'label': 'Out-of-volume neutrinos',
     'color': 'tab:purple', 'legend_rank': 4, 'pinned': False},
    {'key': 'cosmic',              'label': 'Cosmic MC',
     'color': 'darkgray',  'legend_rank': 5, 'pinned': False},  # darker than off-beam's lightgray, so the two grey bands stay distinguishable
]


def order_mc_components_for_stack(components, totals):
    """Bottom-first drawing order: free (non-pinned) bands smallest-count
    first, then pinned bands in reverse declaration order on top -- mirrors
    draw_selection_performance.order_components_for_stack, adapted to work
    from summed counts (this script only has histograms, not record lists)."""
    pinned = [c for c in components if c['pinned']]
    free = sorted((c for c in components if not c['pinned']),
                  key=lambda c: totals[c['key']])
    return free + pinned[::-1]


def load_hist(path, hist_path):
    with uproot.open(path) as f:
        counts, edges = f[hist_path].to_numpy()
    return counts, edges


def drop_0_50_bin(counts_50, edges_50):
    """
    [0, 50) MeV drawn as an explicit ZERO-count bin rather than removed from
    the axis -- so the x-axis still starts at 0 and the missing content shows
    as a visible gap against that origin, instead of looking like the axis
    itself starts at 50. Every bin from 50 MeV on is a genuine 100 MeV bin,
    built by summing consecutive PAIRS of the finer 50 MeV histogram's bins:
    [50,150), [150,250), .... A leftover unpaired bin at the far tail (5000 is
    not reachable by an even number of 50 MeV steps from 50) is kept as its
    own bin rather than dropped -- it sits far past PLOT_X_MAX_MEV, so it
    never appears in a drawn figure, but the histogram stays a true partition
    of every count with none discarded."""
    assert edges_50[1] == 50.0, f"unexpected edges: {edges_50[:2]}"
    rest_counts = counts_50[1:]
    n_pairs = len(rest_counts) // 2
    paired   = rest_counts[:2 * n_pairs].reshape(n_pairs, 2).sum(axis=1)
    leftover = rest_counts[2 * n_pairs:]
    new_counts = np.concatenate(([0.0], paired, leftover))

    # n_pairs+1 boundary points at original (50 MeV) edge indices 1, 3, 5, ...
    # -- one more edge than there are appended if a leftover bin follows (its
    # far edge is the true axis end), none more if it doesn't (the last paired
    # edge already IS the axis end).
    paired_edges = edges_50[1 : 1 + 2 * n_pairs + 1 : 2]
    tail_edges = edges_50[-1:] if len(leftover) else edges_50[0:0]
    new_edges = np.concatenate(([0.0], paired_edges, tail_edges))
    return new_counts, new_edges


def merge_overflow(counts, edges, threshold=OVERFLOW_THRESHOLD_MEV, display_max=PLOT_X_MAX_MEV):
    """Collapse every bin from `threshold` up to the axis max into one bin,
    drawn from `threshold` to `display_max` (PLOT_X_MAX_MEV) -- filling the
    rest of the visible axis exactly, rather than either its true
    [threshold, 5000] span (which put the bin's own center off the visible
    axis, at (threshold+5000)/2, so its data point never showed) or a single
    ordinary-width bin (which left a bare stretch of empty axis after it).
    `threshold` must land exactly on an existing bin edge (true for both 100
    and 200 MeV binning here, since 1400 is a multiple of each)."""
    idx = int(np.searchsorted(edges, threshold))
    assert edges[idx] == threshold, f"{threshold} MeV is not on a bin edge: {edges}"
    new_edges  = np.append(edges[:idx + 1], display_max)
    new_counts = np.append(counts[:idx], counts[idx:].sum())
    return new_counts, new_edges


def style_axes(ax, edges, title, ymax=None, xmax=None):
    ax.set_xlabel('Reco Cluster Energy (MeV)', fontsize=_AXIS_LABEL_FONTSIZE, fontweight='bold')
    ax.set_ylabel('Number of Reco Clusters', fontsize=_AXIS_LABEL_FONTSIZE, fontweight='bold')
    ax.set_title(title, fontsize=_TITLE_FONTSIZE, fontweight='bold')
    ax.tick_params(axis='both', labelsize=_TICK_LABEL_FONTSIZE)
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.set_xlim(edges[0], xmax if xmax is not None else PLOT_X_MAX_MEV)
    ax.xaxis.set_major_locator(MultipleLocator(ENERGY_AXIS_TICK_MEV))
    if ymax is not None:
        ax.set_ylim(0, ymax)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))


def panel_ymax(edges, *count_arrays, xmax=None):
    """Shared y headroom across a set of before/after panels, so the same
    plot's two axes use one y-axis range and the height change from
    normalization is read directly off the axis rather than hidden by
    each panel rescaling itself."""
    limit = xmax if xmax is not None else PLOT_X_MAX_MEV
    tallest = 0.0
    for counts in count_arrays:
        visible = counts[edges[:-1] < limit]
        tallest = max(tallest, float(visible.max()) if len(visible) else 0.0)
    return max(tallest, 1.0) * (1 + _Y_HEADROOM_LINEAR)


def draw_step_panel(ax, edges, counts, label, title, ymax, xmax=None):
    ax.step(edges, np.append(counts, counts[-1]), where='post', label=label, **_TOTAL_STYLE)
    style_axes(ax, edges, title, ymax, xmax=xmax)
    ax.legend(fontsize=_LEGEND_FONTSIZE, loc='upper right', framealpha=0.9)


def draw_points_panel(ax, edges, counts, errors, label, title, ymax, xmax=None):
    centers = 0.5 * (edges[:-1] + edges[1:])
    nonzero = counts > 0
    ax.errorbar(centers[nonzero], counts[nonzero], yerr=errors[nonzero], fmt='o',
                color=_DATA_COLOR, ecolor=_DATA_COLOR, markersize=5, capsize=3,
                linestyle='none', label=label)
    style_axes(ax, edges, title, ymax, xmax=xmax)
    ax.legend(fontsize=_LEGEND_FONTSIZE, loc='upper right', framealpha=0.9)


def run(bin_width, merge_bins, drop_first_bin=False):
    W = f"{bin_width}MeV"

    # drop_first_bin is built ENTIRELY from the finer 50 MeV histograms (paired
    # up into 100 MeV bins by drop_0_50_bin) -- the 100 MeV histograms
    # themselves are not read in this mode.
    if drop_first_bin:
        assert bin_width == 100, "drop_first_bin only makes sense against the 100 MeV grid"
        component_prefix = "selection_AfterBeamWindowCut_50MeV"
        mc_root      = MC_DIR / "50MeV" / "selection_performance_histograms_50MeV.root"
        offbeam_root = OFFBEAM_DIR / "50MeV" / "selected_reco_histograms_50MeV.root"
        onbeam_root  = ONBEAM_DIR / "50MeV" / "selected_reco_histograms_50MeV.root"
    else:
        component_prefix = f"selection_AfterBeamWindowCut_{W}"
        mc_root      = MC_DIR / W / f"selection_performance_histograms_{W}.root"
        offbeam_root = OFFBEAM_DIR / W / f"selected_reco_histograms_{W}.root"
        onbeam_root  = ONBEAM_DIR / W / f"selected_reco_histograms_{W}.root"
    hist_path = f"{component_prefix}/all_selected_reco"

    # Sibling output sets per bin width: the original per-bin plots directly
    # under W/, the bins-above-1400-merged versions in W/merged_after_1400MeV/,
    # and (100 MeV only) the 0-50 MeV bin zeroed out in W/drop_0-50MeV/ --
    # all wanted side by side, none replacing another.
    if drop_first_bin:
        out_dir = OUT_ROOT / W / "drop_0-50MeV"
    elif merge_bins:
        out_dir = OUT_ROOT / W / "merged_after_1400MeV"
    else:
        out_dir = OUT_ROOT / W
    out_dir.mkdir(parents=True, exist_ok=True)

    mc_counts, raw_edges = load_hist(mc_root, hist_path)
    off_counts, _         = load_hist(offbeam_root, hist_path)
    on_counts, _          = load_hist(onbeam_root, hist_path)

    if drop_first_bin:
        # Zeroes out [0,50) (kept as a visible gap against the x=0 origin
        # rather than removed from the axis) and pairs every two 50 MeV bins
        # from 50 MeV on into one 100 MeV bin -- see drop_0_50_bin.
        mc_counts, edges  = drop_0_50_bin(mc_counts, raw_edges)
        off_counts, _      = drop_0_50_bin(off_counts, raw_edges)
        on_counts, _       = drop_0_50_bin(on_counts, raw_edges)
    elif merge_bins:
        # All three histograms share the same fixed raw edges, so
        # merge_overflow's returned edges (from the MC call) apply to all
        # three. The merged bin fills threshold to PLOT_X_MAX_MEV -- see
        # merge_overflow's docstring -- so no xmax override is needed below.
        mc_counts, edges  = merge_overflow(mc_counts, raw_edges)
        off_counts, _      = merge_overflow(off_counts, raw_edges)
        on_counts, _       = merge_overflow(on_counts, raw_edges)
    else:
        edges = raw_edges

    mc_counts_scaled  = mc_counts * MC_SCALE
    mc_errors_scaled   = np.sqrt(mc_counts) * MC_SCALE  # MC is a finite sample too -- Poisson error on the raw count, propagated through the same POT scale
    off_counts_scaled = off_counts * OFF_SCALE
    off_errors         = np.sqrt(off_counts)
    off_errors_scaled  = off_errors * OFF_SCALE
    on_errors           = np.sqrt(on_counts)

    print("=" * 88)
    print(f"Data/MC overlay -- POT normalization -- {W} bins")
    print("=" * 88)
    print(f"POT_MC       = {POT_MC:.6e}")
    print(f"POT_DataOn   = {POT_DATAON:.6e}")
    print(f"gates_off    = {GATES_OFF:.6e}")
    print(f"gates_on     = {GATES_ON:.6e}")
    print(f"POT_off (derived) = POT_DataOn * (gates_off/gates_on) = {POT_OFF:.6e}")
    print(f"MC_scale  = POT_DataOn/POT_MC   = {MC_SCALE:.6f}")
    print(f"OFF_scale = POT_DataOn/POT_off  = {OFF_SCALE:.6f}  (== gates_on/gates_off)")
    print()
    print(f"MC        raw total = {mc_counts.sum():.0f}   scaled total = {mc_counts_scaled.sum():.2f}")
    print(f"Off-beam  raw total = {off_counts.sum():.0f}   scaled total = {off_counts_scaled.sum():.2f}")
    print(f"On-beam   total     = {on_counts.sum():.0f}   (reference, unscaled)")
    print(f"MC + Off-beam scaled total = {(mc_counts_scaled.sum() + off_counts_scaled.sum()):.2f}"
          f"   vs On-beam = {on_counts.sum():.0f}")

    # ------------------------------------------------------------------
    # PLOT 1 -- MC (NuMuCC) before / after POT normalization
    # ------------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
    ymax1 = panel_ymax(edges, mc_counts, mc_counts_scaled)
    draw_step_panel(ax1, edges, mc_counts, f"MC All selected reco ({mc_counts.sum():.0f})",
                     "BNB Light MC (NuMuCC) -- Before POT Normalization", ymax1)
    draw_step_panel(ax2, edges, mc_counts_scaled,
                     f"MC x (POT$_{{Data}}$/POT$_{{MC}}$) ({mc_counts_scaled.sum():.1f})",
                     f"BNB Light MC (NuMuCC) -- After POT Normalization (x{MC_SCALE:.4f})", ymax1)
    fig.suptitle("MC POT Normalization -- Before vs After (scale = POT$_{Data}$/POT$_{MC}$ = "
                 f"{POT_DATAON:.3e}/{POT_MC:.3e} = {MC_SCALE:.4f})", fontsize=_TITLE_FONTSIZE, y=1.02)
    fig.tight_layout()
    path1 = out_dir / f"MC_NuMuCC_BeforeAfter_POT_Normalization_{W}.png"
    fig.savefig(path1, dpi=150, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    print(f"\nwrote {path1}")

    # ------------------------------------------------------------------
    # PLOT 2 -- Off-beam data before / after POT normalization
    # ------------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
    ymax2 = panel_ymax(edges, off_counts + off_errors, off_counts_scaled + off_errors_scaled)
    draw_points_panel(ax1, edges, off_counts, off_errors,
                       f"Off-beam Data selected reco ({off_counts.sum():.0f})",
                       "Off-Beam Data -- Before POT Normalization", ymax2)
    draw_points_panel(ax2, edges, off_counts_scaled, off_errors_scaled,
                       f"Off-beam Data x (POT$_{{on}}$/POT$_{{off}}$) ({off_counts_scaled.sum():.1f})",
                       f"Off-Beam Data -- After POT Normalization (x{OFF_SCALE:.4f})", ymax2)
    fig.suptitle("Off-Beam POT-Equivalent Normalization -- Before vs After "
                 f"(POT$_{{off}}$ = POT$_{{on}}$ x gates$_{{off}}$/gates$_{{on}}$ = {POT_OFF:.3e}; "
                 f"scale = POT$_{{on}}$/POT$_{{off}}$ = gates$_{{on}}$/gates$_{{off}}$ = {OFF_SCALE:.4f})",
                 fontsize=_TITLE_FONTSIZE, y=1.02)
    fig.tight_layout()
    path2 = out_dir / f"OffBeamData_BeforeAfter_POT_Normalization_{W}.png"
    fig.savefig(path2, dpi=150, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    print(f"wrote {path2}")

    # ------------------------------------------------------------------
    # PLOT 3 -- Data/MC overlay: stacked (MC + Off-beam), POT-normalized,
    # on-beam data drawn on top as unconnected black points.
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(11, 8))

    # Stack drawn as a proper stepped/filled histogram (ax.hist(...,
    # stacked=True, histtype='stepfilled'), the same call
    # draw_reco_selection_stack uses elsewhere in this codebase) rather than
    # bar() -- one bin-center "sample" per bin, weighted by that bin's
    # (possibly fractional, post-scaling) count, so ax.hist reproduces the
    # counts exactly while drawing a continuous stepped outline instead of
    # individually-edged bars.
    # Off-beam (background-like, light grey) drawn first/bottom, MC
    # (signal-like, blue) stacked on top -- same "cosmic filled pale, signal
    # solid colour" convention SELECTION_COMPONENTS uses elsewhere.
    stack_top = off_counts_scaled + mc_counts_scaled
    bin_centers_for_hist = 0.5 * (edges[:-1] + edges[1:])
    ax.hist([bin_centers_for_hist, bin_centers_for_hist], bins=edges,
            weights=[off_counts_scaled, mc_counts_scaled],
            stacked=True, histtype='stepfilled',
            color=[_OFF_COLOR, _MC_COLOR], edgecolor='black', linewidth=1.0,
            label=[f"Off-beam Data (POT-equiv. norm.) ({off_counts_scaled.sum():.1f})",
                   f"BNB Light MC (POT norm.) ({mc_counts_scaled.sum():.1f})"])

    # MC statistical uncertainty -- the MC sample is finite too (comparable
    # size to data), so its Poisson error (propagated through MC_SCALE) is
    # drawn as a hatched band around the stack's top edge, the same
    # "MC stat. unc." convention HEP overlay plots use.
    stack_top_stepped = np.append(stack_top, stack_top[-1])
    mc_err_stepped     = np.append(mc_errors_scaled, mc_errors_scaled[-1])
    ax.fill_between(edges, stack_top_stepped - mc_err_stepped, stack_top_stepped + mc_err_stepped,
                     step='post', facecolor='none', edgecolor='dimgray', hatch='///',
                     linewidth=0.0, label="BNB Light MC stat. unc.")

    centers = 0.5 * (edges[:-1] + edges[1:])
    nonzero = on_counts > 0
    ax.errorbar(centers[nonzero], on_counts[nonzero], yerr=on_errors[nonzero], fmt='o',
                color=_DATA_COLOR, ecolor=_DATA_COLOR, markersize=6, capsize=3,
                linestyle='none', label=f"On-beam data ({on_counts.sum():.0f}, POT={POT_DATAON:.3e})")

    visible_stack = (stack_top + mc_errors_scaled)[edges[:-1] < PLOT_X_MAX_MEV]
    visible_data  = (on_counts + on_errors)[edges[:-1] < PLOT_X_MAX_MEV]
    ymax = max(float(visible_stack.max()) if len(visible_stack) else 0.0,
               float(visible_data.max()) if len(visible_data) else 0.0, 1.0) * (1 + _Y_HEADROOM_LINEAR)
    style_axes(ax, edges, "Data/MC Overlay -- On-Beam Data vs POT-Normalized (MC + Off-Beam)", ymax)
    # Data first in the legend, then the stack bands in their drawing order.
    handles3, labels3 = ax.get_legend_handles_labels()
    data_idx = next(i for i, l in enumerate(labels3) if l.startswith("On-beam data"))
    order3 = [data_idx] + [i for i in range(len(labels3)) if i != data_idx]
    ax.legend([handles3[i] for i in order3], [labels3[i] for i in order3],
              fontsize=_LEGEND_FONTSIZE, loc='upper right', framealpha=0.9)
    fig.tight_layout()
    path3 = out_dir / f"DataMC_Overlay_Stack_{W}.png"
    fig.savefig(path3, dpi=150, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    print(f"wrote {path3}")

    # ------------------------------------------------------------------
    # PLOT 4 -- same overlay, but the MC band is broken down into its
    # selection components (signal channels, contamination, out-of-volume,
    # cosmic) instead of one solid colour, as in
    # selection_reco_energy_stack_..._solid_liny_..._Combined.png. Off-beam
    # stays a single band (real data has no truth to categorise it by).
    # ------------------------------------------------------------------
    mc_component_counts = {}
    for component in MC_COMPONENTS:
        counts, _ = load_hist(mc_root, f"{component_prefix}/{component['key']}")
        if drop_first_bin:
            counts, _ = drop_0_50_bin(counts, raw_edges)
        elif merge_bins:
            counts, _ = merge_overflow(counts, raw_edges)
        mc_component_counts[component['key']] = counts * MC_SCALE

    # Closure check: components must sum to the same "all selected reco" total
    # already used above (same records, just split by category).
    component_sum = sum(mc_component_counts.values())
    assert np.allclose(component_sum.sum(), mc_counts_scaled.sum()), (
        f"MC component histograms sum to {component_sum.sum():.2f}, "
        f"expected {mc_counts_scaled.sum():.2f}")

    totals = {key: counts.sum() for key, counts in mc_component_counts.items()}
    drawing_order = order_mc_components_for_stack(MC_COMPONENTS, totals)
    legend_order  = sorted(MC_COMPONENTS, key=lambda c: c['legend_rank'])

    fig, ax = plt.subplots(figsize=(11, 8))
    hist_values  = [bin_centers_for_hist] * (1 + len(drawing_order))
    hist_weights = [off_counts_scaled] + [mc_component_counts[c['key']] for c in drawing_order]
    hist_colors  = [_OFF_COLOR] + [c['color'] for c in drawing_order]
    hist_labels  = ([f"Off-beam Data (POT-equiv. norm.) ({off_counts_scaled.sum():.1f})"]
                     + [f"{c['label']} ({mc_component_counts[c['key']].sum():.1f})" for c in drawing_order])
    ax.hist(hist_values, bins=edges, weights=hist_weights, stacked=True, histtype='stepfilled',
            color=hist_colors, edgecolor='black', linewidth=1.0, label=hist_labels)

    # Same MC statistical uncertainty band as DataMC_Overlay_Stack, drawn
    # around the TOTAL stack top (off-beam + all MC components) -- the
    # component histograms partition mc_counts exactly, so mc_errors_scaled
    # (the total MC's own Poisson error) is still the right quantity here.
    stack_top4 = off_counts_scaled + component_sum
    stack_top4_stepped = np.append(stack_top4, stack_top4[-1])
    ax.fill_between(edges, stack_top4_stepped - mc_err_stepped, stack_top4_stepped + mc_err_stepped,
                     step='post', facecolor='none', edgecolor='dimgray', hatch='///',
                     linewidth=0.0, label="BNB Light MC stat. unc.")

    ax.errorbar(centers[nonzero], on_counts[nonzero], yerr=on_errors[nonzero], fmt='o',
                color=_DATA_COLOR, ecolor=_DATA_COLOR, markersize=6, capsize=3,
                linestyle='none', label=f"On-beam data ({on_counts.sum():.0f}, POT={POT_DATAON:.3e})")

    # Same y-axis range as DataMC_Overlay_Stack (plot 3, `ymax` above) -- the
    # two are the same population, one solid MC band vs broken into
    # components, and sharing the range makes them directly comparable.
    style_axes(ax, edges, "Data/MC Overlay by MC Component", ymax)
    # Data first in the legend, then off-beam, then the MC components ranked
    # in the same order the reference stack plot uses (signal channels, then
    # contamination, out-of-volume, cosmic) -- inside the axes, matching
    # DataMC_Overlay_Stack's style.
    handles, labels = ax.get_legend_handles_labels()
    label_order = (["On-beam data", "Off-beam Data"] + [c['label'] for c in legend_order]
                   + ["BNB Light MC stat. unc."])
    by_label = dict(zip([l.split(' (')[0] for l in labels], zip(handles, labels)))
    ordered = [by_label[key] for key in label_order if key in by_label]
    ax.legend([h for h, _ in ordered], [l for _, l in ordered],
              fontsize=_LEGEND_FONTSIZE, loc='upper right', framealpha=0.9)
    fig.tight_layout()
    path4 = out_dir / f"DataMC_Overlay_StackByComponent_{W}.png"
    fig.savefig(path4, dpi=150, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    print(f"wrote {path4}")
    print()


if __name__ == "__main__":
    for bin_width in (200, 100, 50):
        run(bin_width, merge_bins=False)  # original, per-bin, no overflow merge
        run(bin_width, merge_bins=True)   # bins above 1400 MeV merged into one
    run(100, merge_bins=False, drop_first_bin=True)  # 0-50 MeV dropped, 100 MeV bins for the rest
