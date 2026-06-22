#!/usr/bin/env python3
"""Compare peak detection methods (SG+find_peaks, AsLS baseline, matched filter, CWT).

Usage: python scripts/peak_detection_compare.py [path/to/file.xy]
"""
from __future__ import annotations
import sys
import numpy as np
from scipy.signal import savgol_filter, find_peaks
from scipy.signal import convolve
import os
import matplotlib.pyplot as plt
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve


def ricker_wavelet(points, a):
    # simple Ricker (Mexican hat) wavelet approximation
    if points < 3:
        points = 3
    t = np.arange(points) - (points - 1) / 2.0
    wsq = float(a) ** 2
    psi = (1 - (t ** 2) / wsq) * np.exp(- (t ** 2) / (2.0 * wsq))
    return psi


def read_xy(path):
    x = []
    y = []
    with open(path, 'rb') as f:
        for raw in f:
            try:
                line = raw.decode('utf-8').strip()
            except Exception:
                line = raw.decode('latin1', errors='replace').strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                xv = float(parts[0])
                yv = float(parts[1])
            except ValueError:
                continue
            x.append(xv)
            y.append(yv)
    return np.array(x), np.array(y)


def normalize(y):
    y = np.asarray(y)
    if y.max() == 0:
        return y
    return y / np.max(y)


def asls_baseline(y, lam=1e6, p=0.01, niter=10):
    # Asymmetric Least Squares baseline using sparse matrices
    # Reference: Eilers & Boelens 2005
    L = len(y)
    if L < 3:
        return np.zeros_like(y)
    e = np.ones(L)
    # second difference operator of shape (L-2, L)
    D = sp.diags([e, -2*e, e], [0, 1, 2], shape=(L-2, L))
    H = lam * (D.T @ D)  # sparse (L,L)
    w = np.ones(L)
    for i in range(niter):
        W = sp.diags(w, 0)
        C = (W + H).tocsc()
        z = spsolve(C, w * y)
        # update weights (asymmetric)
        w = p * (y > z) + (1 - p) * (y < z)
    return z


def matched_filter_response(y, kernel_std=10, kernel_len=101):
    # Gaussian kernel
    t = np.arange(kernel_len) - (kernel_len - 1) / 2.0
    kernel = np.exp(-0.5 * (t / kernel_std) ** 2)
    kernel = kernel / np.sum(kernel)
    resp = convolve(y, kernel, mode='same')
    return resp


def cwt_response(y, widths=None):
    # If scipy.signal.cwt isn't available, emulate by convolving with
    # ricker wavelets at several scales.
    if widths is None:
        widths = np.arange(1, 60)
    mat = []
    for w in widths:
        pts = int(min(len(y), max(3, int(8 * w + 1))))
        kern = ricker_wavelet(pts, w)
        kern = kern / (np.sum(np.abs(kern)) + 1e-12)
        resp = convolve(y, kern, mode='same')
        mat.append(resp)
    mat = np.vstack(mat)
    resp = np.max(np.abs(mat), axis=0)
    return resp, mat


def detect_find_peaks(y, prominence=0.015, distance=8, width=None):
    kwargs = dict(prominence=prominence, distance=distance)
    if width is not None:
        kwargs['width'] = width
    peaks, props = find_peaks(y, **kwargs)
    return peaks, props


def summarize_and_print(name, x, y, peaks):
    print(f"Method: {name} -> {len(peaks)} peaks")
    if len(peaks) > 0:
        # print first few peak positions
        pos = x[peaks]
        print("  positions:", np.round(pos[:10], 4))


def plot_results(outdir, basename, x, raw, methods):
    # methods: list of tuples (name, trace, peaks_indices, baseline(optional))
    os.makedirs(outdir, exist_ok=True)
    fig, axes = plt.subplots(len(methods), 1, figsize=(8, 3*len(methods)), sharex=True)
    if len(methods) == 1:
        axes = [axes]
    for ax, (name, trace, peaks, extras) in zip(axes, methods):
        ax.plot(x, raw, color='0.7', label='raw')
        ax.plot(x, trace, label=name)
        if extras is not None and 'baseline' in extras:
            ax.plot(x, extras['baseline'], label='baseline', linestyle='--')
        if peaks is not None and len(peaks) > 0:
            ax.plot(x[peaks], trace[peaks], 'x', label=f'peaks ({len(peaks)})')
        ax.legend(loc='upper right', fontsize='small')
        ax.set_ylabel('Intensity')
    axes[-1].set_xlabel('2theta')
    fig.suptitle(basename)
    out = os.path.join(outdir, f"{basename}_comparison.png")
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(out, dpi=150)
    plt.close(fig)


def merge_peaks(peaks_list, distance=5):
    # peaks_list: list of arrays of peak indices
    all_peaks = np.concatenate(peaks_list) if len(peaks_list) > 0 else np.array([], dtype=int)
    if all_peaks.size == 0:
        return np.array([], dtype=int)
    all_peaks = np.unique(all_peaks)
    all_peaks.sort()
    groups = []
    current = [all_peaks[0]]
    for p in all_peaks[1:]:
        if p - current[-1] <= distance:
            current.append(p)
        else:
            groups.append(current)
            current = [p]
    groups.append(current)
    # representative: mean index rounded
    reps = np.array([int(np.round(np.mean(g))) for g in groups], dtype=int)
    return reps


