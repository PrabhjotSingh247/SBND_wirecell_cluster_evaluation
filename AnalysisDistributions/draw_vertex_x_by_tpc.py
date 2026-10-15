#!/usr/bin/env python3
"""
Vertex x by TPC -- TPC0 is x < 0, TPC1 is x > 0 (the cathode at x = 0).

  true  True numu CC interactions with the vertex in the fiducial volume (the
        selection-efficiency denominator: interaction_type CC, flavor numu,
        vertex_in_volume), from a true_interactions.csv written by the MC
        ROOT-input notebook's records. Draws the true vertex x at 10 and 20 cm
        bins, and the two-bin TPC0/TPC1 count.

  reco  The MC job's reco neutrino candidates (T_tagger vertex nu_x, one entry per
        credited candidate with a vertex) per TPC, two bins, at every candidate
        stage -- from the job's selected_reco_histograms.root (<stage>/nu_x),
        written next to that stage's Reco_Vertex_X/ plots.

    python3 draw_vertex_x_by_tpc.py true --csv true_interactions.csv --out DIR --label "..."
    python3 draw_vertex_x_by_tpc.py reco --mc-run .../CV_MC_Sample/combined_apa_<date>_<time>

Raw MC counts (no POT scaling), sqrt(N) bars, count + fractional uncertainty
labelled on each bin.
"""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import uproot
from matplotlib.ticker import MaxNLocator, MultipleLocator

X_RANGE = (-200.0, 200.0)
CANDIDATE_STAGES = ('NuCandidate', 'NuCandidate_FiducialRecoVertex',
                    'NuCandidate_FiducialRecoVertex_NuMuScore_gt0',
                    'NuCandidate_FiducialRecoVertex_NuMuScore_gt0p9')
MC_COLOR = 'tab:blue'


def draw_hist(counts, edges, path, xlabel, ylabel, title, label, x_tick=None, tpc_labels=False):
    counts = np.asarray(counts, dtype=float)
    errors = np.sqrt(counts)
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.hist(0.5 * (edges[:-1] + edges[1:]), bins=edges, weights=counts, histtype='stepfilled',
            color=MC_COLOR, alpha=0.85, edgecolor='black', linewidth=1.0,
            label=f"{label} ({counts.sum():.0f})")
    centers = 0.5 * (edges[:-1] + edges[1:])
    # MC stat. uncertainty as a hatched band, as in the Data/MC overlays.
    lower, upper = counts - errors, counts + errors
    ax.fill_between(edges, np.append(lower, lower[-1]), np.append(upper, upper[-1]),
                    step='post', facecolor='none', edgecolor='dimgray', hatch='///',
                    linewidth=0.0, label='MC stat. unc.')
    if tpc_labels:
        for c, n, e, name in zip(centers, counts, errors, ('TPC0 (x < 0)', 'TPC1 (x > 0)')):
            frac = f"{100.0 * e / n:.1f}%" if n else "--"
            ax.annotate(f"{name}\n{n:.0f}  ({frac})\n{100.0 * n / counts.sum():.1f}% of total",
                        (c, n + e), textcoords="offset points", xytext=(0, 8),
                        ha='center', fontsize=12)
        ax.set_xticks(centers)
        ax.set_xticklabels(['TPC0  (x < 0)', 'TPC1  (x > 0)'])
    elif x_tick:
        ax.xaxis.set_major_locator(MultipleLocator(x_tick))
    ax.axvline(0.0, color='gray', linestyle=':', linewidth=1.2)
    ax.set_xlim(edges[0], edges[-1])
    ax.set_ylim(0, float((counts + errors).max()) * (1.45 if tpc_labels else 1.3))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlabel(xlabel, fontsize=14, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=14, fontweight='bold')
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.tick_params(axis='both', labelsize=12)
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.legend(fontsize=12, loc='upper right', framealpha=0.9)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    print(f"wrote {path}")


