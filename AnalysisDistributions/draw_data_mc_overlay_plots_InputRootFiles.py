#!/usr/bin/env python3
"""
Data/MC overlay plots from the tracking-pr ROOT-input jobs -- the same POT values
and scale factors as draw_data_mc_overlay_plots.py, with the inputs swapped for
the three *_InputRootFiles runs:

  MC (CV)       SignalBackground_Distributions_BeforeCosmicTagger_MC_InputRootFiles/CV_MC_Sample
  Off-beam data SignalBackground_Distributions_BeforeCosmicTagger_Data_OffBeam_InputRootFiles
  On-beam data  SignalBackground_Distributions_BeforeCosmicTagger_Data_OnBeam_InputRootFiles

Each job writes job_summary/<stage>/<variable>/ for the five stages; the overlays
mirror that layout, one directory per stage and per variable:

  <out>/<stage>/Reco_Cluster_Energy/<W>MeV/      energy (draw_data_mc_overlay_plots.run)
  <out>/<stage>/Reco_Neutrino_Energy/<W>MeV/     kine_reco_Enu        (candidate stages)
  <out>/<stage>/Reco_Muon_Multiplicity/, Reco_Muon_Energy/<W>MeV/,
                Reco_Vertex_X/, Reco_Vertex_Y/, Reco_Vertex_Z/       (candidate stages)
  <out>/<stage>/Length/, NPoints/, Flash_PE/, Flash_Time/, NuMu_Score/, NuE_Score/
                 Flash_Time also the -10..10 us zoom-out (AfterBeamWindowCut, NuCandidate)

Every figure comes as the total-MC overlay and the by-component one (the MC split
into truth categories at the signal definition the MC job wrote its category
histograms at -- completeness > 60%, any purity -- read from those files and
shown in the titles), each in linear and log y, the pair sharing one y range.

    python3 draw_data_mc_overlay_plots_InputRootFiles.py
    python3 draw_data_mc_overlay_plots_InputRootFiles.py --mc-run DIR --offbeam-run DIR \\
        --onbeam-run DIR --out DIR          # e.g. the chunk_00 test outputs
"""
import argparse
from pathlib import Path

import numpy as np
import uproot
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, MaxNLocator

from draw_data_mc_overlay_plots import (
    AD, run, load_hist, MC_SCALE, OFF_SCALE, POT_DATAON, MC_COMPONENTS,
    order_mc_components_for_stack,
    _AXIS_LABEL_FONTSIZE, _TITLE_FONTSIZE, _TICK_LABEL_FONTSIZE, _LEGEND_FONTSIZE,
    _DATA_COLOR, _MC_COLOR, _OFF_COLOR)

PLOTS = AD / "multi_file_plots_charge_light_matching"

# The full 10-chunk runs (update when re-run).
MC_RUN = (PLOTS / "SignalBackground_Distributions_BeforeCosmicTagger_MC_InputRootFiles"
          "/CV_MC_Sample/combined_apa_20261002_225934")
OFFBEAM_RUN = (PLOTS / "SignalBackground_Distributions_BeforeCosmicTagger_Data_OffBeam_InputRootFiles"
               "/combined_apa_TBD")
ONBEAM_RUN = (PLOTS / "SignalBackground_Distributions_BeforeCosmicTagger_Data_OnBeam_InputRootFiles"
              "/combined_apa_TBD")
OUT_ROOT = PLOTS / "Data_MC_Overlay_Plots_InputRootFiles"

# NuCandidate_FiducialRecoVertex: + the candidate's T_tagger reco vertex in the
# fiducial volume; the numu_score stages follow it.
STAGES = ('AfterBeamWindowCut', 'NuCandidate', 'NuCandidate_FiducialRecoVertex',
          'NuCandidate_FiducialRecoVertex_NuMuScore_gt0',
          'NuCandidate_FiducialRecoVertex_NuMuScore_gt0p9')
