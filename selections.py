import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree
import json
from pathlib import Path
from matplotlib.path import Path as MplPath

# Filter clusters by minimum energy threshold.
# Keeps only clusters with total energy >= energy_cutoff.
def apply_energy_cutoff(true_points, energy_cutoff):
    cluster_sums = {}
    for point in true_points:
        cluster_sums[point[3]] = cluster_sums.get(point[3], 0) + point[5]
    true_points = np.array([point for point in true_points if cluster_sums[point[3]] >= energy_cutoff])
    return true_points

# Drop individual true POINTS depositing less than min_point_energy MeV.
#
# Distinct from apply_energy_cutoff above, which is a CLUSTER cut: that one drops
# a whole cluster whose total is too small, this one thins a cluster by removing
# its smallest deposits while leaving the cluster in place.
#
# WHY 0.02 MeV IS THE DEFAULT ELSEWHERE. Measured over the full 100-file sample
# (1363 events, 782 paired neutrino clusters, 5.8M true points): the per-point
# spectrum has a sharp edge at ~0.03 MeV with the bulk of points above it and a
# thin shelf running three decades below. A 0.02 MeV cut sits at the top of that
# shelf, just under the edge -- it removes 1.8% of the points a reco cluster
# covers and 0.12% of their energy, so cluster totals and every energy-binned
# quantity are effectively unchanged, while removing 32% of the true points no
# reco cluster covers at all.
#
# Do NOT raise it much further without re-measuring: 0.02 MeV is close to the
# edge, and by 0.05 MeV the cut has crossed it and removes 48% of covered points
# and 25% of covered energy -- rewriting the completeness denominator rather than
# tidying it. The measurement is
# AnalysisDistributions/draw_true_pointwise_energy_cut.py.
#
# Applied BEFORE apply_energy_cutoff wherever both are used, so the cluster total
# the cluster cut tests is the total of the points that survive -- the other
# order would admit clusters on the strength of energy this cut then discards.
def apply_true_pointwise_energy_cutoff(true_points, min_point_energy):
    if true_points is None or len(true_points) == 0:
        return true_points
    true_points = np.asarray(true_points)
    return true_points[true_points[:, 5] > min_point_energy]

# Filter true clusters by minimum point count threshold.
# Removes clusters with fewer than min_points points.
def apply_min_true_points_cutoff(true_points, min_points):
    cluster_counts = {}
    for point in true_points:
        cluster_id = point[3]
        cluster_counts[cluster_id] = cluster_counts.get(cluster_id, 0) + 1
    true_points = np.array([point for point in true_points if cluster_counts[point[3]] >= min_points])
    return true_points

# Filter reconstructed clusters by minimum point count threshold.
# Removes clusters with fewer than min_points points.
def apply_min_reco_points_cutoff(reco_points, min_points):
    cluster_counts = {}
    for point in reco_points:
        cluster_id = point[3]
        cluster_counts[cluster_id] = cluster_counts.get(cluster_id, 0) + 1
    reco_points = np.array([point for point in reco_points if cluster_counts[point[3]] >= min_points])
    return reco_points

# Remove true points outside the fiducial volume boundaries.
# Keeps only points within x, y, z limits.
# ============================================================================
# WIRE-READOUT SENSITIVE VOLUME
# ============================================================================
# The fiducial bounds, in cm, in ONE place. Every notebook used to carry its own
# copy of these six numbers and pass them to the cut by hand; they are here so a
# change reaches every script at once.
#
# They define two things that must agree: which true POINTS survive the fiducial
# cut, and what vertex_in_volume means for the signal definition
# (metadata.build_neutrino_vertex_records). A notebook that took the cut from
# here but kept its own numbers for the vertex flag would cut points at one
# boundary and call an interaction "in volume" at another.
WIRE_READOUT_X_MIN = -201.45
WIRE_READOUT_X_MAX = 201.45
WIRE_READOUT_Y_MIN = -200.0
WIRE_READOUT_Y_MAX = 200.0
WIRE_READOUT_Z_MIN = 0.15
WIRE_READOUT_Z_MAX = 500.85


def apply_wire_readout_sensitive_yz_plane_cut_true(true_points):
    x_min = WIRE_READOUT_X_MIN
    x_max = WIRE_READOUT_X_MAX
    y_min = WIRE_READOUT_Y_MIN
    y_max = WIRE_READOUT_Y_MAX
    z_min = WIRE_READOUT_Z_MIN
    z_max = WIRE_READOUT_Z_MAX
    
    filtered_points = []
    for point in true_points:
        x, y, z = point[0], point[1], point[2]
        if x_min <= x <= x_max and y_min <= y <= y_max and z_min <= z <= z_max:
            filtered_points.append(point)
    return np.array(filtered_points) if filtered_points else np.array([]).reshape(0, 6)

# Remove reconstructed points outside the fiducial volume boundaries.
# Keeps only points within x, y, z limits.
def apply_wire_readout_sensitive_yz_plane_cut_reco(reco_points):
    x_min = WIRE_READOUT_X_MIN
    x_max = WIRE_READOUT_X_MAX
    y_min = WIRE_READOUT_Y_MIN
    y_max = WIRE_READOUT_Y_MAX
    z_min = WIRE_READOUT_Z_MIN
    z_max = WIRE_READOUT_Z_MAX
    filtered_points = []
    for point in reco_points:
        x, y, z = point[0], point[1], point[2]
        if x_min <= x <= x_max and y_min <= y <= y_max and z_min <= z <= z_max:
            filtered_points.append(point)
    return np.array(filtered_points) if filtered_points else np.array([]).reshape(0, 5)

# ============================================================================
# FIDUCIAL VOLUME CUT
# ============================================================================