def compute_peak_metrics(x, y, peak_idx, width_half=10):
    L = len(y)
    i = peak_idx
    lo = max(0, i - width_half)
    hi = min(L, i + width_half)
    xs = x[lo:hi]
    ys = y[lo:hi]
    if xs.size < 2:
        area = 0.0
    else:
        area = float(np.sum((ys[:-1] + ys[1:]) * (xs[1:] - xs[:-1]) * 0.5))
    height = y[i]
    # local noise estimate
    local = np.concatenate([y[max(0, lo-3*width_half):lo], y[hi: min(L, hi+3*width_half)]])
    if local.size == 0:
        snr = np.nan
    else:
        snr = height / (np.std(local) + 1e-12)
    return dict(index=i, pos=x[i], height=float(height), area=float(area), snr=float(snr))


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    path = argv[0] if len(argv) >= 1 else 'Data/Cell_29_integrated/1p0GPa.xy'

    x, y = read_xy(path)
    if len(x) == 0:
        print('No data read from', path)
        return 1

    y_norm = normalize(y)

    # light SG smoothing
    y_sg = savgol_filter(y_norm, window_length=11, polyorder=3)

    # baseline: wide SG (original approach)
    wide = savgol_filter(y_norm, window_length=501 if len(y_norm) > 501 else (len(y_norm)//2*2+1), polyorder=3)
    residual = y_sg - wide

    # 1) original find_peaks on residual
    p1, props1 = detect_find_peaks(residual, prominence=0.015, distance=8)
    summarize_and_print('original_residual_find_peaks', x, residual, p1)

    # 2) AsLS baseline -> residual2
    try:
        baseline_asls = asls_baseline(y_sg, lam=1e6, p=0.01, niter=10)
        residual2 = y_sg - baseline_asls
        p2, props2 = detect_find_peaks(residual2, prominence=0.01, distance=8)
        summarize_and_print('asls_residual_find_peaks', x, residual2, p2)
    except Exception as e:
        print('AsLS failed:', e)

    # 3) matched filter on smoothed intensity
    resp = matched_filter_response(y_sg, kernel_std=15, kernel_len=121)
    # detect peaks on response (use relative threshold)
    th = np.percentile(resp, 90)
    p3, props3 = detect_find_peaks(resp, prominence=(th*0.1), distance=8)
    summarize_and_print('matched_filter_response', x, resp, p3)

    # 4) CWT multi-scale
    resp_cwt, mat = cwt_response(y_sg, widths=np.arange(1, 80))
    p4, props4 = detect_find_peaks(resp_cwt, prominence=np.percentile(resp_cwt, 75)*0.2, distance=8)
    summarize_and_print('cwt_response', x, resp_cwt, p4)

    # Plot results
    basename = os.path.splitext(os.path.basename(path))[0]
    outdir = os.path.join('outputs', 'peak_detection')
    methods = [
        ('residual_orig', residual, p1, {'baseline': wide}),
    ]
    if 'residual2' in locals():
        methods.append(('residual_asls', residual2, p2, {'baseline': baseline_asls}))
    methods.append(('matched_resp', resp, p3, None))
    methods.append(('cwt_resp', resp_cwt, p4, None))
    plot_results(outdir, basename, x, y_norm, methods)

    # Merge peaks across methods and compute metrics
    merged = merge_peaks([p1, p2 if 'p2' in locals() else np.array([], dtype=int), p3, p4], distance=8)
    print('\nMerged peaks:', merged)
    metrics = [compute_peak_metrics(x, y_norm, int(mi)) for mi in merged]
    # save metrics
    csv_out = os.path.join(outdir, f"{basename}_merged_peaks.csv")
    os.makedirs(outdir, exist_ok=True)
    with open(csv_out, 'w') as f:
        f.write('index,pos,height,area,snr\n')
        for m in metrics:
            f.write(f"{m['index']},{m['pos']},{m['height']},{m['area']},{m['snr']}\n")
    print('Saved merged peak metrics to', csv_out)

    # Simple grid search: vary matched kernel std and find_peaks prominence
    grid = []
    kernel_stds = [5, 10, 15, 25]
    prominences = [0.005, 0.01, 0.015, 0.02]
    for ks in kernel_stds:
        resp_g = matched_filter_response(y_sg, kernel_std=ks, kernel_len=121)
        for prom in prominences:
            p_g, _ = detect_find_peaks(resp_g, prominence=prom, distance=8)
            merged_g = merge_peaks([p1, p_g, p4], distance=8)
            grid.append((ks, prom, len(p_g), len(merged_g)))
    grid_out = os.path.join(outdir, f"{basename}_grid_search.csv")
    with open(grid_out, 'w') as f:
        f.write('kernel_std,prominence,matched_peaks,merged_peaks\n')
        for row in grid:
            f.write(','.join(map(str, row)) + '\n')
    print('Saved grid search results to', grid_out)

    # Print a short table of peaks (first few) for each method
    print('\nSummary (first 10 peaks indices for each):')
    print('original:', p1[:10])
    print('asls   :', p2[:10] if 'p2' in locals() else [])
    print('matched:', p3[:10])
    print('cwt    :', p4[:10])

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
