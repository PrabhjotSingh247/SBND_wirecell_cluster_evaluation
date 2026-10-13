#!/usr/bin/env python3
"""
True (red) and reco (blue) neutrino vertex of every out-of-volume selected
cluster at one stage, in XZ, YZ and XY -- all cases in one figure, each
true/reco pair joined by a line and numbered. The wire-readout sensitive
volume is outlined, the fiducial volume drawn as a dashed box with the
cathode exclusion (|x| <= FIDUCIAL_CATHODE_EXCLUSION_CM) shaded.

Input: selected_clusters_reco_true_vertex.csv (the per-cluster study dump).

    python3 draw_out_of_volume_vertices.py --csv .../selected_clusters_reco_true_vertex.csv \\
        --stage NuCandidate_FiducialRecoVertex_NuMuScore_gt0p9 --out DIR
"""
import argparse
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from selections import (WIRE_READOUT_X_MIN, WIRE_READOUT_X_MAX, WIRE_READOUT_Y_MIN, WIRE_READOUT_Y_MAX,
                        WIRE_READOUT_Z_MIN, WIRE_READOUT_Z_MAX, Fiducial_X_MIN, Fiducial_X_MAX,
                        Fiducial_Y_MIN, Fiducial_Y_MAX, Fiducial_Z_MIN, Fiducial_Z_MAX,
                        FIDUCIAL_CATHODE_EXCLUSION_CM)

ACTIVE = {'x': (WIRE_READOUT_X_MIN, WIRE_READOUT_X_MAX), 'y': (WIRE_READOUT_Y_MIN, WIRE_READOUT_Y_MAX),
          'z': (WIRE_READOUT_Z_MIN, WIRE_READOUT_Z_MAX)}
FIDUCIAL = {'x': (Fiducial_X_MIN, Fiducial_X_MAX), 'y': (Fiducial_Y_MIN, Fiducial_Y_MAX),
            'z': (Fiducial_Z_MIN, Fiducial_Z_MAX)}
# (horizontal, vertical) axis of each view
VIEWS = (('z', 'x'), ('z', 'y'), ('x', 'y'))
TRUE_COLOR, RECO_COLOR = 'red', 'blue'


def draw_volumes(ax, h, v):
    (h0, h1), (v0, v1) = ACTIVE[h], ACTIVE[v]
    ax.add_patch(Rectangle((h0, v0), h1 - h0, v1 - v0, fill=False, edgecolor='black', linewidth=1.6,
                           label='Active (wire-readout) volume'))
    (h0, h1), (v0, v1) = FIDUCIAL[h], FIDUCIAL[v]
    ax.add_patch(Rectangle((h0, v0), h1 - h0, v1 - v0, fill=False, edgecolor='gray', linestyle='--',
                           linewidth=1.3, label='Fiducial volume'))
    gap = FIDUCIAL_CATHODE_EXCLUSION_CM
    if h == 'x':
        ax.axvspan(-gap, gap, color='orange', alpha=0.35, label=f'Cathode exclusion |x| <= {gap:g} cm')
    elif v == 'x':
        ax.axhspan(-gap, gap, color='orange', alpha=0.35, label=f'Cathode exclusion |x| <= {gap:g} cm')