def write_info(path, header, counts, edges):
    lines = [f"# {header}", f"# total: {np.sum(counts):.0f}", "# bin_low\tbin_high\tcount\tsqrt(N)"]
    lines += [f"{lo:g}\t{hi:g}\t{n:.0f}\t{np.sqrt(n):.2f}" for lo, hi, n in zip(edges[:-1], edges[1:], counts)]
    path.write_text("\n".join(lines) + "\n")


def run_true(csv_path, out_dir, label):
    with open(csv_path, newline="") as f:
        rows = [r for r in csv.DictReader(f)
                if r['flavor'] == 'numu' and r['interaction_type'] == 'CC'
                and r['vertex_in_volume'] == 'True']
    x = np.array([float(r['vertex_x']) for r in rows])
    out_dir = Path(out_dir)
    title_base = f"True $\\nu_\\mu$ CC, Vertex in FV -- {label}"
    for width in (10, 20):
        edges = np.arange(X_RANGE[0], X_RANGE[1] + 1e-9, width)
        counts, _ = np.histogram(x, bins=edges)
        name = f"true_numuCC_inFV_vertex_x_{width}cmBins"
        draw_hist(counts, edges, out_dir / f"{name}.png", 'True Neutrino Vertex x (cm)',
                  'Number of True $\\nu_\\mu$ CC', title_base, f'True $\\nu_\\mu$ CC in FV', x_tick=50)
        write_info(out_dir / f"{name}_info.txt", f"{title_base}, {width} cm bins", counts, edges)
    edges = np.array([X_RANGE[0], 0.0, X_RANGE[1]])
    counts, _ = np.histogram(x, bins=edges)
    name = "true_numuCC_inFV_TPC0_vs_TPC1"
    draw_hist(counts, edges, out_dir / f"{name}.png", 'True Neutrino Vertex x (cm)',
              'Number of True $\\nu_\\mu$ CC', f"{title_base}: TPC0 vs TPC1",
              f'True $\\nu_\\mu$ CC in FV', tpc_labels=True)
    write_info(out_dir / f"{name}_info.txt", f"{title_base}: TPC0 (x<0) vs TPC1 (x>0)", counts, edges)


def run_reco(mc_run):
    summary = Path(mc_run) / "job_summary"
    with uproot.open(summary / "selected_reco_histograms.root") as f:
        for stage in CANDIDATE_STAGES:
            counts, edges = f[f"{stage}/nu_x"].to_numpy()
            assert np.isclose(edges[0], X_RANGE[0]) and np.isclose(edges[-1], X_RANGE[1]) \
                and np.any(np.isclose(edges, 0.0)), f"{stage}/nu_x: edges do not split at x = 0"
            tpc = np.array([counts[edges[1:] <= 0].sum(), counts[edges[:-1] >= 0].sum()])
            tpc_edges = np.array([X_RANGE[0], 0.0, X_RANGE[1]])
            out_dir = summary / stage / "Reco_Vertex_X"
            name = f"nu_x_TPC0_vs_TPC1_{stage}_job_Combined"
            title = f"Reco Neutrino Candidates (MC, ROOT): TPC0 vs TPC1\nreco: {stage}"
            draw_hist(tpc, tpc_edges, out_dir / f"{name}.png", 'Reco Neutrino Vertex x (cm)',
                      'Number of Reco Neutrino Candidates', title, 'MC reco candidates (raw)',
                      tpc_labels=True)
            write_info(out_dir / f"{name}_info.txt", f"{title.replace(chr(10), ' -- ')} (raw MC counts)",
                       tpc, tpc_edges)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="mode", required=True)
    t = sub.add_parser("true")
    t.add_argument("--csv", required=True)
    t.add_argument("--out", required=True)
    t.add_argument("--label", required=True)
    r = sub.add_parser("reco")
    r.add_argument("--mc-run", required=True)
    args = ap.parse_args()
    if args.mode == "true":
        run_true(args.csv, args.out, args.label)
    else:
        run_reco(args.mc_run)
