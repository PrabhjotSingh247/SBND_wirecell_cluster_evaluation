#!/usr/bin/env python3
"""
Move the flat r3 tracking-pr/*.root files into the chunk_NN/subchunk_MM/ layout
of the sample's bee zips, so the ROOT file and the zip (JSONs) of the same
(run, subrun, event) sit in one folder:

  matched   : tracking-pr_rX_sY_eZ.root whose bee_rX_sY_eZ.zip exists anywhere
              under bee/, after_1000files/ or corrupted/ -> moved into THAT
              zip's folder
  root-only : no zip on disc -> tracking-pr/chunk_NN/subchunk_MM/, chunked like
              chunk_r3_*_sample.py: seeded random chunk assignment (seed = the
              sample's own date), subchunk by sorted name within the chunk,
              100 / chunk, 10 / subchunk. Chunk numbering continues after the
              highest chunk_NN already used by the sample, so the names stay
              unique across bee/, after_1000files/ and tracking-pr/.

MOVES the files (rename, same volume), then writes tracking-pr/root_manifest.txt
listing where every ROOT file lives. Re-runnable: only files still flat in
tracking-pr/ are planned; anything already placed is left alone (a later batch of
flat root-only files gets new chunks after the current highest).

  python3 chunk_r3_rootfiles.py --sample r3-beam-off-2026-09-11 --dry-run
  python3 chunk_r3_rootfiles.py --sample r3-beam-off-2026-09-11
"""
import argparse
import random
import re
import sys
from pathlib import Path

SAMPLES = Path("/Volumes/My Passport/Research_Life/Experiment/SBND/"
               "Wirecell_Reconstruction/Samples")
CHUNK_SIZE = 100
SUBCHUNK_SIZE = 10
ROOT_RE = re.compile(r'^tracking-pr_r(\d+)_s(\d+)_e(\d+)\.root$')
ZIP_RE = re.compile(r'^bee_r(\d+)_s(\d+)_e(\d+)\.zip$')
CHUNK_RE = re.compile(r'^chunk_(\d+)$')
ZIP_HOMES = ("bee", "after_1000files", "corrupted")


def seed_of(sample_dir):
    """r3-beam-off-2026-09-11 -> 20260911, the convention of chunk_r3_*_sample.py."""
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})$', sample_dir.name)
    if not m:
        sys.exit(f"cannot read a date from sample name {sample_dir.name}")
    return int("".join(m.groups()))


def zip_folders(sample_dir):
    """{(run, subrun, event): folder holding its bee zip}."""
    out = {}
    for home in ZIP_HOMES:
        if not (sample_dir / home).is_dir():
            continue
        for z in (sample_dir / home).rglob("bee_r*_s*_e*.zip"):
            m = ZIP_RE.match(z.name)
            if m:
                out[m.groups()] = z.parent
    return out


def max_chunk_index(sample_dir):
    idx = [-1]
    for home in ZIP_HOMES + ("tracking-pr",):
        if (sample_dir / home).is_dir():
            idx += [int(m.group(1)) for d in (sample_dir / home).iterdir()
                    if d.is_dir() and (m := CHUNK_RE.match(d.name))]
    return max(idx)


def plan(sample_dir):
    """[(root_name, dest_folder), ...] for every ROOT file still flat in tracking-pr/."""
    tp = sample_dir / "tracking-pr"
    flat = sorted(p.name for p in tp.iterdir() if p.is_file() and ROOT_RE.match(p.name))
    zips = zip_folders(sample_dir)

    rows = []
    root_only = []
    for name in flat:
        folder = zips.get(ROOT_RE.match(name).groups())
        if folder is None:
            root_only.append(name)
        else:
            rows.append((name, folder))
    n_matched = len(rows)

    # Seeded shuffle -> chunk assignment, numbered after every chunk already used.
    first = max_chunk_index(sample_dir) + 1
    shuffled = list(root_only)
    random.Random(seed_of(sample_dir)).shuffle(shuffled)
    by_chunk = {}
    for i, name in enumerate(shuffled):
        by_chunk.setdefault(f"chunk_{first + i // CHUNK_SIZE:02d}", []).append(name)
    # Numeric order: past chunk_99 the names stop sorting as strings.
    for ch in sorted(by_chunk, key=lambda c: int(CHUNK_RE.match(c).group(1))):
        for j, name in enumerate(sorted(by_chunk[ch])):
            rows.append((name, tp / ch / f"subchunk_{j // SUBCHUNK_SIZE:02d}"))
    return rows, n_matched, len(root_only), first


