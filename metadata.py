import numpy as np
from pathlib import Path

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
        # The 8888 row is EvaluateEfficiency's "this true cluster matched nothing"
        # sentinel, not a reco cluster, so it must not count towards num_reco_matches --
        # an unmatched true cluster has 0 matches, not 1. (The multiplicity bar chart and
        # non_one_match_*.txt already corrected for this via total_efficiency <= 0; the
        # count is now correct at the source, so those corrections simply agree with it.)
        if eff['reco_cluster_id'] != 8888:
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


# ============================================================================
# CHARGE-LIGHT MATCHING FORMAT (additive; existing functions above are untouched)
# ============================================================================

def build_cluster_flash_metadata(op_data, file_name, event, apa, event_key=None):
    """
    Build per-img-global-cluster-ID optical flash records from the per-flash
    arrays returned by read_op_json() (readfiles.py). op_cluster_ids[i] lists
    the img-global reco cluster IDs matched to flash index i (empty if none);
    every cluster ID in that bracket shares flash i's time (op_t[i]) and APA
    (apa[i]). Verified against the test data: no cluster ID appears in more
    than one flash's bracket, so each cluster ID produces exactly one record.
    Intended for future work (cathode-crossing matching, x-drift-distance
    correction) -- not used for that yet, but feeds DrawRecoTrueFlashes.draw_flashes().

    Args:
        op_data: Dict from read_op_json()
        file_name: Name of the input file (e.g., "file0")
        event: Event number
        apa: Processing-level APA label (e.g. "Combined") -- NOT the same as
            each flash's own detector APA assignment, stored separately below
            as 'flash_apa'
        event_key: Full event key like "file0_9" (if None, constructed from file_name and event)

    Returns a list of dicts (one per matched cluster ID, same shape convention
    as add_metadata_true_clusters/add_metadata_true_reco_pair_cluster) so
    records from multiple events can be concatenated for file/job-level
    aggregation -- see DrawRecoTrueFlashes.draw_flashes().
    """
    if event_key is None:
        event_key = f"{file_name}_{event}"

    records = []
    for flash_index, cluster_ids in enumerate(op_data['op_cluster_ids']):
        if not cluster_ids:
            continue
        flash_time = op_data['op_t'][flash_index]
        flash_apa  = op_data['apa'][flash_index]
        for cluster_id in cluster_ids:
            records.append({
                'file_name': file_name,
                'event': event_key,
                'event_num': event,
                'apa': apa,
                'reco_cluster_id': cluster_id,
                'flash_index': flash_index,
                'flash_time': flash_time,
                'flash_apa': flash_apa,
            })
    return records


CATHODE_CROSSING_TIME_DIFF_MAX_US = 0.02  # 20 ns