CANDIDATE_STAGES = STAGES[1:]
ENERGY_WIDTHS_MEV = (200, 100, 50)
BEAM_BAND = [(0.2, 2.2, 'Beam window 0.2-2.2 us')]

# Each job's plain histograms (selected_reco_histograms.root) and the MC job's
# truth-category ones (<stage>/<key>/<component>, category_histograms_c60pany.root),
# both in job_summary/.
PLAIN_ROOT = "selected_reco_histograms.root"
CATEGORY_ROOT = "category_histograms_c60pany.root"

# The energy overlay's MC bands plus the one the variable stacks add: entries
# with no categorised cluster (draw_selection_performance's
# NO_TRUTH_CATEGORY_COMPONENT -- same key, label and colour).
MC_VARIABLE_COMPONENTS = MC_COMPONENTS + [
    {'key': 'no_truth_category', 'label': 'Uncredited candidate (no truth category)',
     'color': 'saddlebrown', 'legend_rank': 6, 'pinned': False}]

# y headroom above the tallest stack/data point -- shared by the total-MC and
# by-component versions of a figure, so each pair has one y range.
LINY_HEADROOM = 1.2    # linear: ymax x (1 + this)
LOGY_HEADROOM = 1e4    # log: ymax x this

# Overlays drawn in linear y only (no _logy figure): the reco vertex x / y / z.
LINY_ONLY = ('nu_x', 'nu_y', 'nu_z')

RECO_ENERGY_DIRNAME = 'Reco_Cluster_Energy'
NU_ENERGY_DIRNAME = 'Reco_Neutrino_Energy'
DQDX_PARTICLES = (('mu', 'Muon'), ('p', 'Proton'))


