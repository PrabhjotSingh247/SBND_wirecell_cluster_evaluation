"""
SAVED CLUSTER VIEWS -- driven by
AnalysisDistributions/SignalBackground_Distributions.ipynb.

XZ, YZ and XY pictures of individual reco-true pairs, sampled across the
completeness-purity plane so that every corner of it has a concrete example
attached. The scatter says a pair sits at 30% completeness and 90% purity; these
say what that actually looks like.

HOW PAIRS ARE CHOSEN

The completeness-purity square is divided into a 10x10 grid of 10% cells. For
each interaction channel, ONE pair is saved per cell -- 100 cells x 3 channels at
most, in practice far fewer since most cells are empty. Plus a handful of cosmic
reco clusters, which have no pair and are drawn alone.

FIRST ENCOUNTERED, NOT UNIFORMLY RANDOM. The event loop sees each event once and
the point clouds are far too large to keep to the end of the job, so a cell is
filled by the first pair that lands in it and later candidates are skipped. Over
a job the events arrive in file order, which is not correlated with a pair's
completeness or purity, so the sample is arbitrary rather than biased -- but it
is not a uniform draw from the cell, and a cell holding 200 pairs shows the same
one every run. Drawing a genuinely random pair would need a second pass over the
selected events, which is a bigger change than the pictures are worth.

The cosmics ARE a uniform random draw -- see ClusterViewSampler.offer_cosmic.

DIRECTORY LAYOUT

    Saved_Clusters/
        completeness_100_90_purity_100_90_event_chunk0_37/
            pair_numu_CC_chunk0_37.png
        completeness_100_90_purity_90_80_event_chunk0_12/
            pair_NC_chunk0_12.png
        ...
        cosmics_true_energy_above_100MeV/
            cosmic_reco<id>_chunk0_5.png
        completeness_purity.txt

One directory per (cell, event), holding that event's pair view for every channel
that landed in the cell. In practice that is ONE file per directory: a cell is
filled once per channel, the three channels are filled by different events, and
only the event's FIRST neutrino is ever drawn (FIRST_NEUTRINO_CLUSTER_ID), so two
channels can only share a directory if one event's first neutrino somehow served
both -- which cannot happen. The per-channel filename is what makes the picture
identifiable; the directory name is what makes the cell browsable.

WHY A SEPARATE MODULE. draw_selection_performance.py counts clusters;
this draws them. They share no code and have opposite cost profiles -- one figure
here is three panels of a full point cloud -- so the switch that turns these off
(SAVE_CLUSTER_VIEWS in the notebook) can skip this import path entirely.
"""

from collections import Counter

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# The three projections, as (x index, y index, x label, y label). Columns of the
# standard point arrays: 0=x, 1=y, 2=z.
_VIEWS = [
    (2, 0, 'Z (cm)', 'X (cm)', 'XZ'),
    (2, 1, 'Z (cm)', 'Y (cm)', 'YZ'),
    (0, 1, 'X (cm)', 'Y (cm)', 'XY'),
]

_GRID_CELLS = 10          # 10 x 10 cells of 10% each

# Only pairs whose true cluster is the FIRST neutrino of its event (nu_idx 1, so
# cluster id 99991) are drawn. In a multi-neutrino event a picture of the second
# neutrino shows one interaction while another sits in the same readout, and
# nothing in the frame says which points belong to which -- the view stops being
# a clean illustration of its completeness and purity. Restricting to the first
# keeps every saved picture unambiguous, at the cost of never illustrating a
# second-neutrino pair.
FIRST_NEUTRINO_CLUSTER_ID = 99991.0

# A cosmic candidate is only worth a picture above this TRUE deposited energy, in
# MeV. The cosmic category is mostly small fragments -- the smallest in one chunk
# was 2 MeV -- and a three-panel view of a handful of points shows nothing. This
# keeps the saved cosmics to clusters with enough energy to have a visible shape.
#
# The energy tested is that of the true cluster the reco cluster overlaps MOST (by
# purity), summed over all its points -- not the reco cluster's own charge, and
# not just the overlapping part. A cosmic reco cluster is by construction a
# fragment, so its own energy says how much was reconstructed, while the true
# cluster's says how much was there to reconstruct, which is the thing worth
# looking at. A candidate overlapping no true cluster at all has no true energy
# and is never drawn.
MIN_COSMIC_VIEW_ENERGY_MEV = 100.0

# Where the random cosmic sample is written, under the Saved_Clusters root.
COSMIC_DIR_NAME = 'cosmics_true_energy_above_100MeV'

# How many pair views each completeness-purity cell keeps. The cell directory no
# longer carries an event, so several examples of the same region live together
# and can be compared without opening three directories.
PAIRS_PER_CELL = 3

# Events where two or more in-volume true neutrinos both have a selected reco
# cluster in the beam window. Their own directory and quota, drawn like the
# cosmics: these are the cases where one flash covers two interactions, and a
# coarse grouping cannot tell them apart.
TWO_NEUTRINO_DIR_NAME = 'two_neutrino_in_beam'
SAVED_TWO_NEUTRINO_VIEWS = 5

# Fixed so a re-run of the same input draws the same five cosmics. Change it to
# get a different draw from the same job.
COSMIC_SAMPLE_SEED = 12345

# EVERY in-volume pair below this completeness gets a view -- no sampling, no
# quota. These are the pairs the selection is losing, and the question they raise
# ("what does a badly reconstructed neutrino look like?") is not answered by one
# example per cell.
LOW_COMPLETENESS_MAX = 0.60
# ...and only above this RECO energy. Below it a poorly reconstructed cluster is
# a handful of points and the view shows nothing; the interesting failures are
# the ones that reconstructed a substantial cluster and still missed most of the
# true one. Cutting on the RECO side rather than the true side keeps the gate on
# what is actually drawn in the lower panel.
#
# 200 MeV, measured rather than guessed: over the full sample the 17 pairs below
# the completeness bar top out at 432 MeV of reco energy, so anything near 500
# empties the directory. Low completeness and a large reco cluster are close to
# mutually exclusive by construction -- one pair is 521 MeV true against 7 MeV
# reco -- so this gate has to sit low to select anything at all.
LOW_COMPLETENESS_MIN_RECO_ENERGY_MEV = 200.0
LOW_COMPLETENESS_DIR_NAME = 'pairs_below_60pc_completeness'