# Fiducial volume cuts
Fiducial_X_MIN = -198.0
Fiducial_X_MAX = 198.0
Fiducial_Y_MIN = -198.0
Fiducial_Y_MAX = 198.0
Fiducial_Z_MIN = 2.0
Fiducial_Z_MAX = 498.0

# ----------------------------------------------------------------------------
# TWO TPCs, AND THE CATHODE BETWEEN THEM
# ----------------------------------------------------------------------------
# SBND is two drift volumes either side of a cathode centred on x = 0. The
# fiducial volume is therefore NOT one box: it is one box per TPC, and a vertex
# counts as in-volume when it is fiducial in EITHER of them.
#
# The cathode is 2 cm thick, so it occupies |x| <= 2. Applying the same 2 cm
# fiducial margin used elsewhere pushes the exclusion out to |x| <= 4, and a
# vertex anywhere in x = [-4, 4] is OUT of volume. That region is not a fiducial
# choice so much as an admission: charge either side of the cathode drifts away
# from it, so a vertex sitting in it has no well-defined TPC and its drift
# coordinate is the least trustworthy in the detector.
CATHODE_HALF_THICKNESS_CM = 2.0
FIDUCIAL_CATHODE_MARGIN_CM = 2.0
# |x| below this is excluded: the cathode itself plus the margin.
FIDUCIAL_CATHODE_EXCLUSION_CM = CATHODE_HALF_THICKNESS_CM + FIDUCIAL_CATHODE_MARGIN_CM

# The two TPC fiducial x ranges, as (low, high). TPC0 drifts one way and TPC1
# the other; a point is fiducial in x when it falls in either.
FIDUCIAL_X_INTERVALS = ((Fiducial_X_MIN, -FIDUCIAL_CATHODE_EXCLUSION_CM),
                        (FIDUCIAL_CATHODE_EXCLUSION_CM, Fiducial_X_MAX))


def in_fiducial_volume(x, y, z,
                       x_min=None, x_max=None, y_min=None, y_max=None,
                       z_min=None, z_max=None,
                       cathode_exclusion=None):
    """
    Is this position inside the fiducial volume of EITHER TPC?

    y and z are a plain range test. x is the TPC-aware part: the position has to
    sit in one of the two drift volumes, which means |x| at least
    cathode_exclusion (clear of the cathode) and at most x_max (clear of the
    anode). A position in x = [-4, 4] fails both TPCs and is OUT.

    The bounds default to the module constants; pass them to ask the same
    question of a different volume. Scalar or array x/y/z both work -- the array
    form is what apply_fiducial_volume_cut uses.
    """
    x_min = Fiducial_X_MIN if x_min is None else x_min
    x_max = Fiducial_X_MAX if x_max is None else x_max
    y_min = Fiducial_Y_MIN if y_min is None else y_min
    y_max = Fiducial_Y_MAX if y_max is None else y_max
    z_min = Fiducial_Z_MIN if z_min is None else z_min
    z_max = Fiducial_Z_MAX if z_max is None else z_max
    gap   = FIDUCIAL_CATHODE_EXCLUSION_CM if cathode_exclusion is None else cathode_exclusion

    x = np.asarray(x); y = np.asarray(y); z = np.asarray(z)
    in_tpc0 = (x >= x_min) & (x <= -gap)
    in_tpc1 = (x >= gap)   & (x <= x_max)
    inside = (in_tpc0 | in_tpc1) & (y >= y_min) & (y <= y_max) & (z >= z_min) & (z <= z_max)
    return bool(inside) if inside.ndim == 0 else inside


# remove points outside the fiducial volume
def apply_fiducial_volume_cut(points):
    points = np.asarray(points)
    if not len(points):
        return points
    keep = in_fiducial_volume(points[:, 0], points[:, 1], points[:, 2])
    kept = points[keep]
    return kept if len(kept) else np.array([]).reshape(0, points.shape[1])


# THE FIDUCIAL VOLUME IS THE SIGNAL DEFINITION, AND ONLY THAT. The six numbers
# above decide one thing: whether a neutrino INTERACTION VERTEX counts as in
# volume -- vertex_in_volume in metadata.build_neutrino_vertex_records, which is
# what separates signal from out-of-volume background everywhere downstream.
# build_neutrino_vertex_records DEFAULTS to these bounds for that reason.
#
# IT IS NOT A CUT ON THE TRUE POINTS. The points are cut by the wire-readout
# sensitive volume above (the detector geometry) and nothing else. A neutrino
# whose vertex is inside this volume is signal however far its tracks reach, and
# all of its energy belongs to it -- applying these bounds to the points would
# shrink the true energy of exactly the interactions nearest the boundary while
# still counting them as signal.
#
# The volume sits strictly inside the wire-readout sensitive volume above
# (198 < 201.45, 198 < 200, [2, 498] inside [0.15, 500.85]), so a vertex that
# passes it has passed that one too.
#
# Keyed by COLUMN INDEX of the standard point arrays (0=x, 1=y, 2=z) so the
# drawing code can look up a boundary straight from a view's axis index.
FIDUCIAL_BOUNDS_BY_AXIS = {
    0: (Fiducial_X_MIN, Fiducial_X_MAX),
    1: (Fiducial_Y_MIN, Fiducial_Y_MAX),
    2: (Fiducial_Z_MIN, Fiducial_Z_MAX),
}

# The gap in the middle of an axis, for drawing. Only x has one -- the cathode
# exclusion -- and a boundary drawn from FIDUCIAL_BOUNDS_BY_AXIS alone would
# show a single accepted band from -198 to 198 and hide it.
FIDUCIAL_EXCLUDED_BY_AXIS = {
    0: (-FIDUCIAL_CATHODE_EXCLUSION_CM, FIDUCIAL_CATHODE_EXCLUSION_CM),
}


