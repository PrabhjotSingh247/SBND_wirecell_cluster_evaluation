#!/bin/bash
# Sequential lunch-break chain, requested 2026-09-21, all on the NuE CC sample
# (r3-nuecc-2026-09-10):
#   1. Draw_Selection_Cosmics            (chunk_00 only)
#   2. DrawRecoTrueClusters_Below_60pc_Completeness   (chunk_00 only)
#   3. DrawRecoTrueClusters_Below_60pc_Purity         (chunk_00 only)
#   4. Draw_Cluster_Flashes              (full: chunk_00..chunk_09, 1000 events)
#   5. Draw_Signal_Background_True       (full: chunk_00..chunk_09, 1000 events)
# ("DrawInVolumeTwoNeutrinos" from the original request has no matching
#  notebook in the repo -- skipped, flagged in STATUS.txt, not run here.)
# Each target runs to completion; a failure is logged and the chain moves on.
set -u
REPO="/Users/prabhjotsingh/Experiments/SBND/WireCell_Reconstruction"
ND="$REPO/AnalysisDistributions"
RUNDIR="$ND/multi_file_plots_charge_light_matching/lunch_chain_nuecc_20260921"
mkdir -p "$RUNDIR"
STATUS="$RUNDIR/STATUS.txt"

{
  echo "LUNCH CHAIN (NuE CC) -- started $(date)"
  echo "1: Draw_Selection_Cosmics (chunk_00 only)"
  echo "2: DrawRecoTrueClusters_Below_60pc_Completeness (chunk_00 only)"
  echo "3: DrawRecoTrueClusters_Below_60pc_Purity (chunk_00 only)"
  echo "4: Draw_Cluster_Flashes (full, chunk_00..chunk_09)"
  echo "5: Draw_Signal_Background_True (full, chunk_00..chunk_09)"
  echo "SKIPPED: DrawInVolumeTwoNeutrinos -- no matching notebook found in the repo"
  echo
} > "$STATUS"

run_nb () {
  local nb="$1" t0 rc dt out
  t0=$(date +%s)
  echo "[$(date +%H:%M:%S)] START  $nb" | tee -a "$STATUS"
  ( cd "$ND" && python3 -m jupyter nbconvert --to notebook --execute \
      --ExecutePreprocessor.timeout=-1 \
      --output "$RUNDIR/${nb}.executed.ipynb" "${nb}.ipynb" ) > "$RUNDIR/${nb}.log" 2>&1
  rc=$?
  dt=$(( ($(date +%s)-t0)/60 ))
  if [ $rc -eq 0 ] && ! grep -qE "Traceback \(most recent call last\)|CellExecutionError" "$RUNDIR/${nb}.log"; then
    out=$(ls -dt "$ND"/multi_file_plots_charge_light_matching/"$nb"/*/combined_apa_* "$ND"/multi_file_plots_charge_light_matching/"$nb"/combined_apa_* 2>/dev/null | head -1)
    echo "[$(date +%H:%M:%S)] PASS   $nb  (${dt}m)" | tee -a "$STATUS"
    echo "    -> ${out:-<no combined_apa dir found>}" >> "$STATUS"
  else
    echo "[$(date +%H:%M:%S)] FAIL   $nb  (${dt}m, rc=$rc)" | tee -a "$STATUS"
    grep -A25 "Traceback (most recent call last)" "$RUNDIR/${nb}.log" | head -30 | sed 's/^/    /' >> "$STATUS"
    tail -n 8 "$RUNDIR/${nb}.log" | sed 's/^/    | /' >> "$STATUS"
  fi
  echo >> "$STATUS"
}

for nb in \
  Draw_Selection_Cosmics \
  DrawRecoTrueClusters_Below_60pc_Completeness \
  DrawRecoTrueClusters_Below_60pc_Purity \
  Draw_Cluster_Flashes \
  Draw_Signal_Background_True ; do
  run_nb "$nb"
done

{ echo; echo "LUNCH CHAIN COMPLETE $(date)"; } >> "$STATUS"
