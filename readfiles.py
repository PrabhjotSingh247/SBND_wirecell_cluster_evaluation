# Import required libraries
import numpy as np
from pathlib import Path
import os
import json

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
