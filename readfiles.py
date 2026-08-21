# Import required libraries
import numpy as np
from pathlib import Path
import os
import json
import zipfile
import re

def read_true_coordinates_from_json(json_file):
    """Reads true coordinates from JSON file and returns numpy arrays."""
    with open(json_file, 'r') as f:
        data = json.load(f)

    _x = np.array(data.get('x', []))
    _y = np.array(data.get('y', []))
    _z = np.array(data.get('z', []))
    _id = np.array(data.get('cluster_id', []))
    _q = np.array(data.get('q', []))
    _e = np.array(data.get('e', []))
    _t = np.array(data.get('t', []))
    return _x, _y, _z, _id, _q, _e, _t

def read_pred_coordinates_from_json(json_file):
    """Reads reconstructed coordinates from JSON file and returns numpy arrays."""
    with open(json_file, 'r') as f:
        data = json.load(f)

    _x = np.array(data.get('x', []))
    _y = np.array(data.get('y', []))
    _z = np.array(data.get('z', []))
    _id = np.array(data.get('cluster_id', []))
    _q = np.array(data.get('q', []))
    return _x, _y, _z, _id, _q

def read_files_for_event(input_dir, evt, apa):
    """
    Read true and reco data directly from JSON files in the data directory.

    Expected structure:
      data/evt/evt-tru-apa0.json (or apa1)
      data/evt/evt-clustering-apa0-face*.json (or apa1)

    Supports both old (xyz-coordinates) and new (data/) directory structures.
    """
    input_dir = Path(input_dir)

    # Check if input_dir already has data/ subdirectory (new structure)
    if (input_dir / "data").exists():
        data_dir = input_dir / "data" / str(evt)
    else:
        # Fall back to old structure: go up from xyz-coordinates
        parent_dir = input_dir.parent
        data_dir = parent_dir / "data" / str(evt)

    if not data_dir.exists():
        print(f"Warning: Data directory {data_dir} not found. Skipping event {evt}.")
        return None

    # Find true JSON file for the given APA
    # true jsons are named as tru-apa0-0.json
    true_json = input_dir / f"tru-{apa.lower()}-{evt}.json"

    if not true_json.exists():
        print(f"Warning: {true_json} not found. Skipping event {evt}.")
        return None

    # Find clustering JSON files for the given APA (may have multiple faces)
    clustering_files = sorted(data_dir.glob(f"{evt}-clustering-{apa.lower()}-*.json"))

    if not clustering_files:
        print(f"Warning: No clustering files found for {apa.lower()} in {data_dir}. Skipping event {evt}.")
        return None

    try:
        # Load true coordinates
        x_true, y_true, z_true, id_true, q_true, e_true, t_true = read_true_coordinates_from_json(true_json)

        # Load and merge clustering data from all faces
        x_pred_list, y_pred_list, z_pred_list, id_pred_list, q_pred_list = [], [], [], [], []

        for clust_file in clustering_files:
            x, y, z, id_, q = read_pred_coordinates_from_json(clust_file)
            if len(x) > 0:  # Only add if file has data
                x_pred_list.append(x)
                y_pred_list.append(y)
                z_pred_list.append(z)
                id_pred_list.append(id_)
                q_pred_list.append(q)

        if not x_pred_list:
            print(f"Warning: No clustering data found for event {evt}. Skipping.")
            return None

        # Concatenate data from all faces, adjusting cluster IDs to avoid conflicts
        x_pred = np.concatenate(x_pred_list)
        y_pred = np.concatenate(y_pred_list)
        z_pred = np.concatenate(z_pred_list)
        q_pred = np.concatenate(q_pred_list)

        # Merge cluster IDs: renumber to avoid conflicts between faces
        id_pred = np.array([], dtype=int)
        max_id = 0
        for id_arr in id_pred_list:
            id_arr = np.array(id_arr, dtype=int)
            id_arr = id_arr + max_id
            id_pred = np.concatenate([id_pred, id_arr])
            max_id = id_pred.max() + 1

        # Ensure all arrays are float64
        x_true = x_true.astype(np.float64)
        y_true = y_true.astype(np.float64)
        z_true = z_true.astype(np.float64)
        id_true = id_true.astype(np.float64)
        q_true = q_true.astype(np.float64)
        e_true = e_true.astype(np.float64)
        t_true = t_true.astype(np.float64)

        x_pred = x_pred.astype(np.float64)
        y_pred = y_pred.astype(np.float64)
        z_pred = z_pred.astype(np.float64)
        id_pred = id_pred.astype(np.float64)
        q_pred = q_pred.astype(np.float64)

        return x_true, y_true, z_true, id_true, q_true, e_true, t_true, x_pred, y_pred, z_pred, id_pred, q_pred

    except Exception as e:
        print(f"Error reading JSON files for event {evt}: {e}")
        return None