# ============================================================================
# COSMIC TAGGER CUT
# ============================================================================
# WireCell's cosmic taggers (tagger_stm, tagger_tgm, ...) write one file per
# event holding a point cloud with a per-point flag -- see
# readfiles.read_tagger_from_json, which explains why the column named
# 'cluster_id' in those files is a FLAG and not an id.
#
# HOW A TAGGED POINT IS TIED TO A RECO CLUSTER: by POSITION, nearest neighbour
# within COSMIC_TAG_MATCH_RADIUS_CM. NOT by charge -- the tagger files carry a
# 'q' on a different scale from clustering-global's, and of 3698 exactly
# coincident points on chunk0 event 73 only 3 had matching q. Position is exact
# or near enough: 3698 of 4418 coincide to 1e-4 cm, worst offset 0.71 cm.
COSMIC_TAG_MATCH_RADIUS_CM = 1.0

# How many flagged points a cluster needs before it counts as tagged. A
# nearest-neighbour match across two point clouds always finds a few stragglers,
# and one stray point is not a tagged cosmic.
COSMIC_TAG_MIN_POINTS = 10

# ----------------------------------------------------------------------------
# HOW FAR DOES ONE TAG SPREAD?
# ----------------------------------------------------------------------------
# A tagger flags points; those points sit in some cluster; the question is what
# else goes with that cluster.
#
#   'flash' (current)  the tag removes every cluster sharing the tagged
#                      cluster's FLASH, and nothing else. All activity at one
#                      flash time is one interaction and the reconstruction
#                      cannot separate it, so it goes together -- but activity at
#                      a DIFFERENT flash time in the same event is separable, is
#                      demonstrably a different interaction, and is kept.
#   'event'            the original all-or-nothing: one tagged cluster removes
#                      every in-beam cluster in the event, whatever its flash.
#                      This is what wrongly removed the neutrino in chunk4
#                      event 70 -- a tagged cosmic on flash 14 (t = 0.578 us)
#                      took a numu CC on flash 15 (t = 1.596 us) with it.
#   'none'             only the clusters a tagger flagged directly.
#
# WHICH CLUSTERS SHARE A FLASH is supplied by the caller as
# flash_group_by_cluster = {cluster id: flash key}. When it is NOT supplied,
# every cluster is treated as its own flash group, so 'flash' behaves like
# 'none'. That default is correct wherever the reco id is clustering-global's
# COARSE cluster_id, because that grouping is already flash-based -- one coarse
# cluster IS one flash's activity (verified on chunk4 event 70: reals 23 and 28
# share flash 15 and one coarse id, while real 6 on flash 14 stays separate).
# Pass the mapping when working in the real_cluster_id namespace, where
# flash-mates are separate clusters and the tag does need to reach them.
COSMIC_TAG_PROPAGATE_SCOPE = 'flash'


def tagged_tagger_points(tagger_arrays):
    """
    (N, 3) positions of the points one tagger FLAGGED, from an entry of
    read_charge_light_files_for_event()['taggers'].

    Empty when that tagger flagged nothing, which is the normal case for most
    taggers on most events.
    """
    if not tagger_arrays:
        return np.empty((0, 3))
    x, y, z, tagged = (np.asarray(a, dtype=float) for a in tagger_arrays[:4])
    if not len(x):
        return np.empty((0, 3))
    flagged = tagged == 1
    return np.column_stack((x[flagged], y[flagged], z[flagged]))


def tag_reco_clusters(taggers, clusters_reco,
                      match_radius=COSMIC_TAG_MATCH_RADIUS_CM,
                      min_tagged_points=COSMIC_TAG_MIN_POINTS,
                      propagate_scope=None,
                      flash_group_by_cluster=None):
    """
    Which reco clusters the taggers flagged, in ONE event.

    clusters_reco is {cluster id: points}, and should be the BEAM-WINDOW
    survivors -- that is the set a propagated tag would spread across.

    Returns {cluster id: {'taggers', 'n_tagged', 'n_points', 'tagged_directly'}}.

    A cluster is tagged DIRECTLY when min_tagged_points of its own points are
    flagged. That is the whole result when propagate_scope is 'none'.

    propagate_scope defaults to COSMIC_TAG_PROPAGATE_SCOPE -- see there for what
    'flash', 'event' and 'none' mean and why the flash one is the default.
    flash_group_by_cluster = {cluster id: flash key} says which clusters share a
    flash; without it each cluster is its own group.

    Propagated entries carry tagged_directly=False, an empty n_tagged and a
    'propagated_from' listing the clusters actually flagged, so a caller can
    always tell a real tag from an inherited one.
    """
    if propagate_scope is None:
        propagate_scope = COSMIC_TAG_PROPAGATE_SCOPE
    if propagate_scope not in ('none', 'flash', 'event'):
        raise ValueError(f"propagate_scope must be 'none', 'flash' or 'event', "
                         f"got {propagate_scope!r}")
    direct = {}
    for cluster_id, points in (clusters_reco or {}).items():
        points = np.asarray(points, dtype=float)
        if not len(points):
            continue
        tree = cKDTree(points[:, :3])
        per_tagger = {}
        for name, arrays in (taggers or {}).items():
            flagged = tagged_tagger_points(arrays)
            if not len(flagged):
                continue
            distances, _ = tree.query(flagged, k=1)
            n_hit = int((distances <= match_radius).sum())
            if n_hit >= min_tagged_points:
                per_tagger[name] = n_hit
        if per_tagger:
            direct[cluster_id] = {
                'taggers':         sorted(per_tagger),
                'n_tagged':        per_tagger,
                'n_points':        len(points),
                'tagged_directly': True,
            }

    if not direct or propagate_scope == 'none':
        return direct

    # Which clusters a tag is allowed to reach. 'event' is one group holding
    # everything; 'flash' groups by the caller's flash key, and a cluster with no
    # key is its own group -- never lumped in with the others, because "we do not
    # know its flash" is not evidence that it shares one.
    flash_group_by_cluster = flash_group_by_cluster or {}
    def group_of(cluster_id):
        if propagate_scope == 'event':
            return '__event__'
        return flash_group_by_cluster.get(cluster_id, ('__ungrouped__', cluster_id))

    tagged_groups = {group_of(cluster_id) for cluster_id in direct}
    result = dict(direct)
    every_tagger = sorted({name for entry in direct.values() for name in entry['taggers']})
    for cluster_id, points in clusters_reco.items():
        if cluster_id in result or group_of(cluster_id) not in tagged_groups:
            continue
        points = np.asarray(points, dtype=float)
        if not len(points):
            continue
        result[cluster_id] = {
            'taggers':         every_tagger,
            'n_tagged':        {},
            'n_points':        len(points),
            'tagged_directly': False,
            'propagated_from': sorted(cid for cid in direct
                                      if group_of(cid) == group_of(cluster_id)),
        }
    return result


