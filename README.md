# SBND Wirecell Cluster Evaluation

This repository contains scripts and notebooks for evaluating the clustering performance of the Wirecell reconstruction algorithm on SBND detector data.

---

## Scripts Description and Usage


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

### HighStatsEvaluation_MultiFile.ipynb
**Description:** Comprehensive clustering evaluation framework that processes multiple data files simultaneously, calculating efficiency and purity statistics across events, and generating detailed 2D histograms alongside scatter plots for performance analysis.

**How to run:**
1. Open the notebook in Jupyter: `jupyter notebook HighStatsEvaluation_MultiFile.ipynb`
2. Configure the file list, event ranges, and analysis parameters
3. Run all cells to process all events and generate aggregate statistics

**Features:**
- Processes multiple data files in batch
- Applies fiducial volume cuts for neutrino and cosmic event filtering
- Generates 2D colz histograms (efficiency vs purity distributions)
- Produces scatter plots showing individual cluster pair performance

**Output:** Efficiency vs purity scatter plots, 2D histograms, summary tables with performance statistics, and event-by-event analysis plots.

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


### ReadDrawWirecellBoundary.ipynb
**Description:** Reads and visualizes the Wirecell detector boundary geometry to understand the active detector volume and physical constraints of the SBND TPC.

**How to run:**
1. Open the notebook in Jupyter: `jupyter notebook ReadDrawWirecellBoundary.ipynb`
2. Set the event number and APA selection
3. Run all cells to display boundary visualizations

**Output:** Visualization of the TPC boundaries and detector geometry showing the physical limits of the active volume for reference when analyzing fiducial cuts.

---

### deadarea.ipynb
**Description:** Reads and visualizes dead/inactive detector areas from JSON files to understand which regions cannot record data.

**How to run:**
1. Open the notebook in Jupyter: `jupyter notebook deadarea.ipynb`
2. Specify the event number and APA (apa0 or apa1)
3. Run all cells to display dead area maps

**Output:** Visualization of dead areas overlaid on the detector geometry showing inactive channel regions in Y-Z projection.

---

### CompareTimeWindowCorrection.ipynb
**Description:** Analyzes the effects of time window corrections on cluster reconstruction quality and efficiency/purity metrics.

**How to run:**
1. Open the notebook in Jupyter: `jupyter notebook CompareTimeWindowCorrection.ipynb`
2. Configure the event range and time window parameters
3. Run all cells to compare performance metrics before and after corrections

**Output:** Comparison plots showing efficiency and purity variations with different time window settings.

---

## Analysis and Utility Scripts

### efficiency_purity_draw.py
**Description:** Generates visualization plots for efficiency and purity analysis results. Creates heatmaps, scatter plots, and statistical distributions.

**Usage:**
```python
python efficiency_purity_draw.py [options]
```

---

### efficiency_purity_estimate.py
**Description:** Calculates efficiency and purity metrics for cluster matching between true and reconstructed clusters.

**Usage:**
```python
python efficiency_purity_estimate.py [true_clusters] [reco_clusters]
```

---

### efficiency_purity_print.py
**Description:** Prints formatted efficiency and purity statistics and summary tables.

**Usage:**
```python
python efficiency_purity_print.py [results_file]
```

---

### generate_summary_tables.py
**Description:** Generates comprehensive summary tables from analysis results for reporting and documentation.

**Usage:**
```python
python generate_summary_tables.py [input_data] [output_file]
```

---

### DrawRecoTrueClusters.py
**Description:** Visualizes true and reconstructed clusters side-by-side for visual comparison and validation.

**Usage:**
```python
python DrawRecoTrueClusters.py [event_number] [options]
```

---

### readfiles.py
**Description:** Utility module for reading and parsing data files containing cluster information and event data.

---

### selections.py
**Description:** Defines cluster selection criteria and filtering functions for analysis workflows.

---

### clusterpairmatching.py
**Description:** Implements algorithms for matching true clusters to reconstructed clusters based on spatial overlap and hit matching.

---

### bee_display_link.py
**Description:** Generates BEE (Browser Event Display) visualization links for interactive event inspection.

**Usage:**
```python
python bee_display_link.py [event_id]
```

---

### printbeelink.py
**Description:** Prints formatted BEE event display links for easy access to visualization tools.

**Usage:**
```python
python printbeelink.py [event_list]
```

---

### run_bee_uploader.py
**Description:** Automates the upload and registration of events to the BEE visualization system.

**Usage:**
```python
python run_bee_uploader.py [event_range]
```

---

### analyticresults.py
**Description:** Processes and analyzes results from clustering evaluation studies.

---

### draw_analysis.py
**Description:** Generates analysis-specific visualization plots and figures.

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

1. **Single event analysis:** Use `single_cluster_eval.ipynb` to test a specific event
2. **High statistics (multi-file):** Run `HighStatsEvaluation_MultiFile.ipynb` to process all events and get overall performance metrics
3. **Parameter optimization:** Use `single_cluster_eval_optimization.ipynb` to find best threshold values
4. **Diagnostics:** Run `TrueClusterPointSelection.ipynb` and `RecoClusterPointSelection.ipynb` to understand cutoff effects
5. **Event visualization:** Use `DrawRecoTrueClusters.py` for side-by-side cluster comparison
6. **BEE display:** Use `bee_display_link.py` and `run_bee_uploader.py` for interactive event inspection

---

## Author
Prabhjot Singh (prabhjot@fnal.gov)

## Date
2025-2026