# ============================================================================
# CHARGE-LIGHT MATCHING FORMAT (additive; existing readers above are untouched)
# ============================================================================
# The charge-light-matching JSON files ship one event per subdirectory as
# input_dir/data/{evt}/{evt}-<type>.json, combined across APAs (no per-APA/face
# split like the older tru-apa*/clustering-apa* files). This section adds
# readers for that format alongside the originals so both can be used side by
# side without changing existing behavior.

def ensure_data_extracted(input_dir):
    """
    Idempotently extract the single zip file inside input_dir into input_dir/data.
    If input_dir/data already exists, this is a no-op (safe to call every run).
    """
    input_dir = Path(input_dir)
    data_dir = input_dir / "data"
    if data_dir.exists():
        return data_dir

    zip_files = list(input_dir.glob("mabc*.zip"))
    if len(zip_files) != 1:
        print(f"Warning: expected exactly one mabc*.zip file in {input_dir}, found {len(zip_files)}. Skipping extraction.")
        return None

    with zipfile.ZipFile(zip_files[0], 'r') as zf:
        zf.extractall(input_dir)
    print(f"Extracted {zip_files[0].name} -> {data_dir}")
    return data_dir


def read_img_global_from_json(json_file):
    """Reads combined-APA reco cluster points (img-global) from JSON file."""
    with open(json_file, 'r') as f:
        data = json.load(f)

    _x = np.array(data.get('x', []))
    _y = np.array(data.get('y', []))
    _z = np.array(data.get('z', []))
    _id = np.array(data.get('cluster_id', []))
    _q = np.array(data.get('q', []))
    _real_id = np.array(data.get('real_cluster_id', []))
    return _x, _y, _z, _id, _q, _real_id


def read_cluster_global_from_json(json_file):
    """Reads combined-APA clustering points (clustering-global) from JSON file."""
    with open(json_file, 'r') as f:
        data = json.load(f)

    _x = np.array(data.get('x', []))
    _y = np.array(data.get('y', []))
    _z = np.array(data.get('z', []))
    _id = np.array(data.get('cluster_id', []))
    _q = np.array(data.get('q', []))
    _real_id = np.array(data.get('real_cluster_id', []))
    return _x, _y, _z, _id, _q, _real_id


def read_sed_sce_from_json(json_file):
    """
    Reads combined-APA true cluster points (sed-sce_drift_smear_readout) from JSON file.

    Newer files additionally carry 'e' (genuine per-point deposited energy, in
    MeV -- unlike 'q', which is a charge/ADC-like value on a very different
    scale) and 'nu_idx' (0 = cosmic; 1, 2, ... = which neutrino interaction the
    point belongs to, matching mc.json root nodes' nu_idx from flatten_mc_tree()).
    Older files lack both keys -- in that case _e/_nu_idx come back as empty
    arrays (NOT filled with a placeholder value), so length-mismatches against
    x/y/z/... are obvious immediately rather than silently papered over.
    """
    with open(json_file, 'r') as f:
        data = json.load(f)

    _x = np.array(data.get('x', []))
    _y = np.array(data.get('y', []))
    _z = np.array(data.get('z', []))
    _id = np.array(data.get('cluster_id', []))
    _q = np.array(data.get('q', []))
    _real_id = np.array(data.get('real_cluster_id', []))
    _e = np.array(data.get('e', []))
    _nu_idx = np.array(data.get('nu_idx', []))
    return _x, _y, _z, _id, _q, _real_id, _e, _nu_idx


