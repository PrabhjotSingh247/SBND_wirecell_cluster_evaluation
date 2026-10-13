#!/usr/bin/env python3
"""
Number of events per run number, from a build_run_event_table.py CSV.

  python3 draw_events_per_run.py onbeam_full_1000events_run_event.csv --label "On-beam, 10 chunks (bee/)"
  python3 draw_events_per_run.py onbeam_all_10000events_run_event.csv --label "On-beam, all chunks"

One bin per run number, from the first to the last run in the CSV, so runs with
no events show as gaps (empty bins undrawn). Black points, sqrt(N) bars and a
count + fractional-uncertainty label per point. Writes
POT_database/plots/<csv stem>_events_per_run.png and a matching _info.txt.
"""
import argparse
import csv
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator, MultipleLocator


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="run/subrun/event CSV from build_run_event_table.py")
    ap.add_argument("--label", required=True, help="sample name for the title and legend")
    ap.add_argument("--out-dir", default=str(Path(__file__).parent / "plots"))
    args = ap.parse_args()

    csv_path = Path(args.csv)
    with open(csv_path, newline="") as f:
        rows = [(int(row["run"]), int(row["subrun"])) for row in csv.DictReader(f)]
    runs = [run for run, _ in rows]
    per_run = Counter(runs)
    subruns_per_run = {}
    for run, subrun in rows:
        subruns_per_run.setdefault(run, set()).add(subrun)

    run_numbers = np.arange(min(per_run) - 1, max(per_run) + 2)   # one empty bin either side
    counts = np.array([per_run.get(r, 0) for r in run_numbers])
    errors = np.sqrt(counts)
    nonzero = counts > 0

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.errorbar(run_numbers[nonzero], counts[nonzero], yerr=errors[nonzero], fmt="o",
                mfc="none", mec="black", ecolor="black", markersize=8, capsize=3,
                linestyle="none", label=f"{args.label} ({len(runs)} events)")
    for r, n, e in zip(run_numbers[nonzero], counts[nonzero], errors[nonzero]):
        ax.annotate(f"{n}  ({100.0 * e / n:.1f}%)", (r, n + e), textcoords="offset points",
                    xytext=(0, 6), ha="center", fontsize=12)

    ax.set_xlabel("Run Number", fontsize=14, fontweight="bold")
    ax.set_ylabel("Number of Events", fontsize=14, fontweight="bold")
    ax.set_title(f"Events per Run -- {args.label}", fontsize=15, fontweight="bold")
    ax.tick_params(axis="both", labelsize=12)
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.set_xlim(run_numbers[0] - 0.5, run_numbers[-1] + 0.5)
    ax.xaxis.set_major_locator(MultipleLocator(1))
    ax.ticklabel_format(axis="x", useOffset=False, style="plain")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_ylim(0, float((counts + errors).max()) * 1.25)
    ax.legend(fontsize=12, loc="upper right", framealpha=0.9)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{csv_path.stem}_events_per_run"
    fig.savefig(out_dir / f"{stem}.png", dpi=150, bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)

    lines = [f"# Events per run -- {args.label}", f"# source: {csv_path.name}",
             f"# total events: {len(runs)}   runs: {len(per_run)}",
             "# run\tevents\tsqrt(N)\tfrac_unc_%\tsubruns"]
    for r in sorted(per_run):
        n = per_run[r]
        lines.append(f"{r}\t{n}\t{np.sqrt(n):.1f}\t{100.0 / np.sqrt(n):.1f}\t"
                     f"{','.join(str(s) for s in sorted(subruns_per_run[r]))}")
    (out_dir / f"{stem}_info.txt").write_text("\n".join(lines) + "\n")
    print(f"wrote {out_dir / stem}.png and _info.txt")


if __name__ == "__main__":
    main()