def main(csv_path, stage, out_dir):
    with open(csv_path, newline="") as f:
        rows = [r for r in csv.DictReader(f)
                if r['stage'] == stage and r['category'] == 'out_of_volume']
    if not rows:
        raise SystemExit(f"no out-of-volume clusters at {stage}")
    cases = []
    for n, r in enumerate(rows, 1):
        cases.append({'n': n, 'r': r,
                      'true': {a: float(r[f'true_vtx_{a}']) for a in 'xyz'},
                      'reco': {a: float(r[f'reco_nu_{a}']) for a in 'xyz'}})

    fig, axes = plt.subplots(1, 3, figsize=(27, 8.5))
    for ax, (h, v) in zip(axes, VIEWS):
        draw_volumes(ax, h, v)
        for c in cases:
            t, rc = c['true'], c['reco']
            ax.plot([t[h], rc[h]], [t[v], rc[v]], color='dimgray', linewidth=0.9, zorder=2)
            ax.scatter(t[h], t[v], color=TRUE_COLOR, s=70, zorder=4, edgecolor='black', linewidth=0.5)
            ax.scatter(rc[h], rc[v], color=RECO_COLOR, s=70, zorder=4, edgecolor='black', linewidth=0.5)
            ax.annotate(str(c['n']), (t[h], t[v]), textcoords='offset points', xytext=(6, 6),
                        color=TRUE_COLOR, fontsize=12, fontweight='bold', zorder=5)
            ax.annotate(str(c['n']), (rc[h], rc[v]), textcoords='offset points', xytext=(6, -14),
                        color=RECO_COLOR, fontsize=12, fontweight='bold', zorder=5)
        ax.scatter([], [], color=TRUE_COLOR, s=70, edgecolor='black', label='True neutrino vertex')
        ax.scatter([], [], color=RECO_COLOR, s=70, edgecolor='black', label='Reco neutrino vertex (T_tagger)')
        hs = [c[k][h] for c in cases for k in ('true', 'reco')] + list(ACTIVE[h])
        vs = [c[k][v] for c in cases for k in ('true', 'reco')] + list(ACTIVE[v])
        pad_h, pad_v = 0.06 * (max(hs) - min(hs)), 0.08 * (max(vs) - min(vs))
        ax.set_xlim(min(hs) - pad_h, max(hs) + pad_h)
        ax.set_ylim(min(vs) - pad_v, max(vs) + pad_v)
        ax.set_xlabel(f'{h} (cm)', fontsize=14, fontweight='bold')
        ax.set_ylabel(f'{v} (cm)', fontsize=14, fontweight='bold')
        ax.set_title(f'{v.upper()} vs {h.upper()}  ({h.upper()}{v.upper()} view)'.replace('ZX', 'XZ')
                     .replace('ZY', 'YZ'), fontsize=15, fontweight='bold')
        ax.tick_params(axis='both', labelsize=12)
        ax.grid(True, linestyle='--', alpha=0.3)
    axes[0].legend(fontsize=11, loc='upper left', framealpha=0.9)
    fig.suptitle(f"Out-of-Volume Selected Clusters (MC, CV, ROOT): True vs Reco Neutrino Vertex -- "
                 f"{len(cases)} cases\nreco: {stage}", fontsize=16, fontweight='bold')
    fig.tight_layout()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"out_of_volume_true_vs_reco_vertex_XZ_YZ_XY_{stage}"
    fig.savefig(out_dir / f"{name}.png", dpi=150, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)

    lines = [f"# Out-of-volume selected clusters -- {stage}: {len(cases)} cases",
             "# n\trun\tsubrun\tevent\tcluster\tflavor\tCC/NC\tE_nu_MeV\ttrue_x\ttrue_y\ttrue_z\t"
             "reco_x\treco_y\treco_z\tcompleteness\tpurity"]
    for c in cases:
        r, t, rc = c['r'], c['true'], c['reco']
        lines.append("\t".join([str(c['n']), r['run'], r['subrun'], r['event'], r['root_cluster_id'],
                                r['flavor'], r['interaction_type'], f"{float(r['mc_total_energy_MeV']):.0f}",
                                *(f"{t[a]:.1f}" for a in 'xyz'), *(f"{rc[a]:.1f}" for a in 'xyz'),
                                f"{float(r['completeness']):.2f}", f"{float(r['purity']):.2f}"]))
    (out_dir / f"{name}_cases.txt").write_text("\n".join(lines) + "\n")
    print(f"wrote {out_dir / name}.png and _cases.txt")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--csv", required=True)
    ap.add_argument("--stage", default="NuCandidate_FiducialRecoVertex_NuMuScore_gt0p9")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    main(a.csv, a.stage, a.out)
