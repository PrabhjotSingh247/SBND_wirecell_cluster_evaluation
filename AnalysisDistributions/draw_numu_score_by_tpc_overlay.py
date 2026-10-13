#!/usr/bin/env python3
"""
numu_score Data/MC overlay split by TPC of the reco neutrino vertex -- TPC0
(nu_x < 0) and TPC1 (nu_x > 0) side by side, one figure per candidate stage.

The candidates are each ROOT-input job's own credited T_tagger candidates
(job_summary/selected_clusters.txt, NuCandidate section: numu_score per
candidate). That file has no vertex, so each candidate's nu_x/y/z is read back
from its event's tracking-pr ROOT file (T_tagger row with the same cluster_id
and numu_score). The stages are then rebuilt exactly as the notebooks do:
  NuCandidate                                     every credited candidate
  NuCandidate_FiducialRecoVertex                  + vertex in the TPC-aware FV
  NuCandidate_FiducialRecoVertex_NuMuScore_gt0    + numu_score > 0
  NuCandidate_FiducialRecoVertex_NuMuScore_gt0p9  + numu_score > 0.9
and checked against the jobs' own <stage>/numu_score histogram entries.

MC (POT-scaled) + off-beam (POT-equivalent) stacked, MC stat. band, on-beam
data as points -- the same scale factors as draw_data_mc_overlay_plots.py.

    python3 draw_numu_score_by_tpc_overlay.py --mc-run DIR --offbeam-run DIR --onbeam-run DIR --out DIR
"""
import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import uproot
from matplotlib.ticker import MultipleLocator

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from selections import in_fiducial_volume
from draw_data_mc_overlay_plots import (MC_SCALE, OFF_SCALE, POT_DATAON, _DATA_COLOR, _MC_COLOR,
                                        _OFF_COLOR)

SAMPLES = Path("/Volumes/My Passport/Research_Life/Experiment/SBND/Wirecell_Reconstruction/Samples")
SAMPLE_DIRS = {'mc': SAMPLES / "r3-mc-cv-2026-09-09",
               'off': SAMPLES / "r3-beam-off-2026-09-11",
               'on': SAMPLES / "r3-beam-on-2026-09-10"}
NUMU_EDGES = np.arange(-10.0, 5.5, 0.5)          # the notebooks' numu_score binning
NUMU_SCORE_CUTS = (0.0, 0.9)
STAGES = ('NuCandidate', 'NuCandidate_FiducialRecoVertex',
          'NuCandidate_FiducialRecoVertex_NuMuScore_gt0',
          'NuCandidate_FiducialRecoVertex_NuMuScore_gt0p9')
TPCS = (('TPC0', 'TPC0 (reco vertex x < 0)'), ('TPC1', 'TPC1 (reco vertex x > 0)'))


def read_candidates(job_dir):
    """Credited candidates from selected_clusters.txt: (unit, run, subrun, event, cluster_id, numu_score)."""
    out, inside = [], False
    for line in (Path(job_dir) / "job_summary" / "selected_clusters.txt").read_text().splitlines():
        if line.startswith("# NuCandidate (T_tagger, credited"):
            inside = True
            continue
        if line.startswith("#"):
            if inside and not line.startswith("# unit"):
                break
            continue
        if inside and line.strip():
            f = line.split("\t")
            out.append((f[0], int(f[1]), int(f[2]), int(f[3]), int(f[4]), float(f[10])))
    return out


def attach_vertices(candidates, sample_dir):
    """numu_score, nu_x, in_fv for every candidate, from its event's T_tagger."""
    rows, cache = [], {}
    for unit, run, subrun, event, cid, score in candidates:
        path = sample_dir / unit / f"tracking-pr_r{run}_s{subrun}_e{event}.root"
        if path not in cache:
            with uproot.open(path) as f:
                cache[path] = f["T_tagger"].arrays(["cluster_id", "numu_score", "nu_x", "nu_y", "nu_z"],
                                                   library="np")
        t = cache[path]
        match = np.flatnonzero((t["cluster_id"] == cid) & np.isclose(t["numu_score"], score, atol=5e-3, rtol=1e-3))
        assert len(match) == 1, f"{path.name} cluster {cid} numu {score}: {len(match)} T_tagger matches"
        j = match[0]
        vx, vy, vz = (float(t[c][j]) for c in ("nu_x", "nu_y", "nu_z"))
        if not (vx or vy or vz):                       # (0, 0, 0): no vertex
            vx = vy = vz = np.nan
        rows.append({'numu_score': float(t["numu_score"][j]), 'nu_x': vx,
                     'in_fv': bool(in_fiducial_volume(vx, vy, vz))})
    return rows