def variables_for(stage):
    """
    (name, plain-histogram key, category-histogram key, output subdir, x label,
     x tick, y label, legend loc, bands) for every overlay at this stage.
    """
    clusters, candidates = 'Number of Reco Clusters', 'Number of Candidates'
    out = [
        ('length_cm', f"{stage}/length_cm", f"{stage}/length_cm", 'Length',
         'Reco Cluster Length (cm)', 100.0, clusters, 'upper right', None),
        ('npoints', f"{stage}/npoints", f"{stage}/npoints", 'NPoints',
         'Reco Cluster Points (npoints)', 2500.0, clusters, 'upper right', None),
        ('flash_pe', f"{stage}/flash_pe", f"{stage}/flash_pe", 'Flash_PE',
         'Matched Flash PE', 5000.0, clusters, 'upper right', None),
        ('flash_time_us', f"{stage}/flash_time_us", f"{stage}/flash_time_us", 'Flash_Time',
         'Matched Flash Time (us)', 0.2, clusters, 'upper right', None),
        ('numu_score', f"{stage}/numu_score", f"{stage}/numu_score", 'NuMu_Score',
         r'$\nu_\mu$ CC BDT score (numu_score)', 1.0, candidates, 'upper left', None),
        ('nue_score', f"{stage}/nue_score", f"{stage}/nue_score", 'NuE_Score',
         r'$\nu_e$ CC BDT score (nue_score)', 2.0, candidates, 'upper left', None),
    ]
    if stage == 'AfterBeamWindowCut':
        out.append(('flash_time_us_zoomout_-10to10us', "NoCuts/flash_time_us_zoomout",
                    f"{stage}/flash_time_us_zoomout_-10to10us", 'Flash_Time',
                    'Matched Flash Time (us), every cluster with a flash', 2.0, clusters,
                    'upper left', BEAM_BAND))
    if stage == 'NuCandidate':
        out.append(('flash_time_us_zoomout_-10to10us', f"{stage}/flash_time_us_zoomout",
                    f"{stage}/flash_time_us_zoomout_-10to10us", 'Flash_Time',
                    'Matched Flash Time (us), every T_tagger row with a flash', 2.0,
                    'Number of T_tagger Rows', 'upper left', BEAM_BAND))
    if stage in CANDIDATE_STAGES:
        for w in ENERGY_WIDTHS_MEV:
            out.append((f"kine_reco_Enu_{w}MeV", f"{stage}/kine_reco_Enu_{w}MeV",
                        f"{stage}/kine_reco_Enu_{w}MeV", f"{NU_ENERGY_DIRNAME}/{w}MeV",
                        'Reconstructed Neutrino Energy, kine_reco_Enu (MeV)', 500.0, candidates,
                        'upper right', None))
        # The jobs' CANDIDATE_EXTRA_VARIABLES, same directories.
        out.append(('n_muons', f"{stage}/n_muons", f"{stage}/n_muons", 'Reco_Muon_Multiplicity',
                    'Reco Muon Multiplicity (|PDG| = 13 in T_kine)', 1.0, candidates, 'upper right', None))
        for w in ENERGY_WIDTHS_MEV:
            out.append((f"muon_energy_{w}MeV", f"{stage}/muon_energy_{w}MeV",
                        f"{stage}/muon_energy_{w}MeV", f"Reco_Muon_Energy/{w}MeV",
                        'Leading Reco Muon Energy, kine_energy_particle (MeV)', 500.0, candidates,
                        'upper right', None))
        for axis, tick in (('x', 50.0), ('y', 50.0), ('z', 100.0)):
            out.append((f"nu_{axis}", f"{stage}/nu_{axis}", f"{stage}/nu_{axis}",
                        f"Reco_Vertex_{axis.upper()}", f'Reco Neutrino Vertex {axis} (cm)', tick,
                        candidates, 'upper right', None))
        out.append(('muon_cos_theta', f"{stage}/muon_cos_theta", f"{stage}/muon_cos_theta", 'Muon_Cosmu',
                    r'Reco Muon $\cos\theta$ to the Beam (z)', 0.5, candidates, 'upper left', None))
        for key, dirname, xlabel, tick, loc in (
                ('n_protons', 'Reco_Proton_Multiplicity', 'Reco Proton Multiplicity (|PDG| = 2212 in T_kine)', 1.0, 'upper right'),
                ('n_charged_pions', 'Reco_ChargedPion_Multiplicity', 'Reco Charged-Pion Multiplicity (|PDG| = 211 in T_kine)', 1.0, 'upper right'),
                ('n_em_objects', 'Reco_EMObject_Multiplicity', 'Reco EM-Object Multiplicity (|PDG| = 11 in T_kine: any EM-like object, mostly few-MeV fragments)', 2.0, 'upper right'),
                ('proton_energy', 'Reco_Proton_Energy', 'Leading Reco Proton Energy, kine_energy_particle (MeV)', 200.0, 'upper right'),
                ('pi0_mass', 'Pi0_Mass', r'Reco $\pi^0$ Mass, kine_pio_mass (MeV)', 50.0, 'upper right'),
                ('muon_length', 'Muon_Length', 'Longest Reco Muon Track Length, max residual range (cm)', 100.0, 'upper right'),
                ('proton_length', 'Proton_Length', 'Longest Reco Proton Track Length, max residual range (cm)', 20.0, 'upper right'),
                ('numu_1_score', 'NuMu_1_Score', 'numu_1_score (sub-BDT)', 0.2, 'upper left'),
                ('numu_2_score', 'NuMu_2_Score', 'numu_2_score (sub-BDT)', 0.2, 'upper left'),
                ('numu_3_score', 'NuMu_3_Score', 'numu_3_score (sub-BDT)', 0.2, 'upper left'),
                ('cosmict_score', 'Cosmict_Score', 'cosmict_score (cosmic-tagger BDT)', 0.5, 'upper left')):
            out.append((key, f"{stage}/{key}", f"{stage}/{key}", dirname, xlabel, tick, candidates, loc, None))
        for short, label in DQDX_PARTICLES:
            out.append((f"{short}_q", f"{stage}/{short}_q", f"{stage}/{short}_q", f"DQDX_{label}",
                        f'{label} Point Charge q (proportional to dQ/dx)', 2500.0,
                        'Number of Points', 'upper right', None))
    return out