def read_sed_smear_from_json(json_file):
    """
    Reads combined-APA true cluster points (sed-smear_readout) from JSON file --
    TRUE positions, with neither the space-charge displacement nor the drift
    transform applied. Same schema/fields as read_sed_sce_from_json() (x, y, z,
    cluster_id, q, real_cluster_id, e, nu_idx) and identical cluster_id/q/e values
    point-for-point; only x/y/z differ.

    The ~80 cm mean |dx| against sed-sce_drift_smear_readout is NOT space charge,
    which this docstring used to claim. Space charge is the sub-cm part (0.6 cm in
    x, 0.3 cm in y/z -- see read_sed_sce_smear_from_json); the 80 cm is the DRIFT
    transform, and it is a per-cluster constant set by the cluster's t0. Measured
    over 10 events: neutrino clusters, which sit at the beam t0, move 7.6 cm on
    average, while cosmics move 76.9 cm and up to 225.5 cm, implying |t0| up to
    ~1410 us -- the cosmic readout window.

    Used for CLUSTERING-LEVEL (post charge-light-matching) evaluation, paired
    with clustering-global's reco points -- as opposed to sed-sce, which is
    the IMAGING-LEVEL (pre charge-light-matching) truth paired with
    img-global. Older files lack 'e'/'nu_idx' -- see read_sed_sce_from_json's
    docstring for the same empty-array-on-missing-field behavior here.
    """
    with open(json_file, 'r') as f:
        data = json.load(f)

    _x = np.array(data.get('x', []))
    _y = np.array(data.get('y', []))
    _z = np.array(data.get('z', []))
    _id = np.array(data.get('cluster_id', []))
    _q = np.array(data.get('q', []))
    _real_id = np.array(data.get('real_cluster_id', []))
    _e = np.array(data.get('e', []))
    _nu_idx = np.array(data.get('nu_idx', []))
    return _x, _y, _z, _id, _q, _real_id, _e, _nu_idx


def read_mc_json(json_file):
    """Reads the MC truth particle ancestry tree. Returned as-is (list of nested dicts); use flatten_mc_tree() to parse it into per-particle records."""
    with open(json_file, 'r') as f:
        return json.load(f)


# "<particle> <energy> MeV" (e.g. "mu-  1242.5 MeV") or, at an interaction-vertex
# root in the older file format, "<flavor> Edep <energy> MeV" (e.g. "numu  Edep 19.8 MeV")
_MC_TEXT_RE = re.compile(r'^(.*?)\s+(?:Edep\s+)?([\d.]+)\s*MeV$')

# Newer file format's interaction-vertex root text, which adds a neutrino index
# (to tell multiple neutrino interactions in the same event apart) and the
# neutrino's total energy ahead of Edep. TWO producer versions are read by this
# one pattern:
#
#   "1 numu Etot 1821.6 MeV Edep 19.8 MeV"                  (MCP2025C Fall production)
#   "1 numu MEC Etot 953.2 MeV Edep 803.1 MeV T 1.335 us"   (Tagger-included production)
#
# The newer one inserts the interaction MODE (QE / RES / DIS / MEC / COH ...)
# after the flavour and appends the true interaction TIME. Both are optional here
# so the same pattern reads either file, and a producer that adds one of them
# again does not silently break the parse -- which is exactly what happened
# before this was relaxed: the anchored pattern simply failed to match, nu_idx
# came out None, and every neutrino true cluster then failed to join to its
def read_sed_sce_smear_from_json(json_file):
    """
    Reads combined-APA true cluster points (sed-sce_smear_readout) from JSON file.

    The THIRD truth variant. The three form a chain, each stage adding one effect
    on the way to the readout, and they differ ONLY in x/y/z -- cluster_id, q, e
    and nu_idx are identical point-for-point across all three:

      sed-smear_readout            true positions, nothing applied
      sed-sce_smear_readout        + space charge   (this one)
      sed-sce_drift_smear_readout  + space charge + drift

    Measured on chunk0 event 1: the SCE step moves points by 0.6 cm in x and
    ~0.3 cm in y/z, staying inside the physical volume; the drift step then moves
    x by ~78 cm on average and pushes the range out to +-234 cm, outside the
    detector, because it converts to an apparent position from drift time.

    WHICH TO PAIR WITH clustering-global: measured, not assumed. Matching every
    clustering-global point to its nearest true point under both non-drift
    variants over 8 events (225,633 points) gives a median residual of 0.394 cm
    against sed-sce_smear and 0.555 cm against sed-smear, with 81.2% vs 70.3%
    inside 1 cm. Reco carries the space-charge displacement -- nothing in the
    clustering stage undoes it -- so sed-sce_smear is the matching truth. Same
    schema and same missing-field behaviour as read_sed_sce_from_json.
    """
    with open(json_file, 'r') as f:
        data = json.load(f)

    _x = np.array(data.get('x', []))
    _y = np.array(data.get('y', []))
    _z = np.array(data.get('z', []))
    _id = np.array(data.get('cluster_id', []))
    _q = np.array(data.get('q', []))
    _real_id = np.array(data.get('real_cluster_id', []))
    _e = np.array(data.get('e', []))
    _nu_idx = np.array(data.get('nu_idx', []))
    return _x, _y, _z, _id, _q, _real_id, _e, _nu_idx