def apply_cosmic_tagger_cut(reco_points, taggers,
                            match_radius=COSMIC_TAG_MATCH_RADIUS_CM,
                            min_tagged_points=COSMIC_TAG_MIN_POINTS,
                            propagate_scope=None,
                            flash_group_by_cluster=None):
    """
    Remove in-beam reco activity the cosmic taggers flagged.

    reco_points is the BEAM-WINDOW point array (N x 5: x, y, z, cluster_id, q) --
    the output of the beam-window selection, before it is grouped. taggers is the
    event's 'taggers' dict from read_charge_light_files_for_event.

    Returns (kept_points, info) where info is
    {'n_tagged_clusters', 'n_direct', 'tagged_cluster_ids', 'tagged_by',
     'n_points_removed'}.

    WHAT GETS REMOVED is a WHOLE CLUSTER, and how far the tag spreads beyond the
    directly-flagged one is set by COSMIC_TAG_PROPAGATE_SCOPE (overridable per
    call). Read that constant before using any number this produces:

      'flash' (current)  the tagged cluster and anything sharing its flash.
                         Activity at a different flash time in the same event is
                         KEPT -- it is separable, so it is a different
                         interaction.
      'event'            the original all-or-nothing; the returned array is
                         empty. Removes neutrinos that merely shared the window.
      'none'             only the directly-flagged clusters.

    flash_group_by_cluster = {cluster id: flash key} tells 'flash' which clusters
    go together. Omit it when the ids are clustering-global's COARSE cluster_id,
    which is already one-cluster-per-flash; pass it in the real_cluster_id
    namespace, where flash-mates are separate clusters.

    An event with no tagger files, or with nothing flagged, is returned
    unchanged.

    info carries 'n_tagged_clusters', 'n_direct' (flagged on their own points),
    'tagged_cluster_ids', 'tagged_by' and 'n_points_removed'. The gap between
    n_tagged_clusters and n_direct is exactly what propagation added.
    """
    empty_info = {'n_tagged_clusters': 0, 'n_direct': 0, 'tagged_cluster_ids': [],
                  'tagged_by': [], 'n_points_removed': 0}
    reco_points = np.asarray(reco_points)
    if not len(reco_points) or not taggers:
        return reco_points, empty_info

    clusters_reco = GroupClustersByID(reco_points)
    tagged = tag_reco_clusters(taggers, clusters_reco, match_radius=match_radius,
                               min_tagged_points=min_tagged_points,
                               propagate_scope=propagate_scope,
                               flash_group_by_cluster=flash_group_by_cluster)
    if not tagged:
        return reco_points, dict(empty_info)

    keep = ~np.isin(reco_points[:, 3],
                    np.fromiter(tagged, dtype=float, count=len(tagged)))
    info = {
        'n_tagged_clusters':  len(tagged),
        'n_direct':           sum(1 for e in tagged.values() if e['tagged_directly']),
        'tagged_cluster_ids': sorted(tagged),
        'tagged_by':          sorted({name for e in tagged.values() for name in e['taggers']}),
        'n_points_removed':   int((~keep).sum()),
    }
    return reco_points[keep], info


# Reassign cluster IDs to true clusters sequentially.
# Ensures IDs start from 0 and are contiguous.
def reassign_cluster_ID_true(points_5d):
    clusters = {}
    for point in points_5d:
        cluster_id = point[3]
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(point)
    
    new_points = []
    for cluster_id, points in clusters.items():
        points = np.array(points)
        avg_xy = np.mean(points[:, 0])
        avg_xy = round(avg_xy, 2)
        if points[:, 4].any() == 1: 
            avg_xy = 9999
        points[:, 3] = avg_xy
        new_points.append(points)
    
    points_5d_after_reassigning = np.vstack(new_points)
    return points_5d_after_reassigning

