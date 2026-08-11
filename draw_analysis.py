import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Function to match true and reco clusters based on purity and completeness results
# make pairing based on highest purity for each true cluster, then ensure one-to-one matching by keeping only the best pair for each reco cluster
# TODO: we need to change matching creteria to energy-weighted completeness instead of purity
def MatchRecoTruePairs(all_purity_results, all_eff_results):
    # Convert lists of purity and completeness results to DataFrames
    purity_df = pd.DataFrame(all_purity_results)
    completeness_df = pd.DataFrame(all_eff_results)
    
    # Merge the two DataFrames on event, true_cluster_id, and reco_cluster_id
    merged_df = pd.merge(purity_df, completeness_df, on=['event', 'true_cluster_id', 'reco_cluster_id'])
    
    # Keep only pairs with non-zero purity
    matched_pairs = merged_df[merged_df['purity'] > 0]
    
    # For each (event, true_cluster), find the reco_cluster with highest purity
    best_matched_purity = matched_pairs.loc[matched_pairs.groupby(['event', 'true_cluster_id'])['purity'].idxmax()]
    
    
    # For each (event, reco_cluster), keep only the true_cluster with highest purity to ensure one-to-one matching
    final_matched_pairs = []
    for (event, reco_cluster_id), group in best_matched_purity.groupby(['event', 'reco_cluster_id']):
        best_pair = group.loc[group['purity'].idxmax()]
        final_matched_pairs.append(best_pair)
    
    print(f"Found {len(final_matched_pairs)} matched pairs of true and reco clusters")
    return final_matched_pairs

