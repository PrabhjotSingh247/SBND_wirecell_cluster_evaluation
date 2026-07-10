# WireCell Clustering Evaluation - Project Documentation

## Project Overview
A comprehensive evaluation system for comparing true (simulated) vs reconstructed (reco) neutrino clusters from the SBND (Short-Baseline Near Detector) experiment. The system measures reconstruction efficiency and purity, categorizes clusters, and produces visualizations.

**Key Physics Context:**
- Neutrino clusters are marked with `q_true=1` and assigned cluster ID **9999**
- Cosmic clusters are marked with `q_true=0` and classified by angle (isochronous, normal, prolonged)
- Evaluation focuses on both individual events and aggregate statistics

---

## Data Structure

### True Cluster Points (7 columns)
```
[x, y, z, cluster_id, q_true, energy, time]
- x, y, z: 3D spatial coordinates (cm)
- cluster_id: Unique ID (9999 for neutrino clusters after reassignment)
- q_true: Charge flag (1=neutrino, 0=cosmic)
- energy: Energy in MeV
- time: Time in nanoseconds (ns)
```

### Reco Cluster Points (5 columns)
```
[x, y, z, cluster_id, charge]
- x, y, z: 3D reconstructed coordinates (cm)
- cluster_id: Unique ID after reassignment
- charge: Reconstructed charge (ADC arbitrary units)
```

---

## Core Modules & Workflows

### 1. **readfiles.py** - Data Loading
Reads true and reco cluster data from JSON files:
- `read_true_coordinates_from_json()`: Loads true clusters from `tru-apa*.json`
- `read_pred_coordinates_from_json()`: Loads reco clusters from `*-clustering-apa*-*.json`
- `read_files_for_event()`: Orchestrates loading and merges multi-face data

**Input files expected:**
- `data/evt/tru-{apa_lower}-{evt}.json` (true coordinates)
- `data/evt/{evt}-clustering-{apa_lower}-*.json` (reco clusters, may have multiple faces)

---

### 2. **selections.py** - Data Filtering & Cluster ID Assignment

#### Key Functions:

**`reassign_cluster_ID_true(points_5d)`** ⭐ CRITICAL
- Reassigns neutrino clusters to ID **9999** when `points[:, 4].any() == 1` (charge flag)
- Uses `avg_xy = round(np.mean(points[:, 0]), 2)` for non-neutrino clusters
- All other true clusters get ID based on rounded average X coordinate
- **This is where neutrino cluster ID 9999 is assigned**

**`reassign_cluster_ID_reco(points_5d_reco)`**
- Reassigns reco cluster IDs based on rounded average X coordinate
- Uses average X for spatial grouping

**Other Filters:**
- `apply_energy_cutoff()`: Remove clusters below energy threshold
- `apply_min_true_points_cutoff()`: Remove clusters with too few points
- `apply_min_reco_points_cutoff()`: Remove reco clusters with too few points
- `apply_wire_readout_sensitive_yz_plane_cut_true()`: Fiducial volume cut
- `apply_wire_readout_sensitive_yz_plane_cut_reco()`: Fiducial volume cut
- `apply_time_window_cut()`: Time-based filtering with visualization
- `apply_deadarea_cut_true()`: Remove points in dead detector regions

---

### 3. **cluster_category.py** - Cosmic/Neutrino Classification

**`cluster_category(clusters_true, ...)`** Function
Classifies clusters into categories:

**Neutrino Clusters (q_true=1):**
- Always labeled as `track_type="normal"`
- Identified by `is_neutrino=True` flag

**Cosmic Clusters (q_true=0):**
Classified by angle theta_xz in XZ plane:
- **Isochronous**: theta_xz < 20° (shallow angle, mostly vertical in XZ)
- **Normal**: 20° ≤ theta_xz ≤ 70°
- **Prolonged**: theta_xz > 70° (steep angle, mostly horizontal in XZ)

**How it works:**
1. Finds z_min: first Z where ≥10 points in radius
2. Finds z_max: last Z where ≥10 points in radius
3. Calculates theta_xz = arctan(dx/dz) where dx = x_max - x_min
4. Classifies based on angle thresholds

---

### 4. **efficiency_purity_estimate.py** - Core Metrics

**`EvaluateEfficiency(clusters_true, clusters_reco, ...)`**
- Uses KDTree spatial matching (radius_efficiency=1 cm)
- Calculates energy-weighted efficiency for each true-reco pair
- Marks unmatched true clusters with reco_cluster_id = **8888** (sentinel)
- Returns list of efficiency dictionaries

**`EvaluatePurity(clusters_true, clusters_reco, ...)`**
- Uses KDTree projection matching (XZ radius=1 cm, YZ radius=2 cm)
- Calculates fraction of reco points matching true clusters
- Marks unmatched reco clusters with true_cluster_id = **8888** and purity=-0.1
- Returns list of purity dictionaries

**⚠️ IMPORTANT: Sentinel Value**
- Changed from 9999 → 8888 to avoid conflict with neutrino cluster ID 9999
- All unmatched clusters now use 8888 as placeholder
- Your neutrino cluster 9999 is now fully preserved in all evaluations

---

### 5. **efficiency_purity_draw.py** - Visualizations

Major visualization functions (87KB file):

**Heatmaps:**
- `plot_efficiency_heatmap()`: Energy-weighted efficiency matrix
- `plot_purity_heatmap()`: Purity matrix

**2D Efficiency Plots:**
- `DrawEfficiencyVsTrueEnergyPerEvent()`: Event-level efficiency vs true energy
- `DrawEfficiencyVsTrueEnergyPerFile()`: File-level aggregation
- `DrawEfficiencyVsTrueEnergyPerJob()`: Job-level aggregation (all files)
- `DrawEfficiencySummaryAllFilesAllEvents()`: Global summary