def build_img_cluster_flash_metadata(img_data, clustering_data, cluster_flash_records, file_name, event, apa, event_key=None):
    """
    Bridge op.json flash info (attached to img-global cluster IDs by
    build_cluster_flash_metadata) onto clustering-global cluster IDs, even
    though img-global and clustering-global use unrelated cluster_id
    numbering (clustering-global is built AFTER charge-light matching --
    points get re-clustered, possibly merged across the cathode -- so
    cluster_id can't be used to connect the two files directly). This
    function only READS img_data/clustering_data to build an association
    table -- it never modifies or merges the underlying point data in either
    file; any merging visible in clustering-global's clusters already
    happened upstream, before either file was read here.

    The join key is each point's charge ('q'): verified against test data
    that every clustering-global q value has a matching q value somewhere in
    img-global (point order/clustering differs completely between the two
    files, so this must be a value match, not an index match -- only ~0.1%
    of points happen to share position at the same index). img-global q
    values are ~99.2% unique; the rare duplicates are dropped as ambiguous
    rather than guessed at.

    A clustering cluster can match multiple img clusters. Two cases:
      - Same flash (identical flash_time): fragmented img-level sub-clusters
        re-merged into one clustering cluster -- kept as separate records,
        nothing to resolve (their times already agree exactly).
      - Different flashes, close in time (within CATHODE_CROSSING_TIME_DIFF_MAX_US)
        AND from different APAs: this is a cathode-crossing track -- the same
        physical light burst reconstructed independently by each side's
        optical system. These are merged into ONE record with the averaged
        flash_time (verified against test data: e.g. 1.09731/1.09872 us,
        APA 1/0 -> averaged to 1.098015 us). Close-in-time flashes from the
        SAME APA are NOT merged -- that's not the cathode-crossing signature,
        just coincidence (or, as with same-time entries, already handled above).
      - Otherwise (genuinely different, unrelated flashes): kept as separate records.

    Args:
        img_data: Tuple from readfiles.read_img_global_from_json() --
            (x, y, z, cluster_id, q, real_cluster_id)
        clustering_data: Tuple from readfiles.read_cluster_global_from_json() --
            (x, y, z, cluster_id, q, real_cluster_id)
        cluster_flash_records: Output of build_cluster_flash_metadata() for
            this same event (img-global-cluster-ID-keyed flash records)
        file_name: Name of the input file (e.g., "file0")
        event: Event number
        apa: Processing-level APA label (e.g. "Combined")
        event_key: Full event key like "file0_9" (if None, constructed from file_name and event)

    Returns a list of dicts, one per resolved (clustering_cluster_id, flash)
    match -- clustering clusters with no flash-matched img cluster are simply
    absent, same convention as build_cluster_flash_metadata. Each record has
    'img_cluster_id' (representative, first-matched) and 'img_cluster_ids'
    (full list -- length 2 for a cathode-crossing merge), 'flash_apa' and
    'is_cathode_crossing' (bool).
    """
    if event_key is None:
        event_key = f"{file_name}_{event}"

    _, _, _, img_cluster_id, img_q, _ = img_data
    # clustering-global's own 'cluster_id' is a COARSER grouping than
    # 'real_cluster_id' -- it can merge multiple physically distinct tracks
    # that only 'real_cluster_id' keeps separate (confirmed against real data:
    # a single cluster_id spanning two disjoint Y ranges that split cleanly
    # into two real_cluster_id values, each matching a different true
    # cluster). Group/key by real_cluster_id here so clustering_cluster_id in
    # the output records reflects the physically correct clusters.
    _, _, _, _, clu_q, clu_real_cluster_id = clustering_data

    # img cluster_id -> list of flash records (a cluster can only appear in
    # one flash's bracket per build_cluster_flash_metadata, but keep this
    # general in case that changes).
    img_flash_lookup = {}
    for record in cluster_flash_records:
        img_flash_lookup.setdefault(record['reco_cluster_id'], []).append(record)

    # q value -> img cluster_id, dropping ambiguous (duplicate, conflicting) q values.
    q_to_img_cluster = {}
    ambiguous_q = set()
    for q, cid in zip(img_q, img_cluster_id):
        if q in q_to_img_cluster and q_to_img_cluster[q] != cid:
            ambiguous_q.add(q)
        else:
            q_to_img_cluster[q] = cid
    for q in ambiguous_q:
        del q_to_img_cluster[q]

    # Tally, per clustering cluster, how many of its points matched into each img cluster.
    clu_to_img_counts = {}
    for q, clu_cid in zip(clu_q, clu_real_cluster_id):
        img_cid = q_to_img_cluster.get(q)
        if img_cid is None:
            continue
        counts = clu_to_img_counts.setdefault(clu_cid, {})
        counts[img_cid] = counts.get(img_cid, 0) + 1

    records = []
    for clu_cid, img_counts in clu_to_img_counts.items():
        # One entry per (img_cluster_id, flash) match for this clustering cluster.
        entries = []
        for img_cid, n_matched_points in img_counts.items():
            for flash_record in img_flash_lookup.get(img_cid, []):
                entries.append({
                    'img_cluster_id': img_cid,
                    'n_matched_points': n_matched_points,
                    'flash_index': flash_record['flash_index'],
                    'flash_time': flash_record['flash_time'],
                    'flash_apa': flash_record['flash_apa'],
                })
        if not entries:
            continue

        # Greedy adjacent merge (by time) of entries within
        # CATHODE_CROSSING_TIME_DIFF_MAX_US of the previous entry AND from a
        # different APA. Entries with identical time (fragmented same-flash
        # matches, e.g. img sub-clusters re-merged) never satisfy "different
        # APA from a same-time same-APA neighbor" unless they genuinely are
        # on a different APA, so they naturally stay unmerged as before.
        entries.sort(key=lambda e: e['flash_time'])
        groups = []
        for entry in entries:
            if groups and (entry['flash_time'] - groups[-1][-1]['flash_time'] <= CATHODE_CROSSING_TIME_DIFF_MAX_US
                            and entry['flash_apa'] != groups[-1][-1]['flash_apa']):
                groups[-1].append(entry)
            else:
                groups.append([entry])

        for group in groups:
            is_cathode_crossing = len(group) > 1
            avg_time = sum(e['flash_time'] for e in group) / len(group)
            records.append({
                'file_name': file_name,
                'event': event_key,
                'event_num': event,
                'apa': apa,
                'clustering_cluster_id': clu_cid,
                'img_cluster_id': group[0]['img_cluster_id'],
                'img_cluster_ids': [e['img_cluster_id'] for e in group],
                'n_matched_points': sum(e['n_matched_points'] for e in group),
                'flash_index': group[0]['flash_index'],
                'flash_time': avg_time,
                'flash_apa': group[0]['flash_apa'] if not is_cathode_crossing else '/'.join(e['flash_apa'] for e in group),
                'is_cathode_crossing': is_cathode_crossing,
            })
    return records


