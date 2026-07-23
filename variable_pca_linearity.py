import numpy as np


def calculate_pca_linearity(points):
    """
    PCA linearity = lambda_1 / sum(lambda) of the 3D covariance matrix of a cluster's
    (x, y, z) coordinates. 1.0 = points lie along a single line/curve direction, lower =
    scattered across multiple directions (e.g. fragmented clusters or a multi-track
    neutrino vertex). Same definition used in analyze_cluster_spread.py's Phase 1
    spread-cluster diagnostic.

    Args:
        points: Array-like of shape (n_points, >=3); the first three columns are taken
            as x, y, z (matches both true (7-col) and reco (5-col) cluster point arrays
            produced by GroupClustersByID).

    Returns:
        float linearity value in [0, 1]. Clusters with fewer than 3 points return 1.0
        (not enough points to define a meaningful spread).
    """
    xyz = np.asarray(points)[:, :3]
    if len(xyz) < 3:
        return 1.0

    centered = xyz - xyz.mean(axis=0)
    eigvals = np.clip(np.linalg.eigvalsh(np.cov(centered.T)), 0, None)
    total = eigvals.sum()
    return float(eigvals.max() / total) if total > 0 else 1.0
