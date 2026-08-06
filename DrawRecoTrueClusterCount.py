"""
Selection-flow ("cutflow") bar charts for SelectionAnalysis.ipynb: how many
CLUSTERS survive each successive selection, drawn as horizontal bar blocks --
one block per cut stage, top block = before any cut, each block below it the
cumulative result of one more cut.

True side (truth information available) draws three separate bars per block:
Cosmic clusters, neutrino interactions with the vertex in the volume, and
neutrino interactions with the vertex out of it. Reco side draws one bar per
block (Total only) -- reco has no neutrino/cosmic label, that distinction simply
doesn't exist before truth matching, so it is deliberately NOT invented here.

Both drawers take an already-tallied list of stage dicts, so the counting logic
(which lives in the notebook, next to the cuts themselves) stays separate from
the drawing, and the same drawer serves event/file/job level alike.
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from pathlib import Path

# Shared with the rest of the pipeline's conventions: red = neutrino,
# blue = cosmic (see DrawLabelsAggregated in DrawRecoTrueClusters.py).
_CATEGORY_COLORS = {
    'total':    '#555555',
    'cosmic':   'blue',
    'neutrino': 'red',
}
_CATEGORY_LABELS = {
    'total':    'Total (cosmic + neutrino)',
    'cosmic':   'Cosmic',
    'neutrino': 'Neutrino',
}


def _draw_selection_flow(stage_records, categories, output_dir, filename, title,
                         category_labels=None, xlabel='Number of Clusters', log_scale=False):
    """
    Shared renderer for the true/reco selection-flow charts.

    stage_records: list of dicts in cut order, first entry = no cuts, each with
        a 'stage' label plus one integer per name in `categories`.
    categories: which count keys to draw as bars within each block, in order
        (e.g. ['total', 'cosmic', 'neutrino'] or ['total']).
    category_labels: optional {category: legend label} overriding the defaults.

    Bars are labelled with the raw count, and every stage after the first also
    carries that count as a percentage of the SAME category's no-cut value --
    the survival fraction of that category, which is what a cutflow is read for.
    Stages are laid out top-to-bottom in cut order (matplotlib's y axis is
    inverted for this), with a gap between blocks.

    log_scale (default off) switches the x axis to SYMLOG (linear below 1, log
    above) for flows that span several orders of magnitude. Symlog rather than
    log because counts of exactly 0 are legitimate here (a stage can reject
    everything) and a plain log axis cannot draw them. Not needed once the flow
    starts from an energy-cut baseline rather than the raw uncut counts, which
    is why linear is the default.
    """
    if not stage_records:
        return

    labels = dict(_CATEGORY_LABELS)
    if category_labels:
        labels.update(category_labels)

    n_per_block = len(categories)
    block_span  = n_per_block + 0.6        # gap between blocks, in bar-height units
    bar_height  = 1.0 / n_per_block if n_per_block > 1 else 0.9

    baseline = {c: stage_records[0].get(c, 0) for c in categories}
    max_count = max((r.get(c, 0) for r in stage_records for c in categories), default=0)

    fig, ax = plt.subplots(figsize=(12, max(4.0, 1.7 * len(stage_records))))
    if log_scale:
        ax.set_xscale('symlog', linthresh=1)

    block_centers = []
    for block_idx, record in enumerate(stage_records):
        center = block_idx * block_span
        block_centers.append(center)

        # Within a block, category 0 sits at the top: offsets run negative->positive
        # and the axis is inverted at the end.
        offsets = (np.arange(n_per_block) - (n_per_block - 1) / 2.0) * bar_height
        for cat_idx, category in enumerate(categories):
            count = record.get(category, 0)
            ax.barh(center + offsets[cat_idx], count, height=bar_height * 0.92,
                    color=_CATEGORY_COLORS.get(category, 'gray'), alpha=0.7,
                    edgecolor='black', linewidth=1.5,
                    label=labels.get(category, category) if block_idx == 0 else None)

            label = f'{count}'
            if block_idx > 0 and baseline[category] > 0:
                pct = 100.0 * count / baseline[category]
                # A surviving-but-tiny fraction must not print as "0.0%" -- with
                # 20k cosmics in the no-cut stage, the handful that survive round
                # to zero at one decimal and would read as "none left".
                label += '  (<0.1%)' if 0 < pct < 0.1 else f'  ({pct:.1f}%)'
            if log_scale:
                x_text = count * 1.35 if count > 0 else 0.12
            else:
                x_text = count + max_count * 0.01
            ax.text(x_text, center + offsets[cat_idx], label,
                    va='center', ha='left', fontsize=12, fontweight='bold')

    # Separator lines in the gaps, so the blocks read as distinct stages
    for center in block_centers[1:]:
        ax.axhline(center - block_span / 2.0, color='gray', linewidth=0.8, alpha=0.5)

    ax.set_yticks(block_centers)
    ax.set_yticklabels([r['stage'] for r in stage_records], fontsize=13, fontweight='bold')
    if max_count > 0:
        ax.set_xlim(0, max_count * (6.0 if log_scale else 1.22))
    else:
        ax.set_xlim(0, 1)
    ax.set_xlabel(f'{xlabel} (symlog scale)' if log_scale else xlabel,
                  fontsize=13, fontweight='bold')
    ax.tick_params(axis='x', labelsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')
    ax.invert_yaxis()      # first stage on top
    ax.legend(fontsize=14, loc='lower right')

    plt.tight_layout()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_dir / filename, dpi=100, bbox_inches='tight')
    plt.close()


def DrawTrueClusterSelectionFlow(stage_records, output_dir, level_name, filename_prefix, apa,
                                 include_geometry_cuts=True, file_name=None):
    """
    True-side selection flow: one horizontal block per cut stage, top block =
    before any cut. Each block has three SEPARATE bars -- Cosmic, Neutrinos with
    the interaction vertex in the volume, and Neutrinos with the vertex out of
    it. The two neutrino bars are drawn side by side rather than stacked into one
    bar, so each one's length is read directly off the axis instead of by
    subtracting the segment below it.

    The bars count DIFFERENT things on purpose:
      cosmic   = cosmic CLUSTERS surviving that stage (from the sed true points)
      neutrino = true neutrino INTERACTIONS from mc.json. At the no-cut stage
                 that is every interaction -- in-volume, out-of-volume, and those
                 depositing nothing at all -- which no cluster-based count can
                 give, since an interaction with no deposits has no cluster.
                 At later stages it is the interactions whose cluster survived.
    Mixing them is deliberate and is why each is labelled; the neutrino side is
    the physics population, the cosmic side is the reconstruction workload.

    Parameters:
    - stage_records: list of dicts in cut order, each
        {'stage': label, 'cosmic': n, 'neutrino_in': n, 'neutrino_out': n,
         'geometry': bool}
    - output_dir: Output directory
    - level_name: Label for the title (e.g. 'Job Level')
    - filename_prefix: Suffix used in the output filename (e.g. 'job', 'file')
    - apa: APA identifier (label only, e.g. "Combined")
    - include_geometry_cuts: drop stages flagged 'geometry' when False
    - file_name: Optional input file name for title
    """
    records = [r for r in stage_records if include_geometry_cuts or not r.get('geometry')]
    if not records:
        return

    COSMIC_COLOR, IN_COLOR, OUT_COLOR = 'blue', 'green', 'darkorange'
    block_span = 4.0          # three bars plus a gap, in bar-height units
    bar_height = 1.0

    max_count = max(max(r.get('cosmic', 0), r.get('neutrino_in', 0), r.get('neutrino_out', 0))
                    for r in records)

    fig, ax = plt.subplots(figsize=(13, max(5.5, 2.8 * len(records) + 1.2)))
    # SYMLOG x axis: cosmics run to ~20k while neutrinos are tens, so on a linear
    # scale the neutrino bar is an invisible sliver. Symlog rather than log
    # because a stage can legitimately hold zero of a category and a log axis
    # cannot draw that.
    ax.set_xscale('symlog', linthresh=1)

    block_centers = []
    for block_idx, record in enumerate(records):
        center = block_idx * block_span
        block_centers.append(center)
        # Three bars, top to bottom in drawing order: cosmic, neutrino in-volume,
        # neutrino out-of-volume (the y axis is inverted below, so the smaller y
        # ends up on top).
        cosmic_y = center - bar_height
        in_y     = center
        out_y    = center + bar_height

        n_cosmic = record.get('cosmic', 0)
        n_in     = record.get('neutrino_in', 0)
        n_out    = record.get('neutrino_out', 0)

        ax.barh(cosmic_y, n_cosmic, height=bar_height * 0.85, color=COSMIC_COLOR, alpha=0.7,
                edgecolor='black', linewidth=1.5,
                label='Cosmic clusters' if block_idx == 0 else None)
        ax.barh(in_y, n_in, height=bar_height * 0.85, color=IN_COLOR, alpha=0.8,
                edgecolor='black', linewidth=1.5,
                label='Neutrinos, vertex in volume' if block_idx == 0 else None)
        ax.barh(out_y, n_out, height=bar_height * 0.85, color=OUT_COLOR, alpha=0.8,
                edgecolor='black', linewidth=1.5,
                label='Neutrinos, vertex out of volume' if block_idx == 0 else None)

        # Multiplicative text offset -- an additive one collapses to nothing at the
        # low end of a log axis.
        def _x_text(value):
            return value * 1.3 if value > 0 else 0.12

        ax.text(_x_text(n_cosmic), cosmic_y, f'{n_cosmic}',
                va='center', ha='left', fontsize=13, fontweight='bold')
        # Each neutrino bar carries its share of THIS stage's neutrino total, so
        # the two shares sum to 100% and the composition shift between stages is
        # readable directly even though the bars are no longer stacked.
        n_nu = n_in + n_out
        in_label  = f'{n_in} ({100.0 * n_in / n_nu:.1f}% of {n_nu} nu)' if n_nu > 0 else '0'
        out_label = f'{n_out} ({100.0 * n_out / n_nu:.1f}% of {n_nu} nu)' if n_nu > 0 else '0'
        ax.text(_x_text(n_in), in_y, in_label,
                va='center', ha='left', fontsize=13, fontweight='bold')
        ax.text(_x_text(n_out), out_y, out_label,
                va='center', ha='left', fontsize=13, fontweight='bold')

    for center in block_centers[1:]:
        ax.axhline(center - block_span / 2.0, color='gray', linewidth=0.8, alpha=0.5)

    ax.set_yticks(block_centers)
    ax.set_yticklabels([r['stage'] for r in records], fontsize=13, fontweight='bold')
    ax.set_xlim(0, max_count * 40 if max_count > 0 else 1)
    ax.set_xlabel('Number of Cosmic Clusters / True Neutrino Interactions (symlog scale)',
                  fontsize=13, fontweight='bold')
    title = f'True Selection Flow: {level_name}, {apa}'
    if file_name:
        title += f' ({file_name})'
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.tick_params(axis='x', labelsize=12)
    ax.grid(True, alpha=0.3, axis='x')
    # Reserve headroom ABOVE the first block for the legend instead of pushing it
    # outside the axes: the value labels run well to the right of every bar, so an
    # in-axes corner would collide, but empty space added above the top block will
    # not. The extra 0.35 block-span keeps a visible gap between the legend box
    # and the first pair of bars.
    half_bar     = bar_height + bar_height * 0.85 * 0.5
    legend_space = block_span * 0.7
    ax.invert_yaxis()
    ax.set_ylim(block_centers[-1] + half_bar + 0.3, -half_bar - legend_space)

    # Two rows: cosmic alone on the first, the two neutrino entries on the second.
    # matplotlib fills a multi-column legend COLUMN-major, so with ncol=2 the
    # order below lands as  [Cosmic | blank] / [nu in | nu out]; the blank is an
    # invisible proxy purely to hold that grid slot.
    legend_handles = [
        Patch(facecolor=COSMIC_COLOR, alpha=0.7, edgecolor='black', label='Cosmic clusters'),
        Patch(facecolor=IN_COLOR, alpha=0.8, edgecolor='black', label='Neutrinos, vertex in volume'),
        Patch(facecolor='none', edgecolor='none', label=''),
        Patch(facecolor=OUT_COLOR, alpha=0.8, edgecolor='black', label='Neutrinos, vertex out of volume'),
    ]
    ax.legend(handles=legend_handles, fontsize=17, loc='upper center', ncol=2,
              frameon=True, columnspacing=2.0, handlelength=1.8)

    plt.tight_layout()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_dir / f'true_cluster_selection_flow_{filename_prefix}_{apa}.png',
                dpi=100, bbox_inches='tight')
    plt.close()


def DrawRecoClusterSelectionFlow(stage_records, output_dir, level_name, filename_prefix, apa,
                                 include_geometry_cuts=True, file_name=None):
    """
    Reco-cluster selection flow: one Total bar per stage. No cosmic/neutrino
    split -- reco clusters carry no truth label, so that breakdown is not
    available on this side (see module docstring).

    Same parameters as DrawTrueClusterSelectionFlow above; stage_records entries
    are {'stage': label, 'total': n, 'geometry': bool}. include_geometry_cuts is
    kept for callers that still flag geometry stages, but no stage is flagged any
    more, so the filename no longer carries a with/without suffix -- there is only
    one version of this plot.
    """
    records = [r for r in stage_records if include_geometry_cuts or not r.get('geometry')]
    if not records:
        return

    title = f'Reco Cluster Selection Flow: {level_name}, {apa}'
    if file_name:
        title += f' ({file_name})'

    _draw_selection_flow(
        records, ['total'], output_dir,
        f'reco_cluster_selection_flow_{filename_prefix}_{apa}.png', title,
        category_labels={'total': 'All reco clusters'})


def write_selection_flow_table(true_stage_records, reco_stage_records, output_dir,
                               filename='selection_flow_counts.txt', level_name='Job Level'):
    """
    Text dump of the same numbers the two charts show, so the counts can be read
    exactly rather than off a bar. Both cut flows go in one file, each with its
    stages in cut order and the survival percentage relative to the no-cut stage.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / filename

    with open(out_path, 'w') as f:
        f.write(f"{'='*90}\n")
        f.write(f"CLUSTER SELECTION FLOW ({level_name}): clusters surviving each successive cut\n")
        f.write(f"{'='*90}\n")

        if true_stage_records:
            f.write("\nTRUE SIDE\n")
            f.write("  cosmic   = cosmic CLUSTERS surviving the stage\n")
            f.write("  neutrino = true neutrino INTERACTIONS from mc.json (all of them at the no-cut\n")
            f.write("             stage, including those depositing nothing), split by vertex volume\n")
            f.write(f"{'stage':<40} {'cosmic':>9} {'cosmic_%':>10} {'neutrino':>10} "
                    f"{'nu_in_vol':>11} {'nu_out_vol':>12} {'neutrino_%':>12}\n")
            base = true_stage_records[0]
            base_cosmic   = base.get('cosmic', 0)
            base_neutrino = base.get('neutrino_in', 0) + base.get('neutrino_out', 0)
            for r in true_stage_records:
                n_cosmic = r.get('cosmic', 0)
                n_in, n_out = r.get('neutrino_in', 0), r.get('neutrino_out', 0)
                pct_c = 100.0 * n_cosmic / base_cosmic if base_cosmic else 0.0
                pct_n = 100.0 * (n_in + n_out) / base_neutrino if base_neutrino else 0.0
                f.write(f"{r['stage']:<40} {n_cosmic:>9} {pct_c:>9.1f}% {n_in + n_out:>10} "
                        f"{n_in:>11} {n_out:>12} {pct_n:>11.1f}%\n")

        if reco_stage_records:
            base = reco_stage_records[0]
            f.write("\nRECO CLUSTERS (no truth label available -- total only)\n")
            f.write(f"{'stage':<46} {'total':>8} {'total_%':>9}\n")
            for r in reco_stage_records:
                pct = 100.0 * r['total'] / base['total'] if base['total'] else 0.0
                f.write(f"{r['stage']:<46} {r['total']:>8} {pct:>8.1f}%\n")

    return out_path
