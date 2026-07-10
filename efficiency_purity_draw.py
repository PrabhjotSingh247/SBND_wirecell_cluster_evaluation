import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

def plot_efficiency_heatmap(efficiency_results, event, apa, output_dir, file_name=None):
    """Plot energy-weighted efficiency values as a heatmap for visual inspection of cluster matching."""
    df = pd.DataFrame(efficiency_results)
    efficiency_matrix = df.pivot_table(
        index='true_cluster_id',
        columns='reco_cluster_id',
        values='efficiency_energy_weighted',
        fill_value=0
    )

    # avoid to draw reco cluster if it's id is 8888 (sentinel for unmatched)
    efficiency_matrix = efficiency_matrix.loc[:, efficiency_matrix.columns != 8888]

    plt.figure(figsize=(10, 8))
    sns.heatmap(efficiency_matrix, annot=True, fmt=".2f", cmap="YlGnBu",
                xticklabels=[f"{int(x):d}" for x in efficiency_matrix.columns],
                yticklabels=[f"{int(y):d}" for y in efficiency_matrix.index])
    title = f"Energy-Weighted Efficiency: Event {event}, {apa}"
    if file_name:
        title += f" ({file_name})"
    plt.title(title)
    plt.xlabel("Reco Cluster ID")
    plt.ylabel("True Cluster ID")
    plt.savefig(output_dir / f"efficiency_energy_weighted_evt_{event}_{apa}.png")
    plt.close()
    ##plt.show(block=False)

def plot_purity_heatmap(purity_results, event, apa, output_dir, file_name=None):
    """Plot purity values as a heatmap for visual inspection of cluster matching."""
    df = pd.DataFrame(purity_results)
    purity_matrix = df.pivot_table(
        index='true_cluster_id',
        columns='reco_cluster_id',
        values='purity',
        fill_value=0
    )

    # avoid to draw reco cluster if it's id is 8888 (sentinel for unmatched)
    purity_matrix = purity_matrix.loc[:, purity_matrix.columns != 8888]

    plt.figure(figsize=(10, 8))
    sns.heatmap(purity_matrix, annot=True, fmt=".2f", cmap="YlGnBu",
                xticklabels=[f"{int(x):d}" for x in purity_matrix.columns],
                yticklabels=[f"{int(y):d}" for y in purity_matrix.index])
    title = f"Purity: Event {event}, {apa}"
    if file_name:
        title += f" ({file_name})"
    plt.title(title)
    plt.xlabel("Reco Cluster ID")
    plt.ylabel("True Cluster ID")
    plt.savefig(output_dir / f"purity_evt_{event}_{apa}.png")
    plt.close()
    ##plt.show(block=False)

