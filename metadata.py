import numpy as np

def add_metadata_true_clusters(efficiency_results, cluster_category_results, file_name, event, apa, view, event_key=None):
    """
    Create metadata for each true cluster.

    Args:
        efficiency_results: List of efficiency result dictionaries from EvaluateEfficiency
        cluster_category_results: Dictionary mapping cluster IDs to category info (is_neutrino, track_type)
        file_name: Name of the input file (e.g., "file1")
        event: Event number
        apa: APA number (e.g., "APA0")
        view: View type (e.g., "2view", "3view")
        event_key: Full event key like "file1_0" (if None, will be constructed from file_name and event)

    Returns:
        List of metadata dictionaries, one per unique true cluster
    """
    # Construct full event_key if not provided
    if event_key is None:
        event_key = f"{file_name}_{event}"
    if not efficiency_results:
        return []

    # Group efficiency data by true cluster
    true_cluster_data = {}
    for eff in efficiency_results:
        true_cid = eff['true_cluster_id']

        if true_cid not in true_cluster_data:
            true_cluster_data[true_cid] = {
                'total_efficiency': 0,
                'reco_match_count': 0,
                'total_true_energy': eff.get('total_true_cluster_energy', 0)
            }

        true_cluster_data[true_cid]['total_efficiency'] += eff['efficiency_energy_weighted']
        true_cluster_data[true_cid]['reco_match_count'] += 1

    # Create metadata entries for each true cluster
    metadata_list = []

    for true_cid, cluster_info in true_cluster_data.items():
        # Get category information
        category_info = cluster_category_results.get(true_cid, {})
        is_neutrino = category_info.get('is_neutrino', False)
        track_type = category_info.get('track_type', 'normal')

        # Determine cluster type
        cluster_type = 'neutrino' if is_neutrino else 'cosmic'

        # Create metadata dictionary
        metadata = {
            'file_name': file_name,
            'event': event_key,  # Store the full event_key (e.g., "file1_0") for proper matching
            'event_num': event,  # Also store the event number for reference
            'apa': apa,
            'view': view,
            'true_cluster_id': true_cid,
            'cluster_type': cluster_type,  # neutrino or cosmic
            'cluster_category': track_type,  # isochronous, prolonged, normal (only for cosmic)
            'total_efficiency': cluster_info['total_efficiency'],
            'num_reco_matches': cluster_info['reco_match_count'],
            'total_true_energy': cluster_info['total_true_energy']
        }

        metadata_list.append(metadata)

    return metadata_list


def add_metadata_true_reco_pair_cluster(matched_pairs, cluster_category_results, file_name, event, apa, view, event_key=None):
    """
    Create metadata for each matched true-reco cluster pair (1-to-1 matching).

    Args:
        matched_pairs: List of matched pair dictionaries from MatchTrueToReco1to1, each
            containing true_cluster_id, reco_cluster_id, efficiency_energy_weighted, purity,
            and total_true_cluster_energy
        cluster_category_results: Dictionary mapping cluster IDs to category info (is_neutrino, track_type)
        file_name: Name of the input file (e.g., "file1")
        event: Event number
        apa: APA number (e.g., "APA0")
        view: View type (e.g., "2view", "3view")
        event_key: Full event key like "file1_0" (if None, will be constructed from file_name and event)

    Returns:
        List of metadata dictionaries, one per matched true-reco pair
    """
    # Construct full event_key if not provided
    if event_key is None:
        event_key = f"{file_name}_{event}"
    if not matched_pairs:
        return []

    metadata_list = []

    for pair in matched_pairs:
        true_cid = pair['true_cluster_id']
        reco_cid = pair['reco_cluster_id']

        # Get category information
        category_info = cluster_category_results.get(true_cid, {})
        is_neutrino = category_info.get('is_neutrino', False)
        track_type = category_info.get('track_type', 'normal')

        # Determine cluster type
        cluster_type = 'neutrino' if is_neutrino else 'cosmic'

        # Create metadata dictionary
        metadata = {
            'file_name': file_name,
            'event': event_key,  # Store the full event_key (e.g., "file1_0") for proper matching
            'event_num': event,  # Also store the event number for reference
            'apa': apa,
            'view': view,
            'true_cluster_id': true_cid,
            'reco_cluster_id': reco_cid,
            'cluster_type': cluster_type,  # neutrino or cosmic
            'cluster_category': track_type,  # isochronous, prolonged, normal (only for cosmic)
            'efficiency': pair.get('efficiency_energy_weighted', 0),
            'purity': pair.get('purity', 0),
            'total_true_energy': pair.get('total_true_cluster_energy', 0)
        }

        metadata_list.append(metadata)

    return metadata_list


def aggregate_metadata(metadata_list):
    """
    Aggregate metadata entries across multiple events/files.
    Useful for file-level and job-level analysis.

    Args:
        metadata_list: List of metadata dictionaries from multiple calls to add_metadata_true_clusters

    Returns:
        Aggregated metadata dictionary with summary statistics
    """
    if not metadata_list:
        return {}

    # Group by cluster type and category
    stats = {
        'total_clusters': len(metadata_list),
        'by_type': {
            'neutrino': 0,
            'cosmic': 0
        },
        'by_category': {
            'neutrino': 0,
            'isochronous': 0,
            'prolonged': 0,
            'normal': 0
        },
        'efficiency_stats': {
            'mean': np.mean([m['total_efficiency'] for m in metadata_list]),
            'median': np.median([m['total_efficiency'] for m in metadata_list]),
            'min': np.min([m['total_efficiency'] for m in metadata_list]),
            'max': np.max([m['total_efficiency'] for m in metadata_list])
        },
        'reco_matches_stats': {
            'mean': np.mean([m['num_reco_matches'] for m in metadata_list]),
            'median': np.median([m['num_reco_matches'] for m in metadata_list]),
            'min': np.min([m['num_reco_matches'] for m in metadata_list]),
            'max': np.max([m['num_reco_matches'] for m in metadata_list])
        }
    }

    # Count by type and category
    for metadata in metadata_list:
        cluster_type = metadata['cluster_type']
        category = metadata['cluster_category']

        stats['by_type'][cluster_type] += 1
        stats['by_category'][category] += 1

    return stats


def print_metadata(metadata_list):
    """
    Print metadata in a formatted table.

    Args:
        metadata_list: List of metadata dictionaries
    """
    if not metadata_list:
        print("No metadata to display")
        return

    print("\n" + "="*120)
    print(f"{'File':<10} {'Event':<8} {'APA':<6} {'View':<8} {'Cluster ID':<12} {'Type':<10} {'Category':<15} {'Efficiency':<12} {'Reco Matches':<15}")
    print("="*120)

    for metadata in metadata_list:
        print(f"{metadata['file_name']:<10} {metadata['event']:<8} {metadata['apa']:<6} {metadata['view']:<8} "
              f"{metadata['true_cluster_id']:<12.0f} {metadata['cluster_type']:<10} {metadata['cluster_category']:<15} "
              f"{metadata['total_efficiency']:<12.4f} {metadata['num_reco_matches']:<15}")

    print("="*120 + "\n")
