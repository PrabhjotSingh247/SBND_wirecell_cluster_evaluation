#!/bin/bash
# Build a single BEE event-display zip from clustering and truth data
# and upload it. Extends bee-upload.sh to include truth information.
#
# Inputs (in $PWD):
#   mabc-*.zip          each containing data/<n>/<n>-<alg>.json (clustering)
#   tru-apa*.json       truth deposition data for BEE display (optional)
#   tru-*.zip           zipped truth data (optional)
#   data-sep/<n>/<n>-img-apa{0,1}.json   to be merged across APAs
#   data-sep/<n>/<n>-op-apa{0,1}.json    to be merged across APAs
#
# Output:
#   data/<n>/<n>-<alg>.json (union of clustering + truth)
#   combined.zip            zip of data/, uploaded to BEE
set -eo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORIGINAL_BEE_DIR="/exp/sbnd/data/users/prabhjot/wirecell_clustering/developcode/wcp-porting-validation/"
UPLOAD="${UPLOAD_TO_BEE:-$ORIGINAL_BEE_DIR/upload-to-bee.sh}"
MERGE_APA="$ORIGINAL_BEE_DIR/merge-apa.py"
OUT_ZIP="combined.zip"
WORK="data"

if [[ ! -x "$UPLOAD" ]]; then
    echo "ERROR: upload helper not found: $UPLOAD" >&2
    exit 1
fi

# Fresh workspace.
rm -rf "$WORK" "$OUT_ZIP"
mkdir -p "$WORK"

# --- Stream A: drop mabc-*.zip contents into data/<n>/  (cluster JSONs) -----
shopt -s nullglob
mabc_zips=( mabc-*.zip )
if (( ${#mabc_zips[@]} )); then
    echo "[mabc]   extracting ${#mabc_zips[@]} zip(s) -> data/"
    for z in "${mabc_zips[@]}"; do
        python3 -m zipfile -e "$z" .
    done
else
    echo "[mabc]   no mabc-*.zip in $PWD"
fi

# --- Stream B: extract truth data from tru-*.zip (if present) ----------------
tru_zips=( tru-*.zip )
if (( ${#tru_zips[@]} )); then
    echo "[truth]  extracting ${#tru_zips[@]} truth zip(s) -> data/"
    for z in "${tru_zips[@]}"; do
        python3 -m zipfile -e "$z" .
    done
else
    echo "[truth]  no tru-*.zip in $PWD"
fi

# --- Stream C: copy truth JSON files if they exist in the same directory -----
tru_jsons=( tru-apa*.json )
if (( ${#tru_jsons[@]} )); then
    echo "[truth]  found ${#tru_jsons[@]} truth JSON file(s), organizing into data/"
    for tru_file in "${tru_jsons[@]}"; do
        # Extract event number from filename (e.g., tru-apa0.json -> parse event numbers)
        # Truth files are typically named: tru-apa0.json, tru-apa1.json, etc.
        # Each may contain multiple events in JSON array format

        # Determine which APA this truth file is for
        apa_suffix="${tru_file#tru-}"  # Remove "tru-" prefix (e.g., "apa0.json")

        # Copy or integrate truth data into data/ directory
        # Structure: data/<event_no>/
        # If truth file contains per-event data, extract and organize
        if [[ -f "$tru_file" ]]; then
            echo "  Processing truth file: $tru_file"
            # Use Python to parse JSON and organize by event
            python3 << PYTHON_END
import json
import sys
from pathlib import Path

tru_file = "$tru_file"
work_dir = Path("$WORK")
apa_suffix = "$apa_suffix"

try:
    with open(tru_file, 'r') as f:
        data = json.load(f)

    # If data is a dict with event keys
    if isinstance(data, dict):
        for event_key, event_data in data.items():
            event_no = event_key if event_key.isdigit() else str(event_key).split('/')[-1]
            event_dir = work_dir / event_no
            event_dir.mkdir(parents=True, exist_ok=True)

            # Save as truth JSON in data/<event_no>/ directory
            truth_json = event_dir / f"{event_no}-truth-{apa_suffix}"
            with open(truth_json, 'w') as out:
                json.dump(event_data, out, indent=2)

    # If data is a list (array of events)
    elif isinstance(data, list):
        for idx, event_data in enumerate(data):
            event_dir = work_dir / str(idx)
            event_dir.mkdir(parents=True, exist_ok=True)

            # Save as truth JSON in data/<event_no>/ directory
            truth_json = event_dir / f"{idx}-truth-{apa_suffix}"
            with open(truth_json, 'w') as out:
                json.dump(event_data, out, indent=2)

except Exception as e:
    print(f"Warning: Could not process {tru_file}: {e}", file=sys.stderr)
PYTHON_END
        fi
    done
else
    echo "[truth]  no tru-apa*.json in $PWD"
fi

shopt -u nullglob

# --- Stream D: merge per-event APA pairs into data/<n>/<n>-img.json/op.json -
if [[ -d data-sep ]]; then
    for event_dir in data-sep/*; do
        event_no=$(basename "$event_dir")
        if [[ -d "$event_dir" && "$event_no" =~ ^[0-9]+$ ]]; then
            echo "[apa]    event $event_no: merge-apa.py img/op apa0+apa1"
            python3 "$MERGE_APA" --inpath=data-sep --outpath="$WORK" --eventNo="$event_no" > /dev/null
        fi
    done
else
    echo "[apa]    no data-sep/ in $PWD"
fi

echo
echo "=== combined event tree (clustering + truth) ==="
find "$WORK" -maxdepth 2 -type f | sort | sed 's,^,  ,'

# --- Pack + upload ---------------------------------------------------------
echo
echo "[zip]    packaging $WORK -> $OUT_ZIP"
python3 -m zipfile -c "$OUT_ZIP" "$WORK"

echo "[upload] $OUT_ZIP"
URL=$(BROWSER=echo bash "$UPLOAD" "$OUT_ZIP" | tail -1)

echo
echo "=== BEE event display (with truth data) ==="
echo "  $URL"