def reassign_cluster_ID_true_charge_light(points_5d):
    """
    nu_idx-aware version of reassign_cluster_ID_true() for the charge-light
    matching pipeline, where points[:, 4] (q_true) already holds the actual
    neutrino index (0=cosmic, 1/2/3/...=which neutrino interaction) rather
    than a plain 0/1 flag -- see build_true_points_charge_light's nu_idx=
    parameter. Cosmic clusters are reassigned exactly as in
    reassign_cluster_ID_true() (rounded avg X). Neutrino-associated clusters
    are reassigned to 99990 + nu_idx (99991, 99992, 99993, ...) instead of a
    single shared 9999, so GroupClustersByID keeps each neutrino interaction
    as its own cluster instead of merging them all together.

    Kept separate from reassign_cluster_ID_true() -- that function is still
    used by metadata.py, process_events_to_root.py, analyze_cluster_spread.py,
    and Evaluation_BeforeChargeLightMatching_BeforeBeamWindowCut.ipynb, none of which have per-point
    nu_idx available or expect this ID scheme.
    """
    clusters = {}
    for point in points_5d:
        cluster_id = point[3]
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(point)

    new_points = []
    for cluster_id, points in clusters.items():
        points = np.array(points)
        avg_xy = round(np.mean(points[:, 0]), 2)
        nu_idx_values = points[points[:, 4] > 0, 4]
        if len(nu_idx_values) > 0:
            # A pre-reassignment cluster_id groups points from one particle/
            # track, which belongs to exactly one neutrino interaction --
            # take the most common nonzero nu_idx as a defensive fallback in
            # case that's ever not perfectly uniform within the group.
            values, counts = np.unique(nu_idx_values, return_counts=True)
            nu_idx = int(values[np.argmax(counts)])
            avg_xy = 99990 + nu_idx
        points[:, 3] = avg_xy
        new_points.append(points)

    points_5d_after_reassigning = np.vstack(new_points)
    return points_5d_after_reassigning

# Reassign cluster IDs to reconstructed clusters sequentially.
# Ensures IDs start from 0 and are contiguous.
def reassign_cluster_ID_reco(points_5d_reco):
    clusters = {}
    for point in points_5d_reco:
        cluster_id = point[3]
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(point)
    
    new_points = []
    for cluster_id, points in clusters.items():
        points  = np.array(points)
        avg_x   = np.mean(points[:, 0])
        avg_x   = round(avg_x, 3)  # or round(avg_y, 2) depending on your needs
        points[:, 3] = avg_x
        new_points.append(points)
    
    points_5d_after_reassigning = np.vstack(new_points)
    return points_5d_after_reassigning

# Group points by their cluster ID.
# Returns dictionary mapping cluster ID to list of points.
def GroupClustersByID(points_5d):
    clusters = {}
    for point in points_5d:
        cluster_id = point[3]
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(point)
    return clusters

# Shift Z coordinate values of reconstructed clusters by a fixed offset.
# Used to align reco and true coordinate systems.
def ShiftRecoClusterZValues(clusters_reco, shift_value=0.5):
    for cluster_id, points in clusters_reco.items():
        points          = np.array(points)
        shifted_points  = points[:, 2]
        shifted_points  = shifted_points + shift_value
        points[:, 2]    = shifted_points
        clusters_reco[cluster_id] = points
    return clusters_reco

# Apply Time Window Cut to true
# For true points, we need to consider the time of the event (t0) and the drift time to calculate the recorded time (t_recorded).
# time t0 is point[6], x0 is true x position (point[0])
# x_collection is the position of the collection plane (-202.05 for APA0 and +202.05 for APA1)
# x_drft = abs(x0 - x_collection) where x_collection is the collection plane position (202.05 for APA0 and -202.05 for APA1)
# t_drift is x_drft / drift_velocity
# t_recorded = t0 + t_drift
# To apply time window cut, we need to calculate t_recorded for each point and check if it falls within the time window

def apply_time_window_cut(cluster, time_window_min, time_window_max, apa):
    print("Applying Time Window Cut")
    print("APA: ", apa)

    drift_velocity  = 0.1563  # cm/us
    time_min        = time_window_min
    time_max        = time_window_max

    if apa == "APA0":
        x_collection = -202.05
    else:
        x_collection = 202.05

    # print number of points before time window cut for debugging
    print(f"Number of points before time window cut: {len(cluster)}")

    # Track per-cluster statistics and t_recorded values
    cluster_before = {}
    cluster_after = {}
    t_recorded_before = {}  # t_recorded values before cut, per cluster
    t_recorded_after = {}   # t_recorded values after cut, per cluster

    filtered_points = []
    for point in cluster:
        x0          = point[0]                      # true absolute x position in cm
        t0          = point[6]/1000                 # true absolute time. Converted from ns to us
        x_drift     = abs(x0 - x_collection)        # drift distance in cm
        t_drift     = x_drift / drift_velocity      # drift time in us
        t_recorded  = t0 + t_drift                  # recorded time in us

        cluster_id = int(point[3])
        cluster_before[cluster_id] = cluster_before.get(cluster_id, 0) + 1

        if cluster_id not in t_recorded_before:
            t_recorded_before[cluster_id] = []
        t_recorded_before[cluster_id].append(t_recorded)

        if time_min <= t_recorded <= time_max:      # check if recorded time falls within the time window
            filtered_points.append(point)
            cluster_after[cluster_id] = cluster_after.get(cluster_id, 0) + 1

            if cluster_id not in t_recorded_after:
                t_recorded_after[cluster_id] = []
            t_recorded_after[cluster_id].append(t_recorded)

    # print number of points after time window cut for debugging
    print(f"Number of points after time window cut: {len(filtered_points)}")

    # Debug: show clusters that lost all points or significant points
    for cid in cluster_before:
        if cid not in cluster_after:
            print(f"  WARNING: Cluster {cid} lost all {cluster_before[cid]} points to time window cut")
        else:
            lost = cluster_before[cid] - cluster_after[cid]
            if lost > 0:
                pct = (lost / cluster_before[cid]) * 100
                print(f"  Cluster {cid}: {cluster_before[cid]} -> {cluster_after[cid]} points ({lost} removed, {pct:.1f}%)")

    # Create visualization of t_recorded distribution for all clusters
    all_clusters = sorted(list(cluster_before.keys()))
    if all_clusters:
        fig, axes = plt.subplots(len(all_clusters), 1, figsize=(10, 4 * len(all_clusters)), sharex=True)
        if len(all_clusters) == 1:
            axes = [axes]

        for idx, cid in enumerate(all_clusters):
            ax = axes[idx]

            # Plot all t_recorded before cut
            t_before = np.array(t_recorded_before[cid])
            ax.hist(t_before, bins=20, alpha=0.5, label=f'Before cut ({len(t_before)} points)', color='blue', edgecolor='black')

            # Plot t_recorded after cut (if cluster survived)
            if cid in t_recorded_after:
                t_after = np.array(t_recorded_after[cid])
                ax.hist(t_after, bins=20, alpha=0.5, label=f'After cut ({len(t_after)} points)', color='green', edgecolor='black')

            # Draw time window boundaries
            ax.axvline(time_min, color='red', linestyle='--', linewidth=2, label=f'Time window min: {time_min}')
            ax.axvline(time_max, color='red', linestyle='--', linewidth=2, label=f'Time window max: {time_max}')

            # Get y-axis limits for shading
            y_min, y_max = ax.get_ylim()
            ax.fill_betweenx([y_min, y_max], time_min, time_max, alpha=0.2, color='green', label='Valid time window')

            # Check if cluster lost all points
            status = "REMOVED" if cid not in cluster_after else "KEPT"
            ax.set_xlabel('t_recorded (μs)')
            ax.set_ylabel('Number of points')
            ax.set_title(f'Cluster {cid}: t_recorded distribution - {status}')
            ax.legend()
            ax.grid(True, alpha=0.3)

        fig.tight_layout()
        fig.savefig('time_window_cut_analysis.png', dpi=100, bbox_inches='tight')
        print(f"\nVisualization saved to: time_window_cut_analysis.png")
        plt.show()

    return np.array(filtered_points) if filtered_points else np.array([]).reshape(0, cluster.shape[1])


