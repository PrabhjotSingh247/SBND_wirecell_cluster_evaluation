#!/usr/bin/env python3
"""
Apply the dead-area cut to the true-point files ONCE, up front, producing a new
input tree that the notebooks read instead of the raw one.

WHY THIS EXISTS
---------------
Reco points are never reconstructed inside a dead channel region, so true
deposits that land there could never have been seen by the detector. Removing
them is therefore not a "selection" in the same sense as an energy or fiducial
cut -- it is a correction that puts truth and reco on the same measurable
volume, and it belongs BEFORE everything else rather than at the end of the cut
chain. Baking it into the input files is exactly equivalent to applying it as
the first cut at runtime, and it means neither notebook pays for it again.

Note what this changes relative to applying the cut LAST (the ordering used
before this script existed): a true cluster's energy is now summed over
dead-area-filtered points, so the energy cut sees slightly less energy per
cluster and some clusters near the threshold will now fail it. That is the
intended consequence -- the threshold becomes a statement about recoverable
energy rather than deposited energy -- but it does mean completeness/purity
numbers shift versus older runs. It is a physics change, not a refactor.

WHAT IT WRITES
--------------
    <PARENT_DIR>_after_deadareacut/
        file0/data/0/0-sed-smear_readout.json            <- rewritten (filtered)
        file0/data/0/0-sed-sce_drift_smear_readout.json  <- rewritten (filtered)
        file0/data/0/0-img-global.json                   <- hardlink
        file0/data/0/0-clustering-global.json            <- hardlink
        file0/data/0/0-mc.json, 0-op.json, ...           <- hardlink
        DEADAREA_PREPROCESSING.txt                       <- provenance marker

Unmodified files are HARDLINKED, not copied: same filesystem, no extra disk,
and indistinguishable from real files to every reader. Source .zip archives are
deliberately NOT carried over -- they hold uncut data, and a zip of uncut points
sitting inside a tree named "_after_deadareacut" is a trap. The notebooks'
ensure_data_extracted() no-ops when data/ already exists, so nothing needs one.

The distinct directory name is the guard against mixing the two trees up: point
a notebook at this tree and drop Apply_deadarea_cut, point it at the raw tree
and keep it. There is no configuration that silently produces the wrong answer.

WHICH POINTS GET REMOVED
------------------------
The mask is computed by calling selections.apply_deadarea_cut_true_charge_light
itself -- the same function the pipeline used, with the same per-APA polygon
maps and the same X-sign split -- rather than reimplementing the geometry here.
The row index is smuggled through in an unused column and read back out, so what
survives is decided entirely by that function.

sed-smear_readout and sed-sce_drift_smear_readout are point-for-point aligned
(identical cluster_id/q/e/nu_idx per index; only x/y/z differ, since the SCE
correction is position-only -- mean |dx| ~97 cm). By default BOTH are filtered
with the mask derived from sed-smear's coordinates (--sce-mask=smear), on the
grounds that the readout position is what determines which channel saw the
charge, and that keeping the two files index-aligned preserves a property the
readers document. Pass --sce-mask=own to instead test each file against its own
coordinates; that is more literal but leaves the two files no longer aligned.

USAGE
-----
    python3 preprocess_deadarea_cut.py                    # dry run: report only
    python3 preprocess_deadarea_cut.py --write            # actually write
    python3 preprocess_deadarea_cut.py --write --files file0 file1
    python3 preprocess_deadarea_cut.py --write --force    # overwrite existing
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

from selections import apply_deadarea_cut_true_charge_light

DEFAULT_PARENT = Path("Haiwang_files_charge_light_matching_MCP2025C_Fall_production")
SUFFIX = "_after_deadareacut"

# The two true-point files. sed-smear is the one the pipeline cuts on and the one
# the mask is derived from; sed-sce rides along (see --sce-mask).
SED_SMEAR_SUFFIX = "-sed-smear_readout.json"
SED_SCE_SUFFIX = "-sed-sce_drift_smear_readout.json"

MARKER_NAME = "DEADAREA_PREPROCESSING.txt"


def deadarea_keep_mask(x, y, z, cluster_id, q, e, view_type="2view"):
    """
    Boolean keep-mask over the points, decided by the pipeline's own dead-area
    cut rather than by geometry reimplemented here.

    The trick: build the 7-column array the cut expects
    ([x, y, z, cluster_id, q_true, energy, time]) but put the ROW INDEX in the
    last column, which the cut never reads. It returns surviving rows, so the
    indices in that column are exactly the surviving rows' original positions.
    They come back reordered (the cut vstacks its APA0 half then its APA1 half),
    which is why the mask is built from the index set rather than from row order.
    """
    n = len(x)
    if n == 0:
        return np.zeros(0, dtype=bool)

    points = np.column_stack((
        np.asarray(x, dtype=float),
        np.asarray(y, dtype=float),
        np.asarray(z, dtype=float),
        np.asarray(cluster_id, dtype=float),
        np.asarray(q, dtype=float),
        np.asarray(e, dtype=float),
        np.arange(n, dtype=float),      # row index rides here
    ))

    kept = apply_deadarea_cut_true_charge_light(
        points, view_type=view_type, output_dir=None, verbose=False)

    mask = np.zeros(n, dtype=bool)
    if len(kept) > 0:
        mask[kept[:, 6].astype(np.int64)] = True
    return mask


def filter_sed_json(data, mask):
    """
    New dict with every per-point array filtered by mask and every scalar field
    (eventNo, runNo, geom, type, ...) carried through untouched. Key order is
    preserved so the rewritten file reads like the original.
    """
    n = len(mask)
    out = {}
    for key, value in data.items():
        if isinstance(value, list) and len(value) == n:
            out[key] = [v for v, keep in zip(value, mask) if keep]
        else:
            out[key] = value
    return out


def process_event_dir(src_event_dir, dst_event_dir, evt_name, sce_mask_mode, write, force):
    """
    One event directory. Returns (n_points_before, n_points_after, n_files_linked).
    """
    dst_event_dir.mkdir(parents=True, exist_ok=True)

    smear_src = None
    sce_src = None
    others = []
    for item in sorted(src_event_dir.iterdir()):
        if not item.is_file():
            continue
        if item.suffix == ".zip":
            continue                        # never carried over -- see module docstring
        if item.name.endswith(SED_SMEAR_SUFFIX):
            smear_src = item
        elif item.name.endswith(SED_SCE_SUFFIX):
            sce_src = item
        else:
            others.append(item)

    n_linked = 0
    for item in others:
        dst = dst_event_dir / item.name
        if dst.exists():
            if not force:
                continue
            if write:
                dst.unlink()
        if write:
            os.link(item, dst)
        n_linked += 1

    if smear_src is None:
        print(f"    {evt_name}: no {SED_SMEAR_SUFFIX} -- linked {n_linked} file(s), nothing to filter")
        return 0, 0, n_linked

    smear = json.loads(smear_src.read_text())
    n_before = len(smear.get("x", []))
    mask = deadarea_keep_mask(
        smear.get("x", []), smear.get("y", []), smear.get("z", []),
        smear.get("cluster_id", []), smear.get("q", []), smear.get("e", []))
    n_after = int(mask.sum())

    if write:
        (dst_event_dir / smear_src.name).write_text(json.dumps(filter_sed_json(smear, mask)))

    if sce_src is not None:
        sce = json.loads(sce_src.read_text())
        n_sce = len(sce.get("x", []))
        if sce_mask_mode == "own":
            sce_mask = deadarea_keep_mask(
                sce.get("x", []), sce.get("y", []), sce.get("z", []),
                sce.get("cluster_id", []), sce.get("q", []), sce.get("e", []))
        else:
            if n_sce != n_before:
                sys.exit(
                    f"ABORT: {sce_src} has {n_sce} points but {smear_src.name} has {n_before}. "
                    f"--sce-mask=smear requires the two to be point-for-point aligned; "
                    f"rerun with --sce-mask=own.")
            sce_mask = mask
        if write:
            (dst_event_dir / sce_src.name).write_text(json.dumps(filter_sed_json(sce, sce_mask)))

    removed = n_before - n_after
    pct = (100.0 * removed / n_before) if n_before else 0.0
    print(f"    {evt_name}: {n_before} -> {n_after} true points "
          f"({removed} removed, {pct:.2f}%), {n_linked} file(s) linked")
    return n_before, n_after, n_linked


def write_marker(dst_parent, src_parent, sce_mask_mode, stats):
    lines = [
        "=" * 78,
        "DEAD-AREA-PREPROCESSED INPUT TREE",
        "=" * 78,
        "",
        "The true-point files in this tree have already had the dead-area cut",
        "applied. Notebooks reading it must NOT apply the dead-area cut again.",
        "",
        f"Generated:        {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Generated by:     preprocess_deadarea_cut.py",
        f"Source tree:      {src_parent}",
        f"Dead-area maps:   Deadareas/2viewactive_2viewdead/"
        f"0-channel-deadarea-apa{{0,1}}-face0.json (view_type='2view')",
        f"sed-sce masking:  --sce-mask={sce_mask_mode}",
        "",
        "Rewritten (filtered):",
        f"  *{SED_SMEAR_SUFFIX}",
        f"  *{SED_SCE_SUFFIX}",
        "Everything else is hardlinked from the source tree. Source .zip archives",
        "are deliberately absent: they contain uncut data.",
        "",
        "-" * 78,
        f"Files processed:  {stats['files']}",
        f"Events processed: {stats['events']}",
        f"True points:      {stats['before']} -> {stats['after']} "
        f"({stats['before'] - stats['after']} removed, "
        f"{100.0 * (stats['before'] - stats['after']) / stats['before'] if stats['before'] else 0.0:.3f}%)",
        "=" * 78,
        "",
    ]
    (dst_parent / MARKER_NAME).write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--parent", type=Path, default=DEFAULT_PARENT,
                    help=f"source input tree (default: {DEFAULT_PARENT})")
    ap.add_argument("--out", type=Path, default=None,
                    help=f"destination tree (default: <parent>{SUFFIX})")
    ap.add_argument("--files", nargs="*", default=None,
                    help="only these file subdirectories (default: all)")
    ap.add_argument("--sce-mask", choices=("smear", "own"), default="smear",
                    help="how sed-sce is filtered: 'smear' reuses the sed-smear mask "
                         "(keeps the two files index-aligned; default), 'own' tests "
                         "sed-sce against its own coordinates")
    ap.add_argument("--write", action="store_true",
                    help="actually write; without it this is a dry run that only reports")
    ap.add_argument("--force", action="store_true",
                    help="replace files that already exist in the destination")
    args = ap.parse_args()

    src_parent = args.parent
    dst_parent = args.out or src_parent.parent / (src_parent.name + SUFFIX)

    if not src_parent.exists():
        sys.exit(f"ABORT: source tree {src_parent} does not exist")
    if dst_parent.resolve() == src_parent.resolve():
        sys.exit("ABORT: destination is the source tree -- that would destroy the originals")

    print("=" * 78)
    print("DEAD-AREA PREPROCESSING" + ("" if args.write else "  [DRY RUN -- nothing will be written]"))
    print("=" * 78)
    print(f"Source:      {src_parent}")
    print(f"Destination: {dst_parent}")
    print(f"sed-sce mask: {args.sce_mask}")
    print()

    file_dirs = [d for d in sorted(src_parent.iterdir())
                 if d.is_dir() and (d / "data").is_dir()]
    if args.files:
        wanted = set(args.files)
        file_dirs = [d for d in file_dirs if d.name in wanted]
    if not file_dirs:
        sys.exit(f"ABORT: no file subdirectories with data/ found under {src_parent}")

    if args.write:
        dst_parent.mkdir(parents=True, exist_ok=True)

    stats = {"files": 0, "events": 0, "before": 0, "after": 0, "linked": 0}
    t0 = time.time()

    for src_file_dir in file_dirs:
        print(f"  {src_file_dir.name}")
        src_data = src_file_dir / "data"
        dst_data = dst_parent / src_file_dir.name / "data"

        event_dirs = sorted((d for d in src_data.iterdir() if d.is_dir()),
                            key=lambda d: int(d.name) if d.name.isdigit() else d.name)
        for src_event_dir in event_dirs:
            before, after, linked = process_event_dir(
                src_event_dir, dst_data / src_event_dir.name, src_event_dir.name,
                args.sce_mask, args.write, args.force)
            stats["events"] += 1
            stats["before"] += before
            stats["after"] += after
            stats["linked"] += linked
        stats["files"] += 1

    removed = stats["before"] - stats["after"]
    pct = (100.0 * removed / stats["before"]) if stats["before"] else 0.0
    print()
    print("=" * 78)
    print(f"Files processed:  {stats['files']}")
    print(f"Events processed: {stats['events']}")
    print(f"True points:      {stats['before']} -> {stats['after']} ({removed} removed, {pct:.3f}%)")
    print(f"Files hardlinked: {stats['linked']}")
    print(f"Elapsed:          {time.time() - t0:.1f}s")
    print("=" * 78)

    if args.write:
        write_marker(dst_parent, src_parent, args.sce_mask, stats)
        print(f"\nWrote {dst_parent / MARKER_NAME}")
        print(f"Point both notebooks at: {dst_parent}")
        print("and make sure Apply_deadarea_cut is not applied again.")
    else:
        print("\nDry run -- rerun with --write to produce the tree.")


if __name__ == "__main__":
    main()