def write_manifest(sample_dir):
    """tracking-pr/root_manifest.txt: run, subrun, event, folder (relative to the
    sample), and whether its zip is in the same folder."""
    entries = []
    for p in sample_dir.rglob("tracking-pr_r*_s*_e*.root"):
        m = ROOT_RE.match(p.name)
        if m:
            r, s, e = m.groups()
            has_zip = (p.parent / f"bee_r{r}_s{s}_e{e}.zip").exists()
            entries.append((int(r), int(s), int(e), str(p.parent.relative_to(sample_dir)),
                            int(has_zip)))
    entries.sort()
    manifest = sample_dir / "tracking-pr" / "root_manifest.txt"
    with open(manifest, "w") as f:
        f.write(f"# {sample_dir.name} -- {len(entries)} tracking-pr ROOT files, "
                f"{sum(e[4] for e in entries)} next to their bee zip\n")
        f.write("# run\tsubrun\tevent\tfolder\thas_zip\n")
        for row in entries:
            f.write("\t".join(map(str, row)) + "\n")
    return manifest, len(entries)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", required=True, help="e.g. r3-beam-off-2026-09-11")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sample_dir = SAMPLES / args.sample
    if not (sample_dir / "tracking-pr").is_dir():
        sys.exit(f"no tracking-pr/ under {sample_dir}")

    rows, n_matched, n_root_only, first = plan(sample_dir)
    print(f"{args.sample}: {len(rows)} flat ROOT files -> {n_matched} next to their zip, "
          f"{n_root_only} root-only")
    if n_root_only:
        last = first + (n_root_only - 1) // CHUNK_SIZE
        print(f"root-only chunks: tracking-pr/chunk_{first:02d} .. chunk_{last:02d} "
              f"(seed {seed_of(sample_dir)})")
    if args.dry_run:
        from collections import Counter
        homes = Counter(str(d.relative_to(sample_dir)).split("/")[0] for _, d in rows)
        print(f"destinations by top folder: {dict(homes)}")
        sub_counts = Counter(d for _, d in rows[n_matched:])
        odd = {str(k.relative_to(sample_dir)): v for k, v in sub_counts.items()
               if v != SUBCHUNK_SIZE}
        print(f"root-only subchunks not exactly {SUBCHUNK_SIZE}: {odd}")
        for name, d in rows[:3] + rows[n_matched:n_matched + 3]:
            print(f"  {name}  ->  {d.relative_to(sample_dir)}")
        return

    tp = sample_dir / "tracking-pr"
    moved = 0
    for name, dest_dir in rows:
        dest = dest_dir / name
        if dest.exists():
            sys.exit(f"REFUSING to overwrite {dest}")
        dest_dir.mkdir(parents=True, exist_ok=True)
        (tp / name).rename(dest)
        moved += 1
        if moved % 2000 == 0:
            print(f"  moved {moved} ...", flush=True)
    print(f"moved {moved}")

    manifest, n = write_manifest(sample_dir)
    print(f"wrote {manifest} ({n} ROOT files)")
    leftover = [p.name for p in tp.iterdir() if p.is_file() and ROOT_RE.match(p.name)]
    if leftover:
        print(f"WARNING: {len(leftover)} ROOT file(s) still flat in tracking-pr/: {leftover[:5]}")
    else:
        print("tracking-pr/ root is clean -- only chunk_* dirs and root_manifest.txt remain")


if __name__ == "__main__":
    main()
