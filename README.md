# SBND Wirecell Cluster Evaluation

This repository contains scripts and notebooks for evaluating the clustering performance of the Wirecell reconstruction algorithm on SBND detector data.

---

## Scripts Description and Usage

### jsontotext.sh
**Description:** Converts JSON files from image clustering jobs into separate text files containing xyz coordinates, cluster IDs, charge, and energy information.

**How to run:**
```bash
./jsontotext.sh apa0
./jsontotext.sh apa1
```
**Notes:** Extracts truth deposition and clustering information for all events (17 by default) and saves them as text files in the output directory structure.

---

### single_cluster_eval.ipynb
**Description:** Evaluates clustering performance metrics (efficiency and purity) for a single event by matching true and reconstructed clusters.

**How to run:**
1. Open the notebook in Jupyter: `jupyter notebook single_cluster_eval.ipynb`
2. Configure parameters in the notebook (event number, APA, radius thresholds, etc.)
3. Run all cells to generate efficiency/purity heatmaps and comparison plots

**Output:** Generates heatmaps showing efficiency and purity for true-reco cluster pairs, energy-weighted efficiency plots, and side-by-side cluster visualizations.

---

### single_cluster_eval_optimization.ipynb
**Description:** Optimizes single cluster evaluation parameters by testing different threshold values and radius settings to maximize reconstruction quality.

**How to run:**
1. Open the notebook in Jupyter: `jupyter notebook single_cluster_eval_optimization.ipynb`
2. Set the event range and parameter ranges to test
3. Run all cells to compare performance across different configurations

**Output:** Summary tables and plots showing how efficiency and purity vary with different parameter choices.

---

### HighStatsEvaluation.ipynb
**Description:** Performs comprehensive clustering evaluation across multiple events, calculating efficiency and purity statistics, and generating summary reports.

**How to run:**
1. Open the notebook in Jupyter: `jupyter notebook HighStatsEvaluation.ipynb`
2. Configure the event range (event_low and event_high) and analysis parameters
3. Run all cells to process all events and generate aggregate statistics

**Output:** Generates efficiency vs purity scatter plots, summary tables with performance statistics (% of clusters above threshold), and event-by-event analysis plots.

---

### TrueClusterPointSelection.ipynb
**Description:** Tests and visualizes true cluster point selection by applying minimum point count cutoffs to filter out small/noise clusters.

**How to run:**
1. Open the notebook in Jupyter: `jupyter notebook TrueClusterPointSelection.ipynb`
2. Adjust the min_points_threshold and min_cluster_energy parameters
3. Run all cells to see before/after comparisons of cluster populations

**Output:** Bar charts comparing cluster counts before/after cutoff, visualizations of removed vs kept clusters in XZ view, and detailed cluster statistics.

---

### RecoClusterPointSelection.ipynb
**Description:** Tests and visualizes reconstructed cluster point selection by applying minimum point count cutoffs to the reco clusters.

**How to run:**
1. Open the notebook in Jupyter: `jupyter notebook RecoClusterPointSelection.ipynb`
2. Adjust the min_reco_points_threshold parameter
3. Run all cells to analyze the effect of point cutoffs on reco clusters

**Output:** Bar charts, XZ view visualizations with removed clusters highlighted, and statistics on cluster reduction.

---

### WirecellFiducialVolume.ipynb
**Description:** Defines and analyzes the Wirecell fiducial volume boundaries by examining coordinate distributions of all true and reco points across events.

**How to run:**
1. Open the notebook in Jupyter: `jupyter notebook WirecellFiducialVolume.ipynb`
2. Set the event range (first_event and last_event)
3. Run all cells to generate coordinate distribution histograms for x, y, and z axes

**Output:** Histograms showing true vs reco point distributions for each coordinate axis, establishing the active detector volume boundaries.

---

### deadarea.ipynb
**Description:** Reads and visualizes dead/inactive detector areas from JSON files to understand which regions cannot record data.

**How to run:**
1. Open the notebook in Jupyter: `jupyter notebook deadarea.ipynb`
2. Specify the event number and APA (apa0 or apa1)
3. Run all cells to display dead area maps

**Output:** Visualization of dead areas overlaid on the detector geometry showing inactive channel regions in Y-Z projection.

---

## Directory Structure

```
cluster_evaluation/
├── README.md                                    # This file
├── jsontotext.sh                               # JSON to text conversion script
├── *.ipynb                                     # Jupyter notebooks for analysis
├── 24308437_0/                                 # Raw input data directory
│   └── mabc-apa*.zip                           # Compressed clustering data
├── out/                                        # Output directory
│   └── 24308437_0/
│       └── v10_06_00/
│           └── nu_spill/
│               ├── xyz-coordinates/            # Text files with xyz data
│               └── plots/                      # Generated plots and analysis results
└── deadarea.root                               # Root file with dead area data
```

---

## Dependencies

All notebooks require the following Python packages:
- numpy
- matplotlib
- pandas
- seaborn
- scipy (for KDTree spatial queries)
- pathlib (standard library)

Install with: `pip install numpy matplotlib pandas seaborn scipy`

---

## Quick Start Workflow

1. **Extract data:** Run `./jsontotext.sh apa0 && ./jsontotext.sh apa1` to convert JSON to text format
2. **Single event analysis:** Use `single_cluster_eval.ipynb` to test a specific event
3. **High statistics:** Run `HighStatsEvaluation.ipynb` to process all events and get overall performance metrics
4. **Parameter optimization:** Use `*_optimization.ipynb` notebooks to find best threshold values
5. **Diagnostics:** Run `TrueClusterPointSelection.ipynb` and `RecoClusterPointSelection.ipynb` to understand cutoff effects

---

## Author
Prabhjot Singh (prabhjot@fnal.gov)

## Date
2025-2026