# Every in-volume nue CC interaction that produced NO selected reco cluster.
# There are only a handful of nue CC in the whole sample, so losing one matters
# and each deserves a picture and a line in the index.
UNSELECTED_NUE_DIR_NAME = 'unselected_nue_CC'
_ZOOM_MARGIN = 0.15       # padding around the drawn points, as a fraction of span

_TRUE_STYLE = dict(color='tab:red',  marker='.', s=8,  alpha=0.55, label='true cluster')
_RECO_STYLE = dict(color='tab:blue', marker='.', s=8,  alpha=0.55, label='reco cluster')

_TITLE_FONTSIZE = 15
_LABEL_FONTSIZE = 12
_LEGEND_FONTSIZE = 10


def grid_cell(completeness, purity, cells=_GRID_CELLS):
    """
    Which 10% x 10% cell a pair falls in, as (completeness index, purity index).

    A value of exactly 1.0 belongs to the top cell rather than to a cell of its
    own, so the grid is 10x10 and not 11x11.
    """
    def index(value):
        return min(int((value or 0.0) * cells), cells - 1)
    return index(completeness), index(purity)


def cell_directory_name(completeness, purity, cells=_GRID_CELLS):
    """
    The directory a pair view is written to, e.g.

        completeness_100_90_purity_80_70

    One directory per CELL, holding up to PAIRS_PER_CELL examples from different
    events -- the event is in the filename instead. Each bin is written HIGH
    first, so the directories sort in the order the completeness-purity plane is
    usually read, best at the top, rather than alphabetically from the worst.
    """
    completeness_index, purity_index = grid_cell(completeness, purity, cells)
    width = 100 // cells

    def span(index):
        return f"{(index + 1) * width}_{index * width}"

    return f"completeness_{span(completeness_index)}_purity_{span(purity_index)}"


