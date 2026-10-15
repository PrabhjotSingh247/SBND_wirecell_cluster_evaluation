#!/usr/bin/env python3
"""
TPC asymmetry of the reco neutrino vertex through the candidate stages, data vs
prediction (POT-scaled MC + off-beam), from the three ROOT-input jobs'
<stage>/nu_x histograms.

Two figures:
  TPC_asymmetry_...            A = (N_TPC0 - N_TPC1) / (N_TPC0 + N_TPC1); data points with
                               sqrt(N) errors, prediction as a line with its MC (+ off-beam)
                               stat. band
  TPC_data_over_prediction_... data / prediction in TPC0 and in TPC1 separately

The first stage is NuCandidate: before it a cluster has no reco vertex.

    python3 draw_tpc_asymmetry_vs_stage.py --mc-run DIR --offbeam-run DIR --onbeam-run DIR --out DIR
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import uproot

from draw_data_mc_overlay_plots import MC_SCALE, OFF_SCALE, POT_DATAON, _DATA_COLOR, _MC_COLOR

STAGES = (('NuCandidate', 'NuCandidate'),
          ('NuCandidate_FiducialRecoVertex', '+ Reco vertex\nin FV'),
          ('NuCandidate_FiducialRecoVertex_NuMuScore_gt0', '+ numu_score\n> 0'),
          ('NuCandidate_FiducialRecoVertex_NuMuScore_gt0p9', '+ numu_score\n> 0.9'))


def tpc_counts(job_dir, stage):
    with uproot.open(Path(job_dir) / "job_summary" / "selected_reco_histograms.root") as f:
        c, e = f[f"{stage}/nu_x"].to_numpy()
    assert np.any(np.isclose(e, 0.0)), f"{stage}/nu_x: no bin edge at x = 0"
    return np.array([c[e[1:] <= 0].sum(), c[e[:-1] >= 0].sum()], float)


def asymmetry(n, var):
    total = n.sum()
    a = (n[0] - n[1]) / total
    da = 2.0 / total ** 2 * np.sqrt(n[1] ** 2 * var[0] + n[0] ** 2 * var[1])
    return a, da


def main(mc_run, offbeam_run, onbeam_run, out_dir):
    rows = []
    for stage, _ in STAGES:
        mc, off, on = (tpc_counts(d, stage) for d in (mc_run, offbeam_run, onbeam_run))
        pred, pvar = mc * MC_SCALE + off * OFF_SCALE, mc * MC_SCALE ** 2 + off * OFF_SCALE ** 2
        a_d, da_d = asymmetry(on, on)
        a_p, da_p = asymmetry(pred, pvar)
        ratio = on / pred
        dratio = ratio * np.sqrt(1.0 / on + pvar / pred ** 2)
        rows.append(dict(stage=stage, on=on, pred=pred, a_d=a_d, da_d=da_d, a_p=a_p, da_p=da_p,
                         ratio=ratio, dratio=dratio, sigma=(a_p - a_d) / np.hypot(da_d, da_p)))

    x = np.arange(len(STAGES))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = "TPC_asymmetry_reco_vertex_x_vs_stage"
    ratio_name = "TPC_data_over_prediction_reco_vertex_x_vs_stage"

    fig, ax1 = plt.subplots(figsize=(11, 6))
    a_p =np.array([r['a_p'] for r in rows]); da_p = np.array([r['da_p'] for r in rows])
    ax1.fill_between(x, a_p - da_p, a_p + da_p, color=_MC_COLOR, alpha=0.25, linewidth=0,
                     label='Prediction stat. unc.')
    ax1.plot(x, a_p, '-s', color=_MC_COLOR, markersize=7,
             label='Prediction: BNB Light MC (POT norm.) + off-beam')
    ax1.errorbar(x, [r['a_d'] for r in rows], yerr=[r['da_d'] for r in rows], fmt='o',
                 color=_DATA_COLOR, markersize=7, capsize=4, label=f'On-beam data (POT={POT_DATAON:.3e})')
    ax1.axhline(0.0, color='gray', linestyle=':', linewidth=1.0)
    ax1.set_ylabel('TPC asymmetry\n$(N_{TPC0} - N_{TPC1}) / (N_{TPC0} + N_{TPC1})$', fontsize=13,
                   fontweight='bold')
    ax1.set_ylim(-0.1, 0.42)
    ax1.legend(fontsize=11, loc='upper left', framealpha=0.9)
    ax1.grid(True, linestyle='--', alpha=0.3)
    ax1.set_title('Reco Neutrino Vertex TPC Asymmetry vs Selection Stage (ROOT input)\n'
                  'TPC0: reco vertex x < 0, TPC1: x > 0', fontsize=14, fontweight='bold')
    fig2, ax2 = plt.subplots(figsize=(11, 5.5))
    for k, (tpc, color, dx) in enumerate((('TPC0 (x < 0)', 'tab:green', -0.08),
                                           ('TPC1 (x > 0)', 'tab:purple', 0.08))):
        ax2.errorbar(x + dx, [r['ratio'][k] for r in rows], yerr=[r['dratio'][k] for r in rows],
                     fmt='o-', color=color, markersize=7, capsize=4, label=tpc)
    ax2.axhline(1.0, color='gray', linestyle='--', linewidth=1.0)
    ax2.set_ylabel('Data / Prediction', fontsize=13, fontweight='bold')
    ax2.legend(fontsize=11, loc='upper left', framealpha=0.9)
    ax2.grid(True, linestyle='--', alpha=0.3)
    ax2.set_title('Reco Neutrino Vertex Data / Prediction per TPC vs Selection Stage (ROOT input)\n'
                  'TPC0: reco vertex x < 0, TPC1: x > 0', fontsize=14, fontweight='bold')
    for f, ax, n in ((fig, ax1, name), (fig2, ax2, ratio_name)):
        ax.set_xticks(x)
        ax.set_xticklabels([label for _, label in STAGES], fontsize=12)
        ax.set_xlim(-0.4, len(STAGES) - 0.6)
        ax.tick_params(axis='y', labelsize=11)
        f.tight_layout()
        f.savefig(out_dir / f"{n}.png", dpi=150, bbox_inches='tight', pad_inches=0.3)
        plt.close(f)
    lines = [f"# {name}: A = (N_TPC0 - N_TPC1)/(N_TPC0 + N_TPC1); prediction = MC x {MC_SCALE:.4g} "
             f"+ off-beam x {OFF_SCALE:.4g}",
             "# stage\tdata_TPC0\tdata_TPC1\tpred_TPC0\tpred_TPC1\tA_data\tA_pred\tdiff_sigma\t"
             "ratio_TPC0\tratio_TPC1"]
    for r in rows:
        lines.append(f"{r['stage']}\t{r['on'][0]:.0f}\t{r['on'][1]:.0f}\t{r['pred'][0]:.1f}\t{r['pred'][1]:.1f}\t"
                     f"{r['a_d']:+.3f}±{r['da_d']:.3f}\t{r['a_p']:+.3f}±{r['da_p']:.3f}\t{r['sigma']:.1f}\t"
                     f"{r['ratio'][0]:.2f}±{r['dratio'][0]:.2f}\t{r['ratio'][1]:.2f}±{r['dratio'][1]:.2f}")
    (out_dir / f"{name}_info.txt").write_text("\n".join(lines) + "\n")
    print(f"wrote {out_dir / name}.png, {ratio_name}.png and {name}_info.txt")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--mc-run", required=True)
    ap.add_argument("--offbeam-run", required=True)
    ap.add_argument("--onbeam-run", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    main(a.mc_run, a.offbeam_run, a.onbeam_run, a.out)