# Remove true points that lie inside dead area regions.
# Dead areas are defined as 2D polygons in (y, z) coordinates.
# Points inside any dead area polygon are removed.
def apply_deadarea_cut_true(true_points, apa, view_type="2view", output_dir=None, event=None, file_name=None):
    """
    Remove true points that fall inside dead area regions.
    If a cluster is affected by dead area, draw it with the dead area regions.

    Parameters:
    -----------
    true_points : ndarray
        Array of true points with shape (N, M) where columns are:
        [x, y, z, cluster_id, charge, energy, time]
    apa : str
        Which APA ("APA0" or "APA1")
    view_type : str
        Which view to use ("2view" or "3view")
    output_dir : Path, optional
        Directory to save visualization plots of affected clusters
    event : int, optional
        Event number for plot titles
    file_name : str, optional
        File name for plot titles

    Returns:
    --------
    ndarray
        Filtered true points with those inside dead areas removed
    """
    print("Applying Dead Area Cut")
    print(f"APA: {apa}, View: {view_type}")

    # Load dead area JSON files
    deadarea_base = Path(__file__).parent / "Deadareas"

    if view_type == "2view":
        deadarea_path = deadarea_base / "2viewactive_2viewdead"
    else:
        deadarea_path = deadarea_base / "3viewactive_1viewdead"

    if apa == "APA0":
        deadarea_file = deadarea_path / "0-channel-deadarea-apa0-face0.json"
    else:
        deadarea_file = deadarea_path / "0-channel-deadarea-apa1-face0.json"

    if not deadarea_file.exists():
        print(f"Warning: Dead area file not found at {deadarea_file}")
        print("Returning points unmodified")
        return true_points

    # Load dead area data
    with open(deadarea_file, 'r') as f:
        deadarea_data = json.load(f)

    # Create list of matplotlib Path objects for each dead area polygon
    # Dead area coordinates are [y, z] pairs
    polygon_paths = []
    for shape in deadarea_data:
        # Convert list of [y, z] coordinates to (y, z) tuples for matplotlib
        vertices = np.array([[p[0], p[1]] for p in shape])
        path = MplPath(vertices)
        polygon_paths.append(path)

    # Count statistics before and after
    points_before = len(true_points)
    cluster_before = {}
    cluster_after = {}
    affected_clusters = {}  # Track clusters with points removed
    full_clusters = {}  # Store full cluster data before filtering

    # Group points by cluster ID to get full clusters
    for point in true_points:
        cluster_id = int(point[3])
        cluster_before[cluster_id] = cluster_before.get(cluster_id, 0) + 1
        if cluster_id not in full_clusters:
            full_clusters[cluster_id] = []
        full_clusters[cluster_id].append(point)

    # Filter points: keep only those NOT inside any dead area
    # Dead areas are defined only in YZ plane (independent of X coordinate)
    filtered_points = []
    for point in true_points:
        # Extract only YZ coordinates (dead areas are independent of X)
        y, z = point[1], point[2]
        point_yz = np.array([[y, z]])

        # Check if point (in YZ plane) is inside any dead area polygon
        is_in_deadarea = False
        for path in polygon_paths:
            if path.contains_points(point_yz)[0]:
                is_in_deadarea = True
                break

        # Keep point if it's NOT in any dead area
        if not is_in_deadarea:
            filtered_points.append(point)
            cluster_id = int(point[3])
            cluster_after[cluster_id] = cluster_after.get(cluster_id, 0) + 1
        else:
            # Track affected cluster (point is inside dead area)
            cluster_id = int(point[3])
            if cluster_id not in affected_clusters:
                affected_clusters[cluster_id] = {'before': 0, 'after': 0}
            affected_clusters[cluster_id]['before'] += 1

    points_after = len(filtered_points)
    points_removed = points_before - points_after

    print(f"Number of points before dead area cut: {points_before}")
    print(f"Number of points after dead area cut: {points_after}")
    print(f"Points removed: {points_removed} ({100*points_removed/points_before:.1f}%)" if points_before > 0 else "")

    # Show per-cluster statistics
    for cid in sorted(cluster_before.keys()):
        before = cluster_before[cid]
        after = cluster_after.get(cid, 0)
        if after == 0:
            print(f"  Cluster {cid}: {before} -> {after} points (REMOVED)")
        elif after < before:
            removed = before - after
            pct = (removed / before) * 100
            print(f"  Cluster {cid}: {before} -> {after} points ({removed} removed, {pct:.1f}%)")

    # Draw clusters before and after dead area cut
    if output_dir is not None:
        try:
            from DrawRecoTrueClusters import DrawClusterBeforeAfterDeadArea, DrawPointsBeforeAfterDeadArea
            #DrawClusterBeforeAfterDeadArea(true_points, filtered_points, deadarea_data, event, apa, output_dir, file_name)
            DrawPointsBeforeAfterDeadArea(cluster_before, cluster_after, event, apa, output_dir, file_name)
            print(f"\nDrew before/after dead area visualizations")
        except Exception as e:
            print(f"Warning: Could not draw before/after visualizations: {e}")

    # Draw affected clusters with dead area overlay if output_dir is provided
    if output_dir is not None and affected_clusters:
        try:
            from DrawRecoTrueClusters import DrawTrueClusterWithDeadArea
            print(f"\nDrawing {len(affected_clusters)} clusters affected by dead area...")
            for cluster_id in affected_clusters.keys():
                # Draw the FULL cluster (before filtering) with dead area overlay
                if cluster_id in full_clusters:
                    full_cluster_points = np.array(full_clusters[cluster_id])
                    DrawTrueClusterWithDeadArea(full_cluster_points, deadarea_data, cluster_id, event, apa, output_dir, file_name)
                    print(f"  Drew cluster {cluster_id} (full cluster with dead area overlay)")
        except Exception as e:
            print(f"Warning: Could not draw affected clusters: {e}")

    return np.array(filtered_points) if filtered_points else np.array([]).reshape(0, true_points.shape[1])