class ClusterViewSampler:
    """
    Remembers which (channel, cell) slots have been filled and which have not, so
    the event loop can ask "should I draw this one?" and get a cheap answer.

    Kept as an object rather than a module-level dict because a notebook is
    re-run in place: a fresh sampler per job means a re-run fills the same slots
    again instead of silently drawing nothing the second time.
    """

    def __init__(self, cells=_GRID_CELLS, max_cosmics=5, seed=COSMIC_SAMPLE_SEED,
                 per_cell=PAIRS_PER_CELL, max_two_neutrino=SAVED_TWO_NEUTRINO_VIEWS):
        self.cells = cells
        self.max_cosmics = max_cosmics
        self.per_cell = per_cell
        self.filled = Counter()      # (completeness index, purity index) -> count
        self.n_pairs = 0
        # Two-neutrino events get their own reservoir, same scheme as the cosmics.
        self.max_two_neutrino = max_two_neutrino
        self.two_neutrino_slots = []
        self.n_two_neutrino_candidates = 0
        # No quota on these two: every case is drawn.
        self.n_low_completeness = 0
        # Pairs below the completeness bar BEFORE the reco-energy gate, so the
        # summary distinguishes "no badly reconstructed pairs" from "plenty, but
        # all of them too small to be worth a picture" -- which is the usual
        # case, since low completeness and a large reco cluster rarely coincide.
        self.n_low_completeness_candidates = 0
        self.n_unselected_nue = 0
        # Cosmic reservoir: max_cosmics slots, each holding the metadata of the
        # cosmic currently occupying it. n_cosmic_candidates counts every cosmic
        # OFFERED, which is what makes the draw uniform.
        self.cosmic_slots = []
        self.n_cosmic_candidates = 0
        self._rng = np.random.default_rng(seed)
        # What was actually saved, for the index file. Metadata only -- no point
        # clouds -- so this stays small however many views are drawn.
        self.saved = []

    @property
    def n_cosmics(self):
        return len(self.cosmic_slots)

    def wants_pair(self, channel, completeness, purity):
        """
        Room left in this cell? Counted per CELL, not per (channel, cell): the
        directory holds PAIRS_PER_CELL examples of a region of the plane, and
        which channels they happen to be is recorded in the filenames.
        """
        if channel is None:
            return False
        return self.filled[grid_cell(completeness, purity, self.cells)] < self.per_cell

    def take_pair(self, channel, completeness, purity, record=None, path=None,
                  event_label=None, true_energy=None):
        cell = grid_cell(completeness, purity, self.cells)
        self.filled[cell] += 1
        self.n_pairs += 1
        if record is not None:
            self.saved.append({
                'kind':             'pair',
                'true_energy_mev':  true_energy,
                'channel':          channel,
                'completeness_bin': cell[0] * 10,
                'purity_bin':       cell[1] * 10,
                'event':            event_label,
                'completeness':     record.get('pair_completeness'),
                'purity':           record.get('pair_purity'),
                'true_cluster_id':  record.get('pair_true_cluster_id'),
                'reco_cluster_id':  record.get('reco_cluster_id'),
                'reco_energy_mev':  record.get('reco_energy_mev'),
                'category':         record.get('category'),
                'path':             str(path) if path else None,
            })

    def offer_cosmic(self):
        """
        Offer a cosmic candidate. Returns the reservoir slot it should be drawn
        into, or None if it is not in the sample.

        RESERVOIR SAMPLING (Algorithm R), so the max_cosmics kept at the end are a
        uniform random draw from every candidate the job saw -- unlike the pairs,
        which are first-encountered. The first max_cosmics candidates fill the
        reservoir; candidate k > max_cosmics replaces a random existing one with
        probability max_cosmics / k.

        The cost of uniformity is redrawing: a replaced figure is deleted and the
        new one drawn in its place, so a job pays for roughly
        max_cosmics * (1 + ln(N / max_cosmics)) figures rather than max_cosmics.
        For five cosmics out of a few thousand candidates that is ~35 figures --
        cheap enough to be worth an unbiased sample.
        """
        self.n_cosmic_candidates += 1
        if len(self.cosmic_slots) < self.max_cosmics:
            return len(self.cosmic_slots)
        slot = int(self._rng.integers(0, self.n_cosmic_candidates))
        return slot if slot < self.max_cosmics else None

    def take_cosmic(self, slot, record=None, path=None, event_label=None,
                    true_energy=None):
        """Fill a reservoir slot, deleting the figure the evicted cosmic left behind."""
        entry = {
            'kind':             'cosmic',
            'channel':          None,
            'completeness_bin': None,
            'purity_bin':       None,
            'event':            event_label,
            'completeness':     None,
            'purity':           None,
            'true_cluster_id':  None,
            'true_energy_mev':  true_energy,
            'reco_cluster_id':  record.get('reco_cluster_id') if record else None,
            'reco_energy_mev':  record.get('reco_energy_mev') if record else None,
            'category':         'cosmic',
            'path':             str(path) if path else None,
        }
        if slot < len(self.cosmic_slots):
            evicted = self.cosmic_slots[slot]
            if evicted.get('path'):
                Path(evicted['path']).unlink(missing_ok=True)
            self.saved.remove(evicted)
            self.cosmic_slots[slot] = entry
        else:
            self.cosmic_slots.append(entry)
        self.saved.append(entry)

    @property
    def n_two_neutrino(self):
        return len(self.two_neutrino_slots)

    def offer_two_neutrino(self):
        """Reservoir slot for a two-neutrino event, or None. See offer_cosmic."""
        self.n_two_neutrino_candidates += 1
        if len(self.two_neutrino_slots) < self.max_two_neutrino:
            return len(self.two_neutrino_slots)
        slot = int(self._rng.integers(0, self.n_two_neutrino_candidates))
        return slot if slot < self.max_two_neutrino else None

    def take_two_neutrino(self, slot, path=None, event_label=None, detail=None):
        entry = {
            'kind':             'two_neutrino',
            'channel':          None,
            'completeness_bin': None,
            'purity_bin':       None,
            'event':            event_label,
            'completeness':     None,
            'purity':           None,
            'true_cluster_id':  None,
            'reco_cluster_id':  None,
            'reco_energy_mev':  None,
            'category':         'two_neutrino',
            'detail':           detail or {},
            'path':             str(path) if path else None,
        }
        if slot < len(self.two_neutrino_slots):
            evicted = self.two_neutrino_slots[slot]
            if evicted.get('path'):
                Path(evicted['path']).unlink(missing_ok=True)
            self.saved.remove(evicted)
            self.two_neutrino_slots[slot] = entry
        else:
            self.two_neutrino_slots.append(entry)
        self.saved.append(entry)

    def take_low_completeness(self, record, path, event_label, true_energy):
        self.n_low_completeness += 1
        self.saved.append({
            'kind': 'low_completeness', 'channel': record.get('channel'),
            'completeness_bin': None, 'purity_bin': None, 'event': event_label,
            'completeness': record.get('pair_completeness'),
            'purity': record.get('pair_purity'),
            'true_cluster_id': record.get('pair_true_cluster_id'),
            'true_energy_mev': true_energy,
            'reco_cluster_id': record.get('reco_cluster_id'),
            'reco_energy_mev': record.get('reco_energy_mev'),
            'category': record.get('category'), 'path': str(path) if path else None})

    def take_unselected_nue(self, vertex, path, event_label, true_energy, detail):
        self.n_unselected_nue += 1
        self.saved.append({
            'kind': 'unselected_nue', 'channel': 'nue_CC',
            'completeness_bin': None, 'purity_bin': None, 'event': event_label,
            'completeness': None, 'purity': None,
            'true_cluster_id': vertex.get('cluster_id'),
            'true_energy_mev': true_energy,
            'reco_cluster_id': None, 'reco_energy_mev': None,
            'category': 'unselected_nue', 'detail': detail,
            'path': str(path) if path else None})

    def summary(self):
        return (f"{self.n_pairs} pair view(s), {self.n_cosmics} cosmic view(s) "
                f"from {self.n_cosmic_candidates} candidate(s), "
                f"{self.n_two_neutrino} two-neutrino view(s) "
                f"from {self.n_two_neutrino_candidates} candidate(s), "
                f"{self.n_low_completeness} below-{LOW_COMPLETENESS_MAX:.0%}-completeness view(s) "
                f"from {self.n_low_completeness_candidates} such pair(s), "
                f"{self.n_unselected_nue} unselected nue CC view(s)")


def _draw_panels(fig_title, point_sets, output_path, legend_lines):
    """One figure, three panels (XZ / YZ / XY), each with the same point sets."""
    fig, axes = plt.subplots(1, 3, figsize=(19, 6))
    for ax, (ix, iy, xlabel, ylabel, name) in zip(axes, _VIEWS):
        all_x, all_y = [], []
        for points, style in point_sets:
            if points is None or len(points) == 0:
                continue
            points = np.asarray(points)
            ax.scatter(points[:, ix], points[:, iy], **style)
            all_x.append(points[:, ix])
            all_y.append(points[:, iy])
        if all_x:
            # Zoom to the drawn points: these clusters are small next to the
            # detector, and a full-detector frame would show two specks.
            x = np.concatenate(all_x)
            y = np.concatenate(all_y)
            for lo, hi, setter in ((x.min(), x.max(), ax.set_xlim),
                                   (y.min(), y.max(), ax.set_ylim)):
                pad = max((hi - lo) * _ZOOM_MARGIN, 5.0)
                setter(lo - pad, hi + pad)
        ax.set_xlabel(xlabel, fontsize=_LABEL_FONTSIZE, fontweight='bold')
        ax.set_ylabel(ylabel, fontsize=_LABEL_FONTSIZE, fontweight='bold')
        ax.set_title(name, fontsize=_LABEL_FONTSIZE, fontweight='bold')
        ax.grid(True, linestyle='--', alpha=0.3)
    # The legend carries the numbers that make the picture interpretable, so it
    # goes on the first panel where it is read before the eye moves right.
    handles, labels = axes[0].get_legend_handles_labels()
    axes[0].legend(handles, labels, fontsize=_LEGEND_FONTSIZE, loc='upper left', framealpha=0.9)
    fig.suptitle(fig_title + "\n" + "   |   ".join(legend_lines),
                 fontsize=_TITLE_FONTSIZE, fontweight='bold')
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=110, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    return output_path


