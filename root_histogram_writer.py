"""
Phase B helper (see project plan): writes native ROOT TH1D/TH2D histograms via uproot,
mirrored into TDirectory paths that match the PNG output folder structure, alongside the
existing matplotlib-based Draw*/plot_* PNG output (which stays completely unmodified).

PyROOT's canvas.Write() was the original target representation but is unusable on this
machine today (see project plan); these helpers write real, browsable TH1D/TH2D objects via
uproot instead. Swapping to canvas.Write() later only means changing these two functions.
"""
import numpy as np


def save_th1(root_file, dir_path, name, values, bins):
    """Write a 1D histogram at f"{dir_path}/{name}" into an open uproot.recreate file.
    `bins` is anything np.histogram accepts (an int bin count or explicit edges array)."""
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return
    counts, edges = np.histogram(values, bins=bins)
    root_file[f"{dir_path}/{name}"] = (counts, edges)


def save_th2(root_file, dir_path, name, x_values, y_values, x_bins, y_bins):
    """Write a 2D histogram at f"{dir_path}/{name}". `x_bins`/`y_bins` are anything
    np.histogram2d accepts (an int bin count or explicit edges array per axis)."""
    x_values = np.asarray(x_values, dtype=float)
    y_values = np.asarray(y_values, dtype=float)
    mask = np.isfinite(x_values) & np.isfinite(y_values)
    x_values, y_values = x_values[mask], y_values[mask]
    if len(x_values) == 0:
        return
    counts, x_edges, y_edges = np.histogram2d(x_values, y_values, bins=(x_bins, y_bins))
    root_file[f"{dir_path}/{name}"] = (counts, x_edges, y_edges)


def save_th1_counts(root_file, dir_path, name, counts):
    """Write a category-count bar chart (e.g. neutrino/cosmic counts, match-multiplicity
    counts) as a TH1D with one bin per category, in the given order."""
    counts = np.asarray(counts, dtype=float)
    if len(counts) == 0:
        return
    edges = np.arange(len(counts) + 1, dtype=float)
    root_file[f"{dir_path}/{name}"] = (counts, edges)