def build_true_cluster_type_records(clusters_true, file_name, event, event_key=None):
    """
    Per-true-cluster {cluster_id, is_neutrino, nu_idx_values} records for
    DrawLabelsAggregated and DrawLabelsByNuIdx.

    is_neutrino is determined by q_true>0 on the cluster's points, NOT via
    cluster_category_results (which checks only the FIRST point and assumes
    q_true==1 exactly -- silently wrong once q_true can be a neutrino index
    of 2 or higher). All points in a given post-reassignment cosmic cluster
    share q_true=0, so checking any single point is safe there -- the bug in
    the pre-existing code was the ==1 comparison, not the single-point read.

    nu_idx_values: sorted list of the DISTINCT nu_idx (q_true) values present
    among the cluster's points; [] for cosmic clusters. reassign_cluster_ID_true
    merges ALL true clusters with any q_true>0 into a single cluster_id=9999,
    regardless of how many distinct neutrino interactions contributed points --
    so cluster 9999 can itself contain multiple nu_idx values, which is why
    this is a list rather than a single value. is_neutrino's definition and
    the one-record-per-post-reassignment-cluster_id shape are UNCHANGED so
    DrawLabelsAggregated's counts are unaffected by this field.

    There is deliberately NO in_beam_window field. True clusters carry no flash
    and no time (build_true_points_charge_light fills the time column with
    zeros), so any "true cluster in the beam window" flag could only be inferred
    by spatially matching to a reco cluster whose flash landed in the window --
    which mixes beam timing with reconstruction + flash-matching efficiency
    while reading as a truth-level timing selection. Beam-window membership is
    a RECO-side quantity only (see build_img_cluster_flash_metadata and
    writeinformation.write_reco_cluster_info); do not reintroduce it here.

    Args:
        clusters_true: Dict {cluster_id: points}, points columns
            [x, y, z, cluster_id, q_true, energy, time] (post reassign_cluster_ID_true)
        file_name: Name of the input file (e.g., "file0")
        event: Event number
        event_key: Full event key like "file0_9" (if None, constructed from file_name and event)

    Returns:
        List of dicts, one per true cluster:
            {file_name, event, event_num, cluster_id, is_neutrino, nu_idx_values}
    """
    if event_key is None:
        event_key = f"{file_name}_{event}"
    if not clusters_true:
        return []

    records = []
    for cluster_id, points in clusters_true.items():
        points = np.array(points)
        is_neutrino = bool(points[0, 4] > 0) if len(points) > 0 else False
        if is_neutrino:
            nu_idx_values = sorted(set(int(v) for v in points[:, 4] if v > 0))
        else:
            nu_idx_values = []
        records.append({
            'file_name': file_name,
            'event': event_key,
            'event_num': event,
            'cluster_id': cluster_id,
            'is_neutrino': is_neutrino,
            'nu_idx_values': nu_idx_values,
        })
    return records


