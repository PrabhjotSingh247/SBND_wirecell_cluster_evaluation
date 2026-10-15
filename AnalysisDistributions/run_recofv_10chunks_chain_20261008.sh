#!/bin/bash
# 10-chunk (bee/chunk_00..09) ROOT-input chain with the new reco-vertex FV stage,
# requested 2026-10-08. Stages: AfterBeamWindowCut -> NuCandidate ->
# NuCandidate_FiducialRecoVertex -> ..._NuMuScore_gt0 / _gt0p9. All variables.
#   1. SignalBackground_Distributions_BeforeCosmicTagger_Data_OffBeam_InputRootFiles
#   2. SignalBackground_Distributions_BeforeCosmicTagger_Data_OnBeam_InputRootFiles
#   3. SignalBackground_Distributions_BeforeCosmicTagger_MC_InputRootFiles (CV_MC_Sample)
#   4. draw_data_mc_overlay_plots_InputRootFiles.py on the three outputs above
#
# Each notebook runs to completion; a failure is logged and the chain moves on.
# The overlays run only if all three notebooks passed.
set -u
REPO="/Users/prabhjotsingh/Experiments/SBND/WireCell_Reconstruction"
ND="$REPO/AnalysisDistributions"
PLOTS="$ND/multi_file_plots_charge_light_matching"
RUNDIR="$PLOTS/recofv_10chunks_chain_20261008"
mkdir -p "$RUNDIR"
STATUS="$RUNDIR/STATUS.txt"
N_FAIL=0

{
  echo "RECO-VERTEX FV 10-CHUNK CHAIN -- started $(date)"
  echo "1: Data_OffBeam_InputRootFiles   2: Data_OnBeam_InputRootFiles   3: MC_InputRootFiles (CV)"
  echo "4: Data/MC overlay plots"
  echo
} > "$STATUS"

run_nb () {
  local nb="$1" label="$2" outglob="$3" t0 rc dt out
  t0=$(date +%s)
  echo "[$(date +%H:%M:%S)] START  $label" | tee -a "$STATUS"
  ( cd "$ND" && python3 -m jupyter nbconvert --to notebook --execute \
      --ExecutePreprocessor.timeout=-1 \
      --output "$RUNDIR/${label}.executed.ipynb" "${nb}.ipynb" ) > "$RUNDIR/${label}.log" 2>&1
  rc=$?
  dt=$(( ($(date +%s)-t0)/60 ))
  out=$(ls -dt $outglob 2>/dev/null | head -1)
  if [ $rc -eq 0 ] && ! grep -qE "Traceback \(most recent call last\)|CellExecutionError" "$RUNDIR/${label}.log"; then
    echo "[$(date +%H:%M:%S)] PASS   $label  (${dt}m)" | tee -a "$STATUS"
    echo "    -> ${out:-<no combined_apa dir found>}" >> "$STATUS"
    echo "$out" > "$RUNDIR/${label}.outdir"
  else
    N_FAIL=$((N_FAIL+1))
    echo "[$(date +%H:%M:%S)] FAIL   $label  (${dt}m, rc=$rc)" | tee -a "$STATUS"
    grep -A25 "Traceback (most recent call last)" "$RUNDIR/${label}.log" | head -30 | sed 's/^/    /' >> "$STATUS"
    tail -n 8 "$RUNDIR/${label}.log" | sed 's/^/    | /' >> "$STATUS"
  fi
  echo >> "$STATUS"
}

OFF_NB="SignalBackground_Distributions_BeforeCosmicTagger_Data_OffBeam_InputRootFiles"
ON_NB="SignalBackground_Distributions_BeforeCosmicTagger_Data_OnBeam_InputRootFiles"
MC_NB="SignalBackground_Distributions_BeforeCosmicTagger_MC_InputRootFiles"
run_nb "$OFF_NB" "1_Data_OffBeam" "$PLOTS/$OFF_NB/combined_apa_*"
run_nb "$ON_NB"  "2_Data_OnBeam"  "$PLOTS/$ON_NB/combined_apa_*"
run_nb "$MC_NB"  "3_MC_CV"        "$PLOTS/$MC_NB/CV_MC_Sample/combined_apa_*"

if [ $N_FAIL -eq 0 ]; then
  OUT="$PLOTS/Data_MC_Overlay_Plots_InputRootFiles/RecoFV_10chunks_20261008"
  echo "[$(date +%H:%M:%S)] START  4_Overlay -> $OUT" | tee -a "$STATUS"
  ( cd "$ND" && python3 draw_data_mc_overlay_plots_InputRootFiles.py \
      --mc-run "$(cat "$RUNDIR/3_MC_CV.outdir")" \
      --offbeam-run "$(cat "$RUNDIR/1_Data_OffBeam.outdir")" \
      --onbeam-run "$(cat "$RUNDIR/2_Data_OnBeam.outdir")" \
      --out "$OUT" ) > "$RUNDIR/4_Overlay.log" 2>&1
  if [ $? -eq 0 ]; then
    echo "[$(date +%H:%M:%S)] PASS   4_Overlay ($(find "$OUT" -name '*.png' | wc -l | tr -d ' ') PNGs)" | tee -a "$STATUS"
  else
    echo "[$(date +%H:%M:%S)] FAIL   4_Overlay" | tee -a "$STATUS"
    tail -n 25 "$RUNDIR/4_Overlay.log" | sed 's/^/    | /' >> "$STATUS"
  fi
else
  echo "4_Overlay SKIPPED: $N_FAIL notebook(s) failed" | tee -a "$STATUS"
fi

{ echo; echo "CHAIN COMPLETE $(date)"; } >> "$STATUS"