# ============================================================================
# CHARGE-LIGHT MATCHING FORMAT (additive; existing functions above are untouched)
# ============================================================================
# sed-sce_drift_smear_readout.json has no explicit q_true (neutrino/cosmic) flag
# like the older true*.json files. Instead, its cluster_id is a G4 trackID whose
# leading digit encodes the originating generator -- verified to cover 100% of
# points across all 10 test events, no exceptions:
#   10,000,000-19,999,999 -> neutrino-interaction trackIDs
#   20,000,000-29,999,999 -> cosmic-ray (CORSIKA) trackIDs
# build_true_points_charge_light() derives q_true from that namespace and
# assembles the same 7-column [x, y, z, cluster_id, q_true, energy, time] layout
# reassign_cluster_ID_true() already expects, so the existing reassignment /
# selection / completeness / purity pipeline runs unmodified on charge-light data.
# There is no per-point true time in this format, so the time column is filled
# with 0.0 -- apply_time_window_cut should stay disabled for charge-light data
# until a real per-point timing source is identified.

NEUTRINO_TRACKID_PREFIX = 1
COSMIC_TRACKID_PREFIX   = 2

def build_true_points_charge_light(x, y, z, cluster_id, charge, energy=None, nu_idx=None):
    """
    Build the standard 7-column true point array [x, y, z, cluster_id, q_true, energy, time]
    from charge-light sed-sce_drift_smear_readout fields.

    cluster_id: callers in the charge-light pipeline pass the file's REAL_CLUSTER_ID,
    not its cluster_id -- cluster_id is a coarser grouping that can merge physically
    distinct tracks, real_cluster_id is the per-track ID (same convention as the reco
    side). The two are identical in every sed-smear file in the current tree. Note the
    trackID-prefix fallback below assumes whichever ID is passed lives in the
    trackID namespace, which holds for both.
 energy is the per-point
    deposited energy in MeV ('e' field) when available -- same physical quantity/units
    as the old (non charge-light) pipeline's energy column. Falls back to the charge
    ('q') field when energy is None or empty (older-format files that lack 'e'). Time
    has no per-point source in this format and is filled with 0.0.

    q_true: when nu_idx is provided (non-empty, newer file format), q_true is taken
    DIRECTLY from it -- 0=cosmic, 1/2/...=which neutrino interaction, distinguishing
    MULTIPLE neutrino interactions in the same event. Falls back to the older binary
    cluster_id (trackID) namespace check (0=cosmic, 1=neutrino, no index) when nu_idx
    is None or empty. Note: reassign_cluster_ID_true still merges every point with
    q_true>0 into a single cluster_id=9999 regardless of its specific index -- q_true
    itself (column 4) is untouched by that merge, so per-neutrino-index breakdowns
    must read q_true directly from points rather than relying on post-reassignment
    cluster_id/count (see DrawLabelsByNeutrinoIndex in DrawRecoTrueClusters.py).
    """
    trackid_prefix = np.floor_divide(cluster_id, 10_000_000).astype(int)
    if nu_idx is not None and len(nu_idx) == len(x):
        q_true = nu_idx.astype(float)
    else:
        q_true = np.where(trackid_prefix == NEUTRINO_TRACKID_PREFIX, 1.0, 0.0)
    time_placeholder = np.zeros_like(x)
    energy_column = energy if energy is not None and len(energy) == len(x) else charge
    return np.column_stack((x, y, z, cluster_id, q_true, energy_column, time_placeholder))