# mc.json interaction. Nothing raised; the neutrino categories just came out
# empty. Named groups, so adding another optional field cannot renumber the rest.
#
# The (?!Etot) stops the optional mode from swallowing the "Etot" keyword when
# the mode is absent.
_MC_ROOT_TEXT_RE = re.compile(
    r'^(?P<nu_idx>\d+)\s+(?P<flavor>\S+)'
    r'(?:\s+(?P<mode>(?!Etot)\S+))?'
    r'\s+Etot\s+(?P<etot>[\d.]+)\s*MeV'
    r'\s+Edep\s+(?P<edep>[\d.]+)\s*MeV'
    r'(?:\s+T\s+(?P<time_us>[-+\d.eE]+)\s*us)?$')


def flatten_mc_tree(mc_tree):
    """
    Flattens the nested mc.json particle ancestry tree (as returned by read_mc_json)
    into a flat list of per-particle records: {trackid, particle, energy_MeV,
    total_energy_MeV, nu_idx, is_interaction_vertex, parent_trackid,
    root_trackid, start_xyz, end_xyz}.

    Interaction-vertex root nodes (is_interaction_vertex=True) are parsed with
    _MC_ROOT_TEXT_RE first (newer file format: adds nu_idx -- 1, 2, ... to tell
    multiple neutrino interactions in the same event apart -- and total_energy_MeV,
    the neutrino's total energy, ahead of Edep). Falls back to the older format
    (_MC_TEXT_RE, "<flavor> Edep <energy> MeV") if that doesn't match, in which
    case nu_idx/total_energy_MeV stay None -- only energy_MeV (Edep) is available.
    Non-root nodes always use _MC_TEXT_RE ("<particle> <energy> MeV"); that format
    hasn't changed between file versions.

    Note: mc.json only lists a curated subset of trackIDs (primaries and notable
    daughters) -- most low-energy secondaries present in sed-sce_drift_smear_readout
    have no corresponding record here. All trackIDs in this tree fall in the
    neutrino-interaction namespace (cluster_id // 10_000_000 == 1); this is
    per-particle metadata, not a per-point classifier -- see build_true_points_charge_light
    in selections.py for the per-point neutrino/cosmic split (and, in the newer
    file format, sed-sce_drift_smear_readout's own 'nu_idx' field per point).
    """
    records = []

    def _walk(node, root_trackid, parent_trackid):
        text = node.get('text', '').strip()
        is_root = parent_trackid is None
        nu_idx = None
        total_energy_MeV = None
        interaction_mode = None
        interaction_time_us = None

        root_match = _MC_ROOT_TEXT_RE.match(text) if is_root else None
        if root_match:
            nu_idx = int(root_match.group('nu_idx'))
            particle = root_match.group('flavor')
            total_energy_MeV = float(root_match.group('etot'))
            energy_MeV = float(root_match.group('edep'))
            # Only the Tagger-included format carries these; None otherwise.
            interaction_mode = root_match.group('mode')
            time_text = root_match.group('time_us')
            interaction_time_us = float(time_text) if time_text is not None else None
        else:
            match = _MC_TEXT_RE.match(text)
            if match:
                particle, energy_MeV = match.group(1).strip(), float(match.group(2))
            else:
                particle, energy_MeV = text, None

        # start_xyz/end_xyz come from the node's 'data' block (cm, SAME coordinate
        # frame as sed-sce_drift_smear_readout's points -- verified by measuring
        # in-volume interaction vertices against their own cluster's deposits:
        # agreement to ~0.03-0.13 cm). For an interaction-vertex root node,
        # start == end == the neutrino interaction vertex (checked: true for all
        # 223 roots across this dataset, and 221/223 have every child particle
        # starting at that same point). Either can be None for nodes that carry
        # no 'data' block.
        node_data = node.get('data') or {}
        start_xyz = node_data.get('start')
        end_xyz   = node_data.get('end')

        records.append({
            'trackid': node['id'],
            'particle': particle,
            'energy_MeV': energy_MeV,
            'total_energy_MeV': total_energy_MeV,
            'nu_idx': nu_idx,
            # Interaction mode ('QE', 'RES', 'MEC', ...) and the true interaction
            # time in us. Present only in the Tagger-included production's root
            # text; None everywhere else, including on every non-root node.
            'interaction_mode': interaction_mode,
            'interaction_time_us': interaction_time_us,
            'is_interaction_vertex': is_root,
            'parent_trackid': parent_trackid,
            'root_trackid': root_trackid,
            'start_xyz': tuple(start_xyz) if start_xyz else None,
            'end_xyz': tuple(end_xyz) if end_xyz else None,
        })
        for child in node.get('children', []):
            _walk(child, root_trackid, node['id'])

    for root in mc_tree:
        _walk(root, root['id'], None)

    return records


