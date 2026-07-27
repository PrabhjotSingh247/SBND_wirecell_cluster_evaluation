"""
Phase B helper (see project plan): reconstructs the in-memory shapes
HighStatsEvaluation_MultiFile.ipynb's plotting code expects - clusters_true/clusters_reco
point dicts, cluster_category_results, matched_info, and the true/reco/pair metadata lists -
from the Phase A ROOT file (process_events_to_root.py), so efficiency_purity_draw.py and
DrawRecoTrueClusters.py can be called unmodified with reconstructed arguments instead of
recomputing selections/KDTree matching/category classification from raw JSON.

matched_pairs_exact() gives the exact per-(true,reco)-pair efficiency and purity by joining
true_cluster_metadata's matched_reco_ids/matched_reco_efficiencies (efficiency lives on the
true side) with reco_cluster_metadata's matched_true_ids/matched_true_purities (purity lives
on the reco side) - no aggregate approximation needed.
"""
import numpy as np
import pandas as pd
import uproot


class RootEventStore:
    """Loads a Phase A ROOT file once and provides fast (file, event, apa) lookups."""

    def __init__(self, root_path):
        self._f = uproot.open(root_path)

        self.true_points = self._f["true_points"].arrays(library="np")
        self.reco_points = self._f["reco_points"].arrays(library="np")
        self.true_points_before_deadarea = self._f["true_points_before_deadarea"].arrays(library="np")

        self.true_cluster_metadata_df = pd.DataFrame(self._f["true_cluster_metadata"].arrays(library="np"))
        self.reco_cluster_metadata_df = pd.DataFrame(self._f["reco_cluster_metadata"].arrays(library="np"))
        self.true_reco_pair_metadata_df = pd.DataFrame(self._f["true_reco_pair_metadata"].arrays(library="np"))

        self._true_points_index = self._build_index(self.true_points)
        self._reco_points_index = self._build_index(self.reco_points)
        self._true_points_before_deadarea_index = self._build_index(self.true_points_before_deadarea)

    @staticmethod
    def _build_index(points_np):
        if len(points_np.get("file", [])) == 0:
            return {}
        key_df = pd.DataFrame({"file": points_np["file"], "event": points_np["event"], "apa": points_np["apa"]})
        return key_df.groupby(["file", "event", "apa"], sort=False).indices

    def event_keys(self):
        """All distinct (file_name, event_num, apa) triples, mirroring the notebook's
        file/event/apa loop keys, sorted for reproducible iteration order."""
        df = self.true_cluster_metadata_df
        if df.empty:
            return []
        return sorted(set(zip(df["file_name"], df["event_num"], df["apa"])))

    def files_for_apa(self, apa):
        df = self.true_cluster_metadata_df
        return sorted(df.loc[df["apa"] == apa, "file_name"].unique())

    def events_for_file(self, file_name, apa):
        df = self.true_cluster_metadata_df
        sub = df[(df["file_name"] == file_name) & (df["apa"] == apa)]
        return sorted(sub["event_num"].unique())

    # ---- raw point clouds ----

    def clusters_true(self, file_name, event_num, apa):
        idx = self._true_points_index.get((file_name, event_num, apa))
        if idx is None or len(idx) == 0:
            return {}
        p = self.true_points
        cid = p["true_cluster_id"][idx]
        cols = np.column_stack([p["x"][idx], p["y"][idx], p["z"][idx], cid,
                                 p["q_true"][idx], p["energy"][idx], p["time"][idx]])
        return {c: cols[cid == c] for c in np.unique(cid)}

    def clusters_reco(self, file_name, event_num, apa):
        idx = self._reco_points_index.get((file_name, event_num, apa))
        if idx is None or len(idx) == 0:
            return {}
        p = self.reco_points
        cid = p["reco_cluster_id"][idx]
        cols = np.column_stack([p["x"][idx], p["y"][idx], p["z"][idx], cid, p["charge"][idx]])
        return {c: cols[cid == c] for c in np.unique(cid)}

    def pre_deadarea_points_for_cluster(self, file_name, event_num, apa, true_cluster_id):
        """Full pre-cut points for one true cluster, or None if it wasn't affected by the
        dead-area cut (Phase A only stores affected clusters here)."""
        idx = self._true_points_before_deadarea_index.get((file_name, event_num, apa))
        if idx is None or len(idx) == 0:
            return None
        p = self.true_points_before_deadarea
        cid = p["true_cluster_id"][idx]
        m = cid == true_cluster_id
        if not m.any():
            return None
        sub = idx[m]
        return np.column_stack([p["x"][sub], p["y"][sub], p["z"][sub], p["true_cluster_id"][sub],
                                 p["q_true"][sub], p["energy"][sub], p["time"][sub]])

    def deadarea_before_after_counts(self, file_name, event_num, apa):
        """{cluster_id: count} dicts matching apply_deadarea_cut_true's internal
        cluster_before/cluster_after, reconstructed from true_cluster_metadata."""
        rows = self.true_cluster_rows(file_name, event_num, apa)
        before, after = {}, {}
        for r in rows:
            if pd.notna(r.get("n_points_before_deadarea")):
                before[r["true_cluster_id"]] = int(r["n_points_before_deadarea"])
            if pd.notna(r.get("n_points_after_deadarea")):
                after[r["true_cluster_id"]] = int(r["n_points_after_deadarea"])
        return before, after

    # ---- metadata rows (already exactly the shape add_metadata_* functions produce) ----

    def true_cluster_rows(self, file_name, event_num, apa):
        df = self.true_cluster_metadata_df
        sub = df[(df["file_name"] == file_name) & (df["event_num"] == event_num) & (df["apa"] == apa)]
        return sub.to_dict("records")

    def reco_cluster_rows(self, file_name, event_num, apa):
        df = self.reco_cluster_metadata_df
        sub = df[(df["file_name"] == file_name) & (df["event_num"] == event_num) & (df["apa"] == apa)]
        return sub.to_dict("records")

    def pair_rows(self, file_name, event_num, apa):
        df = self.true_reco_pair_metadata_df
        sub = df[(df["file_name"] == file_name) & (df["event_num"] == event_num) & (df["apa"] == apa)]
        return sub.to_dict("records")

    # ---- reconstructed higher-level structures ----

    def cluster_category_results(self, file_name, event_num, apa):
        """Dict keyed by true_cluster_id, matching cluster_category()'s return shape -
        needed to call DrawTrueClusterCategories directly without recomputing geometry."""
        results = {}
        for r in self.true_cluster_rows(file_name, event_num, apa):
            results[r["true_cluster_id"]] = {
                "is_neutrino": bool(r["is_neutrino"]),
                "track_type": r["cluster_category"],
                "theta_xz": None if pd.isna(r["theta_xz"]) else float(r["theta_xz"]),
                "x_at_z_min": None if pd.isna(r["x_at_z_min"]) else float(r["x_at_z_min"]),
                "x_at_z_max": None if pd.isna(r["x_at_z_max"]) else float(r["x_at_z_max"]),
                "z_min": float(r["z_min"]),
                "z_max": float(r["z_max"]),
            }
        return results

    def matched_pairs_exact(self, file_name, event_num, apa):
        """One row per exact matched (true, reco) pair - {true_cluster_id, reco_cluster_id,
        efficiency_energy_weighted, purity} - by joining the true side's matched_reco_ids/
        matched_reco_efficiencies with the reco side's matched_true_ids/matched_true_purities
        (Phase A stores efficiency on the true side and purity on the reco side)."""
        purity_lookup = {}
        for r in self.reco_cluster_rows(file_name, event_num, apa):
            true_ids = r.get("matched_true_ids")
            purities = r.get("matched_true_purities")
            if true_ids is None:
                continue
            for tid, pur in zip(true_ids, purities):
                purity_lookup[(r["reco_cluster_id"], tid)] = pur

        pairs = []
        for r in self.true_cluster_rows(file_name, event_num, apa):
            matched_ids = r.get("matched_reco_ids")
            matched_effs = r.get("matched_reco_efficiencies")
            if matched_ids is None or len(matched_ids) == 0:
                continue
            for rid, eff in zip(matched_ids, matched_effs):
                pairs.append({
                    "true_cluster_id": r["true_cluster_id"],
                    "reco_cluster_id": rid,
                    "efficiency_energy_weighted": eff,
                    "purity": purity_lookup.get((rid, r["true_cluster_id"]), 0),
                })
        return pairs

    def matched_info_list(self, file_name, event_num, apa):
        """List matching MatchTruetoReco_OneToMany's output shape, for
        DrawTrueClusterWithMatchedReco - now built from exact per-pair values
        (matched_pairs_exact), not an aggregate approximation."""
        true_rows_by_id = {r["true_cluster_id"]: r for r in self.true_cluster_rows(file_name, event_num, apa)}
        grouped = {}
        for p in self.matched_pairs_exact(file_name, event_num, apa):
            grouped.setdefault(p["true_cluster_id"], []).append({
                "reco_cluster_id": p["reco_cluster_id"],
                "efficiency_energy_weighted": p["efficiency_energy_weighted"],
                "purity": p["purity"],
            })

        return [
            {"event": true_rows_by_id[tid]["event"], "true_cluster_id": tid, "matched_reco_clusters": matches}
            for tid, matches in grouped.items()
        ]