def _draw_row_panels(fig_title, rows, output_path, legend_lines, footer_note=None):
    """
    One figure, len(rows) x 3 panels: each row is (row title, [(points, style)]),
    the three columns are XZ / YZ / XY.

    footer_note, when given, is (label, url) printed on one line BELOW the bottom
    row of panels. It is text and not a link: PNG cannot carry a hyperlink
    (matplotlib's url= is honoured only by the vector backends), so the url is
    printed in full to be read, and callers that need a clickable one write it to
    a companion file.

    Axes are SHARED down each column -- every row of a column gets the same
    limits, computed from every point in the figure -- so a feature that appears
    in one row and not another is a real difference and not a change of zoom.
    That is the whole reason for splitting true and reco onto separate rows: the
    eye compares position, and it can only do that on a common frame.
    """
    n = len(rows)
    fig, axes = plt.subplots(n, 3, figsize=(19, 5.6 * n), squeeze=False)
    everything = [np.asarray(p) for _, sets in rows for p, _ in sets
                  if p is not None and len(p)]
    for col, (ix, iy, xlabel, ylabel, name) in enumerate(_VIEWS):
        lims = []
        for axis in (ix, iy):
            values = np.concatenate([p[:, axis] for p in everything]) if everything else None
            if values is None or not len(values):
                lims.append(None)
                continue
            lo, hi = values.min(), values.max()
            pad = max((hi - lo) * _ZOOM_MARGIN, 5.0)
            lims.append((lo - pad, hi + pad))
        for row, (row_title, sets) in enumerate(rows):
            ax = axes[row][col]
            for points, style in sets:
                if points is not None and len(points):
                    points = np.asarray(points)
                    ax.scatter(points[:, ix], points[:, iy], **style)
            if lims[0]:
                ax.set_xlim(*lims[0])
            if lims[1]:
                ax.set_ylim(*lims[1])
            ax.set_xlabel(xlabel, fontsize=_LABEL_FONTSIZE, fontweight='bold')
            ax.set_ylabel(ylabel, fontsize=_LABEL_FONTSIZE, fontweight='bold')
            ax.set_title(f"{name} -- {row_title}", fontsize=_LABEL_FONTSIZE, fontweight='bold')
            ax.grid(True, linestyle='--', alpha=0.3)
            handles, labels = ax.get_legend_handles_labels()
            if col == 0 and handles:
                ax.legend(handles, labels, fontsize=_LEGEND_FONTSIZE,
                          loc='upper left', framealpha=0.9, markerscale=3)
    fig.suptitle(fig_title + "\n" + "   |   ".join(legend_lines),
                 fontsize=_TITLE_FONTSIZE, fontweight='bold')
    bottom = 0.035 if footer_note else 0.0
    fig.tight_layout(rect=(0, bottom, 1, 0.94 if n > 1 else 0.90))
    if footer_note:
        # BELOW the bottom row, centred, on one line -- the figure is wide enough
        # for the whole url, and out here it does not cover any data. Space for it
        # is reserved in the tight_layout rect above rather than left to
        # bbox_inches='tight', so the panels shrink to make room instead of the
        # note sitting flush against the axis labels.
        label, url = footer_note
        note = label if not url else f"{label}:  {url}"
        fig.text(0.5, 0.012, note, ha='center', va='bottom',
                 fontsize=_LABEL_FONTSIZE, fontweight='bold',
                 bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                           edgecolor='gray', alpha=0.9))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=110, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    return output_path


def draw_pair_views(record, clusters_true, clusters_reco, output_root, event_label):
    """
    One reco-true pair in XZ, YZ and XY, with the numbers that identify it.

    Parameters:
    - record: a categorize_reco_clusters record (carries the pair's purity,
        completeness, channel, category and both cluster ids)
    - clusters_true / clusters_reco: this event's point dicts
    - output_root: the Saved_Clusters directory
    - event_label: e.g. 'chunk1_37'; the per-event subdirectory is named from it
    """
    true_points = clusters_true.get(record['pair_true_cluster_id'])
    reco_points = clusters_reco.get(record['reco_cluster_id'])
    if reco_points is None:
        return None

    # Column 5 is the per-point true energy, so this is the true cluster's
    # deposited energy AFTER the cuts -- the same quantity the truth-side stacks
    # are filled with, not the pre-cut sum the efficiency is binned in.
    true_energy = float(np.asarray(true_points)[:, 5].sum()) if true_points is not None else None

    in_volume = 'in-volume' if record['category'] != 'out_of_volume' else 'OUT-of-volume'
    legend_lines = [
        f"event {event_label}",
        f"{record['channel']}",
        in_volume,
        f"purity {record['pair_purity']:.3f}",
        f"completeness {record['pair_completeness']:.3f}",
        f"true E {true_energy:.0f} MeV" if true_energy is not None else "true E n/a",
        f"true id {record['pair_true_cluster_id']:.0f}",
        f"reco id {record['reco_cluster_id']:.3f}",
    ]
    directory = cell_directory_name(record['pair_completeness'], record['pair_purity'])
    return _draw_row_panels(
        f"Reco-true pair -- {record['channel']}",
        [("TRUE cluster", [(true_points, _TRUE_STYLE)]),
         ("RECO cluster", [(reco_points, _RECO_STYLE)])],
        Path(output_root) / directory / f"pair_{record['channel']}_{event_label}.png",
        legend_lines)


