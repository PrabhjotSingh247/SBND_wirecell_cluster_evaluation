"""
TRUE-CLUSTER SIGNAL/BACKGROUND STACKS -- driven by
AnalysisDistributions/Draw_Signal_Background_True.ipynb.

What the selected TRUE population is made of, as a stacked histogram of true
cluster energy: the signal channel, the other in-volume channels, and what came
from outside the volume. Pure truth -- no reco cluster is drawn on it, and
nothing here depends on the reco selection.

WHAT IS WRITTEN, per bin width in BIN_WIDTHS_MEV:

    signal_background_true/
        100MeV/
            signal_background_true_energy_stack_100MeV_<scale>_job_Combined.png
            signal_background_info_100MeV.txt      per-bin table + component counts
        200MeV/
            ...
        signal_background_histograms.root          both widths, one file

The ROOT file sits at the top rather than inside either width's directory because
it holds the histograms of both.

ONE SHARED Y RANGE per (scale, bin width), applied to the LOG versions only. A
narrower bin holds fewer clusters, so the tallest bin -- and therefore the axis --
differs between widths, and the headroom differs between log and linear, so a
single number cannot serve every figure. Sharing costs nothing on log, where the
bands span decades; on linear a shared top set by the tallest figure flattens the
other one, so the linear versions autoscale per figure.

THE VARIANTS. PLOT_VARIANTS in the driving notebook chooses which component lists
are drawn: the plain four-band stack, and optionally the five-band one that splits
the signal by how well each cluster was reconstructed. Only the second needs the
reco-true pairing, and only that one makes this notebook expensive -- see
NEEDS_PAIRING there.

WHY A SEPARATE MODULE. These stacks used to be drawn by
SignalBackground_Distributions_AfterCosmic.ipynb, in a loop inline in its job-level cell.
They are the truth-side half of that notebook and nothing else in it depends on
them, so they now stand alone and can be re-run without the reco-space plots --
which, with the plain stack alone, means without the pairing at all.

PER-EVENT nue_CC TRUE-CLUSTER VIEWS -- the second thing this module draws, for
the "nuecc" sample only. Every event holding an IN-VOLUME true nue_CC
interaction gets one XZ/YZ/XY figure (see draw_nue_cc_event_view), filed into
one of three categories by what ELSE -- also in-volume -- shares that event:

    NUE_CC_ONLY_DIR_NAME          no other in-volume neutrino interaction
    NUE_CC_PILEDUP_NUMU_DIR_NAME  an in-volume numu_CC interaction ALSO present
    NUE_CC_PILEDUP_OTHER_DIR_NAME some other in-volume neutrino (NC, or an
                                  unclassified channel) present, but no numu_CC

Cosmic tracks are NOT "other activity" here and never move an event between
categories -- they are in nearly every event, so counting them would leave
NUE_CC_ONLY_DIR_NAME essentially empty. Only in-volume true-neutrino vertices
(vertex_in_volume is True) are considered, on either side of the split.
numu_CC takes priority over "other" when both share an event, since the two
pile-up categories are not meant to double-count one event.

Written to TRUE_CLUSTERS_DIR_NAME, one directory per category, one subdirectory
per chunk (see classify_nue_cc_event / save_event_nue_cc_true_views /
build_and_write_nue_cc_bee_links / write_nue_cc_true_summary).

BEE LINKS -- ONE SET PER CATEGORY, not one shared set. Each category gets its
OWN dedicated BEE set, built and uploaded from only that category's events,
plus one further set over every category combined. Sharing a single set across
categories would make a category's "list" overview link open the WHOLE
population -- e.g. clicking the set link printed in bee_links_PiledUp_NuMuCC.txt
would show all ten events instead of the one that actually piled up -- which
defeats the point of splitting the links by category at all.
"""

from pathlib import Path

import numpy as np

from datetime import datetime, timedelta

