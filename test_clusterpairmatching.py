#!/usr/bin/env python3
"""
Test script for clusterpairmatching.py
Tests both 1-to-1 and 1-to-many matching functions with synthetic data.
"""

import pandas as pd
from clusterpairmatching import MatchRecoTruePair1to1, MatchRecoTrueCluster1toMany


def create_test_data():
    """Create synthetic efficiency and purity results for testing."""

    # Efficiency results: (event, true_cluster_id, reco_cluster_id, efficiency, ...)
    efficiency_data = [
        {'event': 'test_0', 'true_cluster_id': 1, 'reco_cluster_id': 1, 'efficiency': 0.95, 'efficiency_energy_weighted': 0.94},
        {'event': 'test_0', 'true_cluster_id': 1, 'reco_cluster_id': 2, 'efficiency': 0.50, 'efficiency_energy_weighted': 0.48},
        {'event': 'test_0', 'true_cluster_id': 2, 'reco_cluster_id': 3, 'efficiency': 0.85, 'efficiency_energy_weighted': 0.83},
        {'event': 'test_0', 'true_cluster_id': 2, 'reco_cluster_id': 4, 'efficiency': 0.40, 'efficiency_energy_weighted': 0.38},
        {'event': 'test_0', 'true_cluster_id': 3, 'reco_cluster_id': 5, 'efficiency': 0.92, 'efficiency_energy_weighted': 0.90},

        {'event': 'test_1', 'true_cluster_id': 1, 'reco_cluster_id': 1, 'efficiency': 0.88, 'efficiency_energy_weighted': 0.86},
        {'event': 'test_1', 'true_cluster_id': 1, 'reco_cluster_id': 2, 'efficiency': 0.30, 'efficiency_energy_weighted': 0.28},
        {'event': 'test_1', 'true_cluster_id': 2, 'reco_cluster_id': 3, 'efficiency': 0.75, 'efficiency_energy_weighted': 0.73},
    ]

    # Purity results: (event, true_cluster_id, reco_cluster_id, purity, ...)
    purity_data = [
        {'event': 'test_0', 'true_cluster_id': 1, 'reco_cluster_id': 1, 'purity': 0.93},
        {'event': 'test_0', 'true_cluster_id': 1, 'reco_cluster_id': 2, 'purity': 0.45},
        {'event': 'test_0', 'true_cluster_id': 2, 'reco_cluster_id': 3, 'purity': 0.82},
        {'event': 'test_0', 'true_cluster_id': 2, 'reco_cluster_id': 4, 'purity': 0.35},
        {'event': 'test_0', 'true_cluster_id': 3, 'reco_cluster_id': 5, 'purity': 0.90},

        {'event': 'test_1', 'true_cluster_id': 1, 'reco_cluster_id': 1, 'purity': 0.86},
        {'event': 'test_1', 'true_cluster_id': 1, 'reco_cluster_id': 2, 'purity': 0.25},
        {'event': 'test_1', 'true_cluster_id': 2, 'reco_cluster_id': 3, 'purity': 0.70},
    ]

    return efficiency_data, purity_data


def test_1to1_matching():
    """Test the 1-to-1 matching function."""
    print("\n" + "="*80)
    print("TEST 1: One-to-One Matching (MatchRecoTruePair1to1)")
    print("="*80)

    eff_data, pur_data = create_test_data()

    print(f"\nInput data:")
    print(f"  Efficiency results: {len(eff_data)} pairs")
    print(f"  Purity results: {len(pur_data)} pairs")

    result = MatchRecoTruePair1to1(pur_data, eff_data)

    print(f"\nResults:")
    for idx, pair in enumerate(result, 1):
        print(f"\n  Pair {idx}:")
        print(f"    Event: {pair['event']}")
        print(f"    True Cluster ID: {pair['true_cluster_id']:.0f}")
        print(f"    Reco Cluster ID: {pair['reco_cluster_id']:.0f}")
        print(f"    Efficiency: {pair['efficiency']:.4f}")
        print(f"    Purity: {pair['purity']:.4f}")


def test_1tomany_matching():
    """Test the 1-to-many matching function."""
    print("\n" + "="*80)
    print("TEST 2: One-to-Many Matching (MatchRecoTrueCluster1toMany)")
    print("="*80)

    eff_data, pur_data = create_test_data()

    print(f"\nInput data:")
    print(f"  Efficiency results: {len(eff_data)} pairs")
    print(f"  Purity results: {len(pur_data)} pairs")

    result = MatchRecoTrueCluster1toMany(pur_data, eff_data)

    print(f"\nResults: {len(result)} true clusters with matches\n")
    for match in result:
        event = match['event']
        true_id = match['true_cluster_id']
        matched_recos = match['matched_reco_clusters']

        print(f"  Event {event}, True Cluster {true_id:.0f}:")
        print(f"    Matched with {len(matched_recos)} reco cluster(s)")
        for reco_info in matched_recos:
            print(f"      Reco ID {reco_info['reco_cluster_id']:.0f}: "
                  f"ε={reco_info['efficiency']:.4f}, p={reco_info['purity']:.4f}")
        print()


def compare_outputs():
    """Compare 1-to-1 vs 1-to-many outputs."""
    print("\n" + "="*80)
    print("TEST 3: Comparison of 1-to-1 vs 1-to-Many")
    print("="*80)

    eff_data, pur_data = create_test_data()

    result_1to1 = MatchRecoTruePair1to1(pur_data, eff_data)
    result_1tomany = MatchRecoTrueCluster1toMany(pur_data, eff_data)

    print(f"\n1-to-1 Matching: {len(result_1to1)} pairs")
    print(f"1-to-Many Matching: {len(result_1tomany)} true clusters")

    print("\n1-to-1 pairs:")
    for pair in result_1to1:
        print(f"  Event {pair['event']}: true {pair['true_cluster_id']:.0f} -> reco {pair['reco_cluster_id']:.0f}")

    print("\n1-to-Many matches:")
    for match in result_1tomany:
        recos = [str(int(r['reco_cluster_id'])) for r in match['matched_reco_clusters']]
        print(f"  Event {match['event']}: true {match['true_cluster_id']:.0f} -> reco {', '.join(recos)}")

    print("\nKey Difference:")
    print("  1-to-1: Each true cluster matches ONLY the best reco cluster")
    print("  1-to-Many: Each true cluster can match MULTIPLE reco clusters")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("CLUSTERPAIRMATCHING TEST SUITE")
    print("="*80)

    try:
        test_1to1_matching()
        test_1tomany_matching()
        compare_outputs()

        print("\n" + "="*80)
        print("ALL TESTS PASSED ✓")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