def draw_cosmic_views(record, clusters_reco, output_root, event_label,
                      true_energy=None):
    """
    One cosmic candidate in XZ, YZ and XY. Reco points only -- a cosmic candidate
    is by definition a reco cluster that matched no true neutrino, so there is no
    true NEUTRINO cluster to draw beside it. true_energy, if given, is that of the
    true cluster it overlaps most (see MIN_COSMIC_VIEW_ENERGY_MEV).
    """
    reco_points = clusters_reco.get(record['reco_cluster_id'])
    if reco_points is None:
        return None
    legend_lines = [
        f"event {event_label}",
        "cosmic candidate (no true neutrino match)",
        f"reco id {record['reco_cluster_id']:.3f}",
        f"true E {true_energy:.0f} MeV" if true_energy is not None else "true E n/a",
    ]
    name = f"cosmic_reco{record['reco_cluster_id']:.0f}_{event_label}.png"
    return _draw_panels(
        "Cosmic candidate reco cluster",
        [(reco_points, _RECO_STYLE)],
        Path(output_root) / COSMIC_DIR_NAME / name,
        legend_lines)


_TWO_NU_TRUE_STYLES = [dict(color='tab:red', marker='.', s=8, alpha=0.55),
                       dict(color='tab:orange', marker='.', s=8, alpha=0.55),
                       dict(color='tab:brown', marker='.', s=8, alpha=0.55)]
_TWO_NU_RECO_STYLES = [dict(color='tab:blue', marker='.', s=8, alpha=0.55),
                       dict(color='tab:green', marker='.', s=8, alpha=0.55),
                       dict(color='tab:purple', marker='.', s=8, alpha=0.55)]


def two_neutrino_groups(categorized_records):
    """
    {true cluster id: [records]} for events where TWO OR MORE in-volume true
    neutrinos each have a selected reco cluster -- otherwise {}.

    This is the population that makes a coarse, flash-based grouping dangerous:
    one beam flash covers both interactions, so nothing in the timing separates
    them, and merging on it fuses two neutrinos into one object.
    """
    by_true = {}
    for record in categorized_records or []:
        if record['category'] != 'contaminated' and not record['category'].startswith('high_signal_'):
            continue
        if record['pair_true_cluster_id'] is None:
            continue
        by_true.setdefault(record['pair_true_cluster_id'], []).append(record)
    return by_true if len(by_true) >= 2 else {}


def draw_two_neutrino_views(by_true, clusters_true, clusters_reco, output_root, event_label):
    """
    One event holding two or more separately-reconstructed neutrinos: the true
    clusters on the top row, the reco clusters that pair to them below, one
    colour per neutrino so it is visible whether they overlap or sit apart.
    """
    true_sets, reco_sets, lines = [], [], [f"event {event_label}"]
    for n, (true_id, records) in enumerate(sorted(by_true.items())):
        true_points = clusters_true.get(true_id)
        if true_points is not None and len(true_points):
            style = dict(_TWO_NU_TRUE_STYLES[n % len(_TWO_NU_TRUE_STYLES)])
            style['label'] = f'true {true_id:.0f}'
            true_sets.append((true_points, style))
        for m, record in enumerate(records):
            reco_points = clusters_reco.get(record['reco_cluster_id'])
            if reco_points is None or not len(reco_points):
                continue
            style = dict(_TWO_NU_RECO_STYLES[n % len(_TWO_NU_RECO_STYLES)])
            style['label'] = (f"reco {record['reco_cluster_id']:.0f} -> {true_id:.0f}"
                              if m == 0 else None)
            reco_sets.append((reco_points, style))
        best = max(records, key=lambda r: r['pair_completeness'] or 0.0)
        lines.append(f"{true_id:.0f} {best['channel'] or '?'}: "
                     f"compl {best['pair_completeness']:.2f} pur {best['pair_purity']:.2f}")
    if not true_sets or not reco_sets:
        return None
    return _draw_row_panels(
        f"{len(by_true)} in-volume neutrinos in one beam window",
        [("TRUE clusters", true_sets), ("RECO clusters", reco_sets)],
        Path(output_root) / TWO_NEUTRINO_DIR_NAME / f"two_neutrino_{event_label}.png",
        lines)


def cosmic_true_energy_mev(record, purity_results, clusters_true):
    """
    The deposited energy of the true cluster this reco cluster overlaps most, or
    None if it overlaps none.

    Chosen by purity because that is the overlap measured from the RECO side --
    "how much of this reco cluster is that true cluster" -- which is the right
    question for a fragment. Completeness would favour whichever true cluster is
    smallest. The sentinel true id 8888 marks a reco cluster that matched nothing
    and is skipped.
    """
    best = None
    for entry in purity_results or []:
        if entry.get('reco_cluster_id') != record['reco_cluster_id']:
            continue
        if entry.get('true_cluster_id') == 8888 or (entry.get('purity') or 0) <= 0:
            continue
        if best is None or entry['purity'] > best['purity']:
            best = entry
    if best is None:
        return None
    true_points = clusters_true.get(best['true_cluster_id'])
    if true_points is None:
        return None
    return float(np.asarray(true_points)[:, 5].sum())


