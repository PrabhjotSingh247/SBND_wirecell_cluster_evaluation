#!/bin/bash
# Full-scale (10 chunks / 1000 files) chain, requested 2026-09-22:
#   1. SignalBackground_Distributions_BeforeCosmicTagger        (NuMuCC_Sample)
#   2. SignalBackground_Distributions_BeforeCosmicTagger        (NuECC_Sample)
#   3. SignalBackground_Distributions_BeforeCosmicTagger_Data_OffBeam
#   4. SignalBackground_Distributions_BeforeCosmicTagger_Data_OnBeam
#
# (1) and (2) share one notebook file; SAMPLE_NAME is flipped NuMuCC -> NuECC
# between the two runs, then flipped back to NuMuCC (the file's resting
# default) once both have finished, so the checked-in notebook ends up
# unchanged apart from the 50 MeV addition.
#
# All four notebooks already carry the new 50 MeV subdirectory in
# selection_efficiency/ and selection_reco/, added alongside the existing
# 100/200 MeV ones -- see SELECTION_BIN_WIDTHS_MEV in each notebook.
#
# Each target runs to completion; a failure is logged and the chain moves on.
set -u
REPO="/Users/prabhjotsingh/Experiments/SBND/WireCell_Reconstruction"
ND="$REPO/AnalysisDistributions"
RUNDIR="$ND/multi_file_plots_charge_light_matching/beforecosmictagger_chain_20260922"
mkdir -p "$RUNDIR"
STATUS="$RUNDIR/STATUS.txt"
NB_MC="$ND/SignalBackground_Distributions_BeforeCosmicTagger.ipynb"

{
  echo "BEFORE-COSMIC-TAGGER CHAIN -- started $(date)"
  echo "1: SignalBackground_Distributions_BeforeCosmicTagger (NuMuCC_Sample, full 10 chunks)"
  echo "2: SignalBackground_Distributions_BeforeCosmicTagger (NuECC_Sample, full 10 chunks)"
  echo "3: SignalBackground_Distributions_BeforeCosmicTagger_Data_OffBeam (full 10 chunks)"
  echo "4: SignalBackground_Distributions_BeforeCosmicTagger_Data_OnBeam (full 10 chunks)"
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
    out=$(ls -dt "$ND"/multi_file_plots_charge_light_matching/"$nb"/*/combined_apa_* "$ND"/multi_file_plots_charge_light_matching/"$nb"/combined_apa_* 2>/dev/null | head -1)
    echo "[$(date +%H:%M:%S)] PASS   $label  (${dt}m)" | tee -a "$STATUS"
    echo "    -> ${out:-<no combined_apa dir found>}" >> "$STATUS"
  else
    echo "[$(date +%H:%M:%S)] FAIL   $label  (${dt}m, rc=$rc)" | tee -a "$STATUS"
    grep -A25 "Traceback (most recent call last)" "$RUNDIR/${label}.log" | head -30 | sed 's/^/    /' >> "$STATUS"
    tail -n 8 "$RUNDIR/${label}.log" | sed 's/^/    | /' >> "$STATUS"
  fi
  echo >> "$STATUS"
}

flip_sample () {
  python3 "$ND/_flip_sample_name.py" "$NB_MC" "$1" "$2"
}

# 1. NuMuCC -- notebook already configured for it
run_nb "SignalBackground_Distributions_BeforeCosmicTagger" "1_BeforeCosmicTagger_NuMuCC"

# 2. Flip to NuECC, run
flip_sample "NuMuCC_Sample" "NuECC_Sample"
run_nb "SignalBackground_Distributions_BeforeCosmicTagger" "2_BeforeCosmicTagger_NuECC"
# Flip back to the resting default
flip_sample "NuECC_Sample" "NuMuCC_Sample"

# 3. OffBeam Data
run_nb "SignalBackground_Distributions_BeforeCosmicTagger_Data_OffBeam" "3_BeforeCosmicTagger_Data_OffBeam"

# 4. OnBeam Data
run_nb "SignalBackground_Distributions_BeforeCosmicTagger_Data_OnBeam" "4_BeforeCosmicTagger_Data_OnBeam"

{ echo; echo "CHAIN COMPLETE $(date)"; } >> "$STATUS"