def build_neutrino_vertex_records(mc_records, clusters_true, file_name, event, event_key=None,
                                  x_min=None, x_max=None, y_min=None, y_max=None,
                                  z_min=None, z_max=None,
                                  clusters_true_precut=None, min_cluster_energy=None):
    """
    One record per TRUE NEUTRINO INTERACTION in an event, built from mc.json's
    interaction-vertex root nodes (flatten_mc_tree records with
    is_interaction_vertex=True), joined to the true cluster that interaction
    produced.

    The join is by nu_idx, not by position: reassign_cluster_ID_true_charge_light
    gives interaction nu_idx the cluster_id 99990+nu_idx, and mc.json's root text
    carries the same nu_idx -- so the two sides link exactly, with no spatial
    matching and no tolerance to tune.

    VERTEX: the root node's start_xyz. For a root, start == end (it is a point,
    not a track), in the same cm frame as the true points -- verified by
    measuring in-volume vertices against their own cluster's deposits (agreement
    to ~0.03-0.13 cm).

    ENERGY -- read this before using any energy from here:
      - cluster_energy_MeV is the TRUE cluster energy summed from the
        sed-sce_drift_smear_readout points (column 5), i.e. the same quantity
        apply_energy_cutoff and every efficiency plot use. THIS is the energy for
        evaluation and selection.
      - mc_total_energy_MeV ('Etot') and mc_edep_MeV ('Edep') are copied from
        mc.json's root text for reference only -- Etot is the incident neutrino's
        total energy (not deposited anywhere), Edep is mc.json's own deposited
        figure. Neither is used for cuts and neither should be: they come from a
        different bookkeeping than the point cloud the pipeline measures.

    A neutrino interaction can have NO true cluster (has_true_cluster=False):
    an out-of-volume interaction may deposit nothing in the active volume, and a
    cluster may also have been removed by the pipeline's cuts. cluster_energy_MeV
    and n_true_points therefore describe the cluster AS PASSED IN -- if
    clusters_true is post-cut (as in the main pipeline), so are these numbers.

    Pass clusters_true_precut (the same clusters BEFORE the cuts) to get the
    diagnostics for those removed interactions: precut_energy_MeV,
    precut_n_points and removal_reason, which distinguishes "never deposited
    anything" from "deposited, but the cuts took it" -- the two need completely
    different follow-up. removal_reason names the energy cut specifically when
    min_cluster_energy is given and the pre-cut energy falls below it; anything
    that had enough energy and still vanished is attributed to the geometric
    cuts (fiducial / min-points). Records that survived carry
    removal_reason=None.

    NOTE on the dead-area cut: it is no longer one of the geometric cuts counted
    here. It is applied upstream by preprocess_deadarea_cut.py, before this
    pipeline sees the data, so clusters_true_precut is ALREADY dead-area-filtered
    and a dead-area removal can never appear as a removal_reason. That is
    deliberate rather than a gap: points inside a dead channel region could never
    have been reconstructed, so they are not "cut" in any meaningful sense -- they
    are outside the measurable volume, and "no true deposits" is the honest
    description of an interaction that only ever deposited there. If you point the
    pipeline back at a raw tree with Apply_deadarea_cut=True, the cut moves back to
    the end of the chain and dead-area removals fold into the geometric category
    again.

    Parameters:
    - mc_records: flatten_mc_tree(result['mc']) output
    - clusters_true: Dict {cluster_id: points}, points columns
        [x, y, z, cluster_id, q_true, energy, time]
    - file_name, event, event_key: identification, as elsewhere
    - x_min..z_max: volume bounds for the vertex_in_volume flag; if any is None
        the flag is left None rather than guessed

    Returns:
        List of dicts, one per neutrino interaction found in mc.json
    """
    if event_key is None:
        event_key = f"{file_name}_{event}"
    if not mc_records:
        return []

    bounds = (x_min, x_max, y_min, y_max, z_min, z_max)
    have_bounds = all(b is not None for b in bounds)

    records = []
    for mc in mc_records:
        if not mc.get('is_interaction_vertex'):
            continue
        vertex = mc.get('start_xyz')
        nu_idx = mc.get('nu_idx')

        if vertex is not None and have_bounds:
            vx, vy, vz = vertex
            in_volume = bool(x_min <= vx <= x_max and y_min <= vy <= y_max and z_min <= vz <= z_max)
        else:
            in_volume = None

        cluster_id = 99990.0 + nu_idx if nu_idx is not None else None
        points = clusters_true.get(cluster_id) if cluster_id is not None else None
        if points is not None and len(points) > 0:
            points = np.asarray(points)
            cluster_energy = float(points[:, 5].sum())
            n_true_points = int(len(points))
            has_cluster = True
        else:
            cluster_energy, n_true_points, has_cluster = None, 0, False

        precut_energy, precut_n_points, removal_reason, removal_category = None, 0, None, None
        if clusters_true_precut is not None and cluster_id is not None:
            precut_points = clusters_true_precut.get(cluster_id)
            if precut_points is not None and len(precut_points) > 0:
                precut_points = np.asarray(precut_points)
                precut_energy = float(precut_points[:, 5].sum())
                precut_n_points = int(len(precut_points))
        if not has_cluster:
            # removal_category is a FIXED string for grouping; removal_reason adds
            # the per-interaction detail. Keeping them separate matters: folding the
            # energy value into the grouping key makes every energy-cut row its own
            # category and the summary table degenerates into one row per cluster.
            if precut_n_points == 0:
                removal_category = "no true deposits"
                removal_reason   = "no true deposits (nothing to cut)"
            elif min_cluster_energy is not None and precut_energy is not None and precut_energy < min_cluster_energy:
                removal_category = "below energy cut"
                removal_reason   = f"below energy cut ({precut_energy:.1f} < {min_cluster_energy} MeV)"
            else:
                # No "dead area" here: it is applied upstream, before this pipeline
                # sees the data -- see the docstring's NOTE.
                removal_category = "removed by geometric cuts"
                removal_reason   = "removed by geometric cuts (fiducial / min points)"

        records.append({
            'file_name': file_name,
            'event': event_key,
            'event_num': event,
            'nu_idx': nu_idx,
            'cluster_id': cluster_id,
            'flavor': mc.get('particle'),
            'vertex_x': vertex[0] if vertex else None,
            'vertex_y': vertex[1] if vertex else None,
            'vertex_z': vertex[2] if vertex else None,
            'vertex_in_volume': in_volume,
            'mc_total_energy_MeV': mc.get('total_energy_MeV'),
            'mc_edep_MeV': mc.get('energy_MeV'),
            'cluster_energy_MeV': cluster_energy,
            'n_true_points': n_true_points,
            'has_true_cluster': has_cluster,
            'precut_energy_MeV': precut_energy,
            'precut_n_points': precut_n_points,
            'removal_reason': removal_reason,
            'removal_category': removal_category,
        })
    return records
