import pandas as pd


def MatchTrueToReco1to1(completeness_results, purity_results):
    """
    One-to-one matching from true clusters to reco clusters.
    For each true cluster with non-zero completeness to exactly one reco cluster, that pair is the match.
    For each true cluster with non-zero completeness to more than one reco cluster, the reco cluster
    with the highest completeness is selected as the match.
    (No reco-side deduplication: a single reco cluster may end up paired with more than one true cluster.)
    """
    # An event can legitimately have no completeness or no purity rows at all -- e.g.
    # with the beam-window cut on, an event with zero in-spill reco clusters gives
    # EvaluatePurity nothing to loop over. pd.DataFrame([]) has NO columns, so the
    # merge below would raise KeyError: 'event' instead of returning "no pairs".
    if not completeness_results or not purity_results:
        print("Found 0 matched pairs of true and reco clusters (1-to-1)")
        return []

    completeness_df   = pd.DataFrame(completeness_results)
    purity_df       = pd.DataFrame(purity_results)

    # purity_df carries its own 'total_true_cluster_energy' column, but only on its
    # unmatched-sentinel rows (true_cluster_id=8888, which never merge here anyway).
    # Left in place, pandas would silently rename both sides' colliding column to
    # total_true_cluster_energy_x/_y on merge, and every downstream .get('total_true_cluster_energy')
    # lookup would fall through to its default of 0. Drop it here so completeness_df's
    # real per-true-cluster value (the one actually wanted) survives the merge intact.
    purity_df = purity_df.drop(columns=['total_true_cluster_energy'], errors='ignore')

    merged_df       = pd.merge(completeness_df, purity_df, on=['event', 'true_cluster_id', 'reco_cluster_id'])
    matched_pairs   = merged_df[merged_df['completeness_energy_weighted'] > 0]

    if matched_pairs.empty:
        print("Found 0 matched pairs of true and reco clusters (1-to-1)")
        return []

    # For each (event, true_cluster), find the reco_cluster with highest completeness
    best_matched = matched_pairs.loc[matched_pairs.groupby(['event', 'true_cluster_id'])['completeness_energy_weighted'].idxmax()]

    print(f"Found {len(best_matched)} matched pairs of true and reco clusters (1-to-1)")
    return best_matched.to_dict('records')


def MatchTruetoReco_OneToMany(all_purity_results, all_eff_results):
    """
    One-to-many matching between true and reco clusters.
    For each true cluster, finds all reco clusters with non-zero completeness.
    Returns a list of dictionaries with true cluster and its matched reco clusters.
    """
    # Same empty-input guard as MatchTrueToReco1to1: an empty result list becomes a
    # column-less DataFrame and the merge would raise KeyError: 'event'.
    if not all_purity_results or not all_eff_results:
        print("Found 0 true clusters with matched reco clusters (1-to-many)")
        return []

    purity_df       = pd.DataFrame(all_purity_results)
    completeness_df   = pd.DataFrame(all_eff_results)

    merged_df       = pd.merge(purity_df, completeness_df, on=['event', 'true_cluster_id', 'reco_cluster_id'])

    # Keep only pairs with non-zero completeness
    matched_pairs   = merged_df[merged_df['completeness_energy_weighted'] > 0]

    # Group by event and true cluster, collecting all matched reco clusters
    result = []
    for (event, true_cluster_id), group in matched_pairs.groupby(['event', 'true_cluster_id']):
        reco_clusters = group[['reco_cluster_id', 'completeness_energy_weighted', 'purity']].to_dict('records')
        result.append({
            'event': event,
            'true_cluster_id': true_cluster_id,
            'matched_reco_clusters': reco_clusters
        })

    print(f"Found {len(result)} true clusters with matched reco clusters (1-to-many)")
    return result