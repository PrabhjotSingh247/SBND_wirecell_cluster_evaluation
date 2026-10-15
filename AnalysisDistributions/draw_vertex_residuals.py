#!/usr/bin/env python3
"""
Reco - true and (reco - true) / true neutrino vertex, x / y / z, for the MC
ROOT-input job's selected clusters at every candidate stage.

Input: selected_clusters_reco_true_vertex.csv (one row per selected cluster per
stage: the reco vertex of the candidate that passed the stage, and the true
vertex of the interaction the cluster is truth-matched to). Rows without a
reco vertex or without a matched true vertex are left out (counted in the info).

Each figure stacks in-volume (matched true vertex inside the FV) and
out-of-volume (outside). Off-axis entries are counted in the legend, never
silently dropped. (reco - true) / true diverges where the true coordinate is
near 0 (x at the cathode, y at mid-height), hence the fixed +-1 window.

    python3 draw_vertex_residuals.py --csv .../selected_clusters_reco_true_vertex.csv \\
        --mc-run .../CV_MC_Sample/combined_apa_<date>_<time>

Writes job_summary/<stage>/Reco_True_Vertex_Residual/ in the MC run.
"""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

CANDIDATE_STAGES = ('NuCandidate', 'NuCandidate_FiducialRecoVertex',
                    'NuCandidate_FiducialRecoVertex_NuMuScore_gt0',
                    'NuCandidate_FiducialRecoVertex_NuMuScore_gt0p9')
KINDS = {
    'residual': dict(edges=np.arange(-30.0, 30.0 + 1e-9, 1.0), unit='cm',
                     xlabel='Reco - True Vertex {axis} (cm)'),
    'relative': dict(edges=np.arange(-1.0, 1.0 + 1e-9, 0.04), unit='',
                     xlabel='(Reco - True) / True Vertex {axis}'),
}
GROUPS = (('in_volume', 'True vertex in FV', 'tab:blue'),
          ('out_of_volume', 'True vertex outside FV (out-of-volume)', 'tab:purple'))


def as_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return np.nan


def stats(values):
    v = np.asarray(values, float)
    if not len(v):
        return "entries 0"
    lo, hi = np.percentile(v, [16, 84])
    return (f"entries {len(v)}  mean {v.mean():.3f}  median {np.median(v):.3f}  "
            f"RMS {np.sqrt(np.mean(v ** 2)):.3f}  std {v.std():.3f}  "
            f"68% central [{lo:.3f}, {hi:.3f}] (half-width {(hi - lo) / 2:.3f})")


def draw(groups, kind, axis, stage, out_dir):
    spec = KINDS[kind]
    edges = spec['edges']
    centers = 0.5 * (edges[:-1] + edges[1:])
    fig, ax = plt.subplots(figsize=(10, 7))
    weights, colors, labels, info = [], [], [], []
    for key, label, color in GROUPS:
        v = np.asarray(groups[key], float)
        n_under, n_over = int(np.sum(v < edges[0])), int(np.sum(v > edges[-1]))
        counts, _ = np.histogram(v, bins=edges)
        weights.append(counts); colors.append(color)
        off = f", {n_under + n_over} off axis" if n_under + n_over else ""
        labels.append(f"{label} ({len(v)}{off})")
        info.append(f"{key}: {stats(v)}; below axis {n_under}, above axis {n_over}")
    ax.hist([centers] * len(weights), bins=edges, weights=weights, stacked=True,
            histtype='stepfilled', color=colors, edgecolor='black', linewidth=0.8, label=labels)
    total = np.sum(weights, axis=0)
    ax.axvline(0.0, color='gray', linestyle=':', linewidth=1.2)
    ax.set_xlim(edges[0], edges[-1])
    ax.set_ylim(0, max(float(total.max()), 1.0) * 1.3)
    ax.set_xlabel(spec['xlabel'].format(axis=axis), fontsize=14, fontweight='bold')
    ax.set_ylabel('Number of Selected Clusters', fontsize=14, fontweight='bold')
    ax.set_title(f"MC (CV, ROOT): Reco vs True Neutrino Vertex {axis}\nreco: {stage}",
                 fontsize=14, fontweight='bold')
    ax.tick_params(axis='both', labelsize=12)
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.legend(fontsize=11, loc='upper right', framealpha=0.9)
    name = f"vertex_{axis}_{kind}_{stage}_job_Combined"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / f"{name}.png", dpi=150, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    return name, info


def main(csv_path, mc_run):
    with open(csv_path, newline="") as f:
        rows = list(csv.DictReader(f))
    summary = Path(mc_run) / "job_summary"
    for stage in CANDIDATE_STAGES:
        stage_rows = [r for r in rows if r['stage'] == stage]
        usable = [r for r in stage_rows
                  if np.isfinite(as_float(r['reco_nu_x'])) and np.isfinite(as_float(r['true_vtx_x']))]
        out_dir = summary / stage / "Reco_True_Vertex_Residual"
        lines = [f"# Reco vs true neutrino vertex -- {stage}",
                 f"# selected clusters: {len(stage_rows)}; with a reco AND a matched true vertex: "
                 f"{len(usable)} (left out: {len(stage_rows) - len(usable)})", ""]
        for axis in ('x', 'y', 'z'):
            reco = np.array([as_float(r[f'reco_nu_{axis}']) for r in usable])
            true = np.array([as_float(r[f'true_vtx_{axis}']) for r in usable])
            in_vol = np.array([r['true_vertex_in_volume'] == 'True' for r in usable])
            for kind in KINDS:
                with np.errstate(divide='ignore', invalid='ignore'):
                    value = reco - true if kind == 'residual' else (reco - true) / true
                ok = np.isfinite(value)
                groups = {'in_volume': value[ok & in_vol], 'out_of_volume': value[ok & ~in_vol]}
                name, info = draw(groups, kind, axis, stage, out_dir)
                lines += [f"[{name}]"] + [f"  {s}" for s in info] + [""]
        (out_dir / "vertex_residual_summary.txt").write_text("\n".join(lines))
        print(f"{stage}: {len(usable)} clusters -> {out_dir}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--csv", required=True)
    ap.add_argument("--mc-run", required=True)
    args = ap.parse_args()
    main(args.csv, args.mc_run)