def draw_low_completeness_views(record, clusters_true, clusters_reco, output_root, event_label):
    """One badly-reconstructed in-volume pair, true above and reco below."""
    true_points = clusters_true.get(record['pair_true_cluster_id'])
    reco_points = clusters_reco.get(record['reco_cluster_id'])
    if true_points is None or reco_points is None:
        return None
    true_energy = float(np.asarray(true_points)[:, 5].sum())
    legend_lines = [
        f"event {event_label}",
        f"{record['channel']}",
        f"completeness {record['pair_completeness']:.3f}",
        f"purity {record['pair_purity']:.3f}",
        f"true E {true_energy:.0f} MeV",
        f"reco E {record['reco_energy_mev']:.0f} MeV",
        f"true id {record['pair_true_cluster_id']:.0f}",
        f"reco id {record['reco_cluster_id']:.3f}",
    ]
    name = (f"lowcompl_{record['channel']}_c{record['pair_completeness'] * 100:02.0f}"
            f"_{event_label}.png")
    return _draw_row_panels(
        f"Below {LOW_COMPLETENESS_MAX:.0%} completeness -- {record['channel']}",
        [("TRUE cluster", [(true_points, _TRUE_STYLE)]),
         ("RECO cluster", [(reco_points, _RECO_STYLE)])],
        Path(output_root) / LOW_COMPLETENESS_DIR_NAME / name,
        legend_lines)


def draw_unselected_nue_views(vertex, clusters_true, clusters_reco, selected_records,
                              output_root, event_label):
    """
    A nue CC interaction that produced no selected reco cluster.

    Top row: the true cluster that was missed. Bottom row: every reco cluster the
    event DID select, so it is visible whether the charge went somewhere else or
    was not reconstructed at all.
    """
    true_points = clusters_true.get(vertex.get('cluster_id'))
    if true_points is None or not len(true_points):
        return None
    true_energy = float(np.asarray(true_points)[:, 5].sum())
    other = [(clusters_reco[r['reco_cluster_id']], _RECO_STYLE)
             for r in selected_records if r['reco_cluster_id'] in clusters_reco]
    legend_lines = [
        f"event {event_label}",
        "nue CC, in volume, NOT selected",
        f"true id {vertex.get('cluster_id'):.0f}" if vertex.get('cluster_id') else "true id n/a",
        f"true E {true_energy:.0f} MeV",
        f"pre-cut E {(vertex.get('precut_energy_MeV') or 0):.0f} MeV",
        f"{len(other)} selected reco cluster(s) in the event",
    ]
    return _draw_row_panels(
        "Unselected nue CC interaction",
        [("TRUE cluster (missed)", [(true_points, _TRUE_STYLE)]),
         ("RECO clusters selected in this event", other)],
        Path(output_root) / UNSELECTED_NUE_DIR_NAME / f"unselected_nue_{event_label}.png",
        legend_lines)


def save_event_cluster_views(categorized_records, clusters_true, clusters_reco,
                             sampler, output_root, event_label,
                             first_neutrino_only=True,
                             min_cosmic_energy=MIN_COSMIC_VIEW_ENERGY_MEV,
                             purity_results=None, vertex_records=None):
    """
    Draw whatever this event contributes to the sample: pairs for cells not yet
    filled, and cosmics offered to the reservoir. Returns the number of figures
    drawn (which counts a cosmic that is later evicted and deleted).

    first_neutrino_only restricts pair views to the event's FIRST neutrino -- see
    FIRST_NEUTRINO_CLUSTER_ID. Cosmic views are unaffected by that, but are taken
    only above min_cosmic_energy of TRUE deposited energy, which needs
    purity_results for this event to identify the overlapping true cluster; without
    it no cosmic can be drawn.
    """
    drawn = 0

    # Unselected nue CC: decided per INTERACTION, so it needs the vertex records
    # rather than the reco-side categorisation.
    selected = [r for r in categorized_records or []
                if r['category'] == 'contaminated' or r['category'].startswith('high_signal_')]
    paired_true = {r['pair_true_cluster_id'] for r in selected}
    for vertex in vertex_records or []:
        if (vertex.get('interaction_channel') != 'nue_CC'
                or vertex.get('vertex_in_volume') is not True
                or vertex.get('cluster_id') in paired_true):
            continue
        path = draw_unselected_nue_views(vertex, clusters_true, clusters_reco, selected,
                                         output_root, event_label)
        if path:
            true_points = clusters_true.get(vertex.get('cluster_id'))
            sampler.take_unselected_nue(
                vertex, path, event_label,
                float(np.asarray(true_points)[:, 5].sum()) if true_points is not None else None,
                {'precut_energy_MeV': vertex.get('precut_energy_MeV'),
                 'n_selected_in_event': len(selected)})
            drawn += 1

    # Two-neutrino events first: the decision is per EVENT, not per cluster, so it
    # does not belong in the per-record loop below.
    by_true = two_neutrino_groups(categorized_records)
    if by_true:
        slot = sampler.offer_two_neutrino()
        if slot is not None:
            path = draw_two_neutrino_views(by_true, clusters_true, clusters_reco,
                                           output_root, event_label)
            if path:
                sampler.take_two_neutrino(
                    slot, path=path, event_label=event_label,
                    detail={'n_neutrinos': len(by_true),
                            'true_ids': sorted(by_true),
                            'reco_ids': sorted(r['reco_cluster_id']
                                               for rs in by_true.values() for r in rs)})
                drawn += 1

    for record in categorized_records or []:
        if record['category'] == 'cosmic':
            # Energy first, then existence of the points, and only then offer it to
            # the reservoir: offering a candidate that cannot be drawn would still
            # count towards the sampling denominator and bias the draw.
            true_energy = cosmic_true_energy_mev(record, purity_results, clusters_true)
            if true_energy is None or true_energy <= min_cosmic_energy:
                continue
            if clusters_reco.get(record['reco_cluster_id']) is None:
                continue
            slot = sampler.offer_cosmic()
            if slot is None:
                continue
            path = draw_cosmic_views(record, clusters_reco, output_root, event_label,
                                     true_energy=true_energy)
            if path:
                sampler.take_cosmic(slot, record=record, path=path,
                                    event_label=event_label, true_energy=true_energy)
                drawn += 1
            continue
        # Only in-volume pairs are sampled across the grid: out-of-volume pairs are
        # a rejection category, and their completeness/purity are not what the grid
        # is about.
        if record['category'] == 'out_of_volume' or record['pair_true_cluster_id'] is None:
            continue
        # EVERY badly reconstructed in-volume pair, before the first-neutrino
        # restriction: this set is about what the selection loses, and a second
        # neutrino's pair is lost just as thoroughly as a first one's.
        if (record.get('pair_completeness') or 0) < LOW_COMPLETENESS_MAX:
            sampler.n_low_completeness_candidates += 1
        if ((record.get('pair_completeness') or 0) < LOW_COMPLETENESS_MAX
                and (record.get('reco_energy_mev') or 0) > LOW_COMPLETENESS_MIN_RECO_ENERGY_MEV):
            true_points = clusters_true.get(record['pair_true_cluster_id'])
            true_energy = (float(np.asarray(true_points)[:, 5].sum())
                           if true_points is not None else 0.0)
            path = draw_low_completeness_views(record, clusters_true, clusters_reco,
                                               output_root, event_label)
            if path:
                sampler.take_low_completeness(record, path, event_label, true_energy)
                drawn += 1

        if first_neutrino_only and record['pair_true_cluster_id'] != FIRST_NEUTRINO_CLUSTER_ID:
            continue
        channel = record['channel']
        if not sampler.wants_pair(channel, record['pair_completeness'], record['pair_purity']):
            continue
        path = draw_pair_views(record, clusters_true, clusters_reco, output_root, event_label)
        if path:
            true_points = clusters_true.get(record['pair_true_cluster_id'])
            true_energy = (float(np.asarray(true_points)[:, 5].sum())
                           if true_points is not None else None)
            sampler.take_pair(channel, record['pair_completeness'], record['pair_purity'],
                              record=record, path=path, event_label=event_label,
                              true_energy=true_energy)
            drawn += 1
    return drawn


