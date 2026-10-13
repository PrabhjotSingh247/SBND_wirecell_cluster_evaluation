#!/usr/bin/env python3
"""
Stage 1 of the POT database chain: read the on-beam, off-beam, NuECC MC, or
NuMuCC MC bee zip file names for a given chunk/subchunk and write out a
run/subrun/event table.

Later stages use this table to look up the reco file (and then the CAF file)
for each event, and finally the POT for each reco file.

  python3 build_run_event_table.py --sample offbeam
  python3 build_run_event_table.py --sample onbeam --chunk chunk_01 --subchunk subchunk_03
  python3 build_run_event_table.py --sample numucc
  python3 build_run_event_table.py --sample nuecc
  python3 build_run_event_table.py --sample onbeam --full   # all chunk_00..chunk_09 (1000 zips)
  python3 build_run_event_table.py --sample onbeam --all    # every ROOT file in bee/, after_1000files/, tracking-pr/
"""
import argparse
import csv
import re
from pathlib import Path

SAMPLES_ROOT = Path("/Volumes/My Passport/Research_Life/Experiment/SBND/"
                     "Wirecell_Reconstruction/Samples")
BEE_DIR = {"onbeam": SAMPLES_ROOT / "r3-beam-on-2026-09-10" / "bee",
           "offbeam": SAMPLES_ROOT / "r3-beam-off-2026-09-11" / "bee",
           "numucc": SAMPLES_ROOT / "r3-mc-cv-2026-09-09" / "bee",
           "nuecc": SAMPLES_ROOT / "r3-nuecc-2026-09-10" / "bee"}
ZIP_RE = re.compile(r'^bee_r(\d+)_s(\d+)_e(\d+)\.zip$')
ROOT_RE = re.compile(r'^tracking-pr_r(\d+)_s(\d+)_e(\d+)\.root$')
# --all: the chunk_NN/subchunk_MM trees holding the sample's tracking-pr ROOT
# files (chunk_r3_rootfiles.py); tracking-pr/ has no zips, so --all reads ROOT names.
ALL_TOP_DIRS = ("bee", "after_1000files", "tracking-pr")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", choices=["onbeam", "offbeam", "numucc", "nuecc"], required=True)
    ap.add_argument("--chunk", default="chunk_00")
    ap.add_argument("--subchunk", default="subchunk_00")
    ap.add_argument("--full", action="store_true",
                     help="scan all chunk_00..chunk_09 / subchunk_00..09 under bee/ (the full 1000-zip sample) "
                          "instead of a single --chunk/--subchunk")
    ap.add_argument("--all", action="store_true",
                     help="scan every tracking-pr_*.root under bee/, after_1000files/ and tracking-pr/ "
                          "chunk_*/subchunk_* (every chunk of the sample) instead of the bee zips")
    ap.add_argument("--out", default=None,
                     help="output CSV path (default: POT_database/<sample>_<chunk>_<subchunk>_run_event.csv, "
                          "or POT_database/<sample>_full_1000events_run_event.csv with --full, "
                          "or POT_database/<sample>_all_<N>events_run_event.csv with --all)")
    args = ap.parse_args()

    bee_dir = BEE_DIR[args.sample]
    file_re = ROOT_RE if args.all else ZIP_RE
    if args.all:
        src_dirs = [d for top in ALL_TOP_DIRS
                    for d in sorted((bee_dir.parent / top).glob("chunk_*/subchunk_*")) if d.is_dir()]
        if not src_dirs:
            raise SystemExit(f"no chunk_*/subchunk_* directories found under {bee_dir.parent}")
    elif args.full:
        src_dirs = sorted(bee_dir.glob("chunk_*/subchunk_*"))
        if not src_dirs:
            raise SystemExit(f"no chunk_*/subchunk_* directories found under {bee_dir}")
    else:
        src_dirs = [bee_dir / args.chunk / args.subchunk]
        if not src_dirs[0].is_dir():
            raise SystemExit(f"no such directory: {src_dirs[0]}")

    rows = []
    for src_dir in src_dirs:
        for p in sorted(src_dir.iterdir()):
            m = file_re.match(p.name)
            if not m:
                if not args.all:   # --all: bee/ subchunks also hold the zips
                    print(f"WARNING: skipping non-matching file {p.name}")
                continue
            run, subrun, event = m.groups()
            rows.append((int(run), int(subrun), int(event)))

    if not rows:
        raise SystemExit(f"no matching files found in {src_dirs}")
    if args.all:
        rows.sort()
        if len(set(rows)) != len(rows):
            raise SystemExit(f"{len(rows) - len(set(rows))} duplicate run/subrun/event rows")

    if args.out:
        out_path = Path(args.out)
    elif args.all:
        out_path = Path(__file__).parent / f"{args.sample}_all_{len(rows)}events_run_event.csv"
    elif args.full:
        out_path = Path(__file__).parent / f"{args.sample}_full_1000events_run_event.csv"
    else:
        out_path = Path(__file__).parent / f"{args.sample}_{args.chunk}_{args.subchunk}_run_event.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["run", "subrun", "event"])
        writer.writerows(rows)

    print(f"wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