def summary_dir(job_dir):
    return Path(job_dir) / "job_summary"


def energy_dir(job_dir, stage):
    """Where a job keeps its <W>MeV/ energy dirs."""
    return summary_dir(job_dir) / stage / RECO_ENERGY_DIRNAME


def mc_signal_definition(mc_run):
    with uproot.open(summary_dir(mc_run) / CATEGORY_ROOT) as f:
        return str(f["signal_definition"]) if "signal_definition" in f else None


def rebinned(counts, edges, factor):
    """Merge every `factor` adjacent bins -- the bin count must divide evenly."""
    if factor == 1:
        return counts, edges
    assert len(counts) % factor == 0, f"{len(counts)} bins do not merge in groups of {factor}"
    return counts.reshape(-1, factor).sum(axis=1), edges[::factor]


def draw_variable_overlay(runs, out_root, stage, name, plain_key, category_key, subdir, xlabel,
                          tick, ylabel, legend_loc, bands, signal_definition,
                          logy=False, by_component=False, rebin=1, name_suffix=''):
    """
    POT-normalised off-beam + MC stacked, MC stat. band on top, on-beam data as
    points. by_component=True splits the MC into its truth categories (the MC
    job's category histograms, checked to sum to its plain histogram). rebin
    merges every `rebin` adjacent bins of every histogram read; name_suffix is
    appended to the file name.
    """
    mc_run, offbeam_run, onbeam_run = runs
    load = lambda path, key: rebinned(*load_hist(path, key), rebin)
    mc_counts, edges = load(summary_dir(mc_run) / PLAIN_ROOT, plain_key)
    off_counts, off_edges = load(summary_dir(offbeam_run) / PLAIN_ROOT, plain_key)
    on_counts, on_edges = load(summary_dir(onbeam_run) / PLAIN_ROOT, plain_key)
    assert np.array_equal(edges, off_edges) and np.array_equal(edges, on_edges), \
        f"{plain_key}: the three jobs use different bin edges"

    mc_scaled = mc_counts * MC_SCALE
    mc_errors_scaled = np.sqrt(mc_counts) * MC_SCALE
    off_scaled = off_counts * OFF_SCALE
    on_errors = np.sqrt(on_counts)
    stack_top = off_scaled + mc_scaled
    centers = 0.5 * (edges[:-1] + edges[1:])

    if not logy and not by_component:
        print(f"  {stage:<28s} {name:<32s} MC {mc_counts.sum():5.0f} -> {mc_scaled.sum():7.1f}   "
              f"off-beam {off_counts.sum():5.0f} -> {off_scaled.sum():6.1f}   "
              f"on-beam {on_counts.sum():5.0f}")

    off_label = f"Off-beam Data (POT-equiv. norm.) ({off_scaled.sum():.1f})"
    title = f"Data/MC Overlay -- {name}\nreco: {stage} (ROOT input)"
    fig, ax = plt.subplots(figsize=(11, 8))
    for lo, hi, band_label in (bands or []):
        ax.axvspan(lo, hi, color='tab:orange', alpha=0.15, zorder=0, label=band_label)
    if by_component:
        category_root = summary_dir(mc_run) / CATEGORY_ROOT
        component_counts = {}
        for component in MC_VARIABLE_COMPONENTS:
            counts, component_edges = load(category_root, f"{category_key}/{component['key']}")
            assert np.array_equal(component_edges, edges), f"{component['key']}: different bin edges"
            component_counts[component['key']] = counts * MC_SCALE
        # Closure: the categories partition the same entries as the MC total.
        assert np.allclose(np.sum(list(component_counts.values()), axis=0), mc_scaled), (
            f"{category_key}: MC category histograms do not sum to the MC total")
        totals = {key: counts.sum() for key, counts in component_counts.items()}
        drawing_order = [c for c in order_mc_components_for_stack(MC_VARIABLE_COMPONENTS, totals)
                         if totals[c['key']] > 0]
        ax.hist([centers] * (1 + len(drawing_order)), bins=edges,
                weights=[off_scaled] + [component_counts[c['key']] for c in drawing_order],
                stacked=True, histtype='stepfilled',
                color=[_OFF_COLOR] + [c['color'] for c in drawing_order],
                edgecolor='black', linewidth=1.0,
                label=[off_label] + [f"{c['label']} ({totals[c['key']]:.1f})" for c in drawing_order])
        title = (f"Data/MC Overlay by MC Component -- {name}\nreco: {stage} (ROOT input)"
                 + (f" -- MC signal: {signal_definition}" if signal_definition else ""))
    else:
        ax.hist([centers, centers], bins=edges, weights=[off_scaled, mc_scaled],
                stacked=True, histtype='stepfilled',
                color=[_OFF_COLOR, _MC_COLOR], edgecolor='black', linewidth=1.0,
                label=[off_label, f"BNB Light MC (POT norm.) ({mc_scaled.sum():.1f})"])
    lower, upper = stack_top - mc_errors_scaled, stack_top + mc_errors_scaled
    ax.fill_between(edges, np.append(lower, lower[-1]), np.append(upper, upper[-1]),
                    step='post', facecolor='none', edgecolor='dimgray', hatch='///',
                    linewidth=0.0, label="BNB Light MC stat. unc.")
    nonzero = on_counts > 0
    ax.errorbar(centers[nonzero], on_counts[nonzero], yerr=on_errors[nonzero], fmt='o',
                color=_DATA_COLOR, ecolor=_DATA_COLOR, markersize=6, capsize=3,
                linestyle='none', label=f"On-beam data ({on_counts.sum():.0f}, POT={POT_DATAON:.3e})")

    # One y range for the total-MC and by-component figures (the stack top and the
    # data do not depend on the split); the headroom is sized for the longer legend.
    ymax = max(float((stack_top + mc_errors_scaled).max()) if len(stack_top) else 0.0,
               float((on_counts + on_errors).max()) if len(on_counts) else 0.0, 1.0)
    ax.set_xlim(edges[0], edges[-1])
    if logy:
        ax.set_yscale('log')
        ax.set_ylim(0.1, ymax * LOGY_HEADROOM)
    else:
        ax.set_ylim(0, ymax * (1 + LINY_HEADROOM))
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.xaxis.set_major_locator(MultipleLocator(tick))
    ax.set_xlabel(xlabel, fontsize=_AXIS_LABEL_FONTSIZE, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=_AXIS_LABEL_FONTSIZE, fontweight='bold')
    ax.set_title(title, fontsize=_TITLE_FONTSIZE, fontweight='bold')
    ax.tick_params(axis='both', labelsize=_TICK_LABEL_FONTSIZE)
    ax.grid(True, linestyle='--', alpha=0.3)
    # Data first in the legend, then the stack bands in their drawing order.
    handles, labels = ax.get_legend_handles_labels()
    data_idx = next(i for i, l in enumerate(labels) if l.startswith("On-beam data"))
    order = [data_idx] + [i for i in range(len(labels)) if i != data_idx]
    ax.legend([handles[i] for i in order], [labels[i] for i in order],
              fontsize=_LEGEND_FONTSIZE * (0.6 if by_component else 0.8),
              loc=legend_loc, framealpha=0.9)
    fig.tight_layout()

    out_dir = Path(out_root) / stage / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    kind = "StackByComponent_" if by_component else ""
    path = out_dir / f"DataMC_Overlay_{kind}{name}_{stage}{name_suffix}_{'logy' if logy else 'liny'}.png"
    fig.savefig(path, dpi=150, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    return path


def load_hist2d(path, key):
    with uproot.open(path) as f:
        counts, xedges, yedges = f[key].to_numpy()
    return counts, xedges, yedges


def draw_dqdx_profile(runs, out_root, stage, short, label):
    """
    Point charge q against residual range for one particle's trajectory points:
    left, the mean q per residual-range bin -- on-beam data (points, error = RMS /
    sqrt(N)) against POT-normalised MC + off-beam (line, same error as a band);
    right, the two 2D distributions on one colour scale. The means are weighted by
    the scaled counts, so MC and off-beam combine as in the 1D overlays.
    """
    from matplotlib.colors import LogNorm
    mc_run, offbeam_run, onbeam_run = runs
    key = f"{stage}/{short}_q_vs_rr"
    mc, xedges, yedges = load_hist2d(summary_dir(mc_run) / PLAIN_ROOT, key)
    off, _, _ = load_hist2d(summary_dir(offbeam_run) / PLAIN_ROOT, key)
    on, _, _ = load_hist2d(summary_dir(onbeam_run) / PLAIN_ROOT, key)
    pred = mc * MC_SCALE + off * OFF_SCALE
    qc = 0.5 * (yedges[:-1] + yedges[1:])
    xc = 0.5 * (xedges[:-1] + xedges[1:])

    def profile(h):
        n = h.sum(axis=1)
        with np.errstate(invalid='ignore', divide='ignore'):
            mean = (h * qc).sum(axis=1) / n
            rms = np.sqrt((h * (qc - mean[:, None]) ** 2).sum(axis=1) / n)
            err = rms / np.sqrt(n)
        return mean, err, n

    m_on, e_on, n_on = profile(on)
    m_pr, e_pr, n_pr = profile(pred)
    fig, (ax, ax2, ax3) = plt.subplots(1, 3, figsize=(24, 7))
    ok = n_pr > 0
    ax.fill_between(xc[ok], (m_pr - e_pr)[ok], (m_pr + e_pr)[ok], color=_MC_COLOR, alpha=0.3)
    ax.plot(xc[ok], m_pr[ok], color=_MC_COLOR, lw=2, label='MC + off-beam (POT norm.)')
    ok = n_on > 0
    ax.errorbar(xc[ok], m_on[ok], yerr=e_on[ok], fmt='o', color=_DATA_COLOR, ms=5, capsize=2,
                label=f'On-beam data ({int(on.sum())} points)')
    ax.set_xlabel('Residual Range (cm)', fontsize=_AXIS_LABEL_FONTSIZE, fontweight='bold')
    ax.set_ylabel(f'Mean {label} Point Charge q', fontsize=_AXIS_LABEL_FONTSIZE, fontweight='bold')
    ax.set_title(f'{label}: mean q vs residual range\nreco: {stage}', fontsize=_TITLE_FONTSIZE, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.legend(fontsize=_LEGEND_FONTSIZE * 0.6, loc='upper right')
    ax.set_xlim(xedges[0], xedges[-1])
    vmax = max(on.max(), pred.max(), 1)
    for a, h, title in ((ax2, on, 'On-beam data'), (ax3, pred, 'MC + off-beam (POT norm.)')):
        if h.sum() > 0:
            mesh = a.pcolormesh(xedges, yedges, np.ma.masked_less_equal(h.T, 0), cmap='viridis',
                                norm=LogNorm(vmin=0.1, vmax=vmax))
            fig.colorbar(mesh, ax=a, label='Points')
        a.set_xlabel('Residual Range (cm)', fontsize=_AXIS_LABEL_FONTSIZE, fontweight='bold')
        a.set_ylabel(f'{label} Point Charge q (proportional to dQ/dx)', fontsize=_AXIS_LABEL_FONTSIZE, fontweight='bold')
        a.set_title(f'{title} ({h.sum():.0f} points)', fontsize=_TITLE_FONTSIZE, fontweight='bold')
    fig.tight_layout()
    out_dir = Path(out_root) / stage / f"DQDX_{label}"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"DataMC_Overlay_{short}_q_vs_rr_profile_{stage}.png"
    fig.savefig(path, dpi=150, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    return path


def main(mc_run, offbeam_run, onbeam_run, out_root, variables=None, rebin=1, name_suffix=''):
    """variables: None draws everything; otherwise only the overlays whose name is
    listed (e.g. ['muon_cos_theta']) -- matching a one-variable job, whose files
    hold only those histograms. 'reco_energy' selects the energy overlays."""
    runs = (Path(mc_run), Path(offbeam_run), Path(onbeam_run))
    signal_definition = mc_signal_definition(mc_run)
    n_written = 0
    stages = [s for s in STAGES if variables is None or s in CANDIDATE_STAGES
              or 'reco_energy' in variables]
    for stage in stages:
        print(f"\n=== {stage}")
        # Reco cluster energy: draw_data_mc_overlay_plots.run, its four figure kinds
        dirs = dict(mc_dir=energy_dir(mc_run, stage), offbeam_dir=energy_dir(offbeam_run, stage),
                    onbeam_dir=energy_dir(onbeam_run, stage),
                    out_root=Path(out_root) / stage / RECO_ENERGY_DIRNAME,
                    stage=stage, title_tag=f"\nreco: {stage} (ROOT input)"
                    + (f" -- MC signal: {signal_definition}" if signal_definition else ""))
        if variables is None or 'reco_energy' in variables:
            for bin_width in ENERGY_WIDTHS_MEV:
                run(bin_width, merge_bins=False, **dirs)  # original, per-bin, no overflow merge
                run(bin_width, merge_bins=True, **dirs)   # bins above 1400 MeV merged into one
            run(100, merge_bins=False, drop_first_bin=True, **dirs)  # 0-50 MeV dropped
        # Every other variable
        for spec in variables_for(stage):
            if variables is not None and spec[0] not in variables:
                continue
            for by_component in (False, True):
                for logy in ((False,) if spec[0] in LINY_ONLY else (False, True)):
                    draw_variable_overlay(runs, out_root, stage, *spec, signal_definition,
                                          logy=logy, by_component=by_component,
                                          rebin=rebin, name_suffix=name_suffix)
                    n_written += 1
        if stage in CANDIDATE_STAGES and (variables is None or 'dqdx' in variables):
            for short, label in DQDX_PARTICLES:
                draw_dqdx_profile(runs, out_root, stage, short, label)
                n_written += 1
    print(f"\n{n_written} variable overlays written under {out_root} (+ the energy overlays)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--mc-run", default=MC_RUN)
    parser.add_argument("--offbeam-run", default=OFFBEAM_RUN)
    parser.add_argument("--onbeam-run", default=ONBEAM_RUN)
    parser.add_argument("--out", default=OUT_ROOT)
    parser.add_argument("--variables", nargs="+", default=None,
                        help="draw only these overlays (names as in variables_for, or reco_energy)")
    parser.add_argument("--rebin", type=int, default=1,
                        help="merge every N adjacent bins of the variable overlays "
                             "(e.g. --variables nu_x nu_y nu_z --rebin 2: 20 cm vertex bins)")
    parser.add_argument("--name-suffix", default=None,
                        help="appended to each file name (default: _rebin<N> when --rebin > 1)")
    args = parser.parse_args()
    suffix = args.name_suffix if args.name_suffix is not None else (
        f"_rebin{args.rebin}" if args.rebin > 1 else '')
    main(args.mc_run, args.offbeam_run, args.onbeam_run, args.out, args.variables,
         rebin=args.rebin, name_suffix=suffix)