def read_op_json(json_file):
    """Reads per-flash optical (light) info from JSON file, returned as a dict of arrays keyed by field name."""
    with open(json_file, 'r') as f:
        data = json.load(f)

    return {
        'apa': np.array(data.get('apa', [])),
        'op_flash_group': np.array(data.get('op_flash_group', [])),
        'op_peTotal': np.array(data.get('op_peTotal', [])),
        'op_pes': data.get('op_pes', []),            # per-flash, per-channel PE waveform (ragged)
        'op_pes_pred': data.get('op_pes_pred', []),  # per-flash, per-channel predicted PE waveform (ragged)
        'op_t': np.array(data.get('op_t', [])),
        'op_cluster_ids': data.get('op_cluster_ids', []),  # per-flash list of matched cluster IDs (ragged)
    }


def read_charge_light_files_for_event(input_dir, evt):
    """
    Read combined-APA charge-light-matching event data directly from JSON files.

    Expected structure:
      input_dir/data/{evt}/{evt}-img-global.json
      input_dir/data/{evt}/{evt}-sed-sce_drift_smear_readout.json
      input_dir/data/{evt}/{evt}-sed-smear_readout.json
      input_dir/data/{evt}/{evt}-sed-sce_smear_readout.json   (optional)
      input_dir/data/{evt}/{evt}-mc.json
      input_dir/data/{evt}/{evt}-op.json
      input_dir/data/{evt}/{evt}-clustering-global.json

    Returns a dict with keys 'reco', 'true', 'true_clustering',
    'true_clustering_sce', 'mc', 'op', 'clustering', or None if the event
    directory or any of the six REQUIRED files is missing. 'true'/'reco'
    (sed-sce/img-global) are the IMAGING-LEVEL (pre charge-light-matching)
    true/reco pair; 'true_clustering'/'clustering' (sed-smear/clustering-global)
    are the CLUSTERING-LEVEL (post charge-light-matching) true/reco pair.

    'true_clustering_sce' (sed-sce_smear_readout) is the clustering-level truth
    WITH the space-charge displacement -- the variant that actually matches
    clustering-global's positions, see read_sed_sce_smear_from_json. It is
    OPTIONAL: it comes back None when the file is absent rather than skipping the
    event, so callers that do not ask for it keep working on productions that
    predate the file.
    """
    input_dir = Path(input_dir)
    event_dir = input_dir / "data" / str(evt)

    if not event_dir.exists():
        print(f"Warning: Event directory {event_dir} not found. Skipping event {evt}.")
        return None

    img_json = event_dir / f"{evt}-img-global.json"
    sed_json = event_dir / f"{evt}-sed-sce_drift_smear_readout.json"
    sed_smear_json = event_dir / f"{evt}-sed-smear_readout.json"
    sed_sce_smear_json = event_dir / f"{evt}-sed-sce_smear_readout.json"
    mc_json  = event_dir / f"{evt}-mc.json"
    op_json  = event_dir / f"{evt}-op.json"
    clustering_json = event_dir / f"{evt}-clustering-global.json"

    for required_file in (img_json, sed_json, sed_smear_json, mc_json, op_json, clustering_json):
        if not required_file.exists():
            print(f"Warning: {required_file} not found. Skipping event {evt}.")
            return None

    try:
        x_reco, y_reco, z_reco, id_reco, q_reco, real_id_reco = read_img_global_from_json(img_json)
        x_true, y_true, z_true, id_true, q_true, real_id_true, e_true, nu_idx_true = read_sed_sce_from_json(sed_json)
        x_true_clu, y_true_clu, z_true_clu, id_true_clu, q_true_clu, real_id_true_clu, e_true_clu, nu_idx_true_clu = read_sed_smear_from_json(sed_smear_json)
        # Optional -- absent in older productions, so its loss must not cost the event.
        true_clustering_sce = (read_sed_sce_smear_from_json(sed_sce_smear_json)
                               if sed_sce_smear_json.exists() else None)
        mc_tree = read_mc_json(mc_json)
        op_data = read_op_json(op_json)
        x_clu, y_clu, z_clu, id_clu, q_clu, real_id_clu = read_cluster_global_from_json(clustering_json)

        x_reco, y_reco, z_reco = x_reco.astype(np.float64), y_reco.astype(np.float64), z_reco.astype(np.float64)
        id_reco, q_reco, real_id_reco = id_reco.astype(np.float64), q_reco.astype(np.float64), real_id_reco.astype(np.float64)

        x_true, y_true, z_true = x_true.astype(np.float64), y_true.astype(np.float64), z_true.astype(np.float64)
        id_true, q_true, real_id_true = id_true.astype(np.float64), q_true.astype(np.float64), real_id_true.astype(np.float64)
        # e/nu_idx may be empty arrays (older file format lacks these fields) -- still safe to cast.
        e_true, nu_idx_true = e_true.astype(np.float64), nu_idx_true.astype(np.float64)

        x_true_clu, y_true_clu, z_true_clu = x_true_clu.astype(np.float64), y_true_clu.astype(np.float64), z_true_clu.astype(np.float64)
        id_true_clu, q_true_clu, real_id_true_clu = id_true_clu.astype(np.float64), q_true_clu.astype(np.float64), real_id_true_clu.astype(np.float64)
        e_true_clu, nu_idx_true_clu = e_true_clu.astype(np.float64), nu_idx_true_clu.astype(np.float64)

        x_clu, y_clu, z_clu = x_clu.astype(np.float64), y_clu.astype(np.float64), z_clu.astype(np.float64)
        id_clu, q_clu, real_id_clu = id_clu.astype(np.float64), q_clu.astype(np.float64), real_id_clu.astype(np.float64)

        return {
            'reco': (x_reco, y_reco, z_reco, id_reco, q_reco, real_id_reco),
            'true': (x_true, y_true, z_true, id_true, q_true, real_id_true, e_true, nu_idx_true),
            'true_clustering': (x_true_clu, y_true_clu, z_true_clu, id_true_clu, q_true_clu, real_id_true_clu, e_true_clu, nu_idx_true_clu),
            'true_clustering_sce': true_clustering_sce,
            'mc': mc_tree,
            'op': op_data,
            'clustering': (x_clu, y_clu, z_clu, id_clu, q_clu, real_id_clu),
        }

    except Exception as e:
        print(f"Error reading charge-light-matching JSON files for event {evt}: {e}")
        return None