**2D Purity Plots:**
- `DrawPurityVsRecoChargePerEvent()`: Event-level purity vs reco charge
- `DrawPurityVsRecoChargeAllEvents()`: Aggregated purity

**Paired Analysis:**
- `DrawEfficiencyVsPurity_MatchedPairs()`: Scatter plot of matched pairs
- `DrawEfficiencyVsPurity_MatchedPairsColz()`: 2D histogram of efficiency vs purity

**1D Projections:**
- `plot_1d_efficiency_energy()`: Binned energy projections with mean efficiency

---

### 6. **clusterpairmatching.py** - Cluster Matching

**`MatchRecoTruePair1to1(all_purity_results, all_eff_results)`**
- One-to-one matching: Each true cluster → best purity reco cluster
- Each reco cluster → best purity true cluster
- Returns matched pairs meeting criteria

**`MatchTruetoReco_OneToMany(all_purity_results, all_eff_results)`**
- One-to-many matching: Each true cluster → all matched reco clusters
- Useful for understanding fragmented reconstruction

---

### 7. **metadata.py** - Cluster Metadata

**`add_metadata_true_clusters(efficiency_results, cluster_category_results, ...)`**
- Creates metadata entries for each true cluster
- Includes: file_name, event, apa, view, cluster_id, type, category, efficiency, reco_matches
- Used for tracking and analysis across events

**`aggregate_metadata(metadata_list)`**
- Aggregates statistics: total clusters, by type, by category
- Calculates mean/median/min/max for efficiency and reco matches

---

### 8. **DrawRecoTrueClusters.py** - Spatial Visualizations

Large visualization module (34KB):
- Draws true clusters with 3D and 2D projections
- Shows dead areas and their effects
- Categories overlays (neutrino vs cosmic, isochronous vs normal vs prolonged)

---

## Data Flow Diagram

```
Input JSON Files (true & reco)
         ↓
    readfiles.py (loads data)
         ↓
    selections.py (filters & reassigns IDs, assigns 9999 to neutrino)
         ↓
    cluster_category.py (classifies cosmic/neutrino)
         ↓
    efficiency_purity_estimate.py (KDTree matching, calculates metrics)
         ↓
    clusterpairmatching.py (matches true-reco pairs)
         ↓
    ├─ efficiency_purity_draw.py (visualizations)
    ├─ metadata.py (metadata tracking)
    └─ efficiency_purity_print.py (text output)
         ↓
    Output: Plots, Tables, Analysis Results
```

---

## Key Variables & Conventions

| Variable | Meaning | Values |
|----------|---------|--------|
| `q_true` | Charge flag | 1=neutrino, 0=cosmic |
| `cluster_id` | After reassignment | 9999=neutrino, others from avg X |
| `theta_xz` | Angle in XZ plane | Degrees; classifies cosmic tracks |
| `track_type` | Cosmic classification | "isochronous", "normal", "prolonged" |
| `is_neutrino` | Boolean flag | True/False |
| Sentinel ID (unmatched) | For unmatched clusters | **8888** (was 9999, changed to avoid conflict) |

---

## Important Notes

### ⚠️ Neutrino Cluster ID Assignment
- **Location**: `selections.py:73` in `reassign_cluster_ID_true()`
- **Condition**: `if points[:, 4].any() == 1:` (charge flag)
- **Value**: All neutrino points get `cluster_id = 9999`
- **Why**: Unified ID for all neutrino interaction products in an event

### ⚠️ Sentinel Value Change (2026-07-09)
- **Before**: Unmatched clusters marked as 9999 (conflicted with neutrino ID)
- **After**: Unmatched clusters marked as 8888
- **Files Updated**: efficiency_purity_estimate.py, efficiency_purity_draw.py
- **Impact**: Neutrino cluster 9999 now fully preserved in all evaluations and plots

### ⚠️ Coordinate System
- X is drift direction (-202.05 to +202.05 cm depending on APA)
- Y is vertical direction
- Z is beam direction
- APA0 and APA1 have opposite X collection planes

### ⚠️ Time Window & Dead Area Cuts
- Applied before cluster category classification
- May remove entire clusters or individual points
- Visualizations show before/after statistics

---

## Testing & Validation

When modifying code:
1. **Test with single event first** - faster iteration
2. **Check sentinel value 8888** - should never appear in real cluster IDs
3. **Verify neutrino cluster 9999** - must appear in metadata and plots
4. **Check aggregate statistics** - ensure totals across files match
5. **Review visualizations** - plots should show expected distributions

---

## Common Tasks

### Add a new filter:
1. Create function in `selections.py` following existing patterns
2. Apply in main notebook after loading data
3. Update documentation in this file

### Modify cluster classification:
1. Edit thresholds in `cluster_category.py` (lines 136-141 for angle thresholds)
2. Update metadata handling if new categories added
3. Ensure visualizations handle new categories

### Change evaluation metrics:
1. Modify KDTree radii in `efficiency_purity_estimate.py` (lines 9, 65)
2. Update filter logic if needed
3. Regenerate all plots to verify impact

### Debug unmatched clusters:
1. Check sentinel value (8888) in efficiency/purity results
2. Search in `efficiency_purity_draw.py` for filters on sentinel
3. Look for min_reco_points_threshold logic in estimation

---

## File Status (as of 2026-07-09)
- ✅ efficiency_purity_estimate.py - Updated (sentinel 8888)
- ✅ efficiency_purity_draw.py - Updated (sentinel 8888)
- ⚠️ selections.py - Contains neutrino ID 9999 assignment (keep as-is)
- Other files stable

## Contact / Questions
For clarification on neutrino cluster handling, see selections.py:58-78
For visualization details, see efficiency_purity_draw.py header comments
