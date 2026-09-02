# SBND Wirecell Cluster Evaluation

This repository contains notebooks for evaluating the clustering performance of the Wirecell reconstruction algorithm on SBND detector data.

Every analysis is driven from a notebook. The `.py` files at the top level are supporting modules that the notebooks import (reading, selections, efficiency/purity estimation, drawing, metadata); they are not meant to be run on their own and are not documented here.

---

## Charge-Light Matching Notebooks (current pipeline)

These read the combined-APA charge-light-matching JSON format: `img-global` (reco clusters), `sed-sce_drift_smear_readout` / `sed-smear_readout` (true clusters), `mc` (particle truth tree), `op` (optical/light info). Reco is already global across APAs, so there is no per-APA/face looping.

### Evaluation_ChargeLightMatching_BeforeBeamWindowCut.ipynb
**Description:** Full reconstruction-performance evaluation over many files and events, with **no beam-window cut applied** — the true side therefore still contains cosmic clusters alongside the neutrino ones. Runs the whole chain: selections, cluster categorisation, KDTree efficiency and purity, 1-to-1 and 1-to-many true-reco matching, metadata, and all plotting.

**How to run:**
1. Open the notebook: `jupyter notebook Evaluation_ChargeLightMatching_BeforeBeamWindowCut.ipynb`
2. Set `PARENT_DIR` to the input tree, and `files` / `events` to `"all"` or a count to limit the run
3. Adjust the selection parameters (energy cut, fiducial ranges, matching radii, minimum point counts)
4. Run all cells

**Note on the input tree:** point `PARENT_DIR` at the `*_after_deadareacut/` tree, which has the dead-area cut already applied to the true points, and leave the notebook's own dead-area cut off. Pointing it at the raw tree instead requires turning that cut back on. The two trees are deliberately named differently so they cannot be confused.

**Output:** Efficiency and purity heatmaps, efficiency-vs-true-energy and purity-vs-reco-charge plots at event / file / job level, efficiency-vs-purity scatter and 2D histograms for matched pairs, per-cluster metadata, and text summaries — written under `multi_file_plots_charge_light_matching/`.

---

### Evaluation_ChargeLightMatching_AfterBeamWindowCut.ipynb
**Description:** The same evaluation with the **beam-window cut applied to the reco side**: only clustering-global clusters whose bridged flash time falls inside [0.33, 1.93] μs survive into efficiency, purity, matching, metadata, and every plot. The in-spill population is neutrino-dominated, so this is the notebook for questions about how well neutrino interactions specifically are reconstructed.

The cut is reco-side only by design. "In beam window" is not a truth quantity — true clusters carry no flash and no time — so a true-side version could only be inferred by matching to a beam-window-flashed reco cluster, folding beam timing into what would read as a truth-level selection. The true side therefore still holds its cosmic clusters, and a cosmic true cluster that goes unmatched here means "no in-spill reco cluster near it".

**How to run:** Same as the before-cut notebook above. Set `Apply_beam_window_cut = False` in the configuration cell to reproduce the before-cut notebook exactly.

**Output:** Same plot and summary set as the before-cut notebook, written to `multi_file_plots_charge_light_matching/Evaluation_After_TimeWindowCut/` — a subdirectory of the shared charge-light tree, so the two notebooks never overwrite each other.

---

### SelectionAnalysis.ipynb
**Description:** The truth-and-selections counterpart to the evaluation notebooks: what the truth contains and what each cut keeps, deliberately kept separate from reconstruction performance. Reads the same files and events with the same parameters and the same cut functions — no cut is reimplemented — and counts how many clusters survive each successive selection.

**How to run:**
1. Open the notebook: `jupyter notebook SelectionAnalysis.ipynb`
2. Match `PARENT_DIR` and the selection parameters to the evaluation notebook you are comparing against
3. Run all cells

**Output:** Selection-flow bar blocks (one block per cut stage), split into cosmic clusters and neutrino interactions on the true side and a single total on the reco side, plus true-neutrino vertex records showing why interactions dropped out (no true deposits / below energy cut / geometric cuts).

---

## Earlier Multi-File Pipeline

### Evaluation_BeforeChargeLightMatching_BeforeBeamWindowCut.ipynb
**Description:** Multi-file clustering evaluation for the original per-APA JSON format (`tru-apa*` / `*-clustering-apa*`). Detects the number of events in each input directory automatically and aggregates efficiency and purity statistics across all of them.

**How to run:**
1. Open the notebook: `jupyter notebook Evaluation_BeforeChargeLightMatching_BeforeBeamWindowCut.ipynb`
2. Configure the file list, event ranges, and analysis parameters
3. Run all cells

**Output:** Efficiency-vs-purity scatter plots, 2D colz histograms, summary tables, and event-by-event analysis plots.

---