def stage_rows(rows, stage):
    if stage == 'NuCandidate':
        return rows
    fv = [r for r in rows if r['in_fv']]
    if stage == 'NuCandidate_FiducialRecoVertex':
        return fv
    cut = 0.9 if stage.endswith('gt0p9') else 0.0
    return [r for r in fv if r['numu_score'] > cut]


def tpc_split(rows):
    """{TPC0: scores, TPC1: scores}; candidates with no vertex go to neither."""
    x = np.array([r['nu_x'] for r in rows], float)
    s = np.array([r['numu_score'] for r in rows], float)
    return {'TPC0': s[x < 0], 'TPC1': s[x > 0]}, int(np.sum(~np.isfinite(x)))


def check_against_job(job_dir, stage, scores_all):
    """The rebuilt stage has the job's own numu_score histogram entries."""
    with uproot.open(Path(job_dir) / "job_summary" / "selected_reco_histograms.root") as f:
        counts, edges = f[f"{stage}/numu_score"].to_numpy()
    mine, _ = np.histogram(scores_all, bins=edges)
    assert np.array_equal(mine, counts), f"{job_dir}: {stage} numu_score does not match the job's histogram"


def draw_stage(stage, split, out_dir):
    fig, axes = plt.subplots(1, 2, figsize=(18, 7.5), sharey=True)
    centers = 0.5 * (NUMU_EDGES[:-1] + NUMU_EDGES[1:])
    info = [f"# numu_score by TPC -- reco: {stage} (MC x {MC_SCALE:.4g}, off-beam x {OFF_SCALE:.4g})"]
    ymax = 1.0
    hists = {}
    for tpc, _ in TPCS:
        mc, _ = np.histogram(split['mc'][tpc], bins=NUMU_EDGES)
        off, _ = np.histogram(split['off'][tpc], bins=NUMU_EDGES)
        on, _ = np.histogram(split['on'][tpc], bins=NUMU_EDGES)
        hists[tpc] = (mc, off, on)
        ymax = max(ymax, float((off * OFF_SCALE + mc * MC_SCALE + np.sqrt(mc) * MC_SCALE).max()),
                   float((on + np.sqrt(on)).max()))
    for ax, (tpc, title) in zip(axes, TPCS):
        mc, off, on = hists[tpc]
        mc_s, off_s = mc * MC_SCALE, off * OFF_SCALE
        top, err = mc_s + off_s, np.sqrt(mc) * MC_SCALE
        ax.hist([centers, centers], bins=NUMU_EDGES, weights=[off_s, mc_s], stacked=True,
                histtype='stepfilled', color=[_OFF_COLOR, _MC_COLOR], edgecolor='black', linewidth=1.0,
                label=[f"Off-beam Data (POT-equiv. norm.) ({off_s.sum():.1f})",
                       f"BNB Light MC (POT norm.) ({mc_s.sum():.1f})"])
        lo, hi = top - err, top + err
        ax.fill_between(NUMU_EDGES, np.append(lo, lo[-1]), np.append(hi, hi[-1]), step='post',
                        facecolor='none', edgecolor='dimgray', hatch='///', linewidth=0.0,
                        label="BNB Light MC stat. unc.")
        nz = on > 0
        ax.errorbar(centers[nz], on[nz], yerr=np.sqrt(on[nz]), fmt='o', color=_DATA_COLOR,
                    markersize=6, capsize=3, linestyle='none',
                    label=f"On-beam data ({on.sum():.0f}, POT={POT_DATAON:.3e})")
        for cut in NUMU_SCORE_CUTS:
            ax.axvline(cut, color='tab:red', linestyle='--', linewidth=1.0)
        # Fraction above each cut, data vs prediction -- the TPC-dependent selection
        # efficiency -- from EVERY candidate, the off-axis ones included.
        s_mc, s_off, s_on = (np.asarray(split[k][tpc]) for k in ('mc', 'off', 'on'))
        n_pred = len(s_mc) * MC_SCALE + len(s_off) * OFF_SCALE
        lines = []
        for cut in NUMU_SCORE_CUTS:
            n_on = int(np.sum(s_on > cut))
            p_cut = np.sum(s_mc > cut) * MC_SCALE + np.sum(s_off > cut) * OFF_SCALE
            d = n_on / len(s_on) if len(s_on) else np.nan
            p = p_cut / n_pred if n_pred else np.nan
            lines.append(f"numu > {cut:g}: data {100 * d:.0f}%, pred. {100 * p:.0f}%")
            info.append(f"{tpc} numu_score > {cut:g}: data {n_on}/{len(s_on)} = {d:.3f}; "
                        f"pred. {p_cut:.1f}/{n_pred:.1f} = {p:.3f}")
        off_axis = {k: int(np.sum((np.asarray(split[k][tpc]) < NUMU_EDGES[0])
                                  | (np.asarray(split[k][tpc]) > NUMU_EDGES[-1]))) for k in ('mc', 'off', 'on')}
        lines.append(f"off axis (not drawn): data {off_axis['on']}, MC {off_axis['mc']}, off-beam {off_axis['off']}")
        info.append(f"{tpc} candidates: on-beam {len(s_on)}, MC raw {len(s_mc)} -> {len(s_mc) * MC_SCALE:.1f}, "
                    f"off-beam raw {len(s_off)} -> {len(s_off) * OFF_SCALE:.1f}; off the "
                    f"[{NUMU_EDGES[0]:g}, {NUMU_EDGES[-1]:g}] axis: {off_axis}")
        ax.text(0.03, 0.97, "\n".join(lines), transform=ax.transAxes, va='top', ha='left', fontsize=11,
                bbox=dict(facecolor='white', alpha=0.85, edgecolor='lightgray'))
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlim(NUMU_EDGES[0], NUMU_EDGES[-1])
        ax.xaxis.set_major_locator(MultipleLocator(1.0))
        ax.set_xlabel(r'$\nu_\mu$ CC BDT score (numu_score)', fontsize=13, fontweight='bold')
        ax.tick_params(axis='both', labelsize=11)
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.legend(fontsize=10, loc='upper right', framealpha=0.9)
    axes[0].set_ylabel('Number of Candidates', fontsize=13, fontweight='bold')
    axes[0].set_ylim(0, ymax * 1.45)
    fig.suptitle(f"Data/MC Overlay -- numu_score by TPC\nreco: {stage} (ROOT input)",
                 fontsize=15, fontweight='bold')
    fig.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"DataMC_Overlay_numu_score_{stage}_TPC0_vs_TPC1_liny"
    fig.savefig(out_dir / f"{name}.png", dpi=150, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    (out_dir / f"{name}_info.txt").write_text("\n".join(info) + "\n")
    print(f"wrote {out_dir / name}.png")


def main(runs, out_root):
    rows = {k: attach_vertices(read_candidates(runs[k]), SAMPLE_DIRS[k]) for k in ('mc', 'off', 'on')}
    for stage in STAGES:
        split = {}
        for k in ('mc', 'off', 'on'):
            sr = stage_rows(rows[k], stage)
            check_against_job(runs[k], stage, [r['numu_score'] for r in sr])
            split[k], n_novtx = tpc_split(sr)
            if n_novtx:
                print(f"  {stage} {k}: {n_novtx} candidate(s) without a vertex, in neither TPC")
        draw_stage(stage, split, Path(out_root) / stage / "NuMu_Score")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--mc-run", required=True)
    ap.add_argument("--offbeam-run", required=True)
    ap.add_argument("--onbeam-run", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    main({'mc': a.mc_run, 'off': a.offbeam_run, 'on': a.onbeam_run}, a.out)
