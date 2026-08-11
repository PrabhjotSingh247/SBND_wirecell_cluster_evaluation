import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import seaborn as sns
from pathlib import Path

def _draw_empty_placeholder(message, title, output_path, xlabel=None, ylabel=None):
    """
    Save a plot-shaped placeholder saying why there is nothing to draw.

    An event can legitimately contain no true-reco match at all -- e.g. with the
    beam-window cut on, an event whose reco clusters are all out of spill leaves
    every true cluster unmatched (completeness 0, reco id 8888). That is a real
    result, not an error, so the plot for it is still written: a missing file is
    indistinguishable from a crashed job when scanning an output tree.
    """
    plt.figure(figsize=(10, 8))
    plt.text(0.5, 0.5, message, ha='center', va='center', fontsize=13, wrap=True)
    plt.title(title, wrap=True)
    if xlabel:
        plt.xlabel(xlabel)
    if ylabel:
        plt.ylabel(ylabel)
    plt.xticks([])
    plt.yticks([])
    plt.savefig(output_path)
    plt.close()


def plot_completeness_heatmap(completeness_results, event, apa, output_dir, file_name=None):
    """Plot energy-weighted completeness values as a heatmap for visual inspection of cluster matching."""
    output_path = output_dir / f"completeness_energy_weighted_evt_{event}_{apa}.png"
    title = f"Energy-Weighted Completeness: Event {event}, {apa}"
    if file_name:
        title += f" ({file_name})"

    # No completeness rows at all (no true cluster survived the cuts)
    if not completeness_results:
        _draw_empty_placeholder("No true clusters in this event", title, output_path,
                                "Reco Cluster ID", "True Cluster ID")
        return

    df = pd.DataFrame(completeness_results)
    completeness_matrix = df.pivot_table(
        index='true_cluster_id',
        columns='reco_cluster_id',
        values='completeness_energy_weighted',
        fill_value=0
    )

    # avoid to draw reco cluster if it's id is 8888 (sentinel for unmatched)
    completeness_matrix = completeness_matrix.loc[:, completeness_matrix.columns != 8888]

    # Every true cluster went unmatched, so 8888 was the only column and the matrix
    # is now empty -- seaborn's heatmap raises on a zero-size array. Draw the
    # placeholder instead of failing the whole job.
    if completeness_matrix.empty or completeness_matrix.shape[1] == 0:
        _draw_empty_placeholder(
            f"No true-reco matches in this event\n({len(df['true_cluster_id'].unique())} true cluster(s), all unmatched, completeness = 0)",
            title, output_path, "Reco Cluster ID", "True Cluster ID")
        return

    plt.figure(figsize=(10, 8))
    sns.heatmap(completeness_matrix, annot=True, fmt=".2f", cmap="YlGnBu",
                xticklabels=[f"{int(x):d}" for x in completeness_matrix.columns],
                yticklabels=[f"{int(y):d}" for y in completeness_matrix.index])
    plt.title(title, wrap=True)
    plt.xlabel("Reco Cluster ID")
    plt.ylabel("True Cluster ID")
    plt.savefig(output_path)
    plt.close()
    ##plt.show(block=False)

def plot_purity_heatmap(purity_results, event, apa, output_dir, file_name=None):
    """Plot purity values as a heatmap for visual inspection of cluster matching."""
    output_path = output_dir / f"purity_evt_{event}_{apa}.png"
    title = f"Purity: Event {event}, {apa}"
    if file_name:
        title += f" ({file_name})"

    # No purity rows at all -- no reco cluster survived the cuts (see EvaluatePurity)
    if not purity_results:
        _draw_empty_placeholder("No reco clusters in this event", title, output_path,
                                "Reco Cluster ID", "True Cluster ID")
        return

    df = pd.DataFrame(purity_results)
    purity_matrix = df.pivot_table(
        index='true_cluster_id',
        columns='reco_cluster_id',
        values='purity',
        fill_value=0
    )

    # avoid to draw reco cluster if it's id is 8888 (sentinel for unmatched)
    purity_matrix = purity_matrix.loc[:, purity_matrix.columns != 8888]

    # Same zero-size guard as the completeness heatmap: every reco cluster unmatched
    # (true_cluster_id=8888) leaves nothing to draw.
    if purity_matrix.empty or purity_matrix.shape[1] == 0:
        _draw_empty_placeholder(
            f"No true-reco matches in this event\n({len(df['reco_cluster_id'].unique())} reco cluster(s), all unmatched)",
            title, output_path, "Reco Cluster ID", "True Cluster ID")
        return

    plt.figure(figsize=(10, 8))
    sns.heatmap(purity_matrix, annot=True, fmt=".2f", cmap="YlGnBu",
                xticklabels=[f"{int(x):d}" for x in purity_matrix.columns],
                yticklabels=[f"{int(y):d}" for y in purity_matrix.index])
    plt.title(title, wrap=True)
    plt.xlabel("Reco Cluster ID")
    plt.ylabel("True Cluster ID")
    plt.savefig(output_path)
    plt.close()
    ##plt.show(block=False)