def apply_deadarea_cut_true_vectorized(true_points, apa, view_type="2view", output_dir=None, event=None, file_name=None,
                                       verbose=True):
    """
    Vectorized reimplementation of apply_deadarea_cut_true() for charge-light
    matching's larger per-event point counts. The legacy function checks each
    point against each dead-area polygon one point at a time
    (`path.contains_points([[y, z]])` inside a `for point: for polygon:`
    double loop) -- profiling this branch's pipeline showed ~2.1M such calls
    for a single event, ~48% of total per-event runtime. This calls each
    polygon's contains_points() once over ALL points at once instead.
    Produces identical filtering/print output to apply_deadarea_cut_true()
    (diffed against it on real event data before switching this branch over);
    kept as a separate function rather than editing the legacy one, which
    other notebooks/pipelines still depend on.

    verbose=False suppresses the reporting only -- the FILTERING is identical
    either way, so the returned points do not depend on it. What it skips is
    the per-cluster before/after tally, which is O(n_clusters x n_points)
    (~227 clusters x ~92k points per event in this format, computed twice and
    once per APA) and exists purely to feed the per-cluster print lines. Once
    the prints are unwanted that loop is the dominant cost of this function --
    the polygon test above it is vectorized and cheap. The tally IS still
    computed when output_dir is given, since DrawPointsBeforeAfterDeadArea
    needs it; verbose=False then suppresses just the printing. Callers that
    want neither should pass output_dir=None as well.
    """
    if verbose:
        print("Applying Dead Area Cut")
        print(f"APA: {apa}, View: {view_type}")

    deadarea_base = Path(__file__).parent / "Deadareas"

    if view_type == "2view":
        deadarea_path = deadarea_base / "2viewactive_2viewdead"
    else:
        deadarea_path = deadarea_base / "3viewactive_1viewdead"

    if apa == "APA0":
        deadarea_file = deadarea_path / "0-channel-deadarea-apa0-face0.json"
    else:
        deadarea_file = deadarea_path / "0-channel-deadarea-apa1-face0.json"

    if not deadarea_file.exists():
        # Printed regardless of verbose: this is not reporting, it means the cut
        # silently did not happen.
        print(f"Warning: Dead area file not found at {deadarea_file}")
        print("Returning points unmodified")
        return true_points

    with open(deadarea_file, 'r') as f:
        deadarea_data = json.load(f)

    polygon_paths = []
    for shape in deadarea_data:
        vertices = np.array([[p[0], p[1]] for p in shape])
        polygon_paths.append(MplPath(vertices))

    points_before = len(true_points)
    yz_points = true_points[:, 1:3]

    in_deadarea = np.zeros(points_before, dtype=bool)
    for path in polygon_paths:
        in_deadarea |= path.contains_points(yz_points)

    filtered_points = true_points[~in_deadarea]
    points_after = len(filtered_points)
    points_removed = points_before - points_after

    if verbose:
        print(f"Number of points before dead area cut: {points_before}")
        print(f"Number of points after dead area cut: {points_after}")
        print(f"Points removed: {points_removed} ({100*points_removed/points_before:.1f}%)" if points_before > 0 else "")

    # Per-cluster before/after tally: only needed to print, or to draw. Skipping
    # it when neither is wanted is the whole point of verbose=False -- see the
    # docstring.
    cluster_before = {}
    cluster_after = {}
    if verbose or output_dir is not None:
        cluster_ids = true_points[:, 3].astype(int)
        for cid in np.unique(cluster_ids):
            mask = cluster_ids == cid
            cluster_before[int(cid)] = int(mask.sum())
            cluster_after[int(cid)] = int((mask & ~in_deadarea).sum())

    if verbose:
        for cid in sorted(cluster_before.keys()):
            before = cluster_before[cid]
            after = cluster_after.get(cid, 0)
            if after == 0:
                print(f"  Cluster {cid}: {before} -> {after} points (REMOVED)")
            elif after < before:
                removed = before - after
                pct = (removed / before) * 100
                print(f"  Cluster {cid}: {before} -> {after} points ({removed} removed, {pct:.1f}%)")

    if output_dir is not None:
        try:
            from DrawRecoTrueClusters import DrawPointsBeforeAfterDeadArea
            DrawPointsBeforeAfterDeadArea(cluster_before, cluster_after, event, apa, output_dir, file_name)
            if verbose:
                print(f"\nDrew before/after dead area visualizations")
        except Exception as e:
            print(f"Warning: Could not draw before/after visualizations: {e}")

    return filtered_points


def apply_deadarea_cut_true_charge_light(true_points, view_type="2view", output_dir=None, event=None, file_name=None,
                                         verbose=True):
    """
    Applies apply_deadarea_cut_true_vectorized() to combined-APA charge-light
    true points (see that function's docstring for why this doesn't use the
    legacy per-point apply_deadarea_cut_true() anymore). The dead-area maps
    are still per-APA, so this splits points by X sign (X<0 -> APA0, X>=0 ->
    APA1 -- charge drifts to its nearest anode, not across the cathode at
    x=0; verified against this format's continuous, non-gapped X
    distribution) and recombines the two filtered halves. Charge-light
    matching is not per-APA (unlike the older pipeline), so both halves share
    the same output_dir -- no APA0/APA1 subdirectories -- and rely on the apa
    label already embedded in each plot's filename to stay distinguishable.

    verbose is passed straight through; see apply_deadarea_cut_true_vectorized
    for what it does and does not affect (reporting only -- never the filtering).
    """
    if len(true_points) == 0:
        return true_points

    apa0_mask = true_points[:, 0] < 0
    apa1_mask = ~apa0_mask

    filtered_parts = []
    for mask, apa in ((apa0_mask, "APA0"), (apa1_mask, "APA1")):
        if not mask.any():
            continue
        filtered_parts.append(apply_deadarea_cut_true_vectorized(true_points[mask], apa, view_type, output_dir, event, file_name,
                                                                 verbose=verbose))

    filtered_parts = [p for p in filtered_parts if len(p) > 0]
    if not filtered_parts:
        return np.array([]).reshape(0, true_points.shape[1])
    return np.vstack(filtered_parts)