def plot_2d_efficiency_energy(energies, efficiencies, output_dir, event, apa, category_name="All Clusters", file_name=None, num_events=None):
    """
    Draw 2D histogram of Efficiency vs True Energy for a cluster category.
    Returns the energies and efficiencies lists for use in 1D projections.

    Args:
        energies: List of energy values
        efficiencies: List of efficiency values
        output_dir: Output directory for saving plots
        event: Event number (for single event) or 0 (for aggregated data)
        apa: APA number
        category_name: Name of cluster category for title
        file_name: Optional file name for title
        num_events: Optional number of events aggregated (if provided, shows event count instead of event number)
    """
    if not energies or not efficiencies:
        return energies, efficiencies

    plt.figure(figsize=(10, 8))
    x_bin_size = 50  # MeV
    xbins = np.arange(0, max(energies) + x_bin_size, x_bin_size)
    y_bin_size = 0.05
    ybins = np.arange(0, 1 + y_bin_size, y_bin_size)

    plt.hist2d(energies, efficiencies, bins=[xbins, ybins], cmap='YlGnBu')
    plt.colorbar(label='Count')
    plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
    plt.ylabel('Efficiency', fontsize=12, fontweight='bold')

    # Create title based on whether this is a single event or aggregated data
    if num_events is not None:
        title = f'Efficiency vs True Energy (2D) - {category_name} - {num_events} events, {apa}'
    else:
        title = f'Efficiency vs True Energy (2D) - {category_name} - Event {event}, {apa}'
    if file_name:
        title += f' ({file_name})'
    plt.title(title, fontsize=12, fontweight='bold')
    plt.xlim(0, max(energies)*1.1)
    plt.ylim(-0.05, 1.05)

    # Save with appropriate filename based on category
    category_suffix = category_name.lower().replace(' ', '_').replace('_clusters', '')
    if num_events is not None:
        filename = f"efficiency_vs_true_energy_2d_{category_suffix}_{num_events}events_{apa}.png"
    else:
        filename = f"efficiency_vs_true_energy_2d_{category_suffix}_event_{event}_{apa}.png"
    plt.savefig(output_dir / filename, dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()

    return energies, efficiencies

def plot_1d_efficiency_energy(energies, efficiencies, energy_bins):
    """
    Create 1D projection by binning energy and averaging efficiency values.
    Returns bin centers and mean efficiencies for plotting.
    """
    if not energies or not efficiencies:
        return [], []

    bin_centers = (energy_bins[:-1] + energy_bins[1:]) / 2
    bin_centers_nonzero = []
    mean_efficiency_per_bin = []

    for i in range(len(energy_bins)-1):
        mask = (np.array(energies) >= energy_bins[i]) & (np.array(energies) < energy_bins[i+1])
        if np.sum(mask) > 0:
            mean_eff = np.mean(np.array(efficiencies)[mask])
            mean_efficiency_per_bin.append(mean_eff)
            bin_centers_nonzero.append(bin_centers[i])

    return bin_centers_nonzero, mean_efficiency_per_bin

def DrawEfficiencyVsTrueEnergyPerEvent(efficiency_results, output_dir, event, apa, file_name=None, cluster_category_results=None):
    """
    For each true cluster: calculate sum of efficiency values,
    then plot efficiency vs true cluster energy (2D and 1D).
    If cluster_category_results is provided, also plot separate lines for isochronous, normal, and prolonged clusters.
    """
    if not efficiency_results:
        return

    # Group efficiency by true cluster and calculate sum
    true_cluster_efficiency = {}
    for eff in efficiency_results:
        true_cid = eff['true_cluster_id']
        #if true_cid == 8888:  # Skip unmatched sentinel
        #    continue
        if true_cid not in true_cluster_efficiency:
            true_cluster_efficiency[true_cid] = {
                'total_efficiency': 0,
                'total_energy': eff.get('total_true_cluster_energy', 0),
                'num_reco_matches': 0
            }

        true_cluster_efficiency[true_cid]['total_efficiency'] += eff['efficiency_energy_weighted']
        true_cluster_efficiency[true_cid]['num_reco_matches'] += 1

    if not true_cluster_efficiency:
        return

    # Debug: Print information about true clusters and their matched reco clusters
    print_debug_info = False  # Set to False to disable debug printing
    if print_debug_info:
        print("\n" + "="*80)
        print(f"DEBUG: Efficiency vs True Energy - Event {event}, {apa}")
        print("="*80)
        for true_cid in sorted(true_cluster_efficiency.keys()):
            data = true_cluster_efficiency[true_cid]
        print(f"\nTrue Cluster {true_cid:.0f}:")
        print(f"  Total Energy: {data['total_energy']:.3f} MeV")
        print(f"  Total Efficiency (sum): {data['total_efficiency']:.4f}")
        print(f"  Number of Matched Reco Clusters: {data['num_reco_matches']}")

        # Find and print individual efficiencies for each true-reco match
        #print(f"  Individual True-Reco Matches:")
        for eff in efficiency_results:
            if eff['true_cluster_id'] == true_cid and eff['true_cluster_id'] != 8888:
                reco_cid = eff.get('reco_cluster_id', 'N/A')
                eff_val = eff['efficiency_energy_weighted']
                #print(f"    → Reco Cluster {reco_cid:.0f}: efficiency = {eff_val:.4f}")
        print("="*80 + "\n")

    energies        = [data['total_energy']     for data in true_cluster_efficiency.values()]
    efficiencies    = [data['total_efficiency'] for data in true_cluster_efficiency.values()]

    # 2D Histogram for all clusters
    plot_2d_efficiency_energy(energies, efficiencies, output_dir, event, apa,
                             category_name="All Clusters", file_name=file_name)

    # 2D plots by category (only if cluster_category_results is provided)
    if cluster_category_results is not None:
        category_styles = {
            'neutrino': 'Neutrino Clusters',
            'isochronous_cosmic': 'Isochronous Cosmic Clusters',
            'normal_cosmic': 'Normal Cosmic Clusters',
            'prolonged_cosmic': 'Prolonged Cosmic Clusters'
        }

        for category_key, category_label in category_styles.items():
            # Filter clusters by category
            if category_key == 'neutrino':
                category_cluster_ids = [cid for cid, data in cluster_category_results.items() if data['is_neutrino']]
            elif category_key == 'isochronous_cosmic':
                category_cluster_ids = [cid for cid, data in cluster_category_results.items()
                                       if not data['is_neutrino'] and data['track_type'] == 'isochronous']
            elif category_key == 'normal_cosmic':
                category_cluster_ids = [cid for cid, data in cluster_category_results.items()
                                       if not data['is_neutrino'] and data['track_type'] == 'normal']
            elif category_key == 'prolonged_cosmic':
                category_cluster_ids = [cid for cid, data in cluster_category_results.items()
                                       if not data['is_neutrino'] and data['track_type'] == 'prolonged']

            if not category_cluster_ids:
                continue

            # Get energies and efficiencies for this category
            category_energies = [true_cluster_efficiency[cid]['total_energy'] for cid in category_cluster_ids if cid in true_cluster_efficiency]
            category_efficiencies = [true_cluster_efficiency[cid]['total_efficiency'] for cid in category_cluster_ids if cid in true_cluster_efficiency]

            # Draw 2D plot for this category
            if category_energies:
                plot_2d_efficiency_energy(category_energies, category_efficiencies, output_dir, event, apa,
                                         category_name=category_label, file_name=file_name)



    # Setup binning for 1D projections
    n_bins = 15
    if energies:
        energy_bins = np.linspace(0, max(energies)*1.1, n_bins+1)
    else:
        energy_bins = np.linspace(0, 10, n_bins+1)

    # 1D Plot 1: All clusters (separate canvas)
    bin_centers_all, mean_eff_all = plot_1d_efficiency_energy(energies, efficiencies, energy_bins)

    plt.figure(figsize=(12, 6))
    if len(bin_centers_all) > 0:
        plt.plot(bin_centers_all, mean_eff_all, 'o-', linewidth=2.5, markersize=10,
                color='darkblue', label='All Clusters', markeredgecolor='black', markeredgewidth=1)

    plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
    plt.ylabel('Efficiency', fontsize=12, fontweight='bold')
    title = f'Efficiency vs True Energy (1D Projection) - Event {event}, {apa}'
    if file_name:
        title += f' ({file_name})'
    plt.title(title, fontsize=12, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.xlim(0, 3000)  # Adjust x-axis limit based on expected energy range
    plt.ylim(-0.05, 1.05)
    plt.savefig(output_dir / f"efficiency_vs_true_energy_1d_event_{event}_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    ##plt.show(block=False)
    plt.close()

    # 1D Plot 2: By category (only if cluster_category_results is provided)
    if cluster_category_results is not None:
        plt.figure(figsize=(14, 7))

        # Define categories combining track_type and neutrino/cosmic
        category_info = {
            'neutrino': {'label': 'Neutrino Clusters', 'color': 'purple', 'marker': 'D'},
            'isochronous_cosmic': {'label': 'Isochronous Cosmic', 'color': 'red', 'marker': 'o'},
            'normal_cosmic': {'label': 'Normal Cosmic', 'color': 'green', 'marker': 's'},
            'prolonged_cosmic': {'label': 'Prolonged Cosmic', 'color': 'blue', 'marker': '^'}
        }

        for category_key, info in category_info.items():
            # Filter clusters by category
            if category_key == 'neutrino':
                category_cluster_ids = [cid for cid, data in cluster_category_results.items() if data['is_neutrino']]
            elif category_key == 'isochronous_cosmic':
                category_cluster_ids = [cid for cid, data in cluster_category_results.items()
                                       if not data['is_neutrino'] and data['track_type'] == 'isochronous']
            elif category_key == 'normal_cosmic':
                category_cluster_ids = [cid for cid, data in cluster_category_results.items()
                                       if not data['is_neutrino'] and data['track_type'] == 'normal']
            elif category_key == 'prolonged_cosmic':
                category_cluster_ids = [cid for cid, data in cluster_category_results.items()
                                       if not data['is_neutrino'] and data['track_type'] == 'prolonged']

            if not category_cluster_ids:
                continue

            # Get energies and efficiencies for this category
            category_energies = [true_cluster_efficiency[cid]['total_energy'] for cid in category_cluster_ids if cid in true_cluster_efficiency]
            category_efficiencies = [true_cluster_efficiency[cid]['total_efficiency'] for cid in category_cluster_ids if cid in true_cluster_efficiency]

            if category_energies:
                # Get 1D projection for this category
                bin_centers_cat, mean_eff_cat = plot_1d_efficiency_energy(category_energies, category_efficiencies, energy_bins)

                if len(bin_centers_cat) > 0:
                    color = info['color']
                    marker = info['marker']
                    label_text = f"{info['label']} ({len(category_cluster_ids)} clusters)"
                    plt.plot(bin_centers_cat, mean_eff_cat, marker=marker, linestyle='-', linewidth=2, markersize=8,
                            color=color, label=label_text, markeredgecolor='black', markeredgewidth=0.5)

        plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
        plt.ylabel('Efficiency', fontsize=12, fontweight='bold')
        title = f'Efficiency vs True Energy (1D by Category) - Event {event}, {apa}'
        if file_name:
            title += f' ({file_name})'
        plt.title(title, fontsize=12, fontweight='bold')
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.legend(fontsize=10)
        plt.xlim(0, 3000)
        plt.ylim(-0.05, 1.05)
        plt.savefig(output_dir / f"efficiency_vs_true_energy_1d_by_category_event_{event}_{apa}.png",
                    dpi=100, bbox_inches='tight', pad_inches=0.3)
        plt.close()


def DrawEfficiencyVsTrueEnergyPerFile(efficiency_results, output_dir, apa, file_name=None, cluster_category_results=None, file_metadata_list=None):
    """
    File-level version: For each true cluster calculate sum of efficiency values,
    then plot efficiency vs true cluster energy (2D and 1D) for all events in a file.
    If cluster_category_results or file_metadata_list is provided, also plot separate 2D and 1D plots for each cluster category.
    Note: Uses (event, true_cluster_id) composite key to ensure uniqueness across multiple events in a file.
    """
    if not efficiency_results:
        return

    # Count unique events in this file
    unique_events = set()
    if file_metadata_list is not None:
        unique_events = set(m['event'] for m in file_metadata_list)
    else:
        unique_events = set(eff.get('event', 'unknown') for eff in efficiency_results)
    num_events_in_file = len(unique_events)

    # Group efficiency by (event, true_cluster_id) to ensure uniqueness across multiple events
    true_cluster_efficiency = {}
    for eff in efficiency_results:
        event_key = eff.get('event', 'unknown')
        true_cid = eff['true_cluster_id']
        cluster_key = (event_key, true_cid)

        if cluster_key not in true_cluster_efficiency:
            true_cluster_efficiency[cluster_key] = {
                'total_efficiency': 0,
                'total_energy': eff.get('total_true_cluster_energy', 0),
                'num_reco_matches': 0
            }

        true_cluster_efficiency[cluster_key]['total_efficiency'] += eff['efficiency_energy_weighted']
        true_cluster_efficiency[cluster_key]['num_reco_matches'] += 1

    if not true_cluster_efficiency:
        return

    energies        = [data['total_energy']     for data in true_cluster_efficiency.values()]
    efficiencies    = [data['total_efficiency'] for data in true_cluster_efficiency.values()]

    # 2D Histogram for all clusters
    plot_2d_efficiency_energy(energies, efficiencies, output_dir, 0, apa,
                             category_name="All Clusters (File Level)", file_name=file_name, num_events=num_events_in_file)

    # Build category info from file_metadata_list if provided, otherwise use cluster_category_results
    category_info_source = None
    if file_metadata_list is not None:
        # Convert file_metadata_list to category dict format using (event, true_cluster_id) composite key
        category_info_source = {}
        for metadata in file_metadata_list:
            event_key = metadata['event']
            cid = metadata['true_cluster_id']
            cluster_key = (event_key, cid)
            if cluster_key not in category_info_source:
                category_info_source[cluster_key] = {
                    'is_neutrino': metadata['cluster_type'] == 'neutrino',
                    'track_type': metadata['cluster_category']
                }
        print(f"    [FILE LEVEL] Built category_info_source from metadata: {len(category_info_source)} clusters")
    elif cluster_category_results is not None:
        category_info_source = cluster_category_results
        print(f"    [FILE LEVEL] Using cluster_category_results: {len(category_info_source)} clusters")

    # 2D plots by category (only if category info is available)
    if category_info_source is not None:
        print(f"    [FILE LEVEL] Drawing 2D efficiency plots for categories...")
        category_styles = {
            'neutrino': 'Neutrino Clusters',
            'isochronous_cosmic': 'Isochronous Cosmic Clusters',
            'normal_cosmic': 'Normal Cosmic Clusters',
            'prolonged_cosmic': 'Prolonged Cosmic Clusters'
        }

        for category_key, category_label in category_styles.items():
            # Filter clusters by category (using composite keys if available)
            if category_key == 'neutrino':
                category_cluster_keys = [key for key, data in category_info_source.items() if data['is_neutrino']]
            elif category_key == 'isochronous_cosmic':
                category_cluster_keys = [key for key, data in category_info_source.items()
                                       if not data['is_neutrino'] and data['track_type'] == 'isochronous']
            elif category_key == 'normal_cosmic':
                category_cluster_keys = [key for key, data in category_info_source.items()
                                       if not data['is_neutrino'] and data['track_type'] == 'normal']
            elif category_key == 'prolonged_cosmic':
                category_cluster_keys = [key for key, data in category_info_source.items()
                                       if not data['is_neutrino'] and data['track_type'] == 'prolonged']

            print(f"      {category_label}: found {len(category_cluster_keys)} clusters in metadata")

            if not category_cluster_keys:
                print(f"        → No clusters in this category, skipping...")
                continue

            # Get energies and efficiencies for this category
            category_energies = [true_cluster_efficiency[key]['total_energy'] for key in category_cluster_keys if key in true_cluster_efficiency]
            category_efficiencies = [true_cluster_efficiency[key]['total_efficiency'] for key in category_cluster_keys if key in true_cluster_efficiency]

            print(f"        → Matched {len(category_energies)} clusters in efficiency_results")

            # Draw 2D plot for this category
            if category_energies:
                print(f"        → Drawing 2D plot for {category_label}...")
                plot_2d_efficiency_energy(category_energies, category_efficiencies, output_dir, 0, apa,
                                         category_name=category_label, file_name=file_name, num_events=num_events_in_file)
            else:
                print(f"        → No energies/efficiencies found, skipping plot...")

    # Setup binning for 1D projections
    n_bins = 15
    if energies:
        energy_bins = np.linspace(0, max(energies)*1.1, n_bins+1)
    else:
        energy_bins = np.linspace(0, 10, n_bins+1)

    # 1D Plot: All clusters (separate canvas)
    bin_centers_all, mean_eff_all = plot_1d_efficiency_energy(energies, efficiencies, energy_bins)

    plt.figure(figsize=(12, 6))
    if len(bin_centers_all) > 0:
        plt.plot(bin_centers_all, mean_eff_all, 'o-', linewidth=2.5, markersize=10,
                color='darkblue', label='All Clusters', markeredgecolor='black', markeredgewidth=1)

    plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
    plt.ylabel('Efficiency', fontsize=12, fontweight='bold')
    title = f'Efficiency vs True Energy (1D Projection) - File Level, {apa}'
    if file_name:
        title += f' ({file_name})'
    plt.title(title, fontsize=12, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.xlim(0, 3000)
    plt.ylim(-0.05, 1.05)
    plt.savefig(output_dir / f"efficiency_vs_true_energy_1d_file_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()

    # 1D Plot 2: By category (only if category info is available)
    if category_info_source is not None:
        plt.figure(figsize=(14, 7))

        # Define categories combining track_type and neutrino/cosmic
        category_info = {
            'neutrino': {'label': 'Neutrino Clusters', 'color': 'purple', 'marker': 'D'},
            'isochronous_cosmic': {'label': 'Isochronous Cosmic', 'color': 'red', 'marker': 'o'},
            'normal_cosmic': {'label': 'Normal Cosmic', 'color': 'green', 'marker': 's'},
            'prolonged_cosmic': {'label': 'Prolonged Cosmic', 'color': 'blue', 'marker': '^'}
        }

        for category_key, info in category_info.items():
            # Filter clusters by category (using composite keys if available)
            if category_key == 'neutrino':
                category_cluster_keys = [key for key, data in category_info_source.items() if data['is_neutrino']]
            elif category_key == 'isochronous_cosmic':
                category_cluster_keys = [key for key, data in category_info_source.items()
                                       if not data['is_neutrino'] and data['track_type'] == 'isochronous']
            elif category_key == 'normal_cosmic':
                category_cluster_keys = [key for key, data in category_info_source.items()
                                       if not data['is_neutrino'] and data['track_type'] == 'normal']
            elif category_key == 'prolonged_cosmic':
                category_cluster_keys = [key for key, data in category_info_source.items()
                                       if not data['is_neutrino'] and data['track_type'] == 'prolonged']

            if not category_cluster_keys:
                continue

            # Get energies and efficiencies for this category
            category_energies = [true_cluster_efficiency[key]['total_energy'] for key in category_cluster_keys if key in true_cluster_efficiency]
            category_efficiencies = [true_cluster_efficiency[key]['total_efficiency'] for key in category_cluster_keys if key in true_cluster_efficiency]

            if category_energies:
                # Get 1D projection for this category
                bin_centers_cat, mean_eff_cat = plot_1d_efficiency_energy(category_energies, category_efficiencies, energy_bins)

                if len(bin_centers_cat) > 0:
                    color = info['color']
                    marker = info['marker']
                    label_text = f"{info['label']} ({len(category_cluster_keys)} clusters)"
                    plt.plot(bin_centers_cat, mean_eff_cat, marker=marker, linestyle='-', linewidth=2, markersize=8,
                            color=color, label=label_text, markeredgecolor='black', markeredgewidth=0.5)

        plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
        plt.ylabel('Efficiency', fontsize=12, fontweight='bold')
        title = f'Efficiency vs True Energy (1D by Category) - File Level, {apa}'
        if file_name:
            title += f' ({file_name})'
        plt.title(title, fontsize=12, fontweight='bold')
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.legend(fontsize=10)
        plt.xlim(0, 3000)
        plt.ylim(-0.05, 1.05)
        plt.savefig(output_dir / f"efficiency_vs_true_energy_1d_by_category_file_{apa}.png",
                    dpi=100, bbox_inches='tight', pad_inches=0.3)
        plt.close()


def DrawEfficiencyVsTrueEnergyPerJob(efficiency_results, output_dir, apa, cluster_category_results=None, job_metadata_list=None):
    """
    Job-level version: For each true cluster calculate sum of efficiency values,
    then plot efficiency vs true cluster energy (2D and 1D) for all events in all files.
    If cluster_category_results or job_metadata_list is provided, also plot separate 2D and 1D plots for each cluster category.
    Note: Uses (event, true_cluster_id) composite key to ensure uniqueness across all files and events.
    """
    if not efficiency_results:
        return

    # Count unique events across all files
    unique_events = set()
    if job_metadata_list is not None:
        unique_events = set(m['event'] for m in job_metadata_list)
    else:
        unique_events = set(eff.get('event', 'unknown') for eff in efficiency_results)
    num_events_total = len(unique_events)

    # Group efficiency by (event, true_cluster_id) to ensure uniqueness across all files and events
    true_cluster_efficiency = {}
    for eff in efficiency_results:
        event_key = eff.get('event', 'unknown')
        true_cid = eff['true_cluster_id']
        cluster_key = (event_key, true_cid)

        if cluster_key not in true_cluster_efficiency:
            true_cluster_efficiency[cluster_key] = {
                'total_efficiency': 0,
                'total_energy': eff.get('total_true_cluster_energy', 0),
                'num_reco_matches': 0
            }

        true_cluster_efficiency[cluster_key]['total_efficiency'] += eff['efficiency_energy_weighted']
        true_cluster_efficiency[cluster_key]['num_reco_matches'] += 1

    if not true_cluster_efficiency:
        return

    energies        = [data['total_energy']     for data in true_cluster_efficiency.values()]
    efficiencies    = [data['total_efficiency'] for data in true_cluster_efficiency.values()]

    # 2D Histogram for all clusters
    plot_2d_efficiency_energy(energies, efficiencies, output_dir, 0, apa,
                             category_name="All Clusters (Job Level)", file_name=None, num_events=num_events_total)

    # Build category info from job_metadata_list if provided, otherwise use cluster_category_results
    category_info_source = None
    if job_metadata_list is not None:
        # Convert job_metadata_list to category dict format using (event, true_cluster_id) composite key
        category_info_source = {}
        for metadata in job_metadata_list:
            event_key = metadata['event']
            cid = metadata['true_cluster_id']
            cluster_key = (event_key, cid)
            if cluster_key not in category_info_source:
                category_info_source[cluster_key] = {
                    'is_neutrino': metadata['cluster_type'] == 'neutrino',
                    'track_type': metadata['cluster_category']
                }
        print(f"  [JOB LEVEL] Built category_info_source from metadata: {len(category_info_source)} clusters")
    elif cluster_category_results is not None:
        category_info_source = cluster_category_results
        print(f"  [JOB LEVEL] Using cluster_category_results: {len(category_info_source)} clusters")

    # 2D plots by category (only if category info is available)
    if category_info_source is not None:
        print(f"  [JOB LEVEL] Drawing 2D efficiency plots for categories...")
        category_styles = {
            'neutrino': 'Neutrino Clusters',
            'isochronous_cosmic': 'Isochronous Cosmic Clusters',
            'normal_cosmic': 'Normal Cosmic Clusters',
            'prolonged_cosmic': 'Prolonged Cosmic Clusters'
        }

        for category_key, category_label in category_styles.items():
            # Filter clusters by category (using composite keys if available)
            if category_key == 'neutrino':
                category_cluster_keys = [key for key, data in category_info_source.items() if data['is_neutrino']]
            elif category_key == 'isochronous_cosmic':
                category_cluster_keys = [key for key, data in category_info_source.items()
                                       if not data['is_neutrino'] and data['track_type'] == 'isochronous']
            elif category_key == 'normal_cosmic':
                category_cluster_keys = [key for key, data in category_info_source.items()
                                       if not data['is_neutrino'] and data['track_type'] == 'normal']
            elif category_key == 'prolonged_cosmic':
                category_cluster_keys = [key for key, data in category_info_source.items()
                                       if not data['is_neutrino'] and data['track_type'] == 'prolonged']

            print(f"    {category_label}: found {len(category_cluster_keys)} clusters in metadata")

            if not category_cluster_keys:
                print(f"      → No clusters in this category, skipping...")
                continue

            # Get energies and efficiencies for this category
            category_energies = [true_cluster_efficiency[key]['total_energy'] for key in category_cluster_keys if key in true_cluster_efficiency]
            category_efficiencies = [true_cluster_efficiency[key]['total_efficiency'] for key in category_cluster_keys if key in true_cluster_efficiency]

            print(f"      → Matched {len(category_energies)} clusters in efficiency_results")

            # Draw 2D plot for this category
            if category_energies:
                print(f"      → Drawing 2D plot for {category_label}...")
                plot_2d_efficiency_energy(category_energies, category_efficiencies, output_dir, 0, apa,
                                         category_name=category_label, file_name=None, num_events=num_events_total)
            else:
                print(f"      → No energies/efficiencies found, skipping plot...")

    # Setup binning for 1D projections
    n_bins = 15
    if energies:
        energy_bins = np.linspace(0, max(energies)*1.1, n_bins+1)
    else:
        energy_bins = np.linspace(0, 10, n_bins+1)

    # 1D Plot: All clusters (separate canvas)
    bin_centers_all, mean_eff_all = plot_1d_efficiency_energy(energies, efficiencies, energy_bins)

    plt.figure(figsize=(12, 6))
    if len(bin_centers_all) > 0:
        plt.plot(bin_centers_all, mean_eff_all, 'o-', linewidth=2.5, markersize=10,
                color='darkblue', label='All Clusters', markeredgecolor='black', markeredgewidth=1)

    plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
    plt.ylabel('Efficiency', fontsize=12, fontweight='bold')
    title = f'Efficiency vs True Energy (1D Projection) - Job Level, {apa}'
    plt.title(title, fontsize=12, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.xlim(0, 3000)
    plt.ylim(-0.05, 1.05)
    plt.savefig(output_dir / f"efficiency_vs_true_energy_1d_job_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()

    # 1D Plot 2: By category (only if category info is available)
    if category_info_source is not None:
        plt.figure(figsize=(14, 7))

        # Define categories combining track_type and neutrino/cosmic
        category_info = {
            'neutrino': {'label': 'Neutrino Clusters', 'color': 'purple', 'marker': 'D'},
            'isochronous_cosmic': {'label': 'Isochronous Cosmic', 'color': 'red', 'marker': 'o'},
            'normal_cosmic': {'label': 'Normal Cosmic', 'color': 'green', 'marker': 's'},
            'prolonged_cosmic': {'label': 'Prolonged Cosmic', 'color': 'blue', 'marker': '^'}
        }

        for category_key, info in category_info.items():
            # Filter clusters by category (using composite keys if available)
            if category_key == 'neutrino':
                category_cluster_keys = [key for key, data in category_info_source.items() if data['is_neutrino']]
            elif category_key == 'isochronous_cosmic':
                category_cluster_keys = [key for key, data in category_info_source.items()
                                       if not data['is_neutrino'] and data['track_type'] == 'isochronous']
            elif category_key == 'normal_cosmic':
                category_cluster_keys = [key for key, data in category_info_source.items()
                                       if not data['is_neutrino'] and data['track_type'] == 'normal']
            elif category_key == 'prolonged_cosmic':
                category_cluster_keys = [key for key, data in category_info_source.items()
                                       if not data['is_neutrino'] and data['track_type'] == 'prolonged']

            if not category_cluster_keys:
                continue

            # Get energies and efficiencies for this category
            category_energies = [true_cluster_efficiency[key]['total_energy'] for key in category_cluster_keys if key in true_cluster_efficiency]
            category_efficiencies = [true_cluster_efficiency[key]['total_efficiency'] for key in category_cluster_keys if key in true_cluster_efficiency]

            if category_energies:
                # Get 1D projection for this category
                bin_centers_cat, mean_eff_cat = plot_1d_efficiency_energy(category_energies, category_efficiencies, energy_bins)

                if len(bin_centers_cat) > 0:
                    color = info['color']
                    marker = info['marker']
                    label_text = f"{info['label']} ({len(category_cluster_keys)} clusters)"
                    plt.plot(bin_centers_cat, mean_eff_cat, marker=marker, linestyle='-', linewidth=2, markersize=8,
                            color=color, label=label_text, markeredgecolor='black', markeredgewidth=0.5)

        plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
        plt.ylabel('Efficiency', fontsize=12, fontweight='bold')
        title = f'Efficiency vs True Energy (1D by Category) - Job Level, {apa}'
        plt.title(title, fontsize=12, fontweight='bold')
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.legend(fontsize=10)
        plt.xlim(0, 3000)
        plt.ylim(-0.05, 1.05)
        plt.savefig(output_dir / f"efficiency_vs_true_energy_1d_by_category_job_{apa}.png",
                    dpi=100, bbox_inches='tight', pad_inches=0.3)
        plt.close()

def DrawPurityVsRecoChargePerEvent(purity_results, output_dir, event, apa, file_name=None):
    """
    For each reco cluster: plot purity vs reco charge (2D and 1D).
    """
    if not purity_results:
        return

    charges = []
    purities = []

    for pur in purity_results:
        if pur['reco_cluster_id'] == 8888:  # Skip unmatched sentinel
            continue
        charges.append(pur.get('total_reco_cluster_charge', 0))
        purities.append(pur['purity'])

    if not charges:
        return

    # 2D Histogram
    plt.figure(figsize=(10, 8))
    plt.hist2d(charges, purities, bins=20, cmap='YlGnBu')
    plt.colorbar(label='Count')
    plt.xlabel('Reco Cluster Charge', fontsize=12, fontweight='bold')
    plt.ylabel('Purity', fontsize=12, fontweight='bold')
    title = f'Purity vs Reco Charge (2D) - Event {event}, {apa}'
    if file_name:
        title += f' ({file_name})'
    plt.title(title, fontsize=12, fontweight='bold')
    plt.savefig(output_dir / f"purity_vs_reco_charge_2d_event_{event}_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    ##plt.show(block=False)
    plt.close()

    # 1D Projection with binned scatter points connected by lines
    plt.figure(figsize=(12, 6))

    n_bins = 15
    if charges:
        charge_bins = np.linspace(0, max(charges)*1.1, n_bins+1)
    else:
        charge_bins = np.linspace(0, 10, n_bins+1)

    bin_centers = (charge_bins[:-1] + charge_bins[1:]) / 2
    mean_purity_per_bin = []
    bin_counts = []

    if charges:
        for i in range(len(charge_bins)-1):
            mask = (np.array(charges) >= charge_bins[i]) & (np.array(charges) < charge_bins[i+1])
            if np.sum(mask) > 0:
                mean_pur = np.mean(np.array(purities)[mask])
                count = np.sum(mask)
                mean_purity_per_bin.append(mean_pur)
                bin_counts.append(count)
            else:
                mean_purity_per_bin.append(0)
                bin_counts.append(0)

    if len(bin_centers) > 0:
        plt.plot(bin_centers, mean_purity_per_bin, 'o-', linewidth=2, markersize=10,
                color='darkred', label='Mean Purity per Bin', markeredgecolor='black', markeredgewidth=1)

    plt.xlabel('Reco Cluster Charge [ADC] Arbitrary Units', fontsize=12, fontweight='bold')
    plt.ylabel('Purity', fontsize=12, fontweight='bold')
    title = f'Purity vs Reco Charge (1D Projection) - Event {event}, {apa}'
    if file_name:
        title += f' ({file_name})'
    plt.title(title, fontsize=12, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.savefig(output_dir / f"purity_vs_reco_charge_1d_event_{event}_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()

# ============================================================================
# AGGREGATION FUNCTIONS FOR MULTIPLE EVENTS/FILES/JOB
# ============================================================================


def DrawAggregatedEfficiencyPlots(efficiency_results, output_dir, level_name, apa):
    """Draw 2D and 1D efficiency plots for aggregated results."""
    if not efficiency_results:
        return

    efficiencies = [e['efficiency_energy_weighted'] for e in efficiency_results if e['reco_cluster_id'] != 8888]

    if not efficiencies:
        return

    # 2D Histogram
    plt.figure(figsize=(10, 8))
    plt.hist(efficiencies, bins=30, color='skyblue', edgecolor='black', alpha=0.7)
    plt.xlabel('Efficiency', fontsize=12, fontweight='bold')
    plt.ylabel('Count', fontsize=12, fontweight='bold')
    plt.title(f'Efficiency Distribution ({level_name}) - {apa}', fontsize=12, fontweight='bold')
    plt.axvline(np.mean(efficiencies), color='red', linestyle='--', linewidth=2, label=f'Mean: {np.mean(efficiencies):.3f}')
    plt.axvline(np.median(efficiencies), color='green', linestyle='--', linewidth=2, label=f'Median: {np.median(efficiencies):.3f}')
    plt.legend(fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.savefig(output_dir / f"efficiency_distribution_{level_name.lower().replace(' ', '_')}_{apa}.png", dpi=100, bbox_inches='tight', pad_inches=0.3)
    ##plt.show(block=False)
    plt.close()

def DrawAggregatedPurityPlots(purity_results, output_dir, level_name, apa):
    """Draw 2D and 1D purity plots for aggregated results."""
    if not purity_results:
        return

    purities = [p['purity'] for p in purity_results if p['reco_cluster_id'] != 8888]

    if not purities:
        return

    # 2D Histogram
    plt.figure(figsize=(10, 8))
    plt.hist(purities, bins=30, color='lightcoral', edgecolor='black', alpha=0.7)
    plt.xlabel('Purity', fontsize=12, fontweight='bold')
    plt.ylabel('Count', fontsize=12, fontweight='bold')
    plt.title(f'Purity Distribution ({level_name}) - {apa}', fontsize=12, fontweight='bold')
    plt.axvline(np.mean(purities), color='red', linestyle='--', linewidth=2, label=f'Mean: {np.mean(purities):.3f}')
    plt.axvline(np.median(purities), color='green', linestyle='--', linewidth=2, label=f'Median: {np.median(purities):.3f}')
    plt.legend(fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.savefig(output_dir / f"purity_distribution_{level_name.lower().replace(' ', '_')}_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    ##plt.show(block=False)
    plt.close()

def DrawMatchedPairsPlots(matched_pairs, output_dir, level_name, apa):
    """Draw efficiency vs purity scatter plot for matched pairs."""
    if not matched_pairs:
        return

    efficiencies = [p['efficiency_energy_weighted'] for p in matched_pairs]
    purities = [p['purity'] for p in matched_pairs]

    # Scatter plot
    plt.figure(figsize=(10, 8))
    plt.scatter(efficiencies, purities, s=50, alpha=0.6, color='purple', edgecolors='black', linewidth=0.5)
    plt.xlabel('Efficiency', fontsize=12, fontweight='bold')
    plt.ylabel('Purity', fontsize=12, fontweight='bold')
    plt.title(f'Efficiency vs Purity ({level_name}) - {apa}', fontsize=12, fontweight='bold')
    plt.xlim(-0.05, 1.05)
    plt.ylim(-0.05, 1.05)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.savefig(output_dir / f"efficiency_vs_purity_{level_name.lower().replace(' ', '_')}_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()

def DrawEfficiencyVsPurity_MatchedPairs(true_reco_matched_pairs, output_dir, apa):
    plt.figure(figsize=(14, 11))
    plt.scatter([entry['efficiency_energy_weighted'] for entry in true_reco_matched_pairs],
                [entry['purity'] for entry in true_reco_matched_pairs],
                color='blue', alpha=0.7, s=100)

    plt.xlim(-0.02, 1.02)
    plt.ylim(-0.02, 1.02)
    plt.title(f"Efficiency vs Purity for True-Reco Cluster Pairs ({apa}), {len(true_reco_matched_pairs)} clusters", fontsize=20, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xlabel('Efficiency', fontsize=20, fontweight='bold')
    plt.ylabel('Purity', fontsize=20, fontweight='bold')
    plt.xticks(fontsize=20)
    plt.yticks(fontsize=20)
    plt.subplots_adjust(left=0.15, right=0.95, top=0.93, bottom=0.12)
    plt.savefig(output_dir / f"efficiency_vs_purity_{apa}_all_files.png", dpi=150, bbox_inches='tight', pad_inches=0.3)
    plt.close()
    # ##plt.show(block=False)

# function to draw efficiency vs purity 2D histogram (colz)

def DrawEfficiencyVsPurity_MatchedPairsColz(true_reco_matched_pairs, output_dir, apa):
    efficiency_values = [entry['efficiency_energy_weighted'] for entry in true_reco_matched_pairs]
    purity_values = [entry['purity'] for entry in true_reco_matched_pairs]

    plt.figure(figsize=(14, 11))
    h = plt.hist2d(efficiency_values, purity_values, bins=40, cmap='YlOrRd', range=[[0, 1], [0, 1]])
    cbar = plt.colorbar(h[3], label='Count')
    cbar.set_label('Count', fontsize=20, fontweight='bold')
    cbar.ax.tick_params(labelsize=20)

    plt.xlim(-0.02, 1.02)
    plt.ylim(-0.02, 1.02)
    plt.title(f"Efficiency vs Purity 2D Histogram ({apa}), {len(true_reco_matched_pairs)} clusters", fontsize=20, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xlabel('Efficiency', fontsize=20, fontweight='bold')
    plt.ylabel('Purity', fontsize=20, fontweight='bold')
    plt.xticks(fontsize=20)
    plt.yticks(fontsize=20)
    plt.subplots_adjust(left=0.15, right=0.92, top=0.93, bottom=0.12)
    plt.savefig(output_dir / f"efficiency_vs_purity_colz_{apa}_all_files.png", dpi=150, bbox_inches='tight', pad_inches=0.3)
    plt.close()
    #(block=False)# Function to match true and reco clusters based on purity and efficiency results
# make pairing based on highest purity for each true cluster, then ensure one-to-one matching by keeping only the best pair for each reco cluster
# TODO: we need to change matching creteria to energy-weighted efficiency instead of purity

def DrawEfficiencyVsTrueEnergyAllEvents(all_efficiency_results, input_directories_map, output_dir, apa):
    """
    Draw 2D colz histogram of efficiency vs TRUE cluster energy for ALL events.
    Then create a 1D projection showing mean efficiency vs TRUE cluster energy bins.
    Saves organized in hierarchy: output_dir/input_file/event_N/efficiency/
    X-axis: total TRUE cluster energy
    Y-axis: efficiency (energy-weighted)
    """

    # Group results by event
    results_by_event = {}
    for result in all_efficiency_results:
        # Parse composite event key: "input_file_name_event_number"
        event_key = result['event']
        if isinstance(event_key, str) and '_' in event_key:
            event = int(event_key.rsplit('_', 1)[1])  # Get last part after final underscore
        else:
            event = int(event_key)
        if event not in results_by_event:
            results_by_event[event] = []
        results_by_event[event].append(result)

    output_dir = Path(output_dir)

    for event, event_results in results_by_event.items():
        # result['event'] is already the composite key like "file1_0"
        # Use it directly for lookup
        event_key = str(result['event']) if result['event'] not in input_directories_map else result['event']

        # Try composite key first, then extract event number
        if event_key not in input_directories_map:
            # Fallback: extract event number and search
            for key in input_directories_map:
                if isinstance(key, str) and f"_{event}" in key:
                    event_key = key
                    break

        if event_key not in input_directories_map:
            print(f"Warning: No input directory found for event {event}, skipping efficiency plots")
            continue

        input_dir, evt_num = input_directories_map[event_key]

        input_file_name = input_dir.parent.name

        # Create hierarchical directory: output_dir/input_file/event_N/efficiency/
        event_output_dir = output_dir / input_file_name / f"event_{event:03d}" / "efficiency"
        event_output_dir.mkdir(parents=True, exist_ok=True)

        # Extract efficiency and true energy information for this event
        true_energies = []
        efficiencies = []
        ghost_energies = []

        for result in event_results:
            true_energy = result.get('total_true_cluster_energy', 0)
            efficiency = result.get('efficiency_energy_weighted', 0)

            if true_energy > 0:
                # Check for unmatched clusters (efficiency=-0.1 sentinel)
                if abs(efficiency - (-0.1)) < 0.001:
                    ghost_energies.append(true_energy)
                elif efficiency > 0:
                    true_energies.append(true_energy)
                    efficiencies.append(efficiency)

        if len(true_energies) == 0 and len(ghost_energies) == 0:
            print(f"No valid efficiency vs energy data for event {event}")
            continue

        print(f"\nEvent {event} ({input_file_name}):")
        print(f"  Plotting {len(true_energies)} matched cluster points")
        if len(ghost_energies) > 0:
            print(f"  Ghost tracks: {len(ghost_energies)}")

        # Add ghost clusters to histogram at (0, 0)
        if len(ghost_energies) > 0:
            true_energies.extend([0] * len(ghost_energies))
            efficiencies.extend([0] * len(ghost_energies))
            print(f'  Added {len(ghost_energies)} ghost clusters at (0,0)')
        # Create 2D colz histogram
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))

        # 2D histogram
        if true_energies:
            h = ax1.hist2d(true_energies, efficiencies, bins=40, cmap='YlOrRd', range=[[0, max(true_energies)*1.25], [-0.2, 1.05]])
            cbar1 = plt.colorbar(h[3], ax=ax1, label='Count')
            cbar1.set_label('Count', fontsize=16, fontweight='bold')
            cbar1.ax.tick_params(labelsize=14)

            ax1.scatter(true_energies, efficiencies, alpha=0.3, s=20, color='black', marker='.')

        # Set x-axis limits to show both matched and unmatched clusters
        all_energies = true_energies + ghost_energies if ghost_energies else true_energies
        x_max = max(all_energies)*1.25 if all_energies else 10
        ax1.set_xlim(0, x_max)
        ax1.set_ylim(-0.2, 1.05)
        ax1.axvline(x=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax1.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)

        ax1.set_xlabel('True Cluster Energy [MeV]', fontsize=18, fontweight='bold')
        ax1.set_ylabel('Efficiency (Energy-Weighted)', fontsize=18, fontweight='bold')
        ax1.set_title(f'2D Histogram: Efficiency vs True Energy (Event {event})', fontsize=18, fontweight='bold')
        ax1.tick_params(labelsize=14)
        ax1.grid(True, linestyle='--', alpha=0.3)
        if len(ghost_energies) > 0:
            ghost_energies_array = np.array(ghost_energies)
            ghost_x_positions = (ghost_energies_array / max(ghost_energies_array) * (-80) - 20) if max(ghost_energies_array) > 0 else np.full_like(ghost_energies_array, -50)
            ghost_y_positions = np.full_like(ghost_energies_array, -0.1)
            ax2.scatter(ghost_x_positions, ghost_y_positions, c='purple', s=30, alpha=0.6, marker='X', label=f'Ghost Tracks ({len(ghost_energies)})', edgecolors='darkviolet', linewidth=1)
            ax1.legend(fontsize=12, loc='bottom right')
            ax1.text(-50, -0.15, 'GHOST TRACKS', ha='center', fontsize=11,
                    bbox=dict(boxstyle='round', facecolor='purple', alpha=0.2))

        # 1D projection
        n_bins = 20
        if true_energies:
            energy_bins = np.linspace(-100, max(true_energies)*1.25, n_bins+1)
        else:
            energy_bins = np.linspace(-100, 10, n_bins+1)

        bin_centers = (energy_bins[:-1] + energy_bins[1:]) / 2
        mean_efficiency_per_bin = []
        bin_counts = []

        if true_energies:
            for i in range(len(energy_bins)-1):
                mask = (np.array(true_energies) >= energy_bins[i]) & (np.array(true_energies) < energy_bins[i+1])
                if np.sum(mask) > 0:
                    mean_eff = np.mean(np.array(efficiencies)[mask])
                    count = np.sum(mask)
                    mean_efficiency_per_bin.append(mean_eff)
                    bin_counts.append(count)
                else:
                    mean_efficiency_per_bin.append(0)
                    bin_counts.append(0)

        non_empty_mask = np.array(bin_counts) > 0
        valid_bin_centers = bin_centers[non_empty_mask]
        valid_mean_efficiency = np.array(mean_efficiency_per_bin)[non_empty_mask]

        if len(valid_bin_centers) > 0:
            ax2.plot(valid_bin_centers, valid_mean_efficiency, 'o-', linewidth=3, markersize=12,
                    color='darkblue', label='Mean Efficiency per Bin')

        if len(ghost_energies) > 0:
            # Plot unmatched clusters at their true energy but at y=0 (zero efficiency)
            ghost_y_1d = np.zeros(len(ghost_energies))
            ax2.scatter(ghost_energies, ghost_y_1d, c='purple', s=30, alpha=0.6, marker='X',
                label=f'Unmatched Clusters ({len(ghost_energies)})', edgecolors='darkviolet', linewidths=1)

        ax2.set_xlim(-100, max(true_energies)*1.25 if true_energies else 10)
        ax2.set_ylim(-0.2, 1.05)
        ax2.axvline(x=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax2.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)

        ax2.set_xlabel('True Cluster Energy [MeV]', fontsize=18, fontweight='bold')
        ax2.set_ylabel('Efficiency', fontsize=18, fontweight='bold')
        ax2.set_title(f'1D Projection: Mean Efficiency vs True Energy (Event {event})', fontsize=18, fontweight='bold')
        ax2.tick_params(labelsize=14)
        ax2.grid(True, linestyle='--', alpha=0.3)
        if len(valid_bin_centers) > 0:
            ax2.legend(fontsize=14, loc='lower right')
        if len(ghost_energies) > 0:
            ghost_energies_array = np.array(ghost_energies)
            ghost_x_positions = (ghost_energies_array / max(ghost_energies_array) * (-80) - 20) if max(ghost_energies_array) > 0 else np.full_like(ghost_energies_array, -50)
            ghost_y_positions = np.full_like(ghost_energies_array, -0.1)
            ax2.scatter(ghost_x_positions, ghost_y_positions, c='purple', s=30, alpha=0.6, marker='X', label=f'Ghost Tracks ({len(ghost_energies)})', edgecolors='darkviolet', linewidth=1)
            ax2.text(-50, -0.15, 'GHOSTS', ha='center', fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='purple', alpha=0.2))

        plt.tight_layout()
        plt.savefig(event_output_dir / f"efficiency_vs_true_energy_{apa}.png", dpi=150, bbox_inches='tight', pad_inches=0.3)
    plt.close()
        # ##plt.show(block=False)

def DrawEfficiencySummaryAllFilesAllEvents(all_efficiency_results, output_dir, apa):
    """
    Draw summary 2D and 1D plots aggregating efficiency across ALL files and ALL events.
    Saves to top-level output_dir (not nested in file/event subdirectories).
    """

    if len(all_efficiency_results) == 0:
        print("No efficiency results for summary plots")
        return

    output_dir = Path(output_dir)

    # Extract all efficiency and energy data
    true_energies = []
    efficiencies = []
    ghost_energies = []

    for result in all_efficiency_results:
        true_energy = result.get('total_true_cluster_energy', 0)
        efficiency = result.get('efficiency_energy_weighted', 0)

        if true_energy > 0:
            if efficiency > 0:
                true_energies.append(true_energy)
                efficiencies.append(efficiency)
            else:
                ghost_energies.append(true_energy)

    if len(true_energies) == 0:
        print("No valid efficiency data for summary")
        return

    print(f"\n{'='*60}")
    print(f"SUMMARY: Efficiency across ALL files and ALL events")
    print(f"{'='*60}")
    print(f"Total matched clusters: {len(true_energies)}")
    print(f"Ghost tracks: {len(ghost_energies)}")

    # Create summary 2D and 1D plots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))

    # 2D histogram
    h = ax1.hist2d(true_energies, efficiencies, bins=40, cmap='YlOrRd',
                    range=[[0, max(true_energies)*1.25], [0, 1.05]])
    cbar1 = plt.colorbar(h[3], ax=ax1, label='Count')
    cbar1.set_label('Count', fontsize=16, fontweight='bold')
    cbar1.ax.tick_params(labelsize=14)

    ax1.scatter(true_energies, efficiencies, alpha=0.3, s=20, color='black', marker='.')

    if len(ghost_energies) > 0:
        ghost_y = np.full_like(ghost_energies, -0.1)
        ax1.scatter([-50]*len(ghost_energies), ghost_y, c='purple', s=30, alpha=0.6, marker='X',
                    label=f'Ghost Tracks ({len(ghost_energies)})', edgecolors='darkviolet', linewidth=1)

    ax1.set_xlim(-100, max(true_energies)*1.25)
    ax1.set_ylim(-0.2, 1.05)
    ax1.axvline(x=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax1.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)

    ax1.set_xlabel('True Cluster Energy [MeV]', fontsize=18, fontweight='bold')
    ax1.set_ylabel('Efficiency (Energy-Weighted)', fontsize=18, fontweight='bold')
    ax1.set_title(f'SUMMARY: Efficiency vs True Energy (All Files, All Events)', fontsize=18, fontweight='bold')
    ax1.tick_params(labelsize=14)
    ax1.grid(True, linestyle='--', alpha=0.3)
    if len(ghost_energies) > 0:
        ax1.legend(fontsize=12, loc='upper left')

    # 1D projection
    n_bins = 20
    energy_bins = np.linspace(0, max(true_energies)*1.25, n_bins+1)
    bin_centers = (energy_bins[:-1] + energy_bins[1:]) / 2
    mean_efficiency_per_bin = []
    bin_counts = []

    for i in range(len(energy_bins)-1):
        mask = (np.array(true_energies) >= energy_bins[i]) & (np.array(true_energies) < energy_bins[i+1])
        if np.sum(mask) > 0:
            mean_eff = np.mean(np.array(efficiencies)[mask])
            count = np.sum(mask)
            mean_efficiency_per_bin.append(mean_eff)
            bin_counts.append(count)
        else:
            mean_efficiency_per_bin.append(0)
            bin_counts.append(0)

    non_empty_mask = np.array(bin_counts) > 0
    valid_bin_centers = bin_centers[non_empty_mask]
    valid_mean_efficiency = np.array(mean_efficiency_per_bin)[non_empty_mask]

    if len(valid_bin_centers) > 0:
        ax2.plot(valid_bin_centers, valid_mean_efficiency, 'o-', linewidth=3, markersize=12,
                color='darkblue', label='Mean Efficiency per Bin')

    if len(ghost_energies) > 0:
        ghost_y_1d = np.full_like(ghost_energies, -0.1)
        ax2.scatter([-50]*len(ghost_energies), ghost_y_1d, c='purple', s=30, alpha=0.6, marker='X',
                    label=f'Ghost Tracks ({len(ghost_energies)})', edgecolors='darkviolet', linewidth=1)

    ax2.set_xlim(-100, max(true_energies)*1.25)
    ax2.set_ylim(-0.2, 1.05)
    ax2.axvline(x=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax2.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)

    ax2.set_xlabel('True Cluster Energy [MeV]', fontsize=18, fontweight='bold')
    ax2.set_ylabel('Efficiency', fontsize=18, fontweight='bold')
    ax2.set_title(f'SUMMARY: 1D Projection (All Files, All Events)', fontsize=18, fontweight='bold')
    ax2.tick_params(labelsize=14)
    ax2.grid(True, linestyle='--', alpha=0.3)
    ax2.legend(fontsize=14, loc='lower right')

    plt.tight_layout()
    plt.savefig(output_dir / f"SUMMARY_efficiency_vs_true_energy_{apa}.png", dpi=150, bbox_inches='tight', pad_inches=0.3)
    plt.close()
    ## ##plt.show(block=False)
    print(f"Saved: {output_dir}/SUMMARY_efficiency_vs_true_energy_{apa}.png\n")

def DrawPuritySummaryAllFilesAllEvents(all_purity_results, output_dir, apa):
    """
    Draw summary 2D and 1D plots aggregating purity across ALL files and ALL events.
    Saves to top-level output_dir (not nested in file/event subdirectories).
    """

    if len(all_purity_results) == 0:
        print("No purity results for summary plots")
        return

    output_dir = Path(output_dir)

    # Extract all purity and charge data
    purity_values = []
    reco_charge_values = []

    for result in all_purity_results:
        purity = result['purity']
        total_reco_charge = result['total_reco_cluster_charge']

        if purity > 0:
            purity_values.append(purity)
            reco_charge_values.append(total_reco_charge)

    if len(purity_values) == 0:
        print("No valid purity data for summary")
        return

    print(f"\n{'='*60}")
    print(f"SUMMARY: Purity across ALL files and ALL events")
    print(f"{'='*60}")
    print(f"Total reco clusters: {len(purity_values)}")

    # Create summary 2D and 1D plots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))

    # 2D histogram
    h = ax1.hist2d(reco_charge_values, purity_values, bins=40, cmap='YlOrRd',
                    range=[[0, max(reco_charge_values)*1.1], [0, 1.05]])
    cbar1 = plt.colorbar(h[3], ax=ax1, label='Count')
    cbar1.set_label('Count', fontsize=16, fontweight='bold')
    cbar1.ax.tick_params(labelsize=14)

    ax1.scatter(reco_charge_values, purity_values, alpha=0.3, s=20, color='black', marker='.')

    ax1.set_xlim(0, max(reco_charge_values)*1.1)
    ax1.set_ylim(-0.05, 1.05)

    ax1.set_xlabel('Reco Cluster Charge [ADC] Arbitrary Units', fontsize=18, fontweight='bold')
    ax1.set_ylabel('Purity', fontsize=18, fontweight='bold')
    ax1.set_title(f'SUMMARY: Purity vs Reco Charge (All Files, All Events)', fontsize=18, fontweight='bold')
    ax1.tick_params(labelsize=14)
    ax1.grid(True, linestyle='--', alpha=0.3)

    # 1D projection
    n_bins = 20
    charge_bins = np.linspace(0, max(reco_charge_values)*1.1, n_bins+1)
    bin_centers = (charge_bins[:-1] + charge_bins[1:]) / 2
    mean_purity_per_bin = []
    bin_counts = []

    for i in range(len(charge_bins)-1):
        mask = (np.array(reco_charge_values) >= charge_bins[i]) & (np.array(reco_charge_values) < charge_bins[i+1])
        if np.sum(mask) > 0:
            mean_pur = np.mean(np.array(purity_values)[mask])
            count = np.sum(mask)
            mean_purity_per_bin.append(mean_pur)
            bin_counts.append(count)
        else:
            mean_purity_per_bin.append(0)
            bin_counts.append(0)

    non_empty_mask = np.array(bin_counts) > 0
    valid_bin_centers = bin_centers[non_empty_mask]
    valid_mean_purity = np.array(mean_purity_per_bin)[non_empty_mask]

    if len(valid_bin_centers) > 0:
        ax2.plot(valid_bin_centers, valid_mean_purity, 'o-', linewidth=3, markersize=12,
                color='darkblue', label='Mean Purity per Bin')

    # Individual cluster scatter removed for cleaner plot

    ax2.set_xlim(0, max(reco_charge_values)*1.1)
    ax2.set_ylim(-0.05, 1.05)

    ax2.set_xlabel('Reco Cluster Charge [ADC] Arbitrary Units', fontsize=18, fontweight='bold')
    ax2.set_ylabel('Purity', fontsize=18, fontweight='bold')
    ax2.set_title(f'SUMMARY: 1D Projection (All Files, All Events)', fontsize=18, fontweight='bold')
    ax2.tick_params(labelsize=14)
    ax2.grid(True, linestyle='--', alpha=0.3)
    ax2.legend(fontsize=14, loc='lower right')

    plt.tight_layout()
    plt.savefig(output_dir / f"SUMMARY_purity_vs_reco_charge_{apa}.png", dpi=150, bbox_inches='tight', pad_inches=0.3)
    plt.close()
    ## ##plt.show(block=False)
    print(f"Saved: {output_dir}/SUMMARY_purity_vs_reco_charge_{apa}.png\n")

def DrawProblematicClusters(all_efficiency_results, output_dir, n_clusters=3):
    """
    Find and draw high-energy, low-efficiency clusters to understand why they fail.
    Creates spatial visualizations (XZ and YZ) for the worst performers.
    """

    # Convert to DataFrame for easier filtering
    df = pd.DataFrame(all_efficiency_results)
    df = df.sort_values('total_true_cluster_energy', ascending=False)

    # Find high-energy clusters (top 25% by energy)
    high_energy_threshold = df['total_true_cluster_energy'].quantile(0.75)
    high_energy_df = df[df['total_true_cluster_energy'] > high_energy_threshold].copy()

    # Find those with very low efficiency (0 or < 0.2)
    low_eff_df = high_energy_df[high_energy_df['efficiency_energy_weighted'] < 0.2].copy()
    low_eff_df = low_eff_df.sort_values('total_true_cluster_energy', ascending=False)

    if len(low_eff_df) == 0:
        print("No high-energy, low-efficiency clusters found to visualize")
        return

    # Select top N problematic clusters
    problematic = low_eff_df.head(n_clusters)

    print(f"\n{'='*80}")
    print(f"DRAWING {len(problematic)} HIGH-ENERGY, LOW-EFFICIENCY CLUSTERS")
    print(f"{'='*80}")

    for idx, (_, row) in enumerate(problematic.iterrows(), 1):
        event = int(row['event'])
        true_cluster_id = row['true_cluster_id']
        reco_cluster_id = row['reco_cluster_id']
        true_energy = row['total_true_cluster_energy']
        matched_energy = row['matched_true_cluster_energy']
        efficiency = row['efficiency_energy_weighted']

        print(f"\nCluster {idx}/{len(problematic)}: Event {event}")
        print(f"  True Cluster ID: {true_cluster_id:.2f}")
        print(f"  Reco Cluster ID: {reco_cluster_id:.2f}")
        print(f"  True Energy: {true_energy:.2f} MeV")
        print(f"  Matched Energy: {matched_energy:.2f} MeV")
        print(f"  Efficiency: {efficiency:.4f} (VERY LOW!)")
        print(f"  Problem: High energy but only {matched_energy:.2f}/{true_energy:.2f} = {efficiency*100:.1f}% matched")

    print(f"\n{'='*80}")
    print("ANALYSIS:")
    print("- These clusters have HIGH true energy but VERY LOW efficiency")
    print("- This indicates the reconstruction MISSED most of the true energy")
    print("- Likely causes:")
    print("  1. True cluster is spread across multiple reco clusters")
    print("  2. Reco reconstruction is fragmented or incomplete")
    print("  3. Spatial mismatch - true and reco clusters don't overlap well")
    print("  4. Reconstruction algorithm limitation for complex/extended clusters")
    print(f"{'='*80}\n")

def DrawPurityVsRecoChargeAllEvents(all_purity_results, input_directories_map, output_dir, apa):

    """
    Draw 2D colz histogram of purity vs RECO cluster charge for ALL events.
    Saves organized in hierarchy: output_dir/input_file/event_N/purity/
    X-axis: total RECO cluster charge (sum of point charges)
    Y-axis: purity

    """

    # Group results by event
    results_by_event = {}
    for result in all_purity_results:

    # Parse composite event key: "input_file_name_event_number"
        event_key = result['event']
        if isinstance(event_key, str) and '_' in event_key:
            event = int(event_key.rsplit('_', 1)[1])  # Get last part after final underscore
        else:
            event = int(event_key)
        if event not in results_by_event:
            results_by_event[event] = []
        results_by_event[event].append(result)

    output_dir = Path(output_dir)

    for event, event_results in results_by_event.items():

    # result['event'] is already the composite key like "file1_0"

    # Use it directly for lookup
        event_key = str(result['event']) if result['event'] not in input_directories_map else result['event']

    # Try composite key first, then extract event number
        if event_key not in input_directories_map:

    # Fallback: extract event number and search
            for key in input_directories_map:
                if isinstance(key, str) and f"_{event}" in key:
                    event_key = key
                    break

        if event_key not in input_directories_map:
            print(f"Warning: No input directory found for event {event}, skipping purity plots")
            continue

        input_dir, evt_num = input_directories_map[event_key]

        input_file_name = input_dir.parent.name

    # Create hierarchical directory: output_dir/input_file/event_N/purity/
        event_output_dir = output_dir / input_file_name / f"event_{event:03d}" / "purity"
        event_output_dir.mkdir(parents=True, exist_ok=True)

    # Extract purity and reco cluster charge
        purity_values = []
        reco_charge_values = []
        ghost_charges = []

        for result in event_results:
            purity = result['purity']
            total_reco_charge = result['total_reco_cluster_charge']

            if total_reco_charge > 0:

    # Check for unmatched clusters (purity=-0.1 sentinel)
                if abs(purity - (-0.1)) < 0.001:
                    ghost_charges.append(total_reco_charge)
                elif purity > 0:
                    purity_values.append(purity)
                    reco_charge_values.append(total_reco_charge)

        if len(purity_values) == 0 and len(ghost_charges) == 0:
            print(f"No valid purity vs charge data for event {event}")
            continue

        print(f"Event {event} ({input_file_name}):")
        print(f"  Plotting {len(purity_values)} matched clusters")
        if len(ghost_charges) > 0:
            print(f"  Ghost clusters (unmatched): {len(ghost_charges)}")
        if len(reco_charge_values) > 0:
            print(f"  Reco charge range: {min(reco_charge_values):.2f} - {max(reco_charge_values):.2f} ADC")

    # Create 2D colz histogram
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))

    # 2D histogram
        h = ax1.hist2d(reco_charge_values, purity_values, bins=40, cmap='YlOrRd',
                        range=[[-100, max(reco_charge_values)*1.1], [-0.2, 1.05]])
        cbar1 = plt.colorbar(h[3], ax=ax1, label='Count')
        cbar1.set_label('Count', fontsize=16, fontweight='bold')
        cbar1.ax.tick_params(labelsize=14)

        ax1.scatter(reco_charge_values, purity_values, alpha=0.3, s=20, color='black', marker='.')

        ax1.set_xlim(-100, max(reco_charge_values)*1.1)
        ax1.set_ylim(-0.05, 1.05)

        ax1.set_xlabel('Reco Cluster Charge [ADC] Arbitrary Units', fontsize=18, fontweight='bold')
        ax1.set_ylabel('Purity', fontsize=18, fontweight='bold')
        ax1.set_title(f'2D Histogram: Purity vs Reco Charge (Event {event})', fontsize=18, fontweight='bold')
        ax1.tick_params(labelsize=14)
        ax1.grid(True, linestyle='--', alpha=0.3)

    # 1D projection
        n_bins = 20
        charge_bins = np.linspace(-100, max(reco_charge_values)*1.1, n_bins+1)
        bin_centers = (charge_bins[:-1] + charge_bins[1:]) / 2
        mean_purity_per_bin = []
        bin_counts = []

        for i in range(len(charge_bins)-1):
            mask = (np.array(reco_charge_values) >= charge_bins[i]) & (np.array(reco_charge_values) < charge_bins[i+1])
            if np.sum(mask) > 0:
                mean_pur = np.mean(np.array(purity_values)[mask])
                count = np.sum(mask)
                mean_purity_per_bin.append(mean_pur)
                bin_counts.append(count)
            else:
                mean_purity_per_bin.append(0)
                bin_counts.append(0)

        non_empty_mask = np.array(bin_counts) > 0
        valid_bin_centers = bin_centers[non_empty_mask]
        valid_mean_purity = np.array(mean_purity_per_bin)[non_empty_mask]

        if len(valid_bin_centers) > 0:
            ax2.plot(valid_bin_centers, valid_mean_purity, 'o-', linewidth=3, markersize=12,
                    color='darkblue', label='Mean Purity per Bin')

        ax2.set_xlim(0, max(reco_charge_values)*1.1)
        ax2.set_ylim(-0.05, 1.05)

        ax2.set_xlabel('Reco Cluster Charge [ADC] Arbitrary Units', fontsize=18, fontweight='bold')
        ax2.set_ylabel('Purity', fontsize=18, fontweight='bold')
        ax2.set_title(f'1D Projection: Mean Purity vs Reco Charge (Event {event})', fontsize=18, fontweight='bold')
        ax2.tick_params(labelsize=14)
        ax2.grid(True, linestyle='--', alpha=0.3)
        ax2.legend(fontsize=14, loc='lower right')

        plt.tight_layout()
        plt.savefig(event_output_dir / f"purity_vs_reco_charge_{apa}.png", dpi=150, bbox_inches='tight', pad_inches=0.3)
        plt.close()
        print(f"  Saved: {event_output_dir}/purity_vs_reco_charge_{apa}.png")

def DrawPurityVsRecoChargeAllEvents(all_purity_results, input_directories_map, output_dir, apa):

    """
    Draw 2D colz histogram of purity vs RECO cluster charge for ALL events.
    Saves organized in hierarchy: output_dir/input_file/event_N/purity/
    X-axis: total RECO cluster charge (sum of point charges)
    Y-axis: purity

    """

    # Group results by event
    results_by_event = {}
    for result in all_purity_results:

    # Parse composite event key: "input_file_name_event_number"
        event_key = result['event']
        if isinstance(event_key, str) and '_' in event_key:
            event = int(event_key.rsplit('_', 1)[1])  # Get last part after final underscore
        else:
            event = int(event_key)
        if event not in results_by_event:
            results_by_event[event] = []
        results_by_event[event].append(result)

    output_dir = Path(output_dir)

    for event, event_results in results_by_event.items():

    # result['event'] is already the composite key like "file1_0"

    # Use it directly for lookup
        event_key = str(result['event']) if result['event'] not in input_directories_map else result['event']

    # Try composite key first, then extract event number
        if event_key not in input_directories_map:

    # Fallback: extract event number and search
            for key in input_directories_map:
                if isinstance(key, str) and f"_{event}" in key:
                    event_key = key
                    break

        if event_key not in input_directories_map:
            print(f"Warning: No input directory found for event {event}, skipping purity plots")
            continue

        input_dir, evt_num = input_directories_map[event_key]

        input_file_name = input_dir.parent.name

    # Create hierarchical directory: output_dir/input_file/event_N/purity/
        event_output_dir = output_dir / input_file_name / f"event_{event:03d}" / "purity"
        event_output_dir.mkdir(parents=True, exist_ok=True)

    # Extract purity and reco cluster charge
        purity_values = []
        reco_charge_values = []
        ghost_charges = []

        for result in event_results:
            purity = result['purity']
            total_reco_charge = result['total_reco_cluster_charge']

            if total_reco_charge > 0:

    # Check for unmatched clusters (purity=-0.1 sentinel)
                if abs(purity - (-0.1)) < 0.001:
                    ghost_charges.append(total_reco_charge)
                elif purity > 0:
                    purity_values.append(purity)
                    reco_charge_values.append(total_reco_charge)

        if len(purity_values) == 0 and len(ghost_charges) == 0:
            print(f"No valid purity vs charge data for event {event}")
            continue

        print(f"Event {event} ({input_file_name}):")
        print(f"  Plotting {len(purity_values)} matched clusters")
        if len(ghost_charges) > 0:
            print(f"  Ghost clusters (unmatched): {len(ghost_charges)}")
        if len(reco_charge_values) > 0:
            print(f"  Reco charge range: {min(reco_charge_values):.2f} - {max(reco_charge_values):.2f} ADC")

    # Create 2D colz histogram
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))

    # 2D histogram
        h = ax1.hist2d(reco_charge_values, purity_values, bins=40, cmap='YlOrRd',
                        range=[[-100, max(reco_charge_values)*1.1], [-0.2, 1.05]])
        cbar1 = plt.colorbar(h[3], ax=ax1, label='Count')
        cbar1.set_label('Count', fontsize=16, fontweight='bold')
        cbar1.ax.tick_params(labelsize=14)

        ax1.scatter(reco_charge_values, purity_values, alpha=0.3, s=20, color='black', marker='.')

        ax1.set_xlim(-100, max(reco_charge_values)*1.1)
        ax1.set_ylim(-0.05, 1.05)

        ax1.set_xlabel('Reco Cluster Charge [ADC] Arbitrary Units', fontsize=18, fontweight='bold')
        ax1.set_ylabel('Purity', fontsize=18, fontweight='bold')
        ax1.set_title(f'2D Histogram: Purity vs Reco Charge (Event {event})', fontsize=18, fontweight='bold')
        ax1.tick_params(labelsize=14)
        ax1.grid(True, linestyle='--', alpha=0.3)

    # 1D projection
        n_bins = 20
        charge_bins = np.linspace(-100, max(reco_charge_values)*1.1, n_bins+1)
        bin_centers = (charge_bins[:-1] + charge_bins[1:]) / 2
        mean_purity_per_bin = []
        bin_counts = []

        for i in range(len(charge_bins)-1):
            mask = (np.array(reco_charge_values) >= charge_bins[i]) & (np.array(reco_charge_values) < charge_bins[i+1])
            if np.sum(mask) > 0:
                mean_pur = np.mean(np.array(purity_values)[mask])
                count = np.sum(mask)
                mean_purity_per_bin.append(mean_pur)
                bin_counts.append(count)
            else:
                mean_purity_per_bin.append(0)
                bin_counts.append(0)

        non_empty_mask = np.array(bin_counts) > 0
        valid_bin_centers = bin_centers[non_empty_mask]
        valid_mean_purity = np.array(mean_purity_per_bin)[non_empty_mask]

        if len(valid_bin_centers) > 0:
            ax2.plot(valid_bin_centers, valid_mean_purity, 'o-', linewidth=3, markersize=12,
                    color='darkblue', label='Mean Purity per Bin')

        ax2.set_xlim(0, max(reco_charge_values)*1.1)
        ax2.set_ylim(-0.05, 1.05)

        ax2.set_xlabel('Reco Cluster Charge [ADC] Arbitrary Units', fontsize=18, fontweight='bold')
        ax2.set_ylabel('Purity', fontsize=18, fontweight='bold')
        ax2.set_title(f'1D Projection: Mean Purity vs Reco Charge (Event {event})', fontsize=18, fontweight='bold')
        ax2.tick_params(labelsize=14)
        ax2.grid(True, linestyle='--', alpha=0.3)
        ax2.legend(fontsize=14, loc='lower right')

        plt.tight_layout()
        plt.savefig(event_output_dir / f"purity_vs_reco_charge_{apa}.png", dpi=150, bbox_inches='tight', pad_inches=0.3)
        plt.close()
        print(f"  Saved: {event_output_dir}/purity_vs_reco_charge_{apa}.png")

def DrawEfficiencySummaryPerFile(all_efficiency_results, input_directories_map, output_dir):
    """
    Draw summary 2D and 1D plots aggregating efficiency across ALL events within EACH file.
    Saves to: output_dir/input_file/SUMMARY_efficiency/
    """

    # Group results by file
    results_by_file = {}
    for result in all_efficiency_results:
        event_key = result['event']
        # Extract file name from event_key (format: "input_file_name_event_num")
        if isinstance(event_key, str) and '_' in event_key:
            file_name = event_key.rsplit('_', 1)[0]
        else:
            continue

        if file_name not in results_by_file:
            results_by_file[file_name] = []
        results_by_file[file_name].append(result)

    output_dir = Path(output_dir)

    # Create summary plots for each file
    for file_name, file_results in results_by_file.items():
        # Extract efficiency and energy data for this file
        true_energies = []
        efficiencies = []
        ghost_energies = []

        for result in file_results:
            true_energy = result.get('total_true_cluster_energy', 0)
            efficiency = result.get('efficiency_energy_weighted', 0)

            if true_energy > 0:
                if efficiency > 0:
                    true_energies.append(true_energy)
                    efficiencies.append(efficiency)
                else:
                    ghost_energies.append(true_energy)

        if len(true_energies) == 0:
            print(f"No valid efficiency data for file {file_name}")
            continue

        print(f"\nFile Summary: Efficiency for {file_name}")
        print(f"  Total matched clusters: {len(true_energies)}")
        print(f"  Ghost tracks: {len(ghost_energies)}")

        # Create output directory: output_dir/input_file/SUMMARY_efficiency/
        file_output_dir = output_dir / file_name / "SUMMARY_efficiency"
        file_output_dir.mkdir(parents=True, exist_ok=True)

        # Create 2D and 1D plots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))

        # 2D histogram
        h = ax1.hist2d(true_energies, efficiencies, bins=40, cmap='YlOrRd',
                        range=[[0, max(true_energies)*1.25], [0, 1.05]])
        cbar1 = plt.colorbar(h[3], ax=ax1, label='Count')
        cbar1.set_label('Count', fontsize=16, fontweight='bold')
        cbar1.ax.tick_params(labelsize=14)

        ax1.scatter(true_energies, efficiencies, alpha=0.3, s=20, color='black', marker='.')

        if len(ghost_energies) > 0:
            ghost_y = np.full_like(ghost_energies, -0.1)
            ax1.scatter([-50]*len(ghost_energies), ghost_y, c='purple', s=30, alpha=0.6, marker='X',
                        label=f'Ghost Tracks ({len(ghost_energies)})', edgecolors='darkviolet', linewidth=1)

        ax1.set_xlim(-100, max(true_energies)*1.25)
        ax1.set_ylim(-0.2, 1.05)
        ax1.axvline(x=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax1.set_xlabel('True Cluster Energy [MeV]', fontsize=18, fontweight='bold')
        ax1.set_ylabel('Efficiency (Energy-Weighted)', fontsize=18, fontweight='bold')
        ax1.set_title(f'File Summary: Efficiency vs True Energy ({file_name})', fontsize=18, fontweight='bold')
        ax1.tick_params(labelsize=14)
        ax1.grid(True, linestyle='--', alpha=0.3)
        if len(ghost_energies) > 0:
            ax1.legend(fontsize=12, loc='upper left')

        # 1D projection
        n_bins = 20
        energy_bins = np.linspace(0, max(true_energies)*1.25, n_bins+1)
        bin_centers = (energy_bins[:-1] + energy_bins[1:]) / 2
        mean_efficiency_per_bin = []
        bin_counts = []

        for i in range(len(energy_bins)-1):
            mask = (np.array(true_energies) >= energy_bins[i]) & (np.array(true_energies) < energy_bins[i+1])
            if np.sum(mask) > 0:
                mean_eff = np.mean(np.array(efficiencies)[mask])
                count = np.sum(mask)
                mean_efficiency_per_bin.append(mean_eff)
                bin_counts.append(count)
            else:
                mean_efficiency_per_bin.append(0)
                bin_counts.append(0)

        # Plot 1D projection
        ax2.bar(bin_centers, mean_efficiency_per_bin, width=energy_bins[1]-energy_bins[0],
                alpha=0.7, color='steelblue', edgecolor='black')

        # Add count labels on bars
        for i, (x, y, count) in enumerate(zip(bin_centers, mean_efficiency_per_bin, bin_counts)):
            if count > 0:
                ax2.text(x, y + 0.03, f'n={int(count)}', ha='center', fontsize=10, fontweight='bold')

        ax2.set_xlabel('True Cluster Energy [MeV]', fontsize=18, fontweight='bold')
        ax2.set_ylabel('Mean Efficiency', fontsize=18, fontweight='bold')
        ax2.set_title(f'File Summary: Mean Efficiency vs Energy Bins ({file_name})', fontsize=18, fontweight='bold')
        ax2.set_ylim(0, 1.1)
        ax2.tick_params(labelsize=14)
        ax2.grid(True, linestyle='--', alpha=0.3, axis='y')

        plt.tight_layout()

        # Save plot
        filename = f"efficiency_summary_{file_name}.png"
        plt.savefig(file_output_dir / filename, dpi=100, bbox_inches='tight', pad_inches=0.3)
        plt.close()



def DrawPuritySummaryPerFile(all_purity_results, input_directories_map, output_dir):
    """
    Draw summary 2D and 1D plots aggregating purity across ALL events within EACH file.
    Saves to: output_dir/input_file/SUMMARY_purity/
    """

    # Group results by file
    results_by_file = {}
    for result in all_purity_results:
        event_key = result['event']
        # Extract file name from event_key (format: "input_file_name_event_num")
        if isinstance(event_key, str) and '_' in event_key:
            file_name = event_key.rsplit('_', 1)[0]
        else:
            continue

        if file_name not in results_by_file:
            results_by_file[file_name] = []
        results_by_file[file_name].append(result)

    output_dir = Path(output_dir)

    # Create summary plots for each file
    for file_name, file_results in results_by_file.items():
        # Extract purity and charge data for this file
        reco_charges = []
        purities = []
        noise_charges = []

        for result in file_results:
            reco_charge = result.get('total_reco_cluster_charge', 0)
            purity = result.get('purity', 0)

            if reco_charge > 0:
                if purity > 0:
                    reco_charges.append(reco_charge)
                    purities.append(purity)
                else:
                    noise_charges.append(reco_charge)

        if len(reco_charges) == 0:
            print(f"No valid purity data for file {file_name}")
            continue

        print(f"\nFile Summary: Purity for {file_name}")
        print(f"  Total matched clusters: {len(reco_charges)}")
        print(f"  Noise tracks: {len(noise_charges)}")

        # Create output directory: output_dir/input_file/SUMMARY_purity/
        file_output_dir = output_dir / file_name / "SUMMARY_purity"
        file_output_dir.mkdir(parents=True, exist_ok=True)

        # Create 2D and 1D plots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))

        # 2D histogram
        h = ax1.hist2d(reco_charges, purities, bins=40, cmap='YlOrRd',
                        range=[[0, max(reco_charges)*1.25], [0, 1.05]])
        cbar1 = plt.colorbar(h[3], ax=ax1, label='Count')
        cbar1.set_label('Count', fontsize=16, fontweight='bold')
        cbar1.ax.tick_params(labelsize=14)

        ax1.scatter(reco_charges, purities, alpha=0.3, s=20, color='black', marker='.')

        if len(noise_charges) > 0:
            noise_y = np.full_like(noise_charges, -0.1)
            ax1.scatter([-50]*len(noise_charges), noise_y, c='purple', s=30, alpha=0.6, marker='X',
                        label=f'Noise ({len(noise_charges)})', edgecolors='darkviolet', linewidth=1)

        ax1.set_xlim(-100, max(reco_charges)*1.25)
        ax1.set_ylim(-0.2, 1.05)
        ax1.axvline(x=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax1.set_xlabel('Reco Cluster Charge [ADC]', fontsize=18, fontweight='bold')
        ax1.set_ylabel('Purity', fontsize=18, fontweight='bold')
        ax1.set_title(f'File Summary: Purity vs Reco Charge ({file_name})', fontsize=18, fontweight='bold')
        ax1.tick_params(labelsize=14)
        ax1.grid(True, linestyle='--', alpha=0.3)
        if len(noise_charges) > 0:
            ax1.legend(fontsize=12, loc='upper left')

        # 1D projection
        n_bins = 20
        charge_bins = np.linspace(0, max(reco_charges)*1.25, n_bins+1)
        bin_centers = (charge_bins[:-1] + charge_bins[1:]) / 2
        mean_purity_per_bin = []
        bin_counts = []

        for i in range(len(charge_bins)-1):
            mask = (np.array(reco_charges) >= charge_bins[i]) & (np.array(reco_charges) < charge_bins[i+1])
            if np.sum(mask) > 0:
                mean_pur = np.mean(np.array(purities)[mask])
                count = np.sum(mask)
                mean_purity_per_bin.append(mean_pur)
                bin_counts.append(count)
            else:
                mean_purity_per_bin.append(0)
                bin_counts.append(0)

        # Plot 1D projection
        ax2.bar(bin_centers, mean_purity_per_bin, width=charge_bins[1]-charge_bins[0],
                alpha=0.7, color='steelblue', edgecolor='black')

        # Add count labels on bars
        for i, (x, y, count) in enumerate(zip(bin_centers, mean_purity_per_bin, bin_counts)):
            if count > 0:
                ax2.text(x, y + 0.03, f'n={int(count)}', ha='center', fontsize=10, fontweight='bold')

        ax2.set_xlabel('Reco Cluster Charge [ADC]', fontsize=18, fontweight='bold')
        ax2.set_ylabel('Mean Purity', fontsize=18, fontweight='bold')
        ax2.set_title(f'File Summary: Mean Purity vs Charge Bins ({file_name})', fontsize=18, fontweight='bold')
        ax2.set_ylim(0, 1.1)
        ax2.tick_params(labelsize=14)
        ax2.grid(True, linestyle='--', alpha=0.3, axis='y')

        plt.tight_layout()

        # Save plot
        filename = f"purity_summary_{file_name}.png"
        plt.savefig(file_output_dir / filename, dpi=100, bbox_inches='tight', pad_inches=0.3)
        plt.close()



