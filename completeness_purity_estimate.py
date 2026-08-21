import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.spatial import KDTree

# Evaluate reconstruction completeness by comparing true and reconstructed clusters using KDTree spatial matching
# Returns list of completeness metrics for matched cluster pairs, with unmatched true clusters marked as reco_cluster_id=8888
def EvaluateCompleteness(clusters_true, clusters_reco, event, radius_completeness=1, min_recopoints_threshold=5):
    completeness_results = []
    matched_true_cids = set()  # Track which true clusters found a match
    
    # loop over true clusters and find matching reco clusters based on spatial proximity using KDTree
    for true_cluster_id, true_points in clusters_true.items():
        true_points     = np.array(true_points)
        true_coords     = true_points[:, :3]
        true_energies   = true_points[:, 5]

        # loop over reco clusters and find matches based on proximity to true cluster points using KDTree
        for reco_cluster_id, reco_points in clusters_reco.items():
            reco_points = np.array(reco_points)
            reco_coords = reco_points[:, :3]
            
            reco_tree   = KDTree(reco_coords)
            indices     = reco_tree.query_ball_point(true_coords, r=radius_completeness)
            
            matched_true_points_energy = np.sum([true_energies[i] for i, neighbors in enumerate(indices) if len(neighbors) > min_recopoints_threshold])
            total_true_energy = np.sum(true_energies)
            
            completeness_energy_weighted = matched_true_points_energy / total_true_energy if total_true_energy > 0 else 0
            
            # Only keep pairs with non-zero completeness
            if completeness_energy_weighted > 0:
                matched_true_cids.add(true_cluster_id)
                completeness_results.append({
                    'event': event,
                    'true_cluster_id': true_cluster_id,
                    'reco_cluster_id': reco_cluster_id,
                    'completeness_energy_weighted': completeness_energy_weighted,
                    'matched_true_cluster_energy': matched_true_points_energy,
                    'total_true_cluster_energy': total_true_energy
                })    
    unmatched_count = sum(1 for cid in clusters_true if cid not in matched_true_cids)
    
    for cid_true, true_pts in clusters_true.items():
        if cid_true not in matched_true_cids:
            # This true cluster has no reco match
            true_pts            = np.array(true_pts)
            total_true_energy   = np.sum(true_pts[:, 5])
            if total_true_energy > 0:
                completeness_results.append({
                    'event': event,
                    'true_cluster_id': cid_true,
                    'reco_cluster_id': 8888,  # Sentinel for unmatched
                    'completeness_energy_weighted': 0,  # Sentinel for unmatched
                    'matched_true_cluster_energy': 0.0,
                    'total_true_cluster_energy': total_true_energy
                })
    
    #print(f"  [DEBUG EvaluateCompleteness] Event {event}: {len(matched_true_cids)} matched, {unmatched_count} unmatched, {len(completeness_results)} total results")
    return completeness_results

# Evaluate cluster purity by measuring the fraction of reconstructed points matching true cluster locations using KDTree projection matching
# Returns list of purity metrics for matched cluster pairs, with unmatched reco clusters marked as true_cluster_id=8888 and purity=-0.1
def EvaluatePurity(clusters_true, clusters_reco, event, radius_purity_xz=1, radius_purity_yz=2, radius_purity_xy=2, min_projections=3):
    """
    Fraction of each reco cluster's points lying near a true cluster.

    For every reco point the nearest true point is found in 3D (k=1, unbounded),
    then three PROJECTED distances from that one true point are tested against
    the three radii. min_projections says how many of the three must pass:

      3  (default)  all of them -- the historic behaviour, unchanged for every
                    existing caller
      2             any two, which stops a single tight cut from vetoing a match
                    on its own

    WHY THIS IS A PARAMETER AND NOT AN EDIT. Fifteen call sites share this
    function, and purity decides the reco->true pairing, so changing the rule
    globally would silently move every completeness and purity number in the
    repository. Callers opt in.

    MEASURED (full sample, 553 pairs, 1.29M points, 2026-08-15). With radii
    (2, 5, 5) the xz cut binds and the other two are nearly inert. Going to
    (3, 5, 5) with min_projections=2 accepts ~43,000 more points and promotes 16
    pairs into the high-signal region; only 2 of 553 pairings repoint to a
    different true cluster, so completeness barely moves.
    """
    purity_results = []
    matched_reco_cids = set()  # Track which reco clusters found a match
    
    for reco_cluster_id, reco_points in clusters_reco.items():
        reco_points         = np.array(reco_points)
        reco_coords         = reco_points[:, :3]
        reco_charges        = reco_points[:, 4]  # Extract charge (column 4)
        total_reco_charge   = np.sum(reco_charges)  # Sum of all charges in reco cluster
        
        for true_cluster_id, true_points in clusters_true.items():
            true_points = np.array(true_points)
            true_coords = true_points[:, :3]
            
            true_tree   = KDTree(true_coords)
            distances, indices = true_tree.query(reco_coords, k=1)
            
            nearest_points  = true_coords[indices]
            xz_projection   = np.sqrt((nearest_points[:, 0] - reco_coords[:, 0])**2 + (nearest_points[:, 2] - reco_coords[:, 2])**2)
            yz_projection   = np.sqrt((nearest_points[:, 1] - reco_coords[:, 1])**2 + (nearest_points[:, 2] - reco_coords[:, 2])**2)
            xy_projection   = np.sqrt((nearest_points[:, 0] - reco_coords[:, 0])**2 + (nearest_points[:, 1] - reco_coords[:, 1])**2)

            n_passed = ((xz_projection <= radius_purity_xz).astype(int)
                        + (yz_projection <= radius_purity_yz).astype(int)
                        + (xy_projection <= radius_purity_xy).astype(int))
            matched_reco_points = reco_coords[n_passed >= min_projections]
            total_reco_points   = len(reco_coords)
            purity              = len(matched_reco_points) / total_reco_points if total_reco_points > 0 else 0
            
            # Only keep pairs with non-zero purity
            if purity > 0:
                matched_reco_cids.add(reco_cluster_id)
                purity_results.append({
                    'event': event,
                    'reco_cluster_id': reco_cluster_id,
                    'true_cluster_id': true_cluster_id,
                    'matched_reco_points': len(matched_reco_points),
                    'total_reco_points': total_reco_points,
                    'total_reco_cluster_charge': total_reco_charge,
                    'purity': purity
                })
    
    # Add unmatched reco clusters with purity=-0.1 and true_cluster_id=8888
    for cid_reco, reco_pts in clusters_reco.items():
        if cid_reco not in matched_reco_cids:
            # This reco cluster has no true match
            reco_pts = np.array(reco_pts)
            total_reco_charge = np.sum(reco_pts[:, 4])
            if total_reco_charge > 0:
                purity_results.append({
                    'event': event,
                    'reco_cluster_id': cid_reco,
                    'true_cluster_id': 8888,  # Sentinel for unmatched
                    'purity': -0.1,  # Sentinel for unmatched
                    'total_reco_cluster_charge': total_reco_charge,
                    'matched_reco_charge': -50.0,  # Sentinel for unmatched
                    'matched_true_energy': 0.0,
                    'total_true_cluster_energy': 0.0
                })
    
    return purity_results
