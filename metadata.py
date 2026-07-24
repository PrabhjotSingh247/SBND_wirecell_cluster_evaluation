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
            total_true_cluster_energy, and total_reco_cluster_charge
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
            'total_true_energy': pair.get('total_true_cluster_energy', 0),
            'total_reco_charge': pair.get('total_reco_cluster_charge', 0)
        }

        metadata_list.append(metadata)

    return metadata_list


def add_metadata_reco_clusters(purity_results, file_name, event, apa, view, event_key=None):
    """
    Create metadata for each reco cluster. Symmetric counterpart to add_metadata_true_clusters,
    aggregated from purity_results (EvaluatePurity) the same way the true-side function
    aggregates from efficiency_results (EvaluateEfficiency).

    Args:
        purity_results: List of purity result dictionaries from EvaluatePurity
        file_name: Name of the input file (e.g., "file1")
        event: Event number
        apa: APA number (e.g., "APA0")
        view: View type (e.g., "2view", "3view")
        event_key: Full event key like "file1_0" (if None, will be constructed from file_name and event)

    Returns:
        List of metadata dictionaries, one per unique reco cluster
    """
    if event_key is None:
        event_key = f"{file_name}_{event}"
    if not purity_results:
        return []

    # Group purity data by reco cluster
    reco_cluster_data = {}
    for pur in purity_results:
        reco_cid = pur['reco_cluster_id']

        if reco_cid not in reco_cluster_data:
            reco_cluster_data[reco_cid] = {
                'total_purity': 0,
                'true_match_count': 0,
                'total_reco_charge': pur.get('total_reco_cluster_charge', 0)
            }

        # The unmatched sentinel (true_cluster_id=8888, purity=-0.1) marks a reco cluster
        # with no true match at all - don't fold it into the purity sum/match count.
        if pur.get('true_cluster_id') != 8888:
            reco_cluster_data[reco_cid]['total_purity'] += pur['purity']
            reco_cluster_data[reco_cid]['true_match_count'] += 1

    # Create metadata entries for each reco cluster
    metadata_list = []

    for reco_cid, cluster_info in reco_cluster_data.items():
        metadata = {
            'file_name': file_name,
            'event': event_key,  # Store the full event_key (e.g., "file1_0") for proper matching
            'event_num': event,  # Also store the event number for reference
            'apa': apa,
            'view': view,
            'reco_cluster_id': reco_cid,
            'total_purity': cluster_info['total_purity'],
            'num_true_matches': cluster_info['true_match_count'],
            'total_reco_charge': cluster_info['total_reco_charge']
        }

        metadata_list.append(metadata)

    return metadata_list


def add_single_metadata(metadata_list, field_name, value_lookup,
                          key_fields=('file_name', 'event', 'apa', 'true_cluster_id'), default=None):
    """
    Attach one additional field to every entry of an existing metadata list, looked up by key.

    Lets you extend metadata already built by add_metadata_true_clusters (or any other
    list of per-cluster dicts) with a new per-cluster quantity without rebuilding the whole
    list. For example, adding PCA linearity to true-cluster metadata:

        linearity_lookup = {
            (file_name, event_key, apa, true_cluster_id): linearity_value,
            ...
        }
        add_single_metadata(true_metadata_list, 'linearity', linearity_lookup)

    Args:
        metadata_list: List of metadata dictionaries (modified in place).
        field_name: Name of the new field to add to each dictionary.
        value_lookup: Dict mapping a key_fields tuple to the value for that cluster.
        key_fields: Dictionary keys used to build the lookup key, in order (default matches
            the schema produced by add_metadata_true_clusters).
        default: Value to assign when a metadata entry has no matching key in value_lookup.

    Returns:
        The same metadata_list, with field_name added to every entry.
    """
    for metadata in metadata_list:
        key = tuple(metadata[k] for k in key_fields)
        metadata[field_name] = value_lookup.get(key, default)

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
    Print metadata in a formatted table, showing every field present across the metadata
    dictionaries (not a fixed subset) so fields attached later via add_single_metadata
    (e.g. linearity) show up automatically without needing this function updated.

    Args:
        metadata_list: List of metadata dictionaries
    """
    if not metadata_list:
        print("No metadata to display")
        return

    # Union of keys across all entries, in first-seen order (handles entries where a
    # field was only attached to some rows).
    columns = []
    seen = set()
    for metadata in metadata_list:
        for key in metadata:
            if key not in seen:
                seen.add(key)
                columns.append(key)

    def format_value(value):
        if isinstance(value, float):
            return f"{value:.4f}"
        if value is None:
            return "N/A"
        return str(value)

    rows = [[format_value(metadata.get(col, "N/A")) for col in columns] for metadata in metadata_list]
    widths = [max(len(col), *(len(row[i]) for row in rows)) + 2 for i, col in enumerate(columns)]
    total_width = sum(widths)

    print("\n" + "="*total_width)
    print("".join(col.ljust(widths[i]) for i, col in enumerate(columns)))
    print("="*total_width)

    for row in rows:
        print("".join(value.ljust(widths[i]) for i, value in enumerate(row)))

    print("="*total_width + "\n")