def write_cluster_view_index(sampler, output_root, filename='completeness_purity.txt'):
    """
    An index of every view drawn, so a plot can be chosen from the text rather
    than by opening files one at a time.

    Sorted by channel then by cell, and the cells are laid out as a grid at the
    end: reading down a column shows how the pictures change with purity at fixed
    completeness, which is the comparison the sample exists to make. Cells with no
    entry are shown empty, because knowing that a corner of the plane never
    occurs is as useful as seeing one that does.
    """
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / filename

    pairs   = [s for s in sampler.saved if s['kind'] == 'pair']
    cosmics = [s for s in sampler.saved if s['kind'] == 'cosmic']
    two_nu  = [s for s in sampler.saved if s['kind'] == 'two_neutrino']
    low_c   = [s for s in sampler.saved if s['kind'] == 'low_completeness']
    lost_nue = [s for s in sampler.saved if s['kind'] == 'unselected_nue']

    lines = []
    lines.append("=" * 108)
    lines.append("SAVED CLUSTER VIEWS -- index")
    lines.append("=" * 108)
    lines.append("One reco-true pair per 10% x 10% cell of the completeness-purity plane, per")
    lines.append("interaction channel, drawn in XZ, YZ and XY. The pair shown for a cell is the")
    lines.append("FIRST one the event loop met there, not a uniform draw from it.")
    lines.append("")
    lines.append(f"LAYOUT. One directory per CELL, up to {sampler.per_cell} example(s) in each:")
    lines.append("")
    lines.append("    completeness_100_90_purity_80_70/pair_<channel>_<event>.png")
    lines.append("")
    lines.append("Each bin is written high value first, so the directories sort best-first.")
    lines.append("Every pair view has TWO ROWS -- the true cluster above, the reco cluster")
    lines.append("below -- sharing one set of axes per column, so positions can be compared.")
    lines.append("Only the event's FIRST neutrino is drawn.")
    lines.append("")
    lines.append(f"COSMICS -> {COSMIC_DIR_NAME}/")
    lines.append("")
    lines.append(f"Up to {sampler.max_cosmics} cosmic candidates, drawn UNIFORMLY AT RANDOM "
                 f"(reservoir sampling,")
    lines.append(f"seed {COSMIC_SAMPLE_SEED}) from the {sampler.n_cosmic_candidates} "
                 f"candidate(s) the job saw. A candidate qualifies")
    lines.append(f"when the true cluster it overlaps most deposits more than "
                 f"{MIN_COSMIC_VIEW_ENERGY_MEV:.0f} MeV -- true")
    lines.append("energy, not the reco cluster's own charge. E reco can exceed E true, because")
    lines.append("a reco cosmic cluster may span several true ones and only the largest overlap")
    lines.append("is reported here.")
    lines.append("")
    lines.append("")
    lines.append(f"TWO-NEUTRINO EVENTS -> {TWO_NEUTRINO_DIR_NAME}/")
    lines.append("")
    lines.append(f"{sampler.max_two_neutrino} event(s) drawn at random from the")
    lines.append(f"{sampler.n_two_neutrino_candidates} in which two or more in-volume true neutrinos each")
    lines.append("produced a selected reco cluster -- one beam flash covering two interactions,")
    lines.append("which is the case a flash-based grouping cannot separate.")
    lines.append("")
    lines.append("")
    lines.append(f"BADLY RECONSTRUCTED PAIRS -> {LOW_COMPLETENESS_DIR_NAME}/")
    lines.append("")
    lines.append(f"EVERY in-volume pair below {LOW_COMPLETENESS_MAX:.0%} completeness whose RECO cluster")
    lines.append(f"carries more than {LOW_COMPLETENESS_MIN_RECO_ENERGY_MEV:.0f} MeV -- no sampling, no quota.")
    lines.append("The energy gate is on the reco side, so it keeps the failures that")
    lines.append("reconstructed a substantial cluster and still missed most of the true")
    lines.append("one. It is a hard cut: a pair at low completeness usually has a SMALL")
    lines.append("reco cluster by construction, so far fewer pairs pass it than sit below")
    lines.append("the completeness bar (the counts below give both).")
    lines.append("")
    lines.append(f"{len(pairs)} pair view(s), {len(cosmics)} cosmic view(s), "
                 f"{len(two_nu)} two-neutrino view(s), {len(low_c)} below-"
                 f"{LOW_COMPLETENESS_MAX:.0%}-completeness view(s) from "
                 f"{sampler.n_low_completeness_candidates} such pair(s), "
                 f"{len(lost_nue)} unselected nue CC view(s).")
    lines.append("")
    lines.append("-" * 108)
    lines.append(f"  {'channel':<9s}{'comp bin':>9s}{'pur bin':>9s}{'completeness':>14s}{'purity':>9s}"
                 f"{'E true':>9s}{'E reco':>9s}{'true id':>10s}{'reco id':>11s}  file")
    lines.append("-" * 108)
    for entry in sorted(pairs, key=lambda s: (s['channel'], -s['completeness_bin'], s['purity_bin'])):
        name = Path(entry['path']).name if entry['path'] else ''
        lines.append(
            f"  {entry['channel']:<9s}{entry['completeness_bin']:>7d}-{entry['completeness_bin']+10:<2d}"
            f"{entry['purity_bin']:>6d}-{entry['purity_bin']+10:<2d}"
            f"{entry['completeness']:>14.4f}{entry['purity']:>9.4f}"
            f"{(entry.get('true_energy_mev') or 0):>9.0f}{entry['reco_energy_mev']:>9.0f}"
            f"{entry['true_cluster_id']:>10.0f}{entry['reco_cluster_id']:>11.3f}"
            f"  {cell_directory_name(entry['completeness'], entry['purity'])}/{name}")

    if cosmics:
        lines.append("")
        lines.append("-" * 108)
        lines.append(f"  {'cosmic candidates':<32s}{'event':>10s}{'reco id':>11s}"
                     f"{'E true':>9s}{'E reco':>9s}  file")
        lines.append("-" * 108)
        for entry in sorted(cosmics, key=lambda s: -(s.get('true_energy_mev') or 0)):
            name = Path(entry['path']).name if entry['path'] else ''
            lines.append(f"  {'':<32s}{entry['event']:>10s}{entry['reco_cluster_id']:>11.3f}"
                         f"{(entry.get('true_energy_mev') or 0):>9.0f}"
                         f"{entry['reco_energy_mev']:>9.0f}  {COSMIC_DIR_NAME}/{name}")

    if lost_nue:
        lines.append("")
        lines.append("=" * 108)
        lines.append("UNSELECTED nue CC INTERACTIONS -- every in-volume nue CC that produced NO")
        lines.append(f"selected reco cluster. Views in {UNSELECTED_NUE_DIR_NAME}/.")
        lines.append("=" * 108)
        lines.append(f"  {'event':>12s}{'true id':>10s}{'true E':>9s}{'pre-cut E':>11s}"
                     f"{'selected in event':>19s}  file")
        lines.append("-" * 108)
        for entry in lost_nue:
            d = entry.get('detail') or {}
            name = Path(entry['path']).name if entry['path'] else ''
            lines.append(f"  {entry['event']:>12s}{(entry['true_cluster_id'] or 0):>10.0f}"
                         f"{(entry.get('true_energy_mev') or 0):>9.0f}"
                         f"{(d.get('precut_energy_MeV') or 0):>11.0f}"
                         f"{d.get('n_selected_in_event', 0):>19d}"
                         f"  {UNSELECTED_NUE_DIR_NAME}/{name}")

    if low_c:
        lines.append("")
        lines.append("-" * 108)
        heading = (f"below {LOW_COMPLETENESS_MAX:.0%} compl, "
                   f"reco E > {LOW_COMPLETENESS_MIN_RECO_ENERGY_MEV:.0f} MeV")
        lines.append(f"  {heading:<34s}{'event':>12s}{'channel':>9s}{'compl':>8s}"
                     f"{'purity':>8s}{'true E':>9s}{'reco E':>9s}")
        lines.append("-" * 108)
        for entry in sorted(low_c, key=lambda e: e['completeness'] or 0):
            lines.append(f"  {'':<34s}{entry['event']:>12s}{str(entry['channel']):>9s}"
                         f"{(entry['completeness'] or 0):>8.3f}{(entry['purity'] or 0):>8.3f}"
                         f"{(entry.get('true_energy_mev') or 0):>9.0f}"
                         f"{(entry['reco_energy_mev'] or 0):>9.0f}")

    if two_nu:
        lines.append("")
        lines.append("-" * 108)
        lines.append(f"  {'two-neutrino events':<34s}{'event':>12s}{'neutrinos':>11s}"
                     f"  true ids -> reco ids")
        lines.append("-" * 108)
        for entry in two_nu:
            d = entry.get('detail') or {}
            trues = ','.join(f"{v:.0f}" for v in d.get('true_ids', []))
            recos = ','.join(f"{v:.0f}" for v in d.get('reco_ids', []))
            lines.append(f"  {'':<34s}{entry['event']:>12s}{d.get('n_neutrinos', 0):>11d}"
                         f"  {trues} -> {recos}")

    # The occupancy grid: which cells have a picture and which never occurred.
    for channel in sorted({s['channel'] for s in pairs}):
        cells = {(s['completeness_bin'], s['purity_bin']) for s in pairs if s['channel'] == channel}
        lines.append("")
        lines.append("-" * 108)
        lines.append(f"{channel}: cells with a saved view  (X = saved, . = no pair fell here)")
        lines.append("-" * 108)
        lines.append("     purity ->   " + "".join(f"{p:>5d}" for p in range(0, 100, 10)))
        for completeness in range(90, -10, -10):
            row = "".join("    X" if (completeness, p) in cells else "    ."
                          for p in range(0, 100, 10))
            lines.append(f"  completeness {completeness:>3d}" + row)
    lines.append("=" * 108)

    with open(path, 'w') as f:
        f.write("\n".join(lines) + "\n")
    return path
