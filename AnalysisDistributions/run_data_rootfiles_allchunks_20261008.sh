#!/bin/bash
# All-chunk (101 chunks each: bee/ + after_1000files/ + tracking-pr/) ROOT-input
# data chain, requested 2026-10-08, no reco cluster energy plots:
#   1. SignalBackground_Distributions_BeforeCosmicTagger_Data_OffBeam_InputRootFiles  (9999 events)
#   2. SignalBackground_Distributions_BeforeCosmicTagger_Data_OnBeam_InputRootFiles   (10000 events)
#
# Each target runs to completion; a failure is logged and the chain moves on.
set -u
REPO="/Users/prabhjotsingh/Experiments/SBND/WireCell_Reconstruction"
ND="$REPO/AnalysisDistributions"
RUNDIR="$ND/multi_file_plots_charge_light_matching/data_rootfiles_allchunks_chain_20261008"
mkdir -p "$RUNDIR"
STATUS="$RUNDIR/STATUS.txt"

{
  echo "DATA ROOT-FILE ALL-CHUNKS CHAIN -- started $(date)"
  echo "1: SignalBackground_Distributions_BeforeCosmicTagger_Data_OffBeam_InputRootFiles (101 chunks)"
  echo "2: SignalBackground_Distributions_BeforeCosmicTagger_Data_OnBeam_InputRootFiles (101 chunks)"
  echo
} > "$STATUS"

run_nb () {
  local nb="$1" label="$2" t0 rc dt out
  t0=$(date +%s)
  echo "[$(date +%H:%M:%S)] START  $label" | tee -a "$STATUS"
  ( cd "$ND" && python3 -m jupyter nbconvert --to notebook --execute \
      --ExecutePreprocessor.timeout=-1 \
      --output "$RUNDIR/${label}.executed.ipynb" "${nb}.ipynb" ) > "$RUNDIR/${label}.log" 2>&1
  rc=$?
  dt=$(( ($(date +%s)-t0)/60 ))
  if [ $rc -eq 0 ] && ! grep -qE "Traceback \(most recent call last\)|CellExecutionError" "$RUNDIR/${label}.log"; then
    out=$(ls -dt "$ND"/multi_file_plots_charge_light_matching/"$nb"/combined_apa_* 2>/dev/null | head -1)
    echo "[$(date +%H:%M:%S)] PASS   $label  (${dt}m)" | tee -a "$STATUS"
    echo "    -> ${out:-<no combined_apa dir found>}" >> "$STATUS"
  else
    echo "[$(date +%H:%M:%S)] FAIL   $label  (${dt}m, rc=$rc)" | tee -a "$STATUS"
    grep -A25 "Traceback (most recent call last)" "$RUNDIR/${label}.log" | head -30 | sed 's/^/    /' >> "$STATUS"
    tail -n 8 "$RUNDIR/${label}.log" | sed 's/^/    | /' >> "$STATUS"
  fi
  echo >> "$STATUS"
}

run_nb "SignalBackground_Distributions_BeforeCosmicTagger_Data_OffBeam_InputRootFiles" "1_Data_OffBeam_InputRootFiles_allchunks"
run_nb "SignalBackground_Distributions_BeforeCosmicTagger_Data_OnBeam_InputRootFiles"  "2_Data_OnBeam_InputRootFiles_allchunks"

{ echo; echo "CHAIN COMPLETE $(date)"; } >> "$STATUS"