### Evaluation_BeforeChargeLightMatching_BeforeBeamWindowCut_FromROOT.ipynb
**Description:** Reproduces every plot and the `summary.txt` of `Evaluation_BeforeChargeLightMatching_BeforeBeamWindowCut.ipynb` from pre-computed cluster points and metadata stored in a ROOT file, without recomputing selections, KDTree matching, or category classification. Useful for re-plotting quickly once the expensive pass has been run.

**How to run:**
1. Generate the ROOT input first with the corresponding processing step
2. Open the notebook: `jupyter notebook Evaluation_BeforeChargeLightMatching_BeforeBeamWindowCut_FromROOT.ipynb`
3. Point it at the ROOT file and run all cells

**Output:** PNGs mirroring the original notebook's directory structure, plus native ROOT TH1D/TH2D histograms in a single output `.root` file.

---

## Selection and Cut Studies

### TrueClusterPointSelection.ipynb
**Description:** Tests and visualises true cluster point selection by applying minimum point-count cutoffs to filter out small/noise clusters.

**How to run:**
1. Open the notebook: `jupyter notebook TrueClusterPointSelection.ipynb`
2. Adjust `min_points_threshold` and `min_cluster_energy`
3. Run all cells to see before/after comparisons

**Output:** Bar charts comparing cluster counts before/after the cutoff, XZ-view visualisations of removed vs kept clusters, and cluster statistics.

---

### RecoClusterPointSelection.ipynb
**Description:** The same study on the reconstructed side — applies minimum point-count cutoffs to reco clusters.

**How to run:**
1. Open the notebook: `jupyter notebook RecoClusterPointSelection.ipynb`
2. Adjust `min_reco_points_threshold`
3. Run all cells

**Output:** Bar charts, XZ-view visualisations with removed clusters highlighted, and statistics on cluster reduction.

---

### WirecellEnergyCuts.ipynb
**Description:** Scans a set of true-cluster energy cuts (e.g. 5, 10, 50 MeV) for a chosen event range and APA, reading the exported xyz-coordinate text files, to see how the cluster population responds to the energy threshold.

**How to run:**
1. Open the notebook: `jupyter notebook WirecellEnergyCuts.ipynb`
2. Set the event range, sbndcode version, process (`nu_spill` / `cosmic_spill`), APA, and the `energy_cuts` list
3. Run all cells

**Output:** Cluster counts and distributions for each energy cut, with an example event drawn for reference.

---

### CompareTimeWindowCorrection.ipynb
**Description:** Compares true cluster coordinates before and after the time-window correction (old window -200 to 1600 μs vs new window -205 to 1508.5 μs) and the effect on reconstruction quality.

**How to run:**
1. Open the notebook: `jupyter notebook CompareTimeWindowCorrection.ipynb`
2. Configure the event range and time-window parameters
3. Run all cells

**Output:** Comparison plots showing coordinate shifts and efficiency/purity variations between the two time windows.

---

## Detector Geometry Notebooks

### ReadDrawWirecellBoundary.ipynb
**Description:** Reads the SBND wire-cell geometry file and extracts the detector boundaries for both APAs separately, to show the active detector volume.

**How to run:**
1. Open the notebook: `jupyter notebook ReadDrawWirecellBoundary.ipynb`
2. Set the event number and APA selection
3. Run all cells

**Output:** Visualisation of the TPC boundaries and detector geometry — the reference for interpreting fiducial cuts.

---

### deadarea.ipynb
**Description:** Reads and visualises the dead/inactive detector areas from the dead-area JSON files, showing which regions cannot record data.

**How to run:**
1. Open the notebook: `jupyter notebook deadarea.ipynb`
2. Specify the event number and APA (`apa0` or `apa1`)
3. Run all cells

**Output:** Dead areas overlaid on the detector geometry in Y-Z projection.

---

## Dependencies

All notebooks require:
- numpy
- matplotlib
- pandas
- seaborn
- scipy (for KDTree spatial queries)
- uproot (for reading/writing ROOT files)

Install with: `pip install numpy matplotlib pandas seaborn scipy uproot`

---

## Quick Start Workflow

1. **What the cuts keep:** run `SelectionAnalysis.ipynb` to see the selection flow before trusting any performance number
2. **Full evaluation:** run `Evaluation_ChargeLightMatching_BeforeBeamWindowCut.ipynb` over all files and events
3. **Neutrinos only:** run `Evaluation_ChargeLightMatching_AfterBeamWindowCut.ipynb` for the in-beam-window population
4. **Parameter tuning:** use `TrueClusterPointSelection.ipynb` and `RecoClusterPointSelection.ipynb` to understand threshold effects
5. **Geometry reference:** consult `ReadDrawWirecellBoundary.ipynb` and `deadarea.ipynb` when interpreting fiducial and dead-area effects

---

## Author
Prabhjot Singh (prabhjot@fnal.gov)

## Date
2025-2026