def plot_2d_completeness_energy(energies, completenesses, output_dir, event, apa, category_name="All Clusters", file_name=None, num_events=None, num_clusters=None):
    """
    Draw 2D histogram of Completeness vs True Energy for a cluster category.
    Returns the energies and completenesses lists for use in 1D projections.

    Args:
        energies: List of energy values
        completenesses: List of completeness values
        output_dir: Output directory for saving plots
        event: Event number (for single event) or 0 (for aggregated data)
        apa: APA number
        category_name: Name of cluster category for title
        file_name: Optional file name for title
        num_events: Optional number of events aggregated (if provided, shows event count instead of event number)
        num_clusters: Optional number of true clusters that went into this plot (shown alongside num_events)
    """
    if not energies or not completenesses:
        return energies, completenesses

    plt.figure(figsize=(10, 8))
    x_bin_size = 50  # MeV
    xbins = np.arange(0, max(energies) + x_bin_size, x_bin_size)
    y_bin_size = 0.05
    ybins = np.arange(0, 1 + y_bin_size, y_bin_size)

    plt.hist2d(energies, completenesses, bins=[xbins, ybins], cmap='YlGnBu')
    plt.colorbar(label='Count')
    plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
    plt.ylabel('Completeness', fontsize=12, fontweight='bold')

    # Create title based on whether this is a single event or aggregated data
    if num_events is not None:
        title = f'Completeness vs True Energy (2D) - {category_name} - {num_events} events, {apa}'
        if num_clusters is not None:
            title += f', {num_clusters} true clusters'
    else:
        title = f'Completeness vs True Energy (2D) - {category_name} - Event {event}, {apa}'
    if file_name:
        title += f' ({file_name})'
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.xlim(0, max(energies)*1.1)
    plt.ylim(-0.05, 1.05)

    # Save with appropriate filename based on category
    category_suffix = category_name.lower().replace(' ', '_').replace('_clusters', '')
    if num_events is not None:
        filename = f"completeness_vs_true_energy_2d_{category_suffix}_{num_events}events_{apa}.png"
        if num_clusters is not None:
            filename = f"completeness_vs_true_energy_2d_{category_suffix}_{num_events}events_{num_clusters}trueclusters_{apa}.png"
    else:
        filename = f"completeness_vs_true_energy_2d_{category_suffix}_event_{event}_{apa}.png"
    plt.savefig(output_dir / filename, dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()

    return energies, completenesses

def plot_1d_completeness_energy(energies, completenesses, energy_bins):
    """
    Create 1D projection by binning energy and averaging completeness values.
    Returns bin centers and mean completenesses for plotting.
    """
    if not energies or not completenesses:
        return [], []

    bin_centers = (energy_bins[:-1] + energy_bins[1:]) / 2
    bin_centers_nonzero = []
    mean_completeness_per_bin = []

    for i in range(len(energy_bins)-1):
        mask = (np.array(energies) >= energy_bins[i]) & (np.array(energies) < energy_bins[i+1])
        if np.sum(mask) > 0:
            mean_eff = np.mean(np.array(completenesses)[mask])
            mean_completeness_per_bin.append(mean_eff)
            bin_centers_nonzero.append(bin_centers[i])

    return bin_centers_nonzero, mean_completeness_per_bin


# Styles for the single-population 1D completeness plots below. Only two entries:
# these are the neutrino/cosmic split, coarser than the four-way by-category
# breakdown (neutrino + isochronous/normal/prolonged cosmic) drawn elsewhere.
# 'neutrino' reuses the by-category plots' purple/D so the same population looks
# the same wherever it appears.
# Upper limit of the true-energy axis on every 1D completeness plot, in MeV. One
# constant rather than a literal per plot so the 1D plots always share a scale and
# can be read against each other. Raised from 3000: real clusters live past it
# (this dataset reaches ~3060 MeV) and a fixed limit silently cuts them off the
# right-hand edge rather than showing an empty tail. The 2D plots are unaffected --
# they scale to their own data.
TRUE_ENERGY_XMAX_MEV = 5000

POPULATION_STYLES = {
    'neutrino': {'label': 'Neutrino Clusters', 'color': 'purple',     'marker': 'D'},
    'cosmic':   {'label': 'Cosmic Clusters',   'color': 'darkorange', 'marker': 's'},
}


def _draw_1d_completeness_single_population(energies, completenesses, energy_bins, population,
                                          output_dir, filename, title):
    """
    One 1D completeness-vs-true-energy curve for a SINGLE population -- neutrino-only or
    cosmic-only -- on its own canvas and its own file, alongside the "All Clusters"
    plot each caller already draws.

    Takes the caller's energy_bins rather than rebinning: the bins come from the full
    cluster population, so the neutrino-only, cosmic-only and all-cluster curves land
    on identical bin centres and can be read against each other directly. Rebinning per
    population would silently shift the points and make the three plots incomparable.

    Draws nothing at all when the population is empty. An empty canvas would read as
    "completeness is zero everywhere" rather than "there are no clusters of this kind",
    which is the more common case at event level -- most events have no neutrino.
    """
    if not energies:
        return

    bin_centers, mean_completeness = plot_1d_completeness_energy(energies, completenesses, energy_bins)
    if len(bin_centers) == 0:
        return

    style = POPULATION_STYLES[population]

    plt.figure(figsize=(12, 6))
    plt.plot(bin_centers, mean_completeness, marker=style['marker'], linestyle='-',
             linewidth=2.5, markersize=10, color=style['color'],
             label=f"{style['label']} ({len(energies)} clusters)",
             markeredgecolor='black', markeredgewidth=1)

    plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
    plt.ylabel('Completeness', fontsize=12, fontweight='bold')
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.xlim(0, TRUE_ENERGY_XMAX_MEV)
    plt.ylim(-0.05, 1.05)
    plt.savefig(output_dir / filename, dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()


def _draw_1d_purity_single_population(charges, purities, charge_bins, x_max, population,
                                      output_dir, filename, title):
    """
    Purity counterpart to _draw_1d_completeness_single_population: one 1D
    purity-vs-reco-charge curve for a SINGLE population -- neutrino-only or
    cosmic-only -- on its own canvas and file, alongside the "All Clusters" plot
    each caller already draws.

    Takes both the caller's charge_bins AND its x_max, since the purity plots scale
    the x-axis to the population (max(charges)*1.1) rather than using a fixed limit.
    Re-deriving either from the subset would shift the bin centres and rescale the
    axis, leaving three plots that look comparable but are not.

    Draws nothing when the population is empty -- see the completeness version for why
    a blank canvas would be actively misleading here.
    """
    if not charges:
        return

    bin_centers, mean_purity = plot_1d_purity_charge(charges, purities, charge_bins)
    if len(bin_centers) == 0:
        return

    style = POPULATION_STYLES[population]

    plt.figure(figsize=(12, 6))
    plt.plot(bin_centers, mean_purity, marker=style['marker'], linestyle='-',
             linewidth=2, markersize=10, color=style['color'],
             label=f"{style['label']} ({len(charges)} clusters)",
             markeredgecolor='black', markeredgewidth=1)

    plt.xlabel('Reco Cluster Charge [ADC] Arbitrary Units', fontsize=12, fontweight='bold')
    plt.ylabel('Purity', fontsize=12, fontweight='bold')
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.xlim(0, x_max)
    plt.ylim(-0.05, 1.05)
    plt.savefig(output_dir / filename, dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()


def plot_2d_purity_charge(charges, purities, output_dir, event, apa, category_name="All Clusters", file_name=None, num_events=None, num_clusters=None):
    """
    Draw 2D histogram of Purity vs Reco Cluster Charge for a cluster category.
    Returns the charges and purities lists for use in 1D projections.

    Args:
        charges: List of reco cluster charge values (ADC arbitrary units)
        purities: List of purity values
        output_dir: Output directory for saving plots
        event: Event number (for single event) or 0 (for aggregated data)
        apa: APA number
        category_name: Name of cluster category for title
        file_name: Optional file name for title
        num_events: Optional number of events aggregated (if provided, shows event count instead of event number)
        num_clusters: Optional number of reco clusters that went into this plot (shown alongside num_events)
    """
    if not charges or not purities:
        return charges, purities

    plt.figure(figsize=(10, 8))
    n_xbins = 20
    xbins = np.linspace(0, max(charges)*1.1, n_xbins+1)
    y_bin_size = 0.05
    ybins = np.arange(0, 1 + y_bin_size, y_bin_size)

    plt.hist2d(charges, purities, bins=[xbins, ybins], cmap='YlGnBu')
    plt.colorbar(label='Count')
    plt.xlabel('Reco Cluster Charge [ADC] Arbitrary Units', fontsize=12, fontweight='bold')
    plt.ylabel('Purity', fontsize=12, fontweight='bold')

    # Create title based on whether this is a single event or aggregated data
    if num_events is not None:
        title = f'Purity vs Reco Charge (2D) - {category_name} - {num_events} events, {apa}'
        if num_clusters is not None:
            title += f', {num_clusters} reco clusters'
    else:
        title = f'Purity vs Reco Charge (2D) - {category_name} - Event {event}, {apa}'
    if file_name:
        title += f' ({file_name})'
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.xlim(0, max(charges)*1.1)
    plt.ylim(-0.05, 1.05)

    # Save with appropriate filename based on category
    category_suffix = category_name.lower().replace(' ', '_').replace('_clusters', '')
    if num_events is not None:
        filename = f"purity_vs_reco_charge_2d_{category_suffix}_{num_events}events_{apa}.png"
        if num_clusters is not None:
            filename = f"purity_vs_reco_charge_2d_{category_suffix}_{num_events}events_{num_clusters}recoclusters_{apa}.png"
    else:
        filename = f"purity_vs_reco_charge_2d_{category_suffix}_event_{event}_{apa}.png"
    plt.savefig(output_dir / filename, dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()

    return charges, purities

def plot_1d_purity_charge(charges, purities, charge_bins):
    """
    Create 1D projection by binning reco cluster charge and averaging purity values.
    Returns bin centers and mean purities for plotting.
    """
    if not charges or not purities:
        return [], []

    bin_centers = (charge_bins[:-1] + charge_bins[1:]) / 2
    bin_centers_nonzero = []
    mean_purity_per_bin = []

    for i in range(len(charge_bins)-1):
        mask = (np.array(charges) >= charge_bins[i]) & (np.array(charges) < charge_bins[i+1])
        if np.sum(mask) > 0:
            mean_pur = np.mean(np.array(purities)[mask])
            mean_purity_per_bin.append(mean_pur)
            bin_centers_nonzero.append(bin_centers[i])

    return bin_centers_nonzero, mean_purity_per_bin

def DrawCompletenessVsTrueEnergyPerEvent(completeness_results, output_dir, event, apa, file_name=None, cluster_category_results=None):
    """
    For each true cluster: calculate sum of completeness values,
    then plot completeness vs true cluster energy (2D and 1D).
    If cluster_category_results is provided, also plot separate lines for isochronous, normal, and prolonged clusters.
    """
    if not completeness_results:
        return

    # Group completeness by true cluster and calculate sum
    true_cluster_completeness = {}
    for eff in completeness_results:
        true_cid = eff['true_cluster_id']
        #if true_cid == 8888:  # Skip unmatched sentinel
        #    continue
        if true_cid not in true_cluster_completeness:
            true_cluster_completeness[true_cid] = {
                'total_completeness': 0,
                'total_energy': eff.get('total_true_cluster_energy', 0),
                'num_reco_matches': 0
            }

        true_cluster_completeness[true_cid]['total_completeness'] += eff['completeness_energy_weighted']
        true_cluster_completeness[true_cid]['num_reco_matches'] += 1

    if not true_cluster_completeness:
        return

    # Debug: Print information about true clusters and their matched reco clusters
    print_debug_info = False  # Set to False to disable debug printing
    if print_debug_info:
        print("\n" + "="*80)
        print(f"DEBUG: Completeness vs True Energy - Event {event}, {apa}")
        print("="*80)
        for true_cid in sorted(true_cluster_completeness.keys()):
            data = true_cluster_completeness[true_cid]
        print(f"\nTrue Cluster {true_cid:.0f}:")
        print(f"  Total Energy: {data['total_energy']:.3f} MeV")
        print(f"  Total Completeness (sum): {data['total_completeness']:.4f}")
        print(f"  Number of Matched Reco Clusters: {data['num_reco_matches']}")

        # Find and print individual completenesses for each true-reco match
        #print(f"  Individual True-Reco Matches:")
        for eff in completeness_results:
            if eff['true_cluster_id'] == true_cid and eff['true_cluster_id'] != 8888:
                reco_cid = eff.get('reco_cluster_id', 'N/A')
                eff_val = eff['completeness_energy_weighted']
                #print(f"    → Reco Cluster {reco_cid:.0f}: completeness = {eff_val:.4f}")
        print("="*80 + "\n")

    energies        = [data['total_energy']     for data in true_cluster_completeness.values()]
    completenesses    = [data['total_completeness'] for data in true_cluster_completeness.values()]

    # 2D Histogram for all clusters
    plot_2d_completeness_energy(energies, completenesses, output_dir, event, apa,
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

            # Get energies and completenesses for this category
            category_energies = [true_cluster_completeness[cid]['total_energy'] for cid in category_cluster_ids if cid in true_cluster_completeness]
            category_completenesses = [true_cluster_completeness[cid]['total_completeness'] for cid in category_cluster_ids if cid in true_cluster_completeness]

            # Draw 2D plot for this category
            if category_energies:
                plot_2d_completeness_energy(category_energies, category_completenesses, output_dir, event, apa,
                                         category_name=category_label, file_name=file_name)



    # Setup binning for 1D projections
    n_bins = 15
    if energies:
        energy_bins = np.linspace(0, max(energies)*1.1, n_bins+1)
    else:
        energy_bins = np.linspace(0, 10, n_bins+1)

    # 1D Plot 1: All clusters (separate canvas)
    bin_centers_all, mean_eff_all = plot_1d_completeness_energy(energies, completenesses, energy_bins)

    plt.figure(figsize=(12, 6))
    if len(bin_centers_all) > 0:
        plt.plot(bin_centers_all, mean_eff_all, 'o-', linewidth=2.5, markersize=10,
                color='darkblue', label='All Clusters', markeredgecolor='black', markeredgewidth=1)

    plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
    plt.ylabel('Completeness', fontsize=12, fontweight='bold')
    title = f'Completeness vs True Energy (1D Projection) - Event {event}, {apa}'
    if file_name:
        title += f' ({file_name})'
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.xlim(0, TRUE_ENERGY_XMAX_MEV)  # 1D true-energy axis limit, shared -- see the constant
    plt.ylim(-0.05, 1.05)
    plt.savefig(output_dir / f"completeness_vs_true_energy_1d_event_{event}_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    ##plt.show(block=False)
    plt.close()

    # 1D Plots: neutrino-only and cosmic-only, one canvas each, alongside the All
    # Clusters plot above. Same energy_bins as that plot -- built from the full
    # population -- so all three curves share bin centres and can be overlaid or
    # read side by side. This is the coarse two-way split; the four-way
    # neutrino/isochronous/normal/prolonged breakdown is the by_category plot.
    if cluster_category_results is not None:
        for _population in ('neutrino', 'cosmic'):
            _population_keys = [key for key, data in cluster_category_results.items()
                                if bool(data['is_neutrino']) == (_population == 'neutrino')
                                and key in true_cluster_completeness]
            _population_title = f'Completeness vs True Energy (1D Projection, {POPULATION_STYLES[_population]["label"]} Only) - Event {event}, {apa}'
            if file_name:
                _population_title += f' ({file_name})'
            _draw_1d_completeness_single_population(
                [true_cluster_completeness[key]['total_energy']     for key in _population_keys],
                [true_cluster_completeness[key]['total_completeness'] for key in _population_keys],
                energy_bins, _population, output_dir,
                f"completeness_vs_true_energy_1d_{_population}_event_{event}_{apa}.png", _population_title)

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

            # Get energies and completenesses for this category
            category_energies = [true_cluster_completeness[cid]['total_energy'] for cid in category_cluster_ids if cid in true_cluster_completeness]
            category_completenesses = [true_cluster_completeness[cid]['total_completeness'] for cid in category_cluster_ids if cid in true_cluster_completeness]

            if category_energies:
                # Get 1D projection for this category
                bin_centers_cat, mean_eff_cat = plot_1d_completeness_energy(category_energies, category_completenesses, energy_bins)

                if len(bin_centers_cat) > 0:
                    color = info['color']
                    marker = info['marker']
                    label_text = f"{info['label']} ({len(category_cluster_ids)} clusters)"
                    plt.plot(bin_centers_cat, mean_eff_cat, marker=marker, linestyle='-', linewidth=2, markersize=8,
                            color=color, label=label_text, markeredgecolor='black', markeredgewidth=0.5)

        plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
        plt.ylabel('Completeness', fontsize=12, fontweight='bold')
        title = f'Completeness vs True Energy (1D by Category) - Event {event}, {apa}'
        if file_name:
            title += f' ({file_name})'
        plt.title(title, fontsize=12, fontweight='bold', wrap=True)
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.legend(fontsize=10)
        plt.xlim(0, TRUE_ENERGY_XMAX_MEV)
        plt.ylim(-0.05, 1.05)
        plt.savefig(output_dir / f"completeness_vs_true_energy_1d_by_category_event_{event}_{apa}.png",
                    dpi=100, bbox_inches='tight', pad_inches=0.3)
        plt.close()


def _combine_pairs_with_unmatched(pair_metadata_list, all_true_metadata_list):
    """
    Combine 1-to-1 matched true-reco pair metadata with true clusters that never matched
    any reco cluster (present in all_true_metadata_list, from add_metadata_true_clusters,
    but absent from pair_metadata_list). Unmatched true clusters are added with
    completeness=0, so completeness-vs-true-energy plots reflect the full true cluster
    population instead of silently dropping the ones that never found a reco match.
    """
    if not all_true_metadata_list:
        return list(pair_metadata_list)

    matched_keys = {(m['event'], m['true_cluster_id']) for m in pair_metadata_list}
    unmatched_entries = [
        {
            'event': m['event'],
            'true_cluster_id': m['true_cluster_id'],
            'cluster_type': m['cluster_type'],
            'cluster_category': m['cluster_category'],
            'completeness': 0,
            'total_true_energy': m['total_true_energy'],
        }
        for m in all_true_metadata_list
        if (m['event'], m['true_cluster_id']) not in matched_keys
    ]
    return list(pair_metadata_list) + unmatched_entries


def DrawClusterCompletenessVsTrueEnergyPerEvent(pair_metadata_list, output_dir, event, apa, file_name=None, all_true_metadata_list=None):
    """
    For each 1-to-1 true-reco pair (from add_metadata_true_reco_pair_cluster), plot completeness
    vs true cluster energy (2D and 1D), for all clusters and broken down by cluster category
    (neutrino, isochronous/normal/prolonged cosmic).

    If all_true_metadata_list is provided (from add_metadata_true_clusters), true clusters
    that never matched any reco cluster are included as well with completeness=0.
    """
    all_entries = _combine_pairs_with_unmatched(pair_metadata_list, all_true_metadata_list)
    if not all_entries:
        return

    def _in_category(metadata, category_key):
        if category_key == 'neutrino':
            return metadata['cluster_type'] == 'neutrino'
        return metadata['cluster_type'] == 'cosmic' and metadata['cluster_category'] == category_key.replace('_cosmic', '')

    energies        = [m['total_true_energy'] for m in all_entries]
    completenesses    = [m['completeness'] for m in all_entries]

    # 2D Histogram for all clusters
    plot_2d_completeness_energy(energies, completenesses, output_dir, event, apa,
                             category_name="All Clusters ClusteringLevel", file_name=file_name)

    # 2D plots by category
    category_styles = {
        'neutrino': 'Neutrino Clusters ClusteringLevel',
        'isochronous_cosmic': 'Isochronous Cosmic Clusters ClusteringLevel',
        'normal_cosmic': 'Normal Cosmic Clusters ClusteringLevel',
        'prolonged_cosmic': 'Prolonged Cosmic Clusters ClusteringLevel'
    }

    for category_key, category_label in category_styles.items():
        category_entries = [m for m in all_entries if _in_category(m, category_key)]
        if not category_entries:
            continue

        category_energies      = [m['total_true_energy'] for m in category_entries]
        category_completenesses  = [m['completeness'] for m in category_entries]
        plot_2d_completeness_energy(category_energies, category_completenesses, output_dir, event, apa,
                                 category_name=category_label, file_name=file_name)

    # Setup binning for 1D projections
    n_bins = 15
    if energies:
        energy_bins = np.linspace(0, max(energies)*1.1, n_bins+1)
    else:
        energy_bins = np.linspace(0, 10, n_bins+1)

    # 1D Plot 1: All clusters (separate canvas)
    bin_centers_all, mean_eff_all = plot_1d_completeness_energy(energies, completenesses, energy_bins)

    plt.figure(figsize=(12, 6))
    if len(bin_centers_all) > 0:
        plt.plot(bin_centers_all, mean_eff_all, 'o-', linewidth=2.5, markersize=10,
                color='darkblue', label='All Clusters', markeredgecolor='black', markeredgewidth=1)

    plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
    plt.ylabel('Completeness', fontsize=12, fontweight='bold')
    title = f'Completeness vs True Energy (1D Projection, ClusteringLevel) - Event {event}, {apa}'
    if file_name:
        title += f' ({file_name})'
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.xlim(0, TRUE_ENERGY_XMAX_MEV)
    plt.ylim(-0.05, 1.05)
    plt.savefig(output_dir / f"completeness_vs_true_energy_1d_clusteringlevel_event_{event}_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()

    # 1D Plots: neutrino-only and cosmic-only, one canvas each, alongside the All
    # Clusters plot above. Same energy_bins as that plot -- built from the full
    # population -- so all three curves share bin centres and can be overlaid or
    # read side by side. This is the coarse two-way split; the four-way
    # neutrino/isochronous/normal/prolonged breakdown is the by_category plot.
    for _population in ('neutrino', 'cosmic'):
        _population_entries = [m for m in all_entries if m['cluster_type'] == _population]
        _population_title = f'Completeness vs True Energy (1D Projection, ClusteringLevel, {POPULATION_STYLES[_population]["label"]} Only) - Event {event}, {apa}'
        if file_name:
            _population_title += f' ({file_name})'
        _draw_1d_completeness_single_population(
            [m['total_true_energy'] for m in _population_entries],
            [m['completeness'] for m in _population_entries],
            energy_bins, _population, output_dir,
            f"completeness_vs_true_energy_1d_{_population}_clusteringlevel_event_{event}_{apa}.png", _population_title)

    # 1D Plot 2: By category
    plt.figure(figsize=(14, 7))

    category_info = {
        'neutrino': {'label': 'Neutrino Clusters', 'color': 'purple', 'marker': 'D'},
        'isochronous_cosmic': {'label': 'Isochronous Cosmic', 'color': 'red', 'marker': 'o'},
        'normal_cosmic': {'label': 'Normal Cosmic', 'color': 'green', 'marker': 's'},
        'prolonged_cosmic': {'label': 'Prolonged Cosmic', 'color': 'blue', 'marker': '^'}
    }

    for category_key, info in category_info.items():
        category_entries = [m for m in all_entries if _in_category(m, category_key)]
        if not category_entries:
            continue

        category_energies      = [m['total_true_energy'] for m in category_entries]
        category_completenesses  = [m['completeness'] for m in category_entries]

        bin_centers_cat, mean_eff_cat = plot_1d_completeness_energy(category_energies, category_completenesses, energy_bins)
        if len(bin_centers_cat) > 0:
            label_text = f"{info['label']} ({len(category_entries)} clusters)"
            plt.plot(bin_centers_cat, mean_eff_cat, marker=info['marker'], linestyle='-', linewidth=2, markersize=8,
                    color=info['color'], label=label_text, markeredgecolor='black', markeredgewidth=0.5)

    plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
    plt.ylabel('Completeness', fontsize=12, fontweight='bold')
    title = f'Completeness vs True Energy (1D by Category, ClusteringLevel) - Event {event}, {apa}'
    if file_name:
        title += f' ({file_name})'
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.xlim(0, TRUE_ENERGY_XMAX_MEV)
    plt.ylim(-0.05, 1.05)
    plt.savefig(output_dir / f"completeness_vs_true_energy_1d_by_category_clusteringlevel_event_{event}_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()


def DrawCompletenessVsTrueEnergyPerFile(completeness_results, output_dir, apa, file_name=None, cluster_category_results=None, file_metadata_list=None):
    """
    File-level version: For each true cluster calculate sum of completeness values,
    then plot completeness vs true cluster energy (2D and 1D) for all events in a file.
    If cluster_category_results or file_metadata_list is provided, also plot separate 2D and 1D plots for each cluster category.
    Note: Uses (event, true_cluster_id) composite key to ensure uniqueness across multiple events in a file.
    """
    if not completeness_results:
        return

    # Count unique events in this file
    unique_events = set()
    if file_metadata_list is not None:
        unique_events = set(m['event'] for m in file_metadata_list)
    else:
        unique_events = set(eff.get('event', 'unknown') for eff in completeness_results)
    num_events_in_file = len(unique_events)

    # Group completeness by (event, true_cluster_id) to ensure uniqueness across multiple events
    true_cluster_completeness = {}
    for eff in completeness_results:
        event_key = eff.get('event', 'unknown')
        true_cid = eff['true_cluster_id']
        cluster_key = (event_key, true_cid)

        if cluster_key not in true_cluster_completeness:
            true_cluster_completeness[cluster_key] = {
                'total_completeness': 0,
                'total_energy': eff.get('total_true_cluster_energy', 0),
                'num_reco_matches': 0
            }

        true_cluster_completeness[cluster_key]['total_completeness'] += eff['completeness_energy_weighted']
        true_cluster_completeness[cluster_key]['num_reco_matches'] += 1

    if not true_cluster_completeness:
        return

    energies        = [data['total_energy']     for data in true_cluster_completeness.values()]
    completenesses    = [data['total_completeness'] for data in true_cluster_completeness.values()]

    # 2D Histogram for all clusters
    plot_2d_completeness_energy(energies, completenesses, output_dir, 0, apa,
                             category_name="All Clusters (File Level)", file_name=file_name, num_events=num_events_in_file,
                             num_clusters=len(energies))

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
        print(f"    [FILE LEVEL] Drawing 2D completeness plots for categories...")
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

            # Get energies and completenesses for this category
            category_energies = [true_cluster_completeness[key]['total_energy'] for key in category_cluster_keys if key in true_cluster_completeness]
            category_completenesses = [true_cluster_completeness[key]['total_completeness'] for key in category_cluster_keys if key in true_cluster_completeness]

            print(f"        → Matched {len(category_energies)} clusters in completeness_results")

            # Draw 2D plot for this category
            if category_energies:
                print(f"        → Drawing 2D plot for {category_label}...")
                plot_2d_completeness_energy(category_energies, category_completenesses, output_dir, 0, apa,
                                         category_name=category_label, file_name=file_name, num_events=num_events_in_file,
                                         num_clusters=len(category_energies))
            else:
                print(f"        → No energies/completenesses found, skipping plot...")

    # Setup binning for 1D projections
    n_bins = 15
    if energies:
        energy_bins = np.linspace(0, max(energies)*1.1, n_bins+1)
    else:
        energy_bins = np.linspace(0, 10, n_bins+1)

    # 1D Plot: All clusters (separate canvas)
    bin_centers_all, mean_eff_all = plot_1d_completeness_energy(energies, completenesses, energy_bins)

    plt.figure(figsize=(12, 6))
    if len(bin_centers_all) > 0:
        plt.plot(bin_centers_all, mean_eff_all, 'o-', linewidth=2.5, markersize=10,
                color='darkblue', label='All Clusters', markeredgecolor='black', markeredgewidth=1)

    plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
    plt.ylabel('Completeness', fontsize=12, fontweight='bold')
    title = f'Completeness vs True Energy (1D Projection) - File Level, {apa}'
    if file_name:
        title += f' ({file_name})'
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.xlim(0, TRUE_ENERGY_XMAX_MEV)
    plt.ylim(-0.05, 1.05)
    plt.savefig(output_dir / f"completeness_vs_true_energy_1d_file_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()

    # 1D Plots: neutrino-only and cosmic-only, one canvas each, alongside the All
    # Clusters plot above. Same energy_bins as that plot -- built from the full
    # population -- so all three curves share bin centres and can be overlaid or
    # read side by side. This is the coarse two-way split; the four-way
    # neutrino/isochronous/normal/prolonged breakdown is the by_category plot.
    if category_info_source is not None:
        for _population in ('neutrino', 'cosmic'):
            _population_keys = [key for key, data in category_info_source.items()
                                if bool(data['is_neutrino']) == (_population == 'neutrino')
                                and key in true_cluster_completeness]
            _population_title = f'Completeness vs True Energy (1D Projection, {POPULATION_STYLES[_population]["label"]} Only) - File Level, {apa}'
            if file_name:
                _population_title += f' ({file_name})'
            _draw_1d_completeness_single_population(
                [true_cluster_completeness[key]['total_energy']     for key in _population_keys],
                [true_cluster_completeness[key]['total_completeness'] for key in _population_keys],
                energy_bins, _population, output_dir,
                f"completeness_vs_true_energy_1d_{_population}_file_{apa}.png", _population_title)

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

            # Get energies and completenesses for this category
            category_energies = [true_cluster_completeness[key]['total_energy'] for key in category_cluster_keys if key in true_cluster_completeness]
            category_completenesses = [true_cluster_completeness[key]['total_completeness'] for key in category_cluster_keys if key in true_cluster_completeness]

            if category_energies:
                # Get 1D projection for this category
                bin_centers_cat, mean_eff_cat = plot_1d_completeness_energy(category_energies, category_completenesses, energy_bins)

                if len(bin_centers_cat) > 0:
                    color = info['color']
                    marker = info['marker']
                    label_text = f"{info['label']} ({len(category_cluster_keys)} clusters)"
                    plt.plot(bin_centers_cat, mean_eff_cat, marker=marker, linestyle='-', linewidth=2, markersize=8,
                            color=color, label=label_text, markeredgecolor='black', markeredgewidth=0.5)

        plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
        plt.ylabel('Completeness', fontsize=12, fontweight='bold')
        title = f'Completeness vs True Energy (1D by Category) - File Level, {apa}'
        if file_name:
            title += f' ({file_name})'
        plt.title(title, fontsize=12, fontweight='bold', wrap=True)
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.legend(fontsize=10)
        plt.xlim(0, TRUE_ENERGY_XMAX_MEV)
        plt.ylim(-0.05, 1.05)
        plt.savefig(output_dir / f"completeness_vs_true_energy_1d_by_category_file_{apa}.png",
                    dpi=100, bbox_inches='tight', pad_inches=0.3)
        plt.close()


def DrawCompletenessVsTrueEnergyPerJob(completeness_results, output_dir, apa, cluster_category_results=None, job_metadata_list=None):
    """
    Job-level version: For each true cluster calculate sum of completeness values,
    then plot completeness vs true cluster energy (2D and 1D) for all events in all files.
    If cluster_category_results or job_metadata_list is provided, also plot separate 2D and 1D plots for each cluster category.
    Note: Uses (event, true_cluster_id) composite key to ensure uniqueness across all files and events.
    """
    if not completeness_results:
        return [], []

    # Count unique events across all files
    unique_events = set()
    if job_metadata_list is not None:
        unique_events = set(m['event'] for m in job_metadata_list)
    else:
        unique_events = set(eff.get('event', 'unknown') for eff in completeness_results)
    num_events_total = len(unique_events)

    # Group completeness by (event, true_cluster_id) to ensure uniqueness across all files and events
    true_cluster_completeness = {}
    for eff in completeness_results:
        event_key = eff.get('event', 'unknown')
        true_cid = eff['true_cluster_id']
        cluster_key = (event_key, true_cid)

        if cluster_key not in true_cluster_completeness:
            true_cluster_completeness[cluster_key] = {
                'total_completeness': 0,
                'total_energy': eff.get('total_true_cluster_energy', 0),
                'num_reco_matches': 0
            }

        true_cluster_completeness[cluster_key]['total_completeness'] += eff['completeness_energy_weighted']
        true_cluster_completeness[cluster_key]['num_reco_matches'] += 1

    if not true_cluster_completeness:
        return [], []

    energies        = [data['total_energy']     for data in true_cluster_completeness.values()]
    completenesses    = [data['total_completeness'] for data in true_cluster_completeness.values()]

    # 2D Histogram for all clusters
    plot_2d_completeness_energy(energies, completenesses, output_dir, 0, apa,
                             category_name="All Clusters (Job Level)", file_name=None, num_events=num_events_total,
                             num_clusters=len(energies))

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
        print(f"  [JOB LEVEL] Drawing 2D completeness plots for categories...")
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

            # Get energies and completenesses for this category
            category_energies = [true_cluster_completeness[key]['total_energy'] for key in category_cluster_keys if key in true_cluster_completeness]
            category_completenesses = [true_cluster_completeness[key]['total_completeness'] for key in category_cluster_keys if key in true_cluster_completeness]

            print(f"      → Matched {len(category_energies)} clusters in completeness_results")

            # Draw 2D plot for this category
            if category_energies:
                print(f"      → Drawing 2D plot for {category_label}...")
                plot_2d_completeness_energy(category_energies, category_completenesses, output_dir, 0, apa,
                                         category_name=category_label, file_name=None, num_events=num_events_total,
                                         num_clusters=len(category_energies))
            else:
                print(f"      → No energies/completenesses found, skipping plot...")

    # Setup binning for 1D projections
    n_bins = 15
    if energies:
        energy_bins = np.linspace(0, max(energies)*1.1, n_bins+1)
    else:
        energy_bins = np.linspace(0, 10, n_bins+1)

    # 1D Plot: All clusters (separate canvas)
    bin_centers_all, mean_eff_all = plot_1d_completeness_energy(energies, completenesses, energy_bins)

    plt.figure(figsize=(12, 6))
    if len(bin_centers_all) > 0:
        plt.plot(bin_centers_all, mean_eff_all, 'o-', linewidth=2.5, markersize=10,
                color='darkblue', label='All Clusters', markeredgecolor='black', markeredgewidth=1)

    plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
    plt.ylabel('Completeness', fontsize=12, fontweight='bold')
    title = f'Completeness vs True Energy (1D Projection) - Job Level, {apa}'
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.xlim(0, TRUE_ENERGY_XMAX_MEV)
    plt.ylim(-0.05, 1.05)
    plt.savefig(output_dir / f"completeness_vs_true_energy_1d_job_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()

    # 1D Plots: neutrino-only and cosmic-only, one canvas each, alongside the All
    # Clusters plot above. Same energy_bins as that plot -- built from the full
    # population -- so all three curves share bin centres and can be overlaid or
    # read side by side. This is the coarse two-way split; the four-way
    # neutrino/isochronous/normal/prolonged breakdown is the by_category plot.
    if category_info_source is not None:
        for _population in ('neutrino', 'cosmic'):
            _population_keys = [key for key, data in category_info_source.items()
                                if bool(data['is_neutrino']) == (_population == 'neutrino')
                                and key in true_cluster_completeness]
            _population_title = f'Completeness vs True Energy (1D Projection, {POPULATION_STYLES[_population]["label"]} Only) - Job Level, {apa}'
            _draw_1d_completeness_single_population(
                [true_cluster_completeness[key]['total_energy']     for key in _population_keys],
                [true_cluster_completeness[key]['total_completeness'] for key in _population_keys],
                energy_bins, _population, output_dir,
                f"completeness_vs_true_energy_1d_{_population}_job_{apa}.png", _population_title)

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

            # Get energies and completenesses for this category
            category_energies = [true_cluster_completeness[key]['total_energy'] for key in category_cluster_keys if key in true_cluster_completeness]
            category_completenesses = [true_cluster_completeness[key]['total_completeness'] for key in category_cluster_keys if key in true_cluster_completeness]

            if category_energies:
                # Get 1D projection for this category
                bin_centers_cat, mean_eff_cat = plot_1d_completeness_energy(category_energies, category_completenesses, energy_bins)

                if len(bin_centers_cat) > 0:
                    color = info['color']
                    marker = info['marker']
                    label_text = f"{info['label']} ({len(category_cluster_keys)} clusters)"
                    plt.plot(bin_centers_cat, mean_eff_cat, marker=marker, linestyle='-', linewidth=2, markersize=8,
                            color=color, label=label_text, markeredgecolor='black', markeredgewidth=0.5)

        plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
        plt.ylabel('Completeness', fontsize=12, fontweight='bold')
        title = f'Completeness vs True Energy (1D by Category) - Job Level, {apa}'
        plt.title(title, fontsize=12, fontweight='bold', wrap=True)
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.legend(fontsize=10)
        plt.xlim(0, TRUE_ENERGY_XMAX_MEV)
        plt.ylim(-0.05, 1.05)
        plt.savefig(output_dir / f"completeness_vs_true_energy_1d_by_category_job_{apa}.png",
                    dpi=100, bbox_inches='tight', pad_inches=0.3)
        plt.close()

    # Per-true-cluster (event, true_cluster_id) energies/completenesses - the exact
    # population plotted in completeness_vs_true_energy_1d_job_<APA>.png ("All Clusters"),
    # so callers can compute summary statistics that agree with that plot instead of
    # re-deriving them from the raw (fragmented) completeness_results pair rows.
    return energies, completenesses


def DrawClusterCompletenessVsTrueEnergyPerFile(pair_metadata_list, output_dir, apa, file_name=None, all_true_metadata_list=None):
    """
    File-level version: For each 1-to-1 true-reco pair (from add_metadata_true_reco_pair_cluster),
    plot completeness vs true cluster energy (2D and 1D) for all events in a file, for all clusters
    and broken down by cluster category (neutrino, isochronous/normal/prolonged cosmic).

    If all_true_metadata_list is provided (from add_metadata_true_clusters), true clusters
    that never matched any reco cluster are included as well with completeness=0.
    """
    all_entries = _combine_pairs_with_unmatched(pair_metadata_list, all_true_metadata_list)
    if not all_entries:
        return

    def _in_category(metadata, category_key):
        if category_key == 'neutrino':
            return metadata['cluster_type'] == 'neutrino'
        return metadata['cluster_type'] == 'cosmic' and metadata['cluster_category'] == category_key.replace('_cosmic', '')

    num_events_in_file = len(set(m['event'] for m in all_entries))

    energies        = [m['total_true_energy'] for m in all_entries]
    completenesses    = [m['completeness'] for m in all_entries]

    # 2D Histogram for all clusters
    plot_2d_completeness_energy(energies, completenesses, output_dir, 0, apa,
                             category_name="All Clusters ClusteringLevel (File Level)", file_name=file_name,
                             num_events=num_events_in_file, num_clusters=len(energies))

    # 2D plots by category
    category_styles = {
        'neutrino': 'Neutrino Clusters ClusteringLevel',
        'isochronous_cosmic': 'Isochronous Cosmic Clusters ClusteringLevel',
        'normal_cosmic': 'Normal Cosmic Clusters ClusteringLevel',
        'prolonged_cosmic': 'Prolonged Cosmic Clusters ClusteringLevel'
    }

    for category_key, category_label in category_styles.items():
        category_entries = [m for m in all_entries if _in_category(m, category_key)]
        if not category_entries:
            continue

        category_energies      = [m['total_true_energy'] for m in category_entries]
        category_completenesses  = [m['completeness'] for m in category_entries]
        plot_2d_completeness_energy(category_energies, category_completenesses, output_dir, 0, apa,
                                 category_name=category_label, file_name=file_name,
                                 num_events=num_events_in_file, num_clusters=len(category_energies))

    # Setup binning for 1D projections
    n_bins = 15
    if energies:
        energy_bins = np.linspace(0, max(energies)*1.1, n_bins+1)
    else:
        energy_bins = np.linspace(0, 10, n_bins+1)

    # 1D Plot: All clusters (separate canvas)
    bin_centers_all, mean_eff_all = plot_1d_completeness_energy(energies, completenesses, energy_bins)

    plt.figure(figsize=(12, 6))
    if len(bin_centers_all) > 0:
        plt.plot(bin_centers_all, mean_eff_all, 'o-', linewidth=2.5, markersize=10,
                color='darkblue', label='All Clusters', markeredgecolor='black', markeredgewidth=1)

    plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
    plt.ylabel('Completeness', fontsize=12, fontweight='bold')
    title = f'Completeness vs True Energy (1D Projection, ClusteringLevel) - File Level, {apa}'
    if file_name:
        title += f' ({file_name})'
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.xlim(0, TRUE_ENERGY_XMAX_MEV)
    plt.ylim(-0.05, 1.05)
    plt.savefig(output_dir / f"completeness_vs_true_energy_1d_clusteringlevel_file_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()

    # 1D Plots: neutrino-only and cosmic-only, one canvas each, alongside the All
    # Clusters plot above. Same energy_bins as that plot -- built from the full
    # population -- so all three curves share bin centres and can be overlaid or
    # read side by side. This is the coarse two-way split; the four-way
    # neutrino/isochronous/normal/prolonged breakdown is the by_category plot.
    for _population in ('neutrino', 'cosmic'):
        _population_entries = [m for m in all_entries if m['cluster_type'] == _population]
        _population_title = f'Completeness vs True Energy (1D Projection, ClusteringLevel, {POPULATION_STYLES[_population]["label"]} Only) - File Level, {apa}'
        if file_name:
            _population_title += f' ({file_name})'
        _draw_1d_completeness_single_population(
            [m['total_true_energy'] for m in _population_entries],
            [m['completeness'] for m in _population_entries],
            energy_bins, _population, output_dir,
            f"completeness_vs_true_energy_1d_{_population}_clusteringlevel_file_{apa}.png", _population_title)

    # 1D Plot 2: By category
    plt.figure(figsize=(14, 7))

    category_info = {
        'neutrino': {'label': 'Neutrino Clusters', 'color': 'purple', 'marker': 'D'},
        'isochronous_cosmic': {'label': 'Isochronous Cosmic', 'color': 'red', 'marker': 'o'},
        'normal_cosmic': {'label': 'Normal Cosmic', 'color': 'green', 'marker': 's'},
        'prolonged_cosmic': {'label': 'Prolonged Cosmic', 'color': 'blue', 'marker': '^'}
    }

    for category_key, info in category_info.items():
        category_entries = [m for m in all_entries if _in_category(m, category_key)]
        if not category_entries:
            continue

        category_energies      = [m['total_true_energy'] for m in category_entries]
        category_completenesses  = [m['completeness'] for m in category_entries]

        bin_centers_cat, mean_eff_cat = plot_1d_completeness_energy(category_energies, category_completenesses, energy_bins)
        if len(bin_centers_cat) > 0:
            label_text = f"{info['label']} ({len(category_entries)} clusters)"
            plt.plot(bin_centers_cat, mean_eff_cat, marker=info['marker'], linestyle='-', linewidth=2, markersize=8,
                    color=info['color'], label=label_text, markeredgecolor='black', markeredgewidth=0.5)

    plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
    plt.ylabel('Completeness', fontsize=12, fontweight='bold')
    title = f'Completeness vs True Energy (1D by Category, ClusteringLevel) - File Level, {apa}'
    if file_name:
        title += f' ({file_name})'
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.xlim(0, TRUE_ENERGY_XMAX_MEV)
    plt.ylim(-0.05, 1.05)
    plt.savefig(output_dir / f"completeness_vs_true_energy_1d_by_category_clusteringlevel_file_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()


def DrawClusterCompletenessVsTrueEnergyPerJob(pair_metadata_list, output_dir, apa, all_true_metadata_list=None):
    """
    Job-level version: For each 1-to-1 true-reco pair (from add_metadata_true_reco_pair_cluster),
    plot completeness vs true cluster energy (2D and 1D) for all events in all files, for all clusters
    and broken down by cluster category (neutrino, isochronous/normal/prolonged cosmic).

    If all_true_metadata_list is provided (from add_metadata_true_clusters), true clusters
    that never matched any reco cluster are included as well with completeness=0.
    """
    all_entries = _combine_pairs_with_unmatched(pair_metadata_list, all_true_metadata_list)
    if not all_entries:
        return

    def _in_category(metadata, category_key):
        if category_key == 'neutrino':
            return metadata['cluster_type'] == 'neutrino'
        return metadata['cluster_type'] == 'cosmic' and metadata['cluster_category'] == category_key.replace('_cosmic', '')

    num_events_total = len(set(m['event'] for m in all_entries))

    energies        = [m['total_true_energy'] for m in all_entries]
    completenesses    = [m['completeness'] for m in all_entries]

    # 2D Histogram for all clusters
    plot_2d_completeness_energy(energies, completenesses, output_dir, 0, apa,
                             category_name="All Clusters ClusteringLevel (Job Level)", file_name=None,
                             num_events=num_events_total, num_clusters=len(energies))

    # 2D plots by category
    category_styles = {
        'neutrino': 'Neutrino Clusters ClusteringLevel',
        'isochronous_cosmic': 'Isochronous Cosmic Clusters ClusteringLevel',
        'normal_cosmic': 'Normal Cosmic Clusters ClusteringLevel',
        'prolonged_cosmic': 'Prolonged Cosmic Clusters ClusteringLevel'
    }

    for category_key, category_label in category_styles.items():
        category_entries = [m for m in all_entries if _in_category(m, category_key)]
        if not category_entries:
            continue

        category_energies      = [m['total_true_energy'] for m in category_entries]
        category_completenesses  = [m['completeness'] for m in category_entries]
        plot_2d_completeness_energy(category_energies, category_completenesses, output_dir, 0, apa,
                                 category_name=category_label, file_name=None,
                                 num_events=num_events_total, num_clusters=len(category_energies))

    # Setup binning for 1D projections
    n_bins = 15
    if energies:
        energy_bins = np.linspace(0, max(energies)*1.1, n_bins+1)
    else:
        energy_bins = np.linspace(0, 10, n_bins+1)

    # 1D Plot: All clusters (separate canvas)
    bin_centers_all, mean_eff_all = plot_1d_completeness_energy(energies, completenesses, energy_bins)

    plt.figure(figsize=(12, 6))
    if len(bin_centers_all) > 0:
        plt.plot(bin_centers_all, mean_eff_all, 'o-', linewidth=2.5, markersize=10,
                color='darkblue', label='All Clusters', markeredgecolor='black', markeredgewidth=1)

    plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
    plt.ylabel('Completeness', fontsize=12, fontweight='bold')
    title = f'Completeness vs True Energy (1D Projection, ClusteringLevel) - Job Level, {apa}'
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.xlim(0, TRUE_ENERGY_XMAX_MEV)
    plt.ylim(-0.05, 1.05)
    plt.savefig(output_dir / f"completeness_vs_true_energy_1d_clusteringlevel_job_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()

    # 1D Plots: neutrino-only and cosmic-only, one canvas each, alongside the All
    # Clusters plot above. Same energy_bins as that plot -- built from the full
    # population -- so all three curves share bin centres and can be overlaid or
    # read side by side. This is the coarse two-way split; the four-way
    # neutrino/isochronous/normal/prolonged breakdown is the by_category plot.
    for _population in ('neutrino', 'cosmic'):
        _population_entries = [m for m in all_entries if m['cluster_type'] == _population]
        _population_title = f'Completeness vs True Energy (1D Projection, ClusteringLevel, {POPULATION_STYLES[_population]["label"]} Only) - Job Level, {apa}'
        _draw_1d_completeness_single_population(
            [m['total_true_energy'] for m in _population_entries],
            [m['completeness'] for m in _population_entries],
            energy_bins, _population, output_dir,
            f"completeness_vs_true_energy_1d_{_population}_clusteringlevel_job_{apa}.png", _population_title)

    # 1D Plot 2: By category
    plt.figure(figsize=(14, 7))

    category_info = {
        'neutrino': {'label': 'Neutrino Clusters', 'color': 'purple', 'marker': 'D'},
        'isochronous_cosmic': {'label': 'Isochronous Cosmic', 'color': 'red', 'marker': 'o'},
        'normal_cosmic': {'label': 'Normal Cosmic', 'color': 'green', 'marker': 's'},
        'prolonged_cosmic': {'label': 'Prolonged Cosmic', 'color': 'blue', 'marker': '^'}
    }

    for category_key, info in category_info.items():
        category_entries = [m for m in all_entries if _in_category(m, category_key)]
        if not category_entries:
            continue

        category_energies      = [m['total_true_energy'] for m in category_entries]
        category_completenesses  = [m['completeness'] for m in category_entries]

        bin_centers_cat, mean_eff_cat = plot_1d_completeness_energy(category_energies, category_completenesses, energy_bins)
        if len(bin_centers_cat) > 0:
            label_text = f"{info['label']} ({len(category_entries)} clusters)"
            plt.plot(bin_centers_cat, mean_eff_cat, marker=info['marker'], linestyle='-', linewidth=2, markersize=8,
                    color=info['color'], label=label_text, markeredgecolor='black', markeredgewidth=0.5)

    plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
    plt.ylabel('Completeness', fontsize=12, fontweight='bold')
    title = f'Completeness vs True Energy (1D by Category, ClusteringLevel) - Job Level, {apa}'
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.xlim(0, TRUE_ENERGY_XMAX_MEV)
    plt.ylim(-0.05, 1.05)
    plt.savefig(output_dir / f"completeness_vs_true_energy_1d_by_category_clusteringlevel_job_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()


def DrawCompletenessVsTrueEnergy_MatchedPairs_PerEvent(pair_metadata_list, output_dir, event, apa, file_name=None):
    """
    For each 1-to-1 true-reco pair (from add_metadata_true_reco_pair_cluster), plot completeness
    vs true cluster energy (2D and 1D), for all clusters and broken down by cluster category
    (neutrino, isochronous/normal/prolonged cosmic).

    Unlike DrawClusterCompletenessVsTrueEnergyPerEvent, this only considers matched true-reco
    pairs and does not include true clusters that never matched any reco cluster.
    """
    if not pair_metadata_list:
        return

    def _in_category(metadata, category_key):
        if category_key == 'neutrino':
            return metadata['cluster_type'] == 'neutrino'
        return metadata['cluster_type'] == 'cosmic' and metadata['cluster_category'] == category_key.replace('_cosmic', '')

    energies        = [m['total_true_energy'] for m in pair_metadata_list]
    completenesses    = [m['completeness'] for m in pair_metadata_list]

    # 2D Histogram for all clusters
    plot_2d_completeness_energy(energies, completenesses, output_dir, event, apa,
                             category_name="All Clusters ClusteringLevel (Pairs Only)", file_name=file_name)

    # 2D plots by category
    category_styles = {
        'neutrino': 'Neutrino Clusters ClusteringLevel (Pairs Only)',
        'isochronous_cosmic': 'Isochronous Cosmic Clusters ClusteringLevel (Pairs Only)',
        'normal_cosmic': 'Normal Cosmic Clusters ClusteringLevel (Pairs Only)',
        'prolonged_cosmic': 'Prolonged Cosmic Clusters ClusteringLevel (Pairs Only)'
    }

    for category_key, category_label in category_styles.items():
        category_entries = [m for m in pair_metadata_list if _in_category(m, category_key)]
        if not category_entries:
            continue

        category_energies      = [m['total_true_energy'] for m in category_entries]
        category_completenesses  = [m['completeness'] for m in category_entries]
        plot_2d_completeness_energy(category_energies, category_completenesses, output_dir, event, apa,
                                 category_name=category_label, file_name=file_name)

    # Setup binning for 1D projections
    n_bins = 15
    if energies:
        energy_bins = np.linspace(0, max(energies)*1.1, n_bins+1)
    else:
        energy_bins = np.linspace(0, 10, n_bins+1)

    # 1D Plot 1: All clusters (separate canvas)
    bin_centers_all, mean_eff_all = plot_1d_completeness_energy(energies, completenesses, energy_bins)

    plt.figure(figsize=(12, 6))
    if len(bin_centers_all) > 0:
        plt.plot(bin_centers_all, mean_eff_all, 'o-', linewidth=2.5, markersize=10,
                color='darkblue', label='All Clusters', markeredgecolor='black', markeredgewidth=1)

    plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
    plt.ylabel('Completeness', fontsize=12, fontweight='bold')
    title = f'Completeness vs True Energy (1D Projection, ClusteringLevel, Pairs Only) - Event {event}, {apa}'
    if file_name:
        title += f' ({file_name})'
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.xlim(0, TRUE_ENERGY_XMAX_MEV)
    plt.ylim(-0.05, 1.05)
    plt.savefig(output_dir / f"completeness_vs_true_energy_1d_clusteringlevel_pairs_only_event_{event}_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()

    # 1D Plots: neutrino-only and cosmic-only, one canvas each, alongside the All
    # Clusters plot above. Same energy_bins as that plot -- built from the full
    # population -- so all three curves share bin centres and can be overlaid or
    # read side by side. This is the coarse two-way split; the four-way
    # neutrino/isochronous/normal/prolonged breakdown is the by_category plot.
    for _population in ('neutrino', 'cosmic'):
        _population_entries = [m for m in pair_metadata_list if m['cluster_type'] == _population]
        _population_title = f'Completeness vs True Energy (1D Projection, ClusteringLevel, Pairs Only, {POPULATION_STYLES[_population]["label"]} Only) - Event {event}, {apa}'
        if file_name:
            _population_title += f' ({file_name})'
        _draw_1d_completeness_single_population(
            [m['total_true_energy'] for m in _population_entries],
            [m['completeness'] for m in _population_entries],
            energy_bins, _population, output_dir,
            f"completeness_vs_true_energy_1d_{_population}_clusteringlevel_pairs_only_event_{event}_{apa}.png", _population_title)

    # 1D Plot 2: By category
    plt.figure(figsize=(14, 7))

    category_info = {
        'neutrino': {'label': 'Neutrino Clusters', 'color': 'purple', 'marker': 'D'},
        'isochronous_cosmic': {'label': 'Isochronous Cosmic', 'color': 'red', 'marker': 'o'},
        'normal_cosmic': {'label': 'Normal Cosmic', 'color': 'green', 'marker': 's'},
        'prolonged_cosmic': {'label': 'Prolonged Cosmic', 'color': 'blue', 'marker': '^'}
    }

    for category_key, info in category_info.items():
        category_entries = [m for m in pair_metadata_list if _in_category(m, category_key)]
        if not category_entries:
            continue

        category_energies      = [m['total_true_energy'] for m in category_entries]
        category_completenesses  = [m['completeness'] for m in category_entries]

        bin_centers_cat, mean_eff_cat = plot_1d_completeness_energy(category_energies, category_completenesses, energy_bins)
        if len(bin_centers_cat) > 0:
            label_text = f"{info['label']} ({len(category_entries)} clusters)"
            plt.plot(bin_centers_cat, mean_eff_cat, marker=info['marker'], linestyle='-', linewidth=2, markersize=8,
                    color=info['color'], label=label_text, markeredgecolor='black', markeredgewidth=0.5)

    plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
    plt.ylabel('Completeness', fontsize=12, fontweight='bold')
    title = f'Completeness vs True Energy (1D by Category, ClusteringLevel, Pairs Only) - Event {event}, {apa}'
    if file_name:
        title += f' ({file_name})'
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.xlim(0, TRUE_ENERGY_XMAX_MEV)
    plt.ylim(-0.05, 1.05)
    plt.savefig(output_dir / f"completeness_vs_true_energy_1d_by_category_clusteringlevel_pairs_only_event_{event}_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()


def DrawCompletenessVsTrueEnergy_MatchedPairs_PerFile(pair_metadata_list, output_dir, apa, file_name=None):
    """
    File-level version: For each 1-to-1 true-reco pair (from add_metadata_true_reco_pair_cluster),
    plot completeness vs true cluster energy (2D and 1D) for all events in a file, for all clusters
    and broken down by cluster category (neutrino, isochronous/normal/prolonged cosmic).

    Unlike DrawClusterCompletenessVsTrueEnergyPerFile, this only considers matched true-reco
    pairs and does not include true clusters that never matched any reco cluster.
    """
    if not pair_metadata_list:
        return

    def _in_category(metadata, category_key):
        if category_key == 'neutrino':
            return metadata['cluster_type'] == 'neutrino'
        return metadata['cluster_type'] == 'cosmic' and metadata['cluster_category'] == category_key.replace('_cosmic', '')

    num_events_in_file = len(set(m['event'] for m in pair_metadata_list))

    energies        = [m['total_true_energy'] for m in pair_metadata_list]
    completenesses    = [m['completeness'] for m in pair_metadata_list]

    # 2D Histogram for all clusters
    plot_2d_completeness_energy(energies, completenesses, output_dir, 0, apa,
                             category_name="All Clusters ClusteringLevel (File Level, Pairs Only)", file_name=file_name,
                             num_events=num_events_in_file, num_clusters=len(energies))

    # 2D plots by category
    category_styles = {
        'neutrino': 'Neutrino Clusters ClusteringLevel (Pairs Only)',
        'isochronous_cosmic': 'Isochronous Cosmic Clusters ClusteringLevel (Pairs Only)',
        'normal_cosmic': 'Normal Cosmic Clusters ClusteringLevel (Pairs Only)',
        'prolonged_cosmic': 'Prolonged Cosmic Clusters ClusteringLevel (Pairs Only)'
    }

    for category_key, category_label in category_styles.items():
        category_entries = [m for m in pair_metadata_list if _in_category(m, category_key)]
        if not category_entries:
            continue

        category_energies      = [m['total_true_energy'] for m in category_entries]
        category_completenesses  = [m['completeness'] for m in category_entries]
        plot_2d_completeness_energy(category_energies, category_completenesses, output_dir, 0, apa,
                                 category_name=category_label, file_name=file_name,
                                 num_events=num_events_in_file, num_clusters=len(category_energies))

    # Setup binning for 1D projections
    n_bins = 15
    if energies:
        energy_bins = np.linspace(0, max(energies)*1.1, n_bins+1)
    else:
        energy_bins = np.linspace(0, 10, n_bins+1)

    # 1D Plot: All clusters (separate canvas)
    bin_centers_all, mean_eff_all = plot_1d_completeness_energy(energies, completenesses, energy_bins)

    plt.figure(figsize=(12, 6))
    if len(bin_centers_all) > 0:
        plt.plot(bin_centers_all, mean_eff_all, 'o-', linewidth=2.5, markersize=10,
                color='darkblue', label='All Clusters', markeredgecolor='black', markeredgewidth=1)

    plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
    plt.ylabel('Completeness', fontsize=12, fontweight='bold')
    title = f'Completeness vs True Energy (1D Projection, ClusteringLevel, Pairs Only) - File Level, {apa}'
    if file_name:
        title += f' ({file_name})'
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.xlim(0, TRUE_ENERGY_XMAX_MEV)
    plt.ylim(-0.05, 1.05)
    plt.savefig(output_dir / f"completeness_vs_true_energy_1d_clusteringlevel_pairs_only_file_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()

    # 1D Plots: neutrino-only and cosmic-only, one canvas each, alongside the All
    # Clusters plot above. Same energy_bins as that plot -- built from the full
    # population -- so all three curves share bin centres and can be overlaid or
    # read side by side. This is the coarse two-way split; the four-way
    # neutrino/isochronous/normal/prolonged breakdown is the by_category plot.
    for _population in ('neutrino', 'cosmic'):
        _population_entries = [m for m in pair_metadata_list if m['cluster_type'] == _population]
        _population_title = f'Completeness vs True Energy (1D Projection, ClusteringLevel, Pairs Only, {POPULATION_STYLES[_population]["label"]} Only) - File Level, {apa}'
        if file_name:
            _population_title += f' ({file_name})'
        _draw_1d_completeness_single_population(
            [m['total_true_energy'] for m in _population_entries],
            [m['completeness'] for m in _population_entries],
            energy_bins, _population, output_dir,
            f"completeness_vs_true_energy_1d_{_population}_clusteringlevel_pairs_only_file_{apa}.png", _population_title)

    # 1D Plot 2: By category
    plt.figure(figsize=(14, 7))

    category_info = {
        'neutrino': {'label': 'Neutrino Clusters', 'color': 'purple', 'marker': 'D'},
        'isochronous_cosmic': {'label': 'Isochronous Cosmic', 'color': 'red', 'marker': 'o'},
        'normal_cosmic': {'label': 'Normal Cosmic', 'color': 'green', 'marker': 's'},
        'prolonged_cosmic': {'label': 'Prolonged Cosmic', 'color': 'blue', 'marker': '^'}
    }

    for category_key, info in category_info.items():
        category_entries = [m for m in pair_metadata_list if _in_category(m, category_key)]
        if not category_entries:
            continue

        category_energies      = [m['total_true_energy'] for m in category_entries]
        category_completenesses  = [m['completeness'] for m in category_entries]

        bin_centers_cat, mean_eff_cat = plot_1d_completeness_energy(category_energies, category_completenesses, energy_bins)
        if len(bin_centers_cat) > 0:
            label_text = f"{info['label']} ({len(category_entries)} clusters)"
            plt.plot(bin_centers_cat, mean_eff_cat, marker=info['marker'], linestyle='-', linewidth=2, markersize=8,
                    color=info['color'], label=label_text, markeredgecolor='black', markeredgewidth=0.5)

    plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
    plt.ylabel('Completeness', fontsize=12, fontweight='bold')
    title = f'Completeness vs True Energy (1D by Category, ClusteringLevel, Pairs Only) - File Level, {apa}'
    if file_name:
        title += f' ({file_name})'
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.xlim(0, TRUE_ENERGY_XMAX_MEV)
    plt.ylim(-0.05, 1.05)
    plt.savefig(output_dir / f"completeness_vs_true_energy_1d_by_category_clusteringlevel_pairs_only_file_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()


def DrawCompletenessVsTrueEnergy_MatchedPairs_PerJob(pair_metadata_list, output_dir, apa):
    """
    Job-level version: For each 1-to-1 true-reco pair (from add_metadata_true_reco_pair_cluster),
    plot completeness vs true cluster energy (2D and 1D) for all events in all files, for all clusters
    and broken down by cluster category (neutrino, isochronous/normal/prolonged cosmic).

    Unlike DrawClusterCompletenessVsTrueEnergyPerJob, this only considers matched true-reco
    pairs and does not include true clusters that never matched any reco cluster.
    """
    if not pair_metadata_list:
        return [], []

    def _in_category(metadata, category_key):
        if category_key == 'neutrino':
            return metadata['cluster_type'] == 'neutrino'
        return metadata['cluster_type'] == 'cosmic' and metadata['cluster_category'] == category_key.replace('_cosmic', '')

    num_events_total = len(set(m['event'] for m in pair_metadata_list))

    energies        = [m['total_true_energy'] for m in pair_metadata_list]
    completenesses    = [m['completeness'] for m in pair_metadata_list]

    # 2D Histogram for all clusters
    plot_2d_completeness_energy(energies, completenesses, output_dir, 0, apa,
                             category_name="All Clusters ClusteringLevel (Job Level, Pairs Only)", file_name=None,
                             num_events=num_events_total, num_clusters=len(energies))

    # 2D plots by category
    category_styles = {
        'neutrino': 'Neutrino Clusters ClusteringLevel (Pairs Only)',
        'isochronous_cosmic': 'Isochronous Cosmic Clusters ClusteringLevel (Pairs Only)',
        'normal_cosmic': 'Normal Cosmic Clusters ClusteringLevel (Pairs Only)',
        'prolonged_cosmic': 'Prolonged Cosmic Clusters ClusteringLevel (Pairs Only)'
    }

    for category_key, category_label in category_styles.items():
        category_entries = [m for m in pair_metadata_list if _in_category(m, category_key)]
        if not category_entries:
            continue

        category_energies      = [m['total_true_energy'] for m in category_entries]
        category_completenesses  = [m['completeness'] for m in category_entries]
        plot_2d_completeness_energy(category_energies, category_completenesses, output_dir, 0, apa,
                                 category_name=category_label, file_name=None,
                                 num_events=num_events_total, num_clusters=len(category_energies))

    # Setup binning for 1D projections
    n_bins = 15
    if energies:
        energy_bins = np.linspace(0, max(energies)*1.1, n_bins+1)
    else:
        energy_bins = np.linspace(0, 10, n_bins+1)

    # 1D Plot: All clusters (separate canvas)
    bin_centers_all, mean_eff_all = plot_1d_completeness_energy(energies, completenesses, energy_bins)

    plt.figure(figsize=(12, 6))
    if len(bin_centers_all) > 0:
        plt.plot(bin_centers_all, mean_eff_all, 'o-', linewidth=2.5, markersize=10,
                color='darkblue', label='All Clusters', markeredgecolor='black', markeredgewidth=1)

    plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
    plt.ylabel('Completeness', fontsize=12, fontweight='bold')
    title = f'Completeness vs True Energy (1D Projection, ClusteringLevel, Pairs Only) - Job Level, {apa}'
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.xlim(0, TRUE_ENERGY_XMAX_MEV)
    plt.ylim(-0.05, 1.05)
    plt.savefig(output_dir / f"completeness_vs_true_energy_1d_clusteringlevel_pairs_only_job_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()

    # 1D Plots: neutrino-only and cosmic-only, one canvas each, alongside the All
    # Clusters plot above. Same energy_bins as that plot -- built from the full
    # population -- so all three curves share bin centres and can be overlaid or
    # read side by side. This is the coarse two-way split; the four-way
    # neutrino/isochronous/normal/prolonged breakdown is the by_category plot.
    for _population in ('neutrino', 'cosmic'):
        _population_entries = [m for m in pair_metadata_list if m['cluster_type'] == _population]
        _population_title = f'Completeness vs True Energy (1D Projection, ClusteringLevel, Pairs Only, {POPULATION_STYLES[_population]["label"]} Only) - Job Level, {apa}'
        _draw_1d_completeness_single_population(
            [m['total_true_energy'] for m in _population_entries],
            [m['completeness'] for m in _population_entries],
            energy_bins, _population, output_dir,
            f"completeness_vs_true_energy_1d_{_population}_clusteringlevel_pairs_only_job_{apa}.png", _population_title)

    # 1D Plot 2: By category
    plt.figure(figsize=(14, 7))

    category_info = {
        'neutrino': {'label': 'Neutrino Clusters', 'color': 'purple', 'marker': 'D'},
        'isochronous_cosmic': {'label': 'Isochronous Cosmic', 'color': 'red', 'marker': 'o'},
        'normal_cosmic': {'label': 'Normal Cosmic', 'color': 'green', 'marker': 's'},
        'prolonged_cosmic': {'label': 'Prolonged Cosmic', 'color': 'blue', 'marker': '^'}
    }

    for category_key, info in category_info.items():
        category_entries = [m for m in pair_metadata_list if _in_category(m, category_key)]
        if not category_entries:
            continue

        category_energies      = [m['total_true_energy'] for m in category_entries]
        category_completenesses  = [m['completeness'] for m in category_entries]

        bin_centers_cat, mean_eff_cat = plot_1d_completeness_energy(category_energies, category_completenesses, energy_bins)
        if len(bin_centers_cat) > 0:
            label_text = f"{info['label']} ({len(category_entries)} clusters)"
            plt.plot(bin_centers_cat, mean_eff_cat, marker=info['marker'], linestyle='-', linewidth=2, markersize=8,
                    color=info['color'], label=label_text, markeredgecolor='black', markeredgewidth=0.5)

    plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
    plt.ylabel('Completeness', fontsize=12, fontweight='bold')
    title = f'Completeness vs True Energy (1D by Category, ClusteringLevel, Pairs Only) - Job Level, {apa}'
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.xlim(0, TRUE_ENERGY_XMAX_MEV)
    plt.ylim(-0.05, 1.05)
    plt.savefig(output_dir / f"completeness_vs_true_energy_1d_by_category_clusteringlevel_pairs_only_job_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()

    # Per-pair energies/completenesses - the exact population plotted in
    # completeness_vs_true_energy_1d_clusteringlevel_pairs_only_job_<APA>.png ("All Clusters").
    return energies, completenesses


def DrawPurityVsRecoChargePerEvent(pair_metadata_list, output_dir, event, apa, file_name=None):
    """
    For each 1-to-1 true-reco pair (from add_metadata_true_reco_pair_cluster): plot purity
    vs reco cluster charge (2D and 1D). The purity value is the one corresponding to the
    highest-completeness reco cluster matched to each true cluster.
    Draws plots for all clusters and broken down by cluster category
    (neutrino, all cosmics, isochronous/normal/prolonged cosmic).
    """
    if not pair_metadata_list:
        return

    def _in_category(metadata, category_key):
        if category_key == 'neutrino':
            return metadata['cluster_type'] == 'neutrino'
        if category_key == 'cosmic':
            return metadata['cluster_type'] == 'cosmic'
        return metadata['cluster_type'] == 'cosmic' and metadata['cluster_category'] == category_key.replace('_cosmic', '')

    charges  = [m['total_reco_charge'] for m in pair_metadata_list]
    purities = [m['purity'] for m in pair_metadata_list]

    if not charges:
        return

    # 2D Histogram for all clusters
    plot_2d_purity_charge(charges, purities, output_dir, event, apa,
                          category_name="All Clusters", file_name=file_name)

    # 2D plots by category
    category_styles = {
        'neutrino': 'Neutrino Clusters',
        'cosmic': 'All Cosmic Clusters',
        'isochronous_cosmic': 'Isochronous Cosmic Clusters',
        'normal_cosmic': 'Normal Cosmic Clusters',
        'prolonged_cosmic': 'Prolonged Cosmic Clusters'
    }

    for category_key, category_label in category_styles.items():
        category_entries = [m for m in pair_metadata_list if _in_category(m, category_key)]
        if not category_entries:
            continue

        category_charges  = [m['total_reco_charge'] for m in category_entries]
        category_purities = [m['purity'] for m in category_entries]
        plot_2d_purity_charge(category_charges, category_purities, output_dir, event, apa,
                              category_name=category_label, file_name=file_name)

    # Setup binning for 1D projections
    n_bins = 15
    charge_bins = np.linspace(0, max(charges)*1.1, n_bins+1)

    # 1D Plot 1: All clusters (separate canvas)
    bin_centers, mean_purity_per_bin = plot_1d_purity_charge(charges, purities, charge_bins)

    plt.figure(figsize=(12, 6))
    if len(bin_centers) > 0:
        plt.plot(bin_centers, mean_purity_per_bin, 'o-', linewidth=2, markersize=10,
                color='darkred', label='Mean Purity per Bin', markeredgecolor='black', markeredgewidth=1)

    plt.xlabel('Reco Cluster Charge [ADC] Arbitrary Units', fontsize=12, fontweight='bold')
    plt.ylabel('Purity', fontsize=12, fontweight='bold')
    title = f'Purity vs Reco Charge (1D Projection) - Event {event}, {apa}'
    if file_name:
        title += f' ({file_name})'
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.xlim(0, max(charges)*1.1)
    plt.ylim(-0.05, 1.05)
    plt.savefig(output_dir / f"purity_vs_reco_charge_1d_event_{event}_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()

    # 1D Plots: neutrino-only and cosmic-only, one canvas each, alongside the All
    # Clusters plot above. Same charge_bins AND same x-limit as that plot -- both
    # derived from the full population -- so the three curves stay comparable.
    # This is the coarse two-way split; the by_category plot keeps the finer
    # neutrino / all-cosmic / isochronous / normal / prolonged breakdown.
    for _population in ('neutrino', 'cosmic'):
        _population_entries = [m for m in pair_metadata_list if m['cluster_type'] == _population]
        _population_title = f'Purity vs Reco Charge (1D Projection, {POPULATION_STYLES[_population]["label"]} Only) - Event {event}, {apa}'
        if file_name:
            _population_title += f' ({file_name})'
        _draw_1d_purity_single_population(
            [m['total_reco_charge'] for m in _population_entries],
            [m['purity'] for m in _population_entries],
            charge_bins, max(charges)*1.1, _population, output_dir,
            f"purity_vs_reco_charge_1d_{_population}_event_{event}_{apa}.png", _population_title)

    # 1D Plot 2: By category
    plt.figure(figsize=(14, 7))

    category_info = {
        'neutrino': {'label': 'Neutrino Clusters', 'color': 'purple', 'marker': 'D'},
        'cosmic': {'label': 'All Cosmics', 'color': 'black', 'marker': 'v'},
        'isochronous_cosmic': {'label': 'Isochronous Cosmic', 'color': 'red', 'marker': 'o'},
        'normal_cosmic': {'label': 'Normal Cosmic', 'color': 'green', 'marker': 's'},
        'prolonged_cosmic': {'label': 'Prolonged Cosmic', 'color': 'blue', 'marker': '^'}
    }

    for category_key, info in category_info.items():
        category_entries = [m for m in pair_metadata_list if _in_category(m, category_key)]
        if not category_entries:
            continue

        category_charges  = [m['total_reco_charge'] for m in category_entries]
        category_purities = [m['purity'] for m in category_entries]

        bin_centers_cat, mean_pur_cat = plot_1d_purity_charge(category_charges, category_purities, charge_bins)
        if len(bin_centers_cat) > 0:
            label_text = f"{info['label']} ({len(category_entries)} clusters)"
            plt.plot(bin_centers_cat, mean_pur_cat, marker=info['marker'], linestyle='-', linewidth=2, markersize=8,
                    color=info['color'], label=label_text, markeredgecolor='black', markeredgewidth=0.5)

    plt.xlabel('Reco Cluster Charge [ADC] Arbitrary Units', fontsize=12, fontweight='bold')
    plt.ylabel('Purity', fontsize=12, fontweight='bold')
    title = f'Purity vs Reco Charge (1D by Category) - Event {event}, {apa}'
    if file_name:
        title += f' ({file_name})'
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.xlim(0, max(charges)*1.1)
    plt.ylim(-0.05, 1.05)
    plt.savefig(output_dir / f"purity_vs_reco_charge_1d_by_category_event_{event}_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()


def _DrawPurityVsRecoChargeAggregated(pair_metadata_list, output_dir, apa, level_name, filename_suffix, file_name=None):
    """
    Shared implementation for file-level and job-level purity vs reco charge plots (2D and 1D),
    aggregated over many events, using the 1-to-1 true-reco pair metadata. The purity value is
    the one corresponding to the highest-completeness reco cluster matched to each true cluster.
    Draws plots for all clusters and broken down by cluster category
    (neutrino, all cosmics, isochronous/normal/prolonged cosmic).
    """
    if not pair_metadata_list:
        return

    def _in_category(metadata, category_key):
        if category_key == 'neutrino':
            return metadata['cluster_type'] == 'neutrino'
        if category_key == 'cosmic':
            return metadata['cluster_type'] == 'cosmic'
        return metadata['cluster_type'] == 'cosmic' and metadata['cluster_category'] == category_key.replace('_cosmic', '')

    num_events = len(set(m['event'] for m in pair_metadata_list))

    charges  = [m['total_reco_charge'] for m in pair_metadata_list]
    purities = [m['purity'] for m in pair_metadata_list]

    if not charges:
        return

    # 2D Histogram for all clusters
    plot_2d_purity_charge(charges, purities, output_dir, 0, apa,
                          category_name=f"All Clusters ({level_name})", file_name=file_name,
                          num_events=num_events, num_clusters=len(charges))

    # 2D plots by category
    category_styles = {
        'neutrino': 'Neutrino Clusters',
        'cosmic': 'All Cosmic Clusters',
        'isochronous_cosmic': 'Isochronous Cosmic Clusters',
        'normal_cosmic': 'Normal Cosmic Clusters',
        'prolonged_cosmic': 'Prolonged Cosmic Clusters'
    }

    for category_key, category_label in category_styles.items():
        category_entries = [m for m in pair_metadata_list if _in_category(m, category_key)]
        if not category_entries:
            continue

        category_charges  = [m['total_reco_charge'] for m in category_entries]
        category_purities = [m['purity'] for m in category_entries]
        plot_2d_purity_charge(category_charges, category_purities, output_dir, 0, apa,
                              category_name=category_label, file_name=file_name,
                              num_events=num_events, num_clusters=len(category_charges))

    # Setup binning for 1D projections
    n_bins = 15
    charge_bins = np.linspace(0, max(charges)*1.1, n_bins+1)

    # 1D Plot 1: All clusters (separate canvas)
    bin_centers, mean_purity_per_bin = plot_1d_purity_charge(charges, purities, charge_bins)

    plt.figure(figsize=(12, 6))
    if len(bin_centers) > 0:
        plt.plot(bin_centers, mean_purity_per_bin, 'o-', linewidth=2, markersize=10,
                color='darkred', label='Mean Purity per Bin', markeredgecolor='black', markeredgewidth=1)

    plt.xlabel('Reco Cluster Charge [ADC] Arbitrary Units', fontsize=12, fontweight='bold')
    plt.ylabel('Purity', fontsize=12, fontweight='bold')
    title = f'Purity vs Reco Charge (1D Projection) - {level_name}, {num_events} events, {apa}'
    if file_name:
        title += f' ({file_name})'
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.xlim(0, max(charges)*1.1)
    plt.ylim(-0.05, 1.05)
    plt.savefig(output_dir / f"purity_vs_reco_charge_1d_{filename_suffix}_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()

    # 1D Plots: neutrino-only and cosmic-only, one canvas each, alongside the All
    # Clusters plot above. Same charge_bins AND same x-limit as that plot -- both
    # derived from the full population -- so the three curves stay comparable.
    # This is the coarse two-way split; the by_category plot keeps the finer
    # neutrino / all-cosmic / isochronous / normal / prolonged breakdown.
    for _population in ('neutrino', 'cosmic'):
        _population_entries = [m for m in pair_metadata_list if m['cluster_type'] == _population]
        _population_title = f'Purity vs Reco Charge (1D Projection, {POPULATION_STYLES[_population]["label"]} Only) - {level_name}, {num_events} events, {apa}'
        if file_name:
            _population_title += f' ({file_name})'
        _draw_1d_purity_single_population(
            [m['total_reco_charge'] for m in _population_entries],
            [m['purity'] for m in _population_entries],
            charge_bins, max(charges)*1.1, _population, output_dir,
            f"purity_vs_reco_charge_1d_{_population}_{filename_suffix}_{apa}.png", _population_title)

    # 1D Plot 2: By category
    plt.figure(figsize=(14, 7))

    category_info = {
        'neutrino': {'label': 'Neutrino Clusters', 'color': 'purple', 'marker': 'D'},
        'cosmic': {'label': 'All Cosmics', 'color': 'black', 'marker': 'v'},
        'isochronous_cosmic': {'label': 'Isochronous Cosmic', 'color': 'red', 'marker': 'o'},
        'normal_cosmic': {'label': 'Normal Cosmic', 'color': 'green', 'marker': 's'},
        'prolonged_cosmic': {'label': 'Prolonged Cosmic', 'color': 'blue', 'marker': '^'}
    }

    for category_key, info in category_info.items():
        category_entries = [m for m in pair_metadata_list if _in_category(m, category_key)]
        if not category_entries:
            continue

        category_charges  = [m['total_reco_charge'] for m in category_entries]
        category_purities = [m['purity'] for m in category_entries]

        bin_centers_cat, mean_pur_cat = plot_1d_purity_charge(category_charges, category_purities, charge_bins)
        if len(bin_centers_cat) > 0:
            label_text = f"{info['label']} ({len(category_entries)} clusters)"
            plt.plot(bin_centers_cat, mean_pur_cat, marker=info['marker'], linestyle='-', linewidth=2, markersize=8,
                    color=info['color'], label=label_text, markeredgecolor='black', markeredgewidth=0.5)

    plt.xlabel('Reco Cluster Charge [ADC] Arbitrary Units', fontsize=12, fontweight='bold')
    plt.ylabel('Purity', fontsize=12, fontweight='bold')
    title = f'Purity vs Reco Charge (1D by Category) - {level_name}, {num_events} events, {apa}'
    if file_name:
        title += f' ({file_name})'
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10)
    plt.xlim(0, max(charges)*1.1)
    plt.ylim(-0.05, 1.05)
    plt.savefig(output_dir / f"purity_vs_reco_charge_1d_by_category_{filename_suffix}_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()


def DrawPurityVsRecoChargePerFile(pair_metadata_list, output_dir, apa, file_name=None):
    """
    File-level version: purity vs reco charge (2D and 1D) for all events in a file,
    using the 1-to-1 true-reco pair metadata, for all clusters and per cluster category.
    """
    _DrawPurityVsRecoChargeAggregated(pair_metadata_list, output_dir, apa, 'File Level', 'file', file_name=file_name)


def DrawPurityVsRecoChargePerJob(pair_metadata_list, output_dir, apa):
    """
    Job-level version: purity vs reco charge (2D and 1D) for all events in all files,
    using the 1-to-1 true-reco pair metadata, for all clusters and per cluster category.
    """
    _DrawPurityVsRecoChargeAggregated(pair_metadata_list, output_dir, apa, 'Job Level', 'job')

# ============================================================================
# AGGREGATION FUNCTIONS FOR MULTIPLE EVENTS/FILES/JOB
# ============================================================================


def DrawAggregatedCompletenessPlots(completeness_results, output_dir, level_name, apa):
    """Draw 2D and 1D completeness plots for aggregated results."""
    if not completeness_results:
        return

    completenesses = [e['completeness_energy_weighted'] for e in completeness_results if e['reco_cluster_id'] != 8888]

    if not completenesses:
        return

    # 2D Histogram
    plt.figure(figsize=(10, 8))
    plt.hist(completenesses, bins=30, color='skyblue', edgecolor='black', alpha=0.7)
    plt.xlabel('Completeness', fontsize=12, fontweight='bold')
    plt.ylabel('Count', fontsize=12, fontweight='bold')
    plt.title(f'Completeness Distribution ({level_name}) - {apa}', fontsize=12, fontweight='bold', wrap=True)
    plt.axvline(np.mean(completenesses), color='red', linestyle='--', linewidth=2, label=f'Mean: {np.mean(completenesses):.3f}')
    plt.axvline(np.median(completenesses), color='green', linestyle='--', linewidth=2, label=f'Median: {np.median(completenesses):.3f}')
    plt.legend(fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.savefig(output_dir / f"completeness_distribution_{level_name.lower().replace(' ', '_')}_{apa}.png", dpi=100, bbox_inches='tight', pad_inches=0.3)
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
    plt.title(f'Purity Distribution ({level_name}) - {apa}', fontsize=12, fontweight='bold', wrap=True)
    plt.axvline(np.mean(purities), color='red', linestyle='--', linewidth=2, label=f'Mean: {np.mean(purities):.3f}')
    plt.axvline(np.median(purities), color='green', linestyle='--', linewidth=2, label=f'Median: {np.median(purities):.3f}')
    plt.legend(fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.savefig(output_dir / f"purity_distribution_{level_name.lower().replace(' ', '_')}_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    ##plt.show(block=False)
    plt.close()

def DrawMatchedPairsPlots(matched_pairs, output_dir, level_name, apa):
    """Draw completeness vs purity scatter plot for matched pairs."""
    if not matched_pairs:
        return

    completenesses = [p['completeness_energy_weighted'] for p in matched_pairs]
    purities = [p['purity'] for p in matched_pairs]

    # Scatter plot
    plt.figure(figsize=(10, 8))
    plt.scatter(completenesses, purities, s=50, alpha=0.6, color='purple', edgecolors='black', linewidth=0.5)
    plt.xlabel('Completeness', fontsize=12, fontweight='bold')
    plt.ylabel('Purity', fontsize=12, fontweight='bold')
    plt.title(f'Completeness vs Purity ({level_name}) - {apa}', fontsize=12, fontweight='bold', wrap=True)
    plt.xlim(-0.05, 1.05)
    plt.ylim(-0.05, 1.05)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.savefig(output_dir / f"completeness_vs_purity_{level_name.lower().replace(' ', '_')}_{apa}.png",
                dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()

_EFF_PUR_CATEGORY_STYLE = {
    'neutrino':            {'label': 'Neutrino Clusters',  'color': 'purple', 'marker': 'D'},
    'cosmic':              {'label': 'All Cosmics',        'color': 'black',  'marker': 'v'},
    'isochronous_cosmic':  {'label': 'Isochronous Cosmic', 'color': 'red',    'marker': 'o'},
    'normal_cosmic':       {'label': 'Normal Cosmic',      'color': 'green',  'marker': 's'},
    'prolonged_cosmic':    {'label': 'Prolonged Cosmic',   'color': 'blue',   'marker': '^'},
}

# Two off-scale bins below/left of the physical [0, 1] square, one per kind of
# cluster that has no partner and therefore no (purity, completeness) point:
#
#   EXTRA RECO     a reco cluster that is not the winner of any 1-to-1 pair.
#                  Two ways to become one, both counted here: no overlap with any
#                  true cluster at all, or overlap with a true cluster that a
#                  DIFFERENT reco cluster won (MatchTrueToReco1to1 keeps only the
#                  highest-completeness reco per true cluster, so the rest are
#                  extra). Either way the cluster contributes to no pair, so it
#                  has no (purity, completeness) point to be drawn at and sits in
#                  the bin nearest the origin instead.
#   UNMATCHED TRUE a true cluster matched to NO reco cluster. Completeness 0,
#                  purity undefined. Pushed to the outer bin to make room.
#
# Both are placeholders, not measurements: nothing inside either box is a real
# coordinate, which is why they are drawn outside [0, 1] and outlined rather than
# left to blend into the physical points.
_EXTRA_RECO_BOX_LO, _EXTRA_RECO_BOX_HI = -0.1, 0.0   # inner box, both axes
# A blue distinct from the 'blue' the matched points default to in this figure --
# same family, so extra reco still reads as a reco-side quantity, but light enough
# that the two series are told apart by colour and not only by marker.
_EXTRA_RECO_COLOR = 'deepskyblue'

_PURITY_UNMATCHED_TRUE_ID = 8888  # EvaluatePurity's "this reco touched no true cluster" sentinel
_UNMATCHED_BOX_LO,  _UNMATCHED_BOX_HI  = -0.2, -0.1  # outer box, both axes

def DrawCompletenessVsPurity_MatchedPairs(pair_metadata_list, output_dir, level_name, apa, file_name=None,
                                        all_true_metadata_list=None, filename_level=None,
                                        purity_results=None):
    """
    Draw purity-vs-completeness (x=Purity, y=Completeness) scatter and 2D histogram (colz)
    plots from 1-to-1 true-reco pair metadata (add_metadata_true_reco_pair_cluster).
    Used at Event, File, and Job level alike - level_name controls the title/filename,
    e.g. "Event 5", "File Level", "Job Level".

    filename_level overrides what goes in the FILENAME, leaving level_name to the
    title. Callers that decorate level_name with a population ("Job Level (true
    numu CC interactions)") pass the plain level here, so the same plot keeps the
    same filename in every population directory and can be diffed across them.

    Two kinds of partnerless cluster are drawn in dedicated off-scale bins below and
    left of the physical [0, 1] square, each outlined with a dashed box:

      - EXTRA RECO ([-0.1, 0]^2, the bin nearest the origin): reco clusters that
        won no 1-to-1 pair - either they overlap no true cluster at all, or they
        overlap one whose pair slot a higher-completeness reco took. The reco
        population comes from purity_results (one row per reco cluster), minus the
        reco ids present in pair_metadata_list. Drawn only when purity_results is
        passed. These clusters appear in no completeness or purity number the plot
        otherwise shows, so without this bin the reconstruction's over-splitting
        and its spurious clusters are both invisible here however many there are.
      - UNMATCHED TRUE ([-0.2, -0.1]^2, the outer bin): true clusters that never
        matched any reco cluster - present in all_true_metadata_list (from
        add_metadata_true_clusters) but absent from pair_metadata_list. Drawn only
        when all_true_metadata_list is passed.

    Extra reco is ATTRIBUTED to a true category and appears in that category's
    figure as well as in "All Clusters": each one is labelled with the type of the
    true cluster it overlaps most (its highest-purity purity_results row), so a
    reco cluster that split a true neutrino in two shows up in the neutrino figure,
    which is the figure that failure belongs in. Extra reco overlapping no true
    cluster at all cannot be attributed and appears in "All Clusters" only, so the
    per-category counts never claim a truth label that does not exist.

    Produces:
      - All Clusters: one scatter plot, one colz plot
      - Neutrino vs Cosmic: one overlaid scatter plot (2 colors) + separate colz per category
      - Neutrino + Cosmic-by-type: one overlaid scatter plot (4 colors) + separate colz per category
      - Cosmic-by-type only (isochronous/normal/prolonged): one overlaid scatter plot (3 colors)
    """
    # Nothing to draw only when there are no pairs AND no unmatched true clusters. An
    # event with zero 1-to-1 pairs (e.g. no reco cluster survived the beam-window cut)
    # still has something to show in the "including unmatched" variant: every true
    # cluster goes in the no-match box at completeness 0. The "excluding unmatched"
    # variant passes all_true_metadata_list=None and still returns here, as before.
    # Every inner helper already accepts empty `entries` with non-empty `unmatched_entries`.
    if not pair_metadata_list and not all_true_metadata_list and not purity_results:
        return

    def _in_category(metadata, category_key):
        if category_key == 'neutrino':
            return metadata['cluster_type'] == 'neutrino'
        if category_key == 'cosmic':
            return metadata['cluster_type'] == 'cosmic'
        return metadata['cluster_type'] == 'cosmic' and metadata['cluster_category'] == category_key.replace('_cosmic', '')

    # True clusters with no reco match at all: present in all_true_metadata_list but
    # absent from the 1-to-1 matched pair_metadata_list.
    if all_true_metadata_list:
        matched_keys = {(m['event'], m['true_cluster_id']) for m in pair_metadata_list}
        unmatched_metadata_list = [m for m in all_true_metadata_list
                                    if (m['event'], m['true_cluster_id']) not in matched_keys]
    else:
        unmatched_metadata_list = []
    # Only draw the "no match" box/legend when the caller actually asked for unmatched
    # true clusters to be tracked (all_true_metadata_list provided) - otherwise this is
    # the "excluding unmatched" variant and the box shouldn't appear at all.
    show_unmatched_box = bool(all_true_metadata_list)

    # Extra reco: every reco cluster that won no 1-to-1 pair. purity_results carries
    # a row for every reco cluster in the event (a real row per overlapping true
    # cluster, or one true_cluster_id=8888 sentinel row when it overlaps none), so
    # the reco ids in it are the full reco population; subtracting the ids that DID
    # win a pair leaves the extra ones. Both routes into the category land here:
    # zero overlap with any true cluster, and overlap with a true cluster whose
    # 1-to-1 slot a higher-completeness reco took.
    #
    # Both sides key on (event, reco_cluster_id) with event = the event_key string
    # ("file1_0"): EvaluatePurity is called with event_key everywhere in this repo,
    # and add_metadata_true_reco_pair_cluster stores event_key under 'event'. The
    # pair is needed because reco cluster ids are only unique within an event.
    #
    # Each extra reco is ATTRIBUTED to the true category of the true cluster it
    # overlaps most (its highest-purity purity_results row), so it can be drawn in
    # that category's figure and not only in "All Clusters". A reco cluster that
    # split a true neutrino in two is a fact about the NEUTRINO's reconstruction:
    # leaving it out of the neutrino figure hides exactly the failure that figure
    # exists to show. Extra reco overlapping no true cluster (the 8888 sentinel
    # rows) has no category to be attributed to and stays in "All Clusters" alone -
    # cluster_type None matches no category in _in_category.
    true_category_lookup = {}
    for m in list(all_true_metadata_list or []) + list(pair_metadata_list):
        true_category_lookup.setdefault((m['event'], m['true_cluster_id']),
                                        (m.get('cluster_type'), m.get('cluster_category')))

    if purity_results:
        paired_reco_ids = {(m['event'], m['reco_cluster_id']) for m in pair_metadata_list}
        all_reco_ids    = set()
        best_true_by_reco = {}      # (event, reco id) -> (purity, true cluster id)
        for p in purity_results:
            reco_key = (p['event'], p['reco_cluster_id'])
            all_reco_ids.add(reco_key)
            if p.get('true_cluster_id') == _PURITY_UNMATCHED_TRUE_ID:
                continue
            best = best_true_by_reco.get(reco_key)
            if best is None or p['purity'] > best[0]:
                best_true_by_reco[reco_key] = (p['purity'], p['true_cluster_id'])

        extra_reco_entries = []
        for reco_key in sorted(all_reco_ids - paired_reco_ids):
            best_purity, best_true_id = best_true_by_reco.get(reco_key, (None, None))
            cluster_type, cluster_category = true_category_lookup.get(
                (reco_key[0], best_true_id), (None, None))
            extra_reco_entries.append({
                'event':            reco_key[0],
                'reco_cluster_id':  reco_key[1],
                'purity':           best_purity,
                'true_cluster_id':  best_true_id,
                'cluster_type':     cluster_type,
                'cluster_category': cluster_category,
            })
    else:
        extra_reco_entries = []
    show_extra_reco_box = bool(purity_results)

    level_suffix = (filename_level or level_name).lower().replace(' ', '_')

    # Shared across all jitter draws in this call, so unmatched points from
    # different categories/plots don't land on identical coordinates and hide each other.
    _jitter_rng = np.random.default_rng(42)

    def _title_suffix():
        return f' ({file_name})' if file_name else ''

    def _axis_limits():
        # Reach down to whichever off-scale box is actually drawn. With neither
        # (the "excluding unmatched" variant) this still returns the -0.12 the plot
        # has always used, so those figures keep their framing unchanged.
        lo = _UNMATCHED_BOX_LO if show_unmatched_box else _EXTRA_RECO_BOX_LO
        return (lo - 0.02, 1.02)

    def _jitter_in_box(n, box_lo, box_hi):
        if n == 0:
            return np.array([]), np.array([])
        x = _jitter_rng.uniform(box_lo + 0.005, box_hi - 0.005, n)
        y = _jitter_rng.uniform(box_lo + 0.005, box_hi - 0.005, n)
        return x, y

    def _jitter_unmatched(n):
        return _jitter_in_box(n, _UNMATCHED_BOX_LO, _UNMATCHED_BOX_HI)

    def _jitter_extra_reco(n):
        return _jitter_in_box(n, _EXTRA_RECO_BOX_LO, _EXTRA_RECO_BOX_HI)

    def _draw_box(box_lo, box_hi, edgecolor):
        plt.gca().add_patch(Rectangle(
            (box_lo, box_lo), box_hi - box_lo, box_hi - box_lo,
            fill=False, edgecolor=edgecolor, linestyle='--', linewidth=1.5))

    def _format_axes(with_extra_reco_box=False):
        lo, hi = _axis_limits()
        plt.xlim(lo, hi)
        plt.ylim(lo, hi)
        if show_unmatched_box:
            _draw_box(_UNMATCHED_BOX_LO, _UNMATCHED_BOX_HI, 'gray')
        if with_extra_reco_box and show_extra_reco_box:
            _draw_box(_EXTRA_RECO_BOX_LO, _EXTRA_RECO_BOX_HI, _EXTRA_RECO_COLOR)
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.xlabel('Purity', fontsize=20, fontweight='bold')
        plt.ylabel('Completeness', fontsize=20, fontweight='bold')
        plt.xticks(fontsize=16)
        plt.yticks(fontsize=16)

    def _scatter(entries, category_name, filename_tag, unmatched_entries=None, color='blue', marker='o',
                 extra_reco_entries=None):
        unmatched_entries = unmatched_entries or []
        extra_reco_entries = extra_reco_entries or []
        if not entries and not unmatched_entries and not extra_reco_entries:
            return
        purities     = [m['purity'] for m in entries]
        completenesses = [m['completeness'] for m in entries]

        plt.figure(figsize=(14, 11))
        if entries:
            plt.scatter(purities, completenesses, color=color, marker=marker, alpha=0.7, s=100, edgecolors='black', linewidth=0.5,
                        label=f"Matched ({len(entries)})")
        if unmatched_entries:
            ux, uy = _jitter_unmatched(len(unmatched_entries))
            plt.scatter(ux, uy, color='gray', marker='x', alpha=0.8, s=100, linewidth=2,
                        label=f"Unmatched true, no reco match ({len(unmatched_entries)})")
        if extra_reco_entries:
            ex, ey = _jitter_extra_reco(len(extra_reco_entries))
            plt.scatter(ex, ey, color=_EXTRA_RECO_COLOR, marker='+', alpha=0.9, s=120, linewidth=2,
                        label=f"Extra reco, no 1-to-1 pair ({len(extra_reco_entries)})")

        total = len(entries) + len(unmatched_entries) + len(extra_reco_entries)
        plt.title(f"Completeness vs Purity - {category_name} ({level_name}), {apa}, {total} clusters{_title_suffix()}",
                  fontsize=16, fontweight='bold', wrap=True)
        _format_axes(with_extra_reco_box=bool(extra_reco_entries))
        plt.legend(fontsize=12)
        plt.subplots_adjust(left=0.15, right=0.95, top=0.90, bottom=0.12)
        plt.savefig(output_dir / f"completeness_vs_purity_scatter_{filename_tag}_{level_suffix}_{apa}.png",
                    dpi=150, bbox_inches='tight', pad_inches=0.3)
        plt.close()

    def _scatter_overlay(category_keys, group_label, filename_tag):
        entries_by_cat    = {k: [m for m in pair_metadata_list if _in_category(m, k)] for k in category_keys}
        unmatched_by_cat  = {k: [m for m in unmatched_metadata_list if _in_category(m, k)] for k in category_keys}
        extra_by_cat      = {k: [m for m in extra_reco_entries if _in_category(m, k)] for k in category_keys}
        if not any(entries_by_cat.values()) and not any(unmatched_by_cat.values()) \
                and not any(extra_by_cat.values()):
            return

        plt.figure(figsize=(14, 11))
        for category_key in category_keys:
            info    = _EFF_PUR_CATEGORY_STYLE[category_key]
            entries = entries_by_cat[category_key]
            if entries:
                purities     = [m['purity'] for m in entries]
                completenesses = [m['completeness'] for m in entries]
                plt.scatter(purities, completenesses, color=info['color'], marker=info['marker'], alpha=0.6, s=80,
                            edgecolors='black', linewidth=0.5, label=f"{info['label']} ({len(entries)})")

            unmatched = unmatched_by_cat[category_key]
            if unmatched:
                ux, uy = _jitter_unmatched(len(unmatched))
                plt.scatter(ux, uy, color=info['color'], marker='x', alpha=0.8, s=90, linewidth=2,
                            label=f"{info['label']} unmatched ({len(unmatched)})")

            extra = extra_by_cat[category_key]
            if extra:
                ex, ey = _jitter_extra_reco(len(extra))
                plt.scatter(ex, ey, color=info['color'], marker='+', alpha=0.9, s=110, linewidth=2,
                            label=f"{info['label']} extra reco ({len(extra)})")

        total = (sum(len(v) for v in entries_by_cat.values())
                 + sum(len(v) for v in unmatched_by_cat.values())
                 + sum(len(v) for v in extra_by_cat.values()))
        plt.title(f"Completeness vs Purity - {group_label} ({level_name}), {apa}, {total} clusters{_title_suffix()}",
                  fontsize=16, fontweight='bold', wrap=True)
        _format_axes(with_extra_reco_box=any(extra_by_cat.values()))
        plt.legend(fontsize=11)
        plt.subplots_adjust(left=0.15, right=0.95, top=0.90, bottom=0.12)
        plt.savefig(output_dir / f"completeness_vs_purity_scatter_{filename_tag}_{level_suffix}_{apa}.png",
                    dpi=150, bbox_inches='tight', pad_inches=0.3)
        plt.close()

    def _colz(entries, category_name, filename_tag, unmatched_entries=None, extra_reco_entries=None):
        unmatched_entries = unmatched_entries or []
        extra_reco_entries = extra_reco_entries or []
        if not entries and not unmatched_entries and not extra_reco_entries:
            return
        purities     = [m['purity'] for m in entries]
        completenesses = [m['completeness'] for m in entries]
        # Place all partnerless clusters at a single representative point inside their
        # own box, so each kind collects into exactly one 2D-histogram cell.
        if unmatched_entries:
            box_mid = (_UNMATCHED_BOX_LO + _UNMATCHED_BOX_HI) / 2
            purities     = purities + [box_mid] * len(unmatched_entries)
            completenesses = completenesses + [box_mid] * len(unmatched_entries)
        if extra_reco_entries:
            box_mid = (_EXTRA_RECO_BOX_LO + _EXTRA_RECO_BOX_HI) / 2
            purities     = purities + [box_mid] * len(extra_reco_entries)
            completenesses = completenesses + [box_mid] * len(extra_reco_entries)

        # One wide bin per off-scale box, then regular bins across [0, 1]. The extra
        # reco box's lower edge is always present so this variant's binning inside
        # [0, 1] is identical whether or not the outer box is drawn; np.linspace's
        # first edge IS _EXTRA_RECO_BOX_HI (0.0), so no duplicate edge is produced.
        special_edges = ([_UNMATCHED_BOX_LO, _EXTRA_RECO_BOX_LO] if show_unmatched_box
                         else [_EXTRA_RECO_BOX_LO])
        edges = np.concatenate((special_edges, np.linspace(0, 1, 41)))

        plt.figure(figsize=(14, 11))
        h = plt.hist2d(purities, completenesses, bins=[edges, edges], cmap='YlOrRd')
        cbar = plt.colorbar(h[3], label='Count')
        cbar.set_label('Count', fontsize=18, fontweight='bold')
        cbar.ax.tick_params(labelsize=16)

        total = len(entries) + len(unmatched_entries) + len(extra_reco_entries)
        plt.title(f"Completeness vs Purity 2D Histogram - {category_name} ({level_name}), {apa}, {total} clusters{_title_suffix()}",
                  fontsize=16, fontweight='bold', wrap=True)
        _format_axes(with_extra_reco_box=bool(extra_reco_entries))
        plt.subplots_adjust(left=0.15, right=0.92, top=0.90, bottom=0.12)
        plt.savefig(output_dir / f"completeness_vs_purity_colz_{filename_tag}_{level_suffix}_{apa}.png",
                    dpi=150, bbox_inches='tight', pad_inches=0.3)
        plt.close()

    # All clusters -- every extra reco, including the ones no category could claim.
    _scatter(pair_metadata_list, "All Clusters", "all", unmatched_entries=unmatched_metadata_list,
             extra_reco_entries=extra_reco_entries)
    _colz(pair_metadata_list, "All Clusters", "all", unmatched_entries=unmatched_metadata_list,
          extra_reco_entries=extra_reco_entries)

    # Overlaid scatter groupings
    _scatter_overlay(['neutrino', 'cosmic'],
                      "Neutrino vs Cosmic", "neutrino_vs_cosmic")
    _scatter_overlay(['neutrino', 'isochronous_cosmic', 'normal_cosmic', 'prolonged_cosmic'],
                      "Neutrino + Cosmic by Type", "neutrino_and_cosmic_by_type")
    _scatter_overlay(['isochronous_cosmic', 'normal_cosmic', 'prolonged_cosmic'],
                      "Cosmic by Type", "cosmic_by_type")

    # Separate scatter and colz figure per individual category
    for category_key in ['neutrino', 'cosmic', 'isochronous_cosmic', 'normal_cosmic', 'prolonged_cosmic']:
        category_entries   = [m for m in pair_metadata_list if _in_category(m, category_key)]
        category_unmatched = [m for m in unmatched_metadata_list if _in_category(m, category_key)]
        category_extra     = [m for m in extra_reco_entries if _in_category(m, category_key)]
        info = _EFF_PUR_CATEGORY_STYLE[category_key]
        _scatter(category_entries, info['label'], category_key,
                 unmatched_entries=category_unmatched, color=info['color'], marker=info['marker'],
                 extra_reco_entries=category_extra)
        _colz(category_entries, info['label'], category_key,
              unmatched_entries=category_unmatched, extra_reco_entries=category_extra)

# Function to match true and reco clusters based on purity and completeness results
# make pairing based on highest purity for each true cluster, then ensure one-to-one matching by keeping only the best pair for each reco cluster
# TODO: we need to change matching creteria to energy-weighted completeness instead of purity

def DrawCompletenessVsTrueEnergyAllEvents(all_completeness_results, input_directories_map, output_dir, apa):
    """
    Draw 2D colz histogram of completeness vs TRUE cluster energy for ALL events.
    Then create a 1D projection showing mean completeness vs TRUE cluster energy bins.
    Saves organized in hierarchy: output_dir/input_file/event_N/completeness/
    X-axis: total TRUE cluster energy
    Y-axis: completeness (energy-weighted)
    """

    # Group results by event
    results_by_event = {}
    for result in all_completeness_results:
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
            print(f"Warning: No input directory found for event {event}, skipping completeness plots")
            continue

        input_dir, evt_num = input_directories_map[event_key]

        input_file_name = input_dir.parent.name

        # Create hierarchical directory: output_dir/input_file/event_N/completeness/
        event_output_dir = output_dir / input_file_name / f"event_{event:03d}" / "completeness"
        event_output_dir.mkdir(parents=True, exist_ok=True)

        # Extract completeness and true energy information for this event
        true_energies = []
        completenesses = []
        ghost_energies = []

        for result in event_results:
            true_energy = result.get('total_true_cluster_energy', 0)
            completeness = result.get('completeness_energy_weighted', 0)

            if true_energy > 0:
                # Check for unmatched clusters (completeness=-0.1 sentinel)
                if abs(completeness - (-0.1)) < 0.001:
                    ghost_energies.append(true_energy)
                elif completeness > 0:
                    true_energies.append(true_energy)
                    completenesses.append(completeness)

        if len(true_energies) == 0 and len(ghost_energies) == 0:
            print(f"No valid completeness vs energy data for event {event}")
            continue

        print(f"\nEvent {event} ({input_file_name}):")
        print(f"  Plotting {len(true_energies)} matched cluster points")
        if len(ghost_energies) > 0:
            print(f"  Ghost tracks: {len(ghost_energies)}")

        # Add ghost clusters to histogram at (0, 0)
        if len(ghost_energies) > 0:
            true_energies.extend([0] * len(ghost_energies))
            completenesses.extend([0] * len(ghost_energies))
            print(f'  Added {len(ghost_energies)} ghost clusters at (0,0)')
        # Create 2D colz histogram
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))

        # 2D histogram
        if true_energies:
            h = ax1.hist2d(true_energies, completenesses, bins=40, cmap='YlOrRd', range=[[0, max(true_energies)*1.25], [-0.2, 1.05]])
            cbar1 = plt.colorbar(h[3], ax=ax1, label='Count')
            cbar1.set_label('Count', fontsize=16, fontweight='bold')
            cbar1.ax.tick_params(labelsize=14)

            ax1.scatter(true_energies, completenesses, alpha=0.3, s=20, color='black', marker='.')

        # Set x-axis limits to show both matched and unmatched clusters
        all_energies = true_energies + ghost_energies if ghost_energies else true_energies
        x_max = max(all_energies)*1.25 if all_energies else 10
        ax1.set_xlim(0, x_max)
        ax1.set_ylim(-0.2, 1.05)
        ax1.axvline(x=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax1.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)

        ax1.set_xlabel('True Cluster Energy [MeV]', fontsize=18, fontweight='bold')
        ax1.set_ylabel('Completeness (Energy-Weighted)', fontsize=18, fontweight='bold')
        ax1.set_title(f'2D Histogram: Completeness vs True Energy (Event {event})', fontsize=18, fontweight='bold', wrap=True)
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
        mean_completeness_per_bin = []
        bin_counts = []

        if true_energies:
            for i in range(len(energy_bins)-1):
                mask = (np.array(true_energies) >= energy_bins[i]) & (np.array(true_energies) < energy_bins[i+1])
                if np.sum(mask) > 0:
                    mean_eff = np.mean(np.array(completenesses)[mask])
                    count = np.sum(mask)
                    mean_completeness_per_bin.append(mean_eff)
                    bin_counts.append(count)
                else:
                    mean_completeness_per_bin.append(0)
                    bin_counts.append(0)

        non_empty_mask = np.array(bin_counts) > 0
        valid_bin_centers = bin_centers[non_empty_mask]
        valid_mean_completeness = np.array(mean_completeness_per_bin)[non_empty_mask]

        if len(valid_bin_centers) > 0:
            ax2.plot(valid_bin_centers, valid_mean_completeness, 'o-', linewidth=3, markersize=12,
                    color='darkblue', label='Mean Completeness per Bin')

        if len(ghost_energies) > 0:
            # Plot unmatched clusters at their true energy but at y=0 (zero completeness)
            ghost_y_1d = np.zeros(len(ghost_energies))
            ax2.scatter(ghost_energies, ghost_y_1d, c='purple', s=30, alpha=0.6, marker='X',
                label=f'Unmatched Clusters ({len(ghost_energies)})', edgecolors='darkviolet', linewidths=1)

        ax2.set_xlim(-100, max(true_energies)*1.25 if true_energies else 10)
        ax2.set_ylim(-0.2, 1.05)
        ax2.axvline(x=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax2.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)

        ax2.set_xlabel('True Cluster Energy [MeV]', fontsize=18, fontweight='bold')
        ax2.set_ylabel('Completeness', fontsize=18, fontweight='bold')
        ax2.set_title(f'1D Projection: Mean Completeness vs True Energy (Event {event})', fontsize=18, fontweight='bold', wrap=True)
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
        plt.savefig(event_output_dir / f"completeness_vs_true_energy_{apa}.png", dpi=150, bbox_inches='tight', pad_inches=0.3)
    plt.close()
        # ##plt.show(block=False)

def DrawCompletenessSummaryAllFilesAllEvents(all_completeness_results, output_dir, apa):
    """
    Draw summary 2D and 1D plots aggregating completeness across ALL files and ALL events.
    Saves to top-level output_dir (not nested in file/event subdirectories).
    """

    if len(all_completeness_results) == 0:
        print("No completeness results for summary plots")
        return

    output_dir = Path(output_dir)

    # Extract all completeness and energy data
    true_energies = []
    completenesses = []
    ghost_energies = []

    for result in all_completeness_results:
        true_energy = result.get('total_true_cluster_energy', 0)
        completeness = result.get('completeness_energy_weighted', 0)

        if true_energy > 0:
            if completeness > 0:
                true_energies.append(true_energy)
                completenesses.append(completeness)
            else:
                ghost_energies.append(true_energy)

    if len(true_energies) == 0:
        print("No valid completeness data for summary")
        return

    print(f"\n{'='*60}")
    print(f"SUMMARY: Completeness across ALL files and ALL events")
    print(f"{'='*60}")
    print(f"Total matched clusters: {len(true_energies)}")
    print(f"Ghost tracks: {len(ghost_energies)}")

    # Create summary 2D and 1D plots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))

    # 2D histogram
    h = ax1.hist2d(true_energies, completenesses, bins=40, cmap='YlOrRd',
                    range=[[0, max(true_energies)*1.25], [0, 1.05]])
    cbar1 = plt.colorbar(h[3], ax=ax1, label='Count')
    cbar1.set_label('Count', fontsize=16, fontweight='bold')
    cbar1.ax.tick_params(labelsize=14)

    ax1.scatter(true_energies, completenesses, alpha=0.3, s=20, color='black', marker='.')

    if len(ghost_energies) > 0:
        ghost_y = np.full_like(ghost_energies, -0.1)
        ax1.scatter([-50]*len(ghost_energies), ghost_y, c='purple', s=30, alpha=0.6, marker='X',
                    label=f'Ghost Tracks ({len(ghost_energies)})', edgecolors='darkviolet', linewidth=1)

    ax1.set_xlim(-100, max(true_energies)*1.25)
    ax1.set_ylim(-0.2, 1.05)
    ax1.axvline(x=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax1.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)

    ax1.set_xlabel('True Cluster Energy [MeV]', fontsize=18, fontweight='bold')
    ax1.set_ylabel('Completeness (Energy-Weighted)', fontsize=18, fontweight='bold')
    ax1.set_title(f'SUMMARY: Completeness vs True Energy (All Files, All Events)', fontsize=18, fontweight='bold', wrap=True)
    ax1.tick_params(labelsize=14)
    ax1.grid(True, linestyle='--', alpha=0.3)
    if len(ghost_energies) > 0:
        ax1.legend(fontsize=12, loc='upper left')

    # 1D projection
    n_bins = 20
    energy_bins = np.linspace(0, max(true_energies)*1.25, n_bins+1)
    bin_centers = (energy_bins[:-1] + energy_bins[1:]) / 2
    mean_completeness_per_bin = []
    bin_counts = []

    for i in range(len(energy_bins)-1):
        mask = (np.array(true_energies) >= energy_bins[i]) & (np.array(true_energies) < energy_bins[i+1])
        if np.sum(mask) > 0:
            mean_eff = np.mean(np.array(completenesses)[mask])
            count = np.sum(mask)
            mean_completeness_per_bin.append(mean_eff)
            bin_counts.append(count)
        else:
            mean_completeness_per_bin.append(0)
            bin_counts.append(0)

    non_empty_mask = np.array(bin_counts) > 0
    valid_bin_centers = bin_centers[non_empty_mask]
    valid_mean_completeness = np.array(mean_completeness_per_bin)[non_empty_mask]

    if len(valid_bin_centers) > 0:
        ax2.plot(valid_bin_centers, valid_mean_completeness, 'o-', linewidth=3, markersize=12,
                color='darkblue', label='Mean Completeness per Bin')

    if len(ghost_energies) > 0:
        ghost_y_1d = np.full_like(ghost_energies, -0.1)
        ax2.scatter([-50]*len(ghost_energies), ghost_y_1d, c='purple', s=30, alpha=0.6, marker='X',
                    label=f'Ghost Tracks ({len(ghost_energies)})', edgecolors='darkviolet', linewidth=1)

    ax2.set_xlim(-100, max(true_energies)*1.25)
    ax2.set_ylim(-0.2, 1.05)
    ax2.axvline(x=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax2.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)

    ax2.set_xlabel('True Cluster Energy [MeV]', fontsize=18, fontweight='bold')
    ax2.set_ylabel('Completeness', fontsize=18, fontweight='bold')
    ax2.set_title(f'SUMMARY: 1D Projection (All Files, All Events)', fontsize=18, fontweight='bold', wrap=True)
    ax2.tick_params(labelsize=14)
    ax2.grid(True, linestyle='--', alpha=0.3)
    ax2.legend(fontsize=14, loc='lower right')

    plt.tight_layout()
    plt.savefig(output_dir / f"SUMMARY_completeness_vs_true_energy_{apa}.png", dpi=150, bbox_inches='tight', pad_inches=0.3)
    plt.close()
    ## ##plt.show(block=False)
    print(f"Saved: {output_dir}/SUMMARY_completeness_vs_true_energy_{apa}.png\n")

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
    ax1.set_title(f'SUMMARY: Purity vs Reco Charge (All Files, All Events)', fontsize=18, fontweight='bold', wrap=True)
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
    ax2.set_title(f'SUMMARY: 1D Projection (All Files, All Events)', fontsize=18, fontweight='bold', wrap=True)
    ax2.tick_params(labelsize=14)
    ax2.grid(True, linestyle='--', alpha=0.3)
    ax2.legend(fontsize=14, loc='lower right')

    plt.tight_layout()
    plt.savefig(output_dir / f"SUMMARY_purity_vs_reco_charge_{apa}.png", dpi=150, bbox_inches='tight', pad_inches=0.3)
    plt.close()
    ## ##plt.show(block=False)
    print(f"Saved: {output_dir}/SUMMARY_purity_vs_reco_charge_{apa}.png\n")

def DrawProblematicClusters(all_completeness_results, output_dir, n_clusters=3):
    """
    Find and draw high-energy, low-completeness clusters to understand why they fail.
    Creates spatial visualizations (XZ and YZ) for the worst performers.
    """

    # Convert to DataFrame for easier filtering
    df = pd.DataFrame(all_completeness_results)
    df = df.sort_values('total_true_cluster_energy', ascending=False)

    # Find high-energy clusters (top 25% by energy)
    high_energy_threshold = df['total_true_cluster_energy'].quantile(0.75)
    high_energy_df = df[df['total_true_cluster_energy'] > high_energy_threshold].copy()

    # Find those with very low completeness (0 or < 0.2)
    low_eff_df = high_energy_df[high_energy_df['completeness_energy_weighted'] < 0.2].copy()
    low_eff_df = low_eff_df.sort_values('total_true_cluster_energy', ascending=False)

    if len(low_eff_df) == 0:
        print("No high-energy, low-completeness clusters found to visualize")
        return

    # Select top N problematic clusters
    problematic = low_eff_df.head(n_clusters)

    print(f"\n{'='*80}")
    print(f"DRAWING {len(problematic)} HIGH-ENERGY, LOW-COMPLETENESS CLUSTERS")
    print(f"{'='*80}")

    for idx, (_, row) in enumerate(problematic.iterrows(), 1):
        event = int(row['event'])
        true_cluster_id = row['true_cluster_id']
        reco_cluster_id = row['reco_cluster_id']
        true_energy = row['total_true_cluster_energy']
        matched_energy = row['matched_true_cluster_energy']
        completeness = row['completeness_energy_weighted']

        print(f"\nCluster {idx}/{len(problematic)}: Event {event}")
        print(f"  True Cluster ID: {true_cluster_id:.2f}")
        print(f"  Reco Cluster ID: {reco_cluster_id:.2f}")
        print(f"  True Energy: {true_energy:.2f} MeV")
        print(f"  Matched Energy: {matched_energy:.2f} MeV")
        print(f"  Completeness: {completeness:.4f} (VERY LOW!)")
        print(f"  Problem: High energy but only {matched_energy:.2f}/{true_energy:.2f} = {completeness*100:.1f}% matched")

    print(f"\n{'='*80}")
    print("ANALYSIS:")
    print("- These clusters have HIGH true energy but VERY LOW completeness")
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
        ax1.set_title(f'2D Histogram: Purity vs Reco Charge (Event {event})', fontsize=18, fontweight='bold', wrap=True)
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
        ax2.set_title(f'1D Projection: Mean Purity vs Reco Charge (Event {event})', fontsize=18, fontweight='bold', wrap=True)
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
        ax1.set_title(f'2D Histogram: Purity vs Reco Charge (Event {event})', fontsize=18, fontweight='bold', wrap=True)
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
        ax2.set_title(f'1D Projection: Mean Purity vs Reco Charge (Event {event})', fontsize=18, fontweight='bold', wrap=True)
        ax2.tick_params(labelsize=14)
        ax2.grid(True, linestyle='--', alpha=0.3)
        ax2.legend(fontsize=14, loc='lower right')

        plt.tight_layout()
        plt.savefig(event_output_dir / f"purity_vs_reco_charge_{apa}.png", dpi=150, bbox_inches='tight', pad_inches=0.3)
        plt.close()
        print(f"  Saved: {event_output_dir}/purity_vs_reco_charge_{apa}.png")

def DrawCompletenessSummaryPerFile(all_completeness_results, input_directories_map, output_dir):
    """
    Draw summary 2D and 1D plots aggregating completeness across ALL events within EACH file.
    Saves to: output_dir/input_file/SUMMARY_completeness/
    """

    # Group results by file
    results_by_file = {}
    for result in all_completeness_results:
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
        # Extract completeness and energy data for this file
        true_energies = []
        completenesses = []
        ghost_energies = []

        for result in file_results:
            true_energy = result.get('total_true_cluster_energy', 0)
            completeness = result.get('completeness_energy_weighted', 0)

            if true_energy > 0:
                if completeness > 0:
                    true_energies.append(true_energy)
                    completenesses.append(completeness)
                else:
                    ghost_energies.append(true_energy)

        if len(true_energies) == 0:
            print(f"No valid completeness data for file {file_name}")
            continue

        print(f"\nFile Summary: Completeness for {file_name}")
        print(f"  Total matched clusters: {len(true_energies)}")
        print(f"  Ghost tracks: {len(ghost_energies)}")

        # Create output directory: output_dir/input_file/SUMMARY_completeness/
        file_output_dir = output_dir / file_name / "SUMMARY_completeness"
        file_output_dir.mkdir(parents=True, exist_ok=True)

        # Create 2D and 1D plots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))

        # 2D histogram
        h = ax1.hist2d(true_energies, completenesses, bins=40, cmap='YlOrRd',
                        range=[[0, max(true_energies)*1.25], [0, 1.05]])
        cbar1 = plt.colorbar(h[3], ax=ax1, label='Count')
        cbar1.set_label('Count', fontsize=16, fontweight='bold')
        cbar1.ax.tick_params(labelsize=14)

        ax1.scatter(true_energies, completenesses, alpha=0.3, s=20, color='black', marker='.')

        if len(ghost_energies) > 0:
            ghost_y = np.full_like(ghost_energies, -0.1)
            ax1.scatter([-50]*len(ghost_energies), ghost_y, c='purple', s=30, alpha=0.6, marker='X',
                        label=f'Ghost Tracks ({len(ghost_energies)})', edgecolors='darkviolet', linewidth=1)

        ax1.set_xlim(-100, max(true_energies)*1.25)
        ax1.set_ylim(-0.2, 1.05)
        ax1.axvline(x=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax1.set_xlabel('True Cluster Energy [MeV]', fontsize=18, fontweight='bold')
        ax1.set_ylabel('Completeness (Energy-Weighted)', fontsize=18, fontweight='bold')
        ax1.set_title(f'File Summary: Completeness vs True Energy ({file_name})', fontsize=18, fontweight='bold', wrap=True)
        ax1.tick_params(labelsize=14)
        ax1.grid(True, linestyle='--', alpha=0.3)
        if len(ghost_energies) > 0:
            ax1.legend(fontsize=12, loc='upper left')

        # 1D projection
        n_bins = 20
        energy_bins = np.linspace(0, max(true_energies)*1.25, n_bins+1)
        bin_centers = (energy_bins[:-1] + energy_bins[1:]) / 2
        mean_completeness_per_bin = []
        bin_counts = []

        for i in range(len(energy_bins)-1):
            mask = (np.array(true_energies) >= energy_bins[i]) & (np.array(true_energies) < energy_bins[i+1])
            if np.sum(mask) > 0:
                mean_eff = np.mean(np.array(completenesses)[mask])
                count = np.sum(mask)
                mean_completeness_per_bin.append(mean_eff)
                bin_counts.append(count)
            else:
                mean_completeness_per_bin.append(0)
                bin_counts.append(0)

        # Plot 1D projection
        ax2.bar(bin_centers, mean_completeness_per_bin, width=energy_bins[1]-energy_bins[0],
                alpha=0.7, color='steelblue', edgecolor='black')

        # Add count labels on bars
        for i, (x, y, count) in enumerate(zip(bin_centers, mean_completeness_per_bin, bin_counts)):
            if count > 0:
                ax2.text(x, y + 0.03, f'n={int(count)}', ha='center', fontsize=10, fontweight='bold')

        ax2.set_xlabel('True Cluster Energy [MeV]', fontsize=18, fontweight='bold')
        ax2.set_ylabel('Mean Completeness', fontsize=18, fontweight='bold')
        ax2.set_title(f'File Summary: Mean Completeness vs Energy Bins ({file_name})', fontsize=18, fontweight='bold', wrap=True)
        ax2.set_ylim(0, 1.1)
        ax2.tick_params(labelsize=14)
        ax2.grid(True, linestyle='--', alpha=0.3, axis='y')

        plt.tight_layout()

        # Save plot
        filename = f"completeness_summary_{file_name}.png"
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
        ax1.set_title(f'File Summary: Purity vs Reco Charge ({file_name})', fontsize=18, fontweight='bold', wrap=True)
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
        ax2.set_title(f'File Summary: Mean Purity vs Charge Bins ({file_name})', fontsize=18, fontweight='bold', wrap=True)
        ax2.set_ylim(0, 1.1)
        ax2.tick_params(labelsize=14)
        ax2.grid(True, linestyle='--', alpha=0.3, axis='y')

        plt.tight_layout()

        # Save plot
        filename = f"purity_summary_{file_name}.png"
        plt.savefig(file_output_dir / filename, dpi=100, bbox_inches='tight', pad_inches=0.3)
        plt.close()




def summarize_cluster_completeness_by_energy(pair_metadata_list, all_true_metadata_list=None,
                                           energy_threshold=500):
    """
    Mean completeness below vs above an energy threshold, for the SAME cluster
    population the completeness_2d_1d_clusteringlevel 1D plots are drawn from:
    _combine_pairs_with_unmatched(pair_metadata_list, all_true_metadata_list),
    i.e. 1-to-1 matched true-reco pairs PLUS true clusters that never matched
    any reco cluster, the latter entering at completeness=0. Pass the same two
    lists given to DrawClusterCompletenessVsTrueEnergyPerJob and these numbers
    describe exactly the curves in
    completeness_vs_true_energy_1d_clusteringlevel_job_*.png and its by-category
    companion -- drop all_true_metadata_list and it instead describes the
    pairs-only directory's plots.

    The mean is CLUSTER-weighted (mean over every cluster on that side of the
    threshold), not the unweighted mean of the plotted per-bin means: the 1D
    plot's bins hold wildly different cluster counts, so averaging the bin
    values would let a bin holding one cluster count as much as a bin holding
    hundreds. Reading a single "average completeness below/above X MeV" off that
    curve by eye is really this number.

    Returns a list of dicts, one for all clusters plus one per category present:
        {'category', 'n_below', 'mean_below', 'n_above', 'mean_above', 'n_total'}
    with mean_* None when that side has no clusters. Categories use the same
    definitions as the by-category 1D plot (neutrino, isochronous/normal/
    prolonged cosmic).
    """
    all_entries = _combine_pairs_with_unmatched(pair_metadata_list, all_true_metadata_list)
    if not all_entries:
        return []

    def _in_category(metadata, category_key):
        if category_key == 'neutrino':
            return metadata['cluster_type'] == 'neutrino'
        return metadata['cluster_type'] == 'cosmic' and metadata['cluster_category'] == category_key.replace('_cosmic', '')

    def _summarize(entries, label):
        below = [m['completeness'] for m in entries if m['total_true_energy'] < energy_threshold]
        above = [m['completeness'] for m in entries if m['total_true_energy'] >= energy_threshold]
        return {
            'category':   label,
            'n_total':    len(entries),
            'n_below':    len(below),
            'mean_below': float(np.mean(below)) if below else None,
            'n_above':    len(above),
            'mean_above': float(np.mean(above)) if above else None,
        }

    category_labels = {
        'neutrino':           'Neutrino Clusters',
        'isochronous_cosmic': 'Isochronous Cosmic',
        'normal_cosmic':      'Normal Cosmic',
        'prolonged_cosmic':   'Prolonged Cosmic',
    }

    records = [_summarize(all_entries, 'All Clusters')]
    for category_key, label in category_labels.items():
        category_entries = [m for m in all_entries if _in_category(m, category_key)]
        if category_entries:
            records.append(_summarize(category_entries, label))
    return records


def format_cluster_completeness_by_energy(records, energy_threshold=500):
    """
    Render summarize_cluster_completeness_by_energy()'s records as text lines for
    job_summary/summary.txt. Returns [] for empty records so the caller can
    extend() unconditionally.
    """
    if not records:
        return []

    lines = [
        f"Completeness vs True Energy (clusteringlevel 1D plots, split at {energy_threshold} MeV):",
        "  Mean completeness, cluster-weighted; includes unmatched true clusters at completeness=0",
        f"  {'category':<22} {'<'+str(energy_threshold)+' MeV':>12} {'n':>7} {'>='+str(energy_threshold)+' MeV':>13} {'n':>7}",
    ]
    for r in records:
        below = f"{r['mean_below']:.4f}" if r['mean_below'] is not None else "n/a"
        above = f"{r['mean_above']:.4f}" if r['mean_above'] is not None else "n/a"
        lines.append(f"  {r['category']:<22} {below:>12} {r['n_below']:>7} {above:>13} {r['n_above']:>7}")
    lines.append("")
    return lines


# ============================================================================
# POPULATION COMPARISON PLOTS (job level)
# ============================================================================
# Several neutrino populations overlaid on ONE canvas so they can be compared
# directly instead of by flipping between output directories. Two splits use
# these: in-volume vs out-of-volume vertices, and the numu CC / nue CC / NC
# interaction channels. Everything else about either split renders each
# population into its own directory; these two drawers are the only place the
# curves meet.
#
# Both take records that were computed ONCE against the full true and reco
# populations and merely filtered (see metadata.filter_records_by_label) --
# nothing here recomputes an completeness or a purity, so a curve drawn here is the
# same curve as in that population's own directory, on shared bins.
#
# SHARED BINNING is the point of these functions: bins and x-limit are derived
# from ALL the populations combined. Letting each population bin itself would put
# the curves on different bin centres and different axes -- plots that look
# comparable and are not.


def _order_legend_like(ax, keys, styles, population_note=None, fontsize=15):
    """
    The legend, plus the line of text that says WHICH neutrino population the plot
    is drawn from, sitting directly above it.

    Two jobs beyond calling ax.legend():

    ORDER -- entries follow the CALLER's population order, whatever order the
    curves were drawn in (they are drawn largest-population-first so a
    single-cluster channel is not buried). Matched by the style label each curve's
    legend text starts with.

    PLACEMENT -- both go in the reserved band above y=1.05 that the callers open
    up with their y-limit. Completeness and purity are both bounded by 1, so nothing
    can ever be drawn there and the legend cannot cover a curve. That is why the
    band exists rather than relying on loc='best', which only minimises overlap
    and still lands on top of a curve when the plot is busy.
    """
    handles, labels = ax.get_legend_handles_labels()
    wanted = [styles[key]['label'] for key in keys if key in styles]
    ordered = [(h, l) for w in wanted for h, l in zip(handles, labels) if l.startswith(w)]
    # Anything unmatched (a label whose style is missing) keeps its drawn order.
    ordered += [(h, l) for h, l in zip(handles, labels) if not any(l is ol for _, ol in ordered)]

    if ordered:
        legend = ax.legend([h for h, _ in ordered], [l for _, l in ordered],
                           fontsize=fontsize, loc='upper center',
                           bbox_to_anchor=(0.5, 0.90), framealpha=0.95,
                           borderpad=0.6, labelspacing=0.4)
    else:
        legend = ax.legend(fontsize=fontsize, loc='upper center',
                           bbox_to_anchor=(0.5, 0.90), framealpha=0.95)

    if not population_note:
        return

    # Above the legend box, in axes coordinates -- needs a draw first so the
    # legend has a measured extent to sit on top of.
    ax.figure.canvas.draw()
    try:
        box = legend.get_window_extent().transformed(ax.transAxes.inverted())
        x_center, y_top = box.x0 + box.width / 2.0, box.y1
    except Exception:
        # No measurable extent (rare backend cases) -- fall back to the top of the
        # reserved band rather than losing the note.
        x_center, y_top = 0.5, 0.93
    ax.text(x_center, min(y_top + 0.025, 0.965), population_note,
            transform=ax.transAxes, ha='center', va='bottom',
            fontsize=fontsize, fontweight='bold')

VOLUME_COMPARISON_STYLES = {
    'in':  {'label': 'Vertex in volume',     'color': 'green',      'marker': 'o'},
    'out': {'label': 'Vertex out of volume', 'color': 'darkorange', 'marker': 's'},
}

# Same three channels, same colours as DrawNeutrinoFlavor's bars in
# DrawRecoTrueClusters.py, so a channel keeps one colour across the whole output.
CHANNEL_COMPARISON_STYLES = {
    'numu_CC': {'label': r'$\nu_\mu$ CC', 'color': 'steelblue',  'marker': 'o'},
    'nue_CC':  {'label': r'$\nu_e$ CC',    'color': 'purple',     'marker': 'D'},
    'NC':      {'label': 'NC',              'color': 'darkorange', 'marker': 's'},
}


def DrawClusterCompletenessVsTrueEnergy_PopulationComparison(populations, output_dir, apa,
                                                           level_name="Job Level", file_name=None,
                                                           n_bins=15, styles=None,
                                                           comparison_label="In vs Out of Volume",
                                                           filename_suffix="in_vs_out_volume",
                                                           population_note=None):
    """
    Clusteringlevel 1D completeness-vs-true-energy curves for several true neutrino
    populations, overlaid on one canvas: in-volume vs out-of-volume vertices, or
    the numu CC / nue CC / NC channels.

    "Clusteringlevel" means the same population DrawClusterCompletenessVsTrueEnergyPerJob
    uses: the 1-to-1 matched pairs PLUS the true clusters that matched nothing,
    entered at completeness 0 via _combine_pairs_with_unmatched -- so a neutrino that
    reconstructed to nothing counts against its population's completeness instead of
    quietly leaving the plot.

    Parameters:
    - populations: ordered list of (key, pair_metadata_list, all_true_metadata_list);
      each key must be present in `styles`
    - output_dir: Output directory
    - apa: APA identifier (label only)
    - level_name: Title label (this is a job-level plot; the parameter is here so
      the same drawer can serve another level if that is ever wanted)
    - file_name: Optional input file name for the title
    - n_bins: Energy bins across the combined population
    - styles: {key: {label, color, marker}}; VOLUME_COMPARISON_STYLES by default,
      CHANNEL_COMPARISON_STYLES for the CC/NC split
    - comparison_label: what the title calls the comparison
    - filename_suffix: what the filename calls it
    - population_note: the line printed inside the plot above the legend, saying
      which neutrino population these curves are drawn from (e.g. "In-volume true
      neutrinos"). The title says it too; the note is there so a plot pulled out
      of its directory still states what it is.

    Writes completeness_vs_true_energy_1d_clusteringlevel_{filename_suffix}_{apa}.png
    and does nothing at all if no population has an entry.
    """
    styles = styles or VOLUME_COMPARISON_STYLES

    resolved = []
    for key, pair_metadata_list, all_true_metadata_list in populations:
        entries = _combine_pairs_with_unmatched(pair_metadata_list, all_true_metadata_list)
        resolved.append((key, entries))

    all_energies = [m['total_true_energy'] for _, entries in resolved for m in entries]
    if not all_energies:
        return None

    energy_bins = np.linspace(0, max(all_energies) * 1.1, n_bins + 1)

    plt.figure(figsize=(12, 7.5))
    drawn_any = False
    # Smallest population last, so it lands ON TOP: a channel with one cluster is
    # a single marker, and drawn first it disappears under a populous curve
    # passing through the same point. Legend order is fixed separately below so
    # it still follows the caller's order rather than the drawing order.
    for key, entries in sorted(resolved, key=lambda item: -len(item[1])):
        if not entries:
            continue
        style = styles[key]
        energies     = [m['total_true_energy'] for m in entries]
        completenesses = [m['completeness'] for m in entries]
        bin_centers, mean_completeness = plot_1d_completeness_energy(energies, completenesses, energy_bins)
        if len(bin_centers) == 0:
            continue
        drawn_any = True
        plt.plot(bin_centers, mean_completeness, marker=style['marker'], linestyle='-',
                 linewidth=2.5, markersize=9, color=style['color'],
                 label=f"{style['label']} ({len(entries)} clusters, mean {np.mean(completenesses):.3f})",
                 markeredgecolor='black', markeredgewidth=1)

    if not drawn_any:
        plt.close()
        return None

    plt.xlabel('True Cluster Energy [MeV]', fontsize=12, fontweight='bold')
    plt.ylabel('Completeness', fontsize=12, fontweight='bold')
    title = (f'Completeness vs True Energy (1D, ClusteringLevel) - True Neutrinos, '
             f'{comparison_label} - {level_name}, {apa}')
    if file_name:
        title += f' ({file_name})'
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.grid(True, linestyle='--', alpha=0.3)
    # TRUE_ENERGY_XMAX_MEV is the scale the per-population 1D completeness plots
    # use, kept here so this reads against them -- but extended when the data runs
    # past it. A
    # comparison plot that silently drops a whole population off the right edge
    # (the single nue CC cluster of this dataset sits at 3059 MeV) is worse than
    # one with an unfamiliar axis.
    plt.xlim(0, max(TRUE_ENERGY_XMAX_MEV, energy_bins[-1]))
    # Headroom above y=1 for the legend and the population note. Completeness cannot
    # exceed 1, so this band is guaranteed empty and the legend cannot cover a
    # curve -- set BEFORE the legend, which measures itself against these limits.
    plt.ylim(-0.05, 1.55)
    _order_legend_like(plt.gca(), [key for key, _ in resolved], styles,
                       population_note=population_note)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"completeness_vs_true_energy_1d_clusteringlevel_{filename_suffix}_{apa}.png"
    plt.savefig(out_path, dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()
    return out_path


def DrawPurityVsRecoCharge_PopulationComparison(populations, output_dir, apa,
                                                level_name="Job Level", file_name=None,
                                                n_bins=15, styles=None,
                                                comparison_label="In vs Out of Volume",
                                                filename_suffix="in_vs_out_volume",
                                                population_note=None):
    """
    1D purity-vs-reco-charge curves for several true neutrino populations,
    overlaid on one canvas. Counterpart to
    DrawClusterCompletenessVsTrueEnergy_PopulationComparison above.

    Purity comes from the 1-to-1 matched pairs only: an unmatched true neutrino has
    no reco cluster and therefore no purity to plot (it is in the completeness plot at
    0, which is where that failure belongs). The purity values themselves were
    computed against the FULL reco population, so they still measure the cosmic
    contamination of the matched reco cluster.

    Parameters:
    - populations: ordered list of (key, pair_metadata_list)
    - output_dir, apa, level_name, file_name, n_bins, styles, comparison_label,
      filename_suffix, population_note: as above

    Writes purity_vs_reco_charge_1d_{filename_suffix}_{apa}.png.
    """
    styles = styles or VOLUME_COMPARISON_STYLES

    all_charges = [m['total_reco_charge'] for _, pairs in populations for m in pairs]
    if not all_charges:
        return None

    x_max       = max(all_charges) * 1.1
    charge_bins = np.linspace(0, x_max, n_bins + 1)

    plt.figure(figsize=(12, 7.5))
    drawn_any = False
    # Smallest population last -- see the completeness drawer above.
    for key, pairs in sorted(populations, key=lambda item: -len(item[1])):
        if not pairs:
            continue
        style    = styles[key]
        charges  = [m['total_reco_charge'] for m in pairs]
        purities = [m['purity'] for m in pairs]
        bin_centers, mean_purity = plot_1d_purity_charge(charges, purities, charge_bins)
        if len(bin_centers) == 0:
            continue
        drawn_any = True
        plt.plot(bin_centers, mean_purity, marker=style['marker'], linestyle='-',
                 linewidth=2.5, markersize=9, color=style['color'],
                 label=f"{style['label']} ({len(pairs)} pairs, mean {np.mean(purities):.3f})",
                 markeredgecolor='black', markeredgewidth=1)

    if not drawn_any:
        plt.close()
        return None

    plt.xlabel('Reco Cluster Charge [ADC] Arbitrary Units', fontsize=12, fontweight='bold')
    plt.ylabel('Purity', fontsize=12, fontweight='bold')
    title = (f'Purity vs Reco Charge (1D) - True Neutrinos, {comparison_label} - '
             f'{level_name}, {apa}')
    if file_name:
        title += f' ({file_name})'
    plt.title(title, fontsize=12, fontweight='bold', wrap=True)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.xlim(0, x_max)
    # Headroom for legend + note -- see the completeness drawer above.
    plt.ylim(-0.05, 1.55)
    _order_legend_like(plt.gca(), [key for key, _ in populations], styles,
                       population_note=population_note)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"purity_vs_reco_charge_1d_{filename_suffix}_{apa}.png"
    plt.savefig(out_path, dpi=100, bbox_inches='tight', pad_inches=0.3)
    plt.close()
    return out_path


# The names these were introduced under, when the only comparison was by vertex
# volume. Kept so existing callers keep working; both default to the volume
# styles, labels and filenames, so a call written for the volume split behaves
# exactly as before.
DrawClusterCompletenessVsTrueEnergy_VolumeComparison = DrawClusterCompletenessVsTrueEnergy_PopulationComparison
DrawPurityVsRecoCharge_VolumeComparison            = DrawPurityVsRecoCharge_PopulationComparison
