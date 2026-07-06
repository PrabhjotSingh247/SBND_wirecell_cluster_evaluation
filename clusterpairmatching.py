import pandas as pd


def MatchRecoTruePair1to1(all_purity_results, all_eff_results):
    """
    One-to-one matching between true and reco clusters.
    For each true cluster, finds the reco cluster with highest purity.
    For each reco cluster, keeps only the true cluster with highest purity.
    """
    purity_df       = pd.DataFrame(all_purity_results)
    efficiency_df   = pd.DataFrame(all_eff_results)

    merged_df       = pd.merge(purity_df, efficiency_df, on=['event', 'true_cluster_id', 'reco_cluster_id'])
    matched_pairs   = merged_df[merged_df['efficiency'] > 0]

    # For each (event, true_cluster), find the reco_cluster with highest purity
    best_matched_eff = matched_pairs.loc[matched_pairs.groupby(['event', 'true_cluster_id'])['efficiency'].idxmax()]

    # For each (event, reco_cluster), keep only the true_cluster with highest purity
    final_matched_pairs = []
    for (event, reco_cluster_id), group in best_matched_eff.groupby(['event', 'reco_cluster_id']):
        best_pair = group.loc[group['purity'].idxmax()]
        final_matched_pairs.append(best_pair)

    print(f"Found {len(final_matched_pairs)} matched pairs of true and reco clusters (1-to-1)")
    return final_matched_pairs


def MatchRecoTrueCluster1toMany(all_purity_results, all_eff_results):
    """
    One-to-many matching between true and reco clusters.
    For each true cluster, finds all reco clusters with non-zero efficiency.
    Returns a list of dictionaries with true cluster and its matched reco clusters.
    """
    purity_df       = pd.DataFrame(all_purity_results)
    efficiency_df   = pd.DataFrame(all_eff_results)

    merged_df       = pd.merge(purity_df, efficiency_df, on=['event', 'true_cluster_id', 'reco_cluster_id'])

    # Keep only pairs with non-zero efficiency
    matched_pairs   = merged_df[merged_df['efficiency_energy_weighted'] > 0]

    # Group by event and true cluster, collecting all matched reco clusters
    result = []
    for (event, true_cluster_id), group in matched_pairs.groupby(['event', 'true_cluster_id']):
        reco_clusters = group[['reco_cluster_id', 'efficiency_energy_weighted', 'purity']].to_dict('records')
        result.append({
            'event': event,
            'true_cluster_id': true_cluster_id,
            'matched_reco_clusters': reco_clusters
        })

    print(f"Found {len(result)} true clusters with matched reco clusters (1-to-many)")
    return result