from draw_signal_background import (
    BIN_WIDTHS_MEV, SIGNAL_BACKGROUND_COMPONENTS, Y_SCALES,
    draw_stacked_true_energy, shared_y_top, write_signal_background_info,
    write_signal_background_root, order_components_for_stack,
)
from draw_selection_performance import plot_directory
from draw_saved_clusters import _draw_row_panels
from draw_contamination_clusters import split_event_key, _id_text


SIGNAL_BACKGROUND_TRUE_DIR_NAME = 'signal_background_true'


def _fmt_seconds(seconds):
    """'0:01:51 (110.6 seconds)' -- the same shape SignalBackground's summary uses."""
    if seconds is None:
        return "n/a"
    return f"{timedelta(seconds=int(seconds))} ({seconds:.1f} seconds)"


def write_signal_background_true_summary(
        output_root, job_true_var_records, *,
        total_files, total_events, job_start_time, job_runtime_s,
        staging_seconds=None, event_loop_seconds=None, draw_seconds=None,
        config_lines=None, components=None):
    """
    signal_background_true/summary.txt -- the run's configuration, the stack
    component counts (= histogram entries, recomputed from the same selectors the
    figures were drawn from) and a JOB RUNTIME block broken down into staging,
    the event loop and drawing. Returns the path written.

    config_lines is an optional list of pre-formatted 'key: value' strings from
    the notebook (parent dir, cut flags, ...) -- printed verbatim under
    "Configuration:" so the file is self-contained without this module needing to
    know the notebook's knobs.
    """
    components = components if components is not None else SIGNAL_BACKGROUND_COMPONENTS
    true_dir = plot_directory(output_root, SIGNAL_BACKGROUND_TRUE_DIR_NAME)

    component_counts = {c['key']: len(c['select'](job_true_var_records)) for c in components}
    n_neutrino = sum(1 for r in job_true_var_records if r.get('is_neutrino'))
    finish_dt = datetime.fromtimestamp(job_start_time + job_runtime_s)

    lines = []
    lines.append("=" * 80)
    lines.append("JOB SUMMARY -- SIGNAL & BACKGROUND, TRUE CLUSTERS")
    lines.append("=" * 80)
    lines.append(f"Generated: {finish_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    if config_lines:
        lines.append("")
        lines.append("Configuration:")
        lines.extend(f"  {line}" for line in config_lines)
    lines.append("")
    lines.append("=" * 80)
    lines.append("JOB-LEVEL AGGREGATION")
    lines.append("=" * 80)
    lines.append(f"Total files processed:  {total_files}")
    lines.append(f"Total events processed: {total_events}")
    lines.append(f"Total selected true clusters: {len(job_true_var_records)}")
    lines.append(f"  of which true neutrino clusters: {n_neutrino}")
    lines.append("")
    lines.append("Stack components (= histogram entries, bottom of the stack first):")
    for component in order_components_for_stack(components):
        lines.append(f"  {component['key']:<28s} {component_counts[component['key']]:6d} clusters")
    lines.append(f"  {'TOTAL IN STACK':<28s} {sum(component_counts.values()):6d} clusters")
    lines.append("")
    lines.append("=" * 80)
    lines.append("JOB RUNTIME")
    lines.append("=" * 80)
    lines.append(f"Job started at:  {datetime.fromtimestamp(job_start_time).strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Job finished at: {finish_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Total job runtime: {_fmt_seconds(job_runtime_s)}")
    lines.append("")
    lines.append("Breakdown:")
    lines.append(f"  input staging:  {_fmt_seconds(staging_seconds)}"
                 + ("   (0 on re-runs / non-nuecc samples -- data already extracted)"
                    if staging_seconds is not None and staging_seconds < 1 else ""))
    lines.append(f"  event loop:     {_fmt_seconds(event_loop_seconds)}"
                 + (f"   ({event_loop_seconds / total_events:.2f} s/event)"
                    if event_loop_seconds is not None and total_events else ""))
    lines.append(f"  drawing + I/O:  {_fmt_seconds(draw_seconds)}")
    lines.append("=" * 80)

    summary_path = true_dir / "summary.txt"
    summary_path.write_text("\n".join(lines) + "\n")
    return summary_path

# The default figure set: the plain stack only. Mirrors PLOT_VARIANTS in the
# notebook, which is where it is normally chosen.
DEFAULT_PLOT_VARIANTS = [(None, None)]


def draw_job_signal_background_true(job_true_var_records, output_root,
                                    plot_variants=None,
                                    bin_widths=BIN_WIDTHS_MEV,
                                    y_scales=Y_SCALES,
                                    level_name="Job Level",
                                    filename_prefix="job", apa="Combined",
                                    title="True Signal and Backgrounds"):
    """
    Every stack, table and the ROOT file, into SIGNAL_BACKGROUND_TRUE_DIR_NAME
    under output_root.

    title is the base plot title on every figure ("True Signal and Backgrounds"
    by default); a variant_label is still appended to it where one applies.

    Returns (root_path, counts_by_variant): the ROOT file written, and
    {(variant label, bin width): {component key: n clusters}} -- the histogram
    entry counts, taken from the same mapping each figure was drawn from rather
    than recomputed, so they cannot disagree with what was plotted.
    """
    plot_variants = plot_variants if plot_variants is not None else DEFAULT_PLOT_VARIANTS

    # One shared top per (scale, width) -- see the module docstring for why it is
    # keyed on both and applied to log only.
    job_y_top = {(scale, width): shared_y_top(job_true_var_records, [],
                                              bin_width=width, y_scale=scale)
                 for scale in y_scales for width in bin_widths}

    root_entries = []   # one per FIGURE-pair; the ROOT histograms do not depend on the y scale
    counts_by_variant = {}
    for variant_components, variant_label in plot_variants:
        for bin_width in bin_widths:
            true_dir = plot_directory(output_root, SIGNAL_BACKGROUND_TRUE_DIR_NAME, bin_width)
            for y_scale in y_scales:
                selected_by_key, _reco_values = draw_stacked_true_energy(
                    job_true_var_records, true_dir, level_name, filename_prefix, apa,
                    components=variant_components, bin_width=bin_width,
                    y_top=job_y_top[(y_scale, bin_width)] if y_scale == 'log' else None,
                    variant_label=variant_label, y_scale=y_scale, title=title)
                # _reco_values is empty by construction -- no reco_records were passed.

            # The table and the ROOT histograms are scale-independent but NOT
            # bin-width independent, so they are written once per (variant, width).
            write_signal_background_info(selected_by_key, true_dir, level_name,
                                         components=variant_components,
                                         bin_width=bin_width,
                                         variant_label=variant_label)
            root_entries.append({
                'dir_name': ((variant_label + '_' if variant_label else 'stack_')
                             + f'{bin_width:.0f}MeV'),
                'selected_by_key': selected_by_key,
                'reco_values': [],
                'components': variant_components,
                'bin_width': bin_width,
            })
            counts_by_variant[(variant_label, bin_width)] = {
                key: len(records) for key, records in selected_by_key.items()}

    # One file for both widths, so it sits at the top of the directory rather than
    # inside either width's.
    root_path = write_signal_background_root(
        root_entries, plot_directory(output_root, SIGNAL_BACKGROUND_TRUE_DIR_NAME))
    return root_path, counts_by_variant


def component_counts(job_true_var_records, components=None):
    """
    {component key: n clusters} for the DEFAULT four-band stack, recomputed from
    the selectors rather than taken from a drawing loop.

    The selectors are pure, so this gives exactly the counts the figures were
    drawn from -- and unlike the loop's last mapping, it belongs to the component
    list asked for rather than to whichever variant happened to run last.
    """
    components = components if components is not None else SIGNAL_BACKGROUND_COMPONENTS
    return {c['key']: len(c['select'](job_true_var_records)) for c in components}


# ============================================================================
# PER-EVENT nue_CC TRUE-CLUSTER VIEWS -- see the module docstring.
# ============================================================================

TRUE_CLUSTERS_DIR_NAME = 'TrueClusters'

NUE_CC_CHANNEL = 'nue_CC'
NUMU_CC_CHANNEL = 'numu_CC'

NUE_CC_ONLY_DIR_NAME          = 'NuECC_Events_Only'
NUE_CC_PILEDUP_NUMU_DIR_NAME  = 'NuECC_Events_PiledUp_NuMuCC'
NUE_CC_PILEDUP_OTHER_DIR_NAME = 'NuECC_Events_PiledUp_AnythingElse'
NUE_CC_CATEGORIES = (NUE_CC_ONLY_DIR_NAME, NUE_CC_PILEDUP_NUMU_DIR_NAME,
                     NUE_CC_PILEDUP_OTHER_DIR_NAME)

# BEE SET SIZE. A full 10-chunk run's NUE_CC_ONLY_DIR_NAME holds ~850 events;
# uploading all of them as one BEE set produced a 4.3 GB zip that the BEE
# server silently rejected (its own practical ceiling is roughly 0.9 GB -- see
# build_bee_set_from_links.UPLOAD_SIZE_WARN_GB). The two pile-up categories
# are two orders of magnitude smaller (a few dozen events at most) and upload
# fine whole, so only NUE_CC_ONLY_DIR_NAME is sampled by default.
#
# This trims the BEE SET AND ITS LINK FILE, not the figures: every event still
# gets its PNG (save_event_nue_cc_true_views runs on all of them regardless),
# only the 90% left out of the sample get no bee_links_NuECC_Events_Only.txt
# row / no upload.
NUE_CC_BEE_SAMPLE_FRACTIONS = {NUE_CC_ONLY_DIR_NAME: 0.10}

# One colour family per role, a couple of shades deep so two interactions of the
# same channel in one event (e.g. two nue_CC) are still visibly distinct.
_NUE_CC_STYLES  = [dict(color='tab:red',    marker='.', s=8, alpha=0.55),
                   dict(color='tab:pink',   marker='.', s=8, alpha=0.55)]
_NUMU_CC_STYLES = [dict(color='tab:blue',   marker='.', s=8, alpha=0.55),
                   dict(color='tab:cyan',   marker='.', s=8, alpha=0.55)]
_OTHER_STYLES   = [dict(color='tab:green',  marker='.', s=8, alpha=0.55),
                   dict(color='tab:olive',  marker='.', s=8, alpha=0.55)]


def _style_for_channel(channel, index):
    palette = {NUE_CC_CHANNEL: _NUE_CC_STYLES, NUMU_CC_CHANNEL: _NUMU_CC_STYLES}.get(
        channel, _OTHER_STYLES)
    return dict(palette[index % len(palette)])


def classify_nue_cc_event(vertex_records):
    """
    Split one event's true-neutrino vertex records (build_neutrino_vertex_records
    output for that event) into (category, nue_cc_records, other_records), or
    None if the event holds no IN-VOLUME nue_CC interaction at all.

    Restricted to vertex_in_volume is True throughout -- see the module
    docstring: cosmic tracks and out-of-volume neutrinos are not "other
    activity" for this split.

    category is one of the NUE_CC_*_DIR_NAME constants above; other_records is
    every other in-volume neutrino record sharing the event (empty for
    NUE_CC_ONLY_DIR_NAME), which is what the figure overlays alongside the
    nue_CC cluster(s).
    """
    in_volume = [r for r in vertex_records or [] if r.get('vertex_in_volume') is True]
    nue_records = [r for r in in_volume if r.get('interaction_channel') == NUE_CC_CHANNEL]
    if not nue_records:
        return None
    other_records = [r for r in in_volume if r.get('interaction_channel') != NUE_CC_CHANNEL]
    if not other_records:
        category = NUE_CC_ONLY_DIR_NAME
    elif any(r.get('interaction_channel') == NUMU_CC_CHANNEL for r in other_records):
        category = NUE_CC_PILEDUP_NUMU_DIR_NAME
    else:
        category = NUE_CC_PILEDUP_OTHER_DIR_NAME
    return category, nue_records, other_records


def draw_nue_cc_event_view(category, nue_records, other_records, clusters_true,
                           output_root, event_key):
    """
    One figure: every in-volume neutrino cluster relevant to this nue_CC event
    (the nue_CC cluster(s) plus whatever triggered the pile-up category)
    overlaid in a single TRUE-only row -- one colour per interaction, so a
    piled-up event shows which points belong to which neutrino, and every true
    vertex involved marked with its own star. XZ/YZ/XY, as everywhere else in
    this codebase.

    Returns the path written, or None if none of the relevant clusters had any
    surviving true points.
    """
    chunk, event = split_event_key(event_key)
    sets, vertices, lines = [], [], [f"event {event_key}", category.replace('_', ' ')]

    channel_seen = {}
    for record in nue_records + other_records:
        channel = record.get('interaction_channel') or 'unknown'
        index = channel_seen.get(channel, 0)
        channel_seen[channel] = index + 1
        cluster_id = record.get('cluster_id')
        points = clusters_true.get(cluster_id)
        if points is None or not len(points):
            continue
        style = _style_for_channel(channel, index)
        style['label'] = f"{channel} (id {cluster_id:.0f})"
        sets.append((points, style))
        vx, vy, vz = record.get('vertex_x'), record.get('vertex_y'), record.get('vertex_z')
        if None not in (vx, vy, vz):
            vertices.append((vx, vy, vz))
        energy = float(np.asarray(points)[:, 5].sum())
        lines.append(f"{channel} id {cluster_id:.0f}: {energy:.0f} MeV")

    if not sets:
        return None

    primary_id = nue_records[0].get('cluster_id')
    name = f"nue_cc_true_{chunk}_event{event}_trueID{_id_text(primary_id)}.png"
    return _draw_row_panels(
        f"True neutrino clusters -- {category.replace('_', ' ')}",
        [("TRUE clusters", sets, vertices or None)],
        Path(output_root) / TRUE_CLUSTERS_DIR_NAME / category / (chunk or 'unknown_chunk') / name,
        lines)


def save_event_nue_cc_true_views(event_vertex_records, clusters_true, output_root, event_key):
    """
    Classify this event (classify_nue_cc_event) and draw its nue_CC true-cluster
    view if it qualifies. Returns one entry dict for write_nue_cc_bee_links /
    write_nue_cc_true_summary / build_population_bee_set, or None if the event
    holds no in-volume nue_CC interaction, or none of the relevant clusters had
    surviving true points.
    """
    classified = classify_nue_cc_event(event_vertex_records)
    if classified is None:
        return None
    category, nue_records, other_records = classified
    path = draw_nue_cc_event_view(category, nue_records, other_records,
                                  clusters_true, output_root, event_key)
    if path is None:
        return None

    chunk, event = split_event_key(event_key)
    true_energy_mev = sum(
        float(np.asarray(clusters_true[r['cluster_id']])[:, 5].sum())
        for r in nue_records
        if r.get('cluster_id') in clusters_true and len(clusters_true[r['cluster_id']]))
    return {
        'path':            path,
        'event_key':       event_key,
        'chunk':           chunk,
        'event':           event,
        'category':        category,
        'n_nue_cc':        len(nue_records),
        'other_channels':  sorted({r.get('interaction_channel') or 'unknown' for r in other_records}),
        'true_energy_mev': true_energy_mev,
        'bee_url':         None,
    }


def _relative_nue_cc_path(entry, output_root):
    """'NuECC_Events_Only/chunk_00__subchunk_00/nue_cc_true_....png'."""
    return str(Path(entry['path']).relative_to(Path(output_root) / TRUE_CLUSTERS_DIR_NAME))


def _sample_rows(rows_sorted, fraction):
    """
    Every Nth of rows_sorted, N = round(1 / fraction) -- a deterministic,
    reproducible-across-reruns subsample (no RNG/seed to track), spread evenly
    across the sorted (chunk, event) order rather than e.g. the first 10%,
    which would silently favour one chunk. fraction >= 1 (or no rows) returns
    everything unchanged.
    """
    if fraction >= 1.0 or not rows_sorted:
        return list(rows_sorted)
    if fraction <= 0.0:
        return []
    stride = max(1, round(1.0 / fraction))
    return rows_sorted[::stride]


def _write_nue_cc_bee_link_file(rows, path, heading, output_root, bee_set_url=None):
    """One bee_links_<...>.txt: a header naming its own dedicated BEE set (if
    any), then one line per figure with that set's per-event url."""
    lines = [f"# BEE event display -- {heading}",
             "# One line per figure. The same URL is printed on the figure itself,",
             "# where it cannot be clicked: PNG has no hyperlinks."]
    if bee_set_url:
        lines.append(f"# BEE SET (one upload, only these events): {bee_set_url}")
    lines.append("")
    if not rows:
        lines.append(f"# (no events in {heading})")
    for entry in sorted(rows, key=lambda e: (str(e['chunk']), int(e['event'] or 0))):
        rel = _relative_nue_cc_path(entry, output_root)
        if entry.get('bee_url'):
            lines.append(f"{rel}  {entry['bee_url']}")
        else:
            lines.append(f"{rel}  (no BEE set for {entry['chunk']})")
    path.write_text("\n".join(lines) + "\n")


def build_and_write_nue_cc_bee_links(entries, parent_dir, output_root,
                                     categories=NUE_CC_CATEGORIES, prefix='bee_links',
                                     sample_fractions=None):
    """
    ONE BEE set PER CATEGORY -- built and uploaded from ONLY that category's
    events -- plus one further set over every category combined. A single
    shared set for all of them would make each category's "list" overview link
    show the WHOLE population regardless of which file it is printed in, which
    defeats the point of splitting the links by category in the first place.

    entries: job_nue_cc_entries (save_event_nue_cc_true_views output). parent_dir:
    the staged production tree build_population_bee_set assembles events from
    (NUECC_STAGING_ROOT). output_root: the run's output_dir -- the sets and
    link files are written under output_root/TRUE_CLUSTERS_DIR_NAME.

    sample_fractions defaults to NUE_CC_BEE_SAMPLE_FRACTIONS -- see its comment
    for why NUE_CC_ONLY_DIR_NAME needs one and the pile-up categories do not.
    A category not listed in it gets every one of its events. The PNG figures
    are unaffected either way; this only pares down what gets a BEE upload and
    a row in that category's link file (and, in turn, what "all" carries for
    that category, so "all" cannot balloon back up to the unsampled size).

    Each group (a category, or "all") gets its OWN list of entry COPIES before
    its upload: build_population_bee_set mutates 'bee_url' in place on whatever
    list it is given, so reusing the same dicts across the 4 uploads would leave
    every entry's bee_url pointing at whichever upload happened to run last,
    rather than at the set the file it is printed in actually belongs to.

    Returns (set_urls, paths), each a dict keyed by category plus 'all'.
    set_urls values are None where that group had nothing to draw (no upload
    attempted).
    """
    from build_bee_set_from_links import build_population_bee_set

    sample_fractions = (sample_fractions if sample_fractions is not None
                        else NUE_CC_BEE_SAMPLE_FRACTIONS)
    true_dir = Path(output_root) / TRUE_CLUSTERS_DIR_NAME
    true_dir.mkdir(parents=True, exist_ok=True)

    def _upload(rows, dir_name, label):
        return (build_population_bee_set(rows, parent_dir, true_dir / dir_name, label)
                if rows else None)

    set_urls, paths, sampled_by_category = {}, {}, {}
    for category in categories:
        rows = sorted(
            (dict(e) for e in entries or [] if e.get('category') == category),
            key=lambda e: (str(e['chunk']), int(e['event'] or 0)))
        fraction = sample_fractions.get(category, 1.0)
        sampled = _sample_rows(rows, fraction)
        sampled_by_category[category] = sampled

        set_urls[category] = _upload(sampled, f"bee_set_{category}", category)
        heading = (category if fraction >= 1.0 else
                  f"{category} ({fraction:.0%} sample, {len(sampled)} of {len(rows)} events)")
        path = true_dir / f"{prefix}_{category}.txt"
        _write_nue_cc_bee_link_file(sampled, path, heading, output_root,
                                    bee_set_url=set_urls[category])
        paths[category] = path

    # Built from the SAME sampled subsets, not every entry -- otherwise "all"
    # would drag NUE_CC_ONLY_DIR_NAME's full, too-large-to-upload population
    # right back in.
    all_rows = [row for category in categories for row in sampled_by_category[category]]
    set_urls['all'] = _upload(all_rows, "bee_set_all", "AllCategories")
    all_path = true_dir / f"{prefix}_all.txt"
    _write_nue_cc_bee_link_file(all_rows, all_path, "ALL categories combined", output_root,
                                bee_set_url=set_urls['all'])
    paths['all'] = all_path

    return set_urls, paths


def write_nue_cc_true_summary(entries, output_root, categories=NUE_CC_CATEGORIES,
                              filename='true_clusters_summary.txt'):
    """
    Counts per category plus a full per-event table, written directly under
    TRUE_CLUSTERS_DIR_NAME. Returns the path written.
    """
    true_dir = Path(output_root) / TRUE_CLUSTERS_DIR_NAME
    true_dir.mkdir(parents=True, exist_ok=True)
    entries = entries or []

    # Column widths sized to the longest values actually printed here (not the
    # generic width other summaries use) -- NUE_CC_PILEDUP_OTHER_DIR_NAME is 34
    # characters and the nuecc event_key ('chunk_00__subchunk_00_9') runs to 23,
    # both wider than the widths a shorter-name population would need.
    cat_w = max(len(c) for c in categories) + 2
    evt_w = max((len(str(e['event_key'])) for e in entries), default=5) + 2
    rule_w = max(92, cat_w + evt_w + 22)

    lines = []
    lines.append("=" * rule_w)
    lines.append("TRUE NEUTRINO CLUSTER VIEWS -- NuECC SAMPLE, BY PILE-UP CATEGORY")
    lines.append("=" * rule_w)
    lines.append("")
    lines.append("Every event holding an IN-VOLUME true nue_CC interaction, split by what")
    lines.append("ELSE -- also in-volume -- shares that event. Cosmic tracks and")
    lines.append("out-of-volume neutrinos are not counted as 'other activity' here.")
    lines.append("")
    lines.append(f"  {NUE_CC_ONLY_DIR_NAME:<{cat_w}s} no other in-volume neutrino interaction")
    lines.append(f"  {NUE_CC_PILEDUP_NUMU_DIR_NAME:<{cat_w}s} an in-volume numu_CC interaction ALSO present")
    lines.append(f"  {NUE_CC_PILEDUP_OTHER_DIR_NAME:<{cat_w}s} some other in-volume neutrino (NC, ...) present, no numu_CC")
    lines.append("")
    lines.append(f"{len(entries)} figure(s) total.")
    lines.append("")
    lines.append("-" * rule_w)
    lines.append(f"  {'category':<{cat_w}s}{'events':>10s}")
    lines.append("-" * rule_w)
    for category in categories:
        n = sum(1 for e in entries if e['category'] == category)
        lines.append(f"  {category:<{cat_w}s}{n:10d}")
    lines.append("-" * rule_w)
    lines.append(f"  {'TOTAL':<{cat_w}s}{len(entries):10d}")
    lines.append("")
    if entries:
        lines.append("-" * rule_w)
        lines.append(f"  {'event':<{evt_w}s}{'category':<{cat_w}s}{'nue_CC':>8s}{'true E':>10s}  other channels")
        lines.append("-" * rule_w)
        for entry in sorted(entries, key=lambda e: (e['category'], str(e['chunk']), int(e['event'] or 0))):
            lines.append(
                f"  {str(entry['event_key']):<{evt_w}s}{entry['category']:<{cat_w}s}"
                f"{entry['n_nue_cc']:>8d}{(entry['true_energy_mev'] or 0):>10.0f}  "
                f"{', '.join(entry['other_channels']) or '-'}")
    lines.append("=" * rule_w)

    path = true_dir / filename
    path.write_text("\n".join(lines) + "\n")
    return path
