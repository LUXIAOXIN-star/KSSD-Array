#!/usr/bin/python3
"""Match the supplied reference layout using the unchanged, audited 12 points.

Only saved plotting data are read. No scientific target or benchmark is run.
Error bars are drawn AFTER the white-filled markers so short SD caps stay visible.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
_mpl_config = tempfile.TemporaryDirectory(prefix='kssd-figure3-mpl-')
os.environ.setdefault('MPLCONFIGDIR', _mpl_config.name)
sys.dont_write_bytecode = True
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

METHODS = ['KSSD-Array', 'GreedyMini-derived (prefix12)', 'seq-hash']
COLORS = dict(zip(METHODS, ['#0072B2', '#E69F00', '#009E73']))
MARKERS = dict(zip(METHODS, ['o', '^', 's']))
PANELS = [('Synthetic', 21, '(a)'), ('Human chr1', 21, '(b)'),
          ('Synthetic', 31, '(c)'), ('Human chr1', 31, '(d)')]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True, help='Published figure3_data.csv')
    parser.add_argument('--manifest', type=Path, required=True, help='Published sha256.tsv')
    parser.add_argument('--out', type=Path, required=True, help='Output directory; existing files are never replaced')
    args = parser.parse_args()
    out = args.out.resolve()
    outputs = [out / ('Figure3_runtime_density.' + ext) for ext in ['png', 'svg', 'pdf']]
    outputs.append(out / 'Figure3_redraw_validation.json')
    for output in outputs:
        if output.exists():
            raise SystemExit('Refusing to overwrite: ' + str(output))
    source = args.data.resolve()
    with args.manifest.open(newline='') as handle:
        manifest_rows = list(csv.DictReader(handle, delimiter='\t'))
    entries = [r for r in manifest_rows if r.get('relative_path') == 'figure3_data.csv']
    if len(entries) != 1 or sha(source) != entries[0].get('sha256'):
        raise SystemExit('figure3_data.csv SHA-256 does not match the supplied manifest')
    with source.open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 12 or set((r['input'], int(r['k']), r['method']) for r in rows) != {
        (dataset, k, method) for dataset, k, _ in PANELS for method in METHODS}:
        raise SystemExit('Expected one observation per dataset, k, and method (12 total)')
    if any(int(r['w']) != 20 or int(r['independent_processes']) != 5 for r in rows):
        raise SystemExit('Unexpected window size or number of processes')
    out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({
        'font.family': 'DejaVu Sans', 'font.size': 10,
        'mathtext.fontset': 'dejavusans', 'axes.titlesize': 11.5,
        'axes.labelsize': 11, 'xtick.labelsize': 9.5, 'ytick.labelsize': 9.5,
        'axes.edgecolor': '#333333', 'axes.linewidth': 0.8,
        'axes.facecolor': 'white', 'figure.facecolor': 'white',
        'savefig.facecolor': 'white', 'pdf.fonttype': 42,
        'ps.fonttype': 42, 'svg.fonttype': 'none',
    })
    # Same aspect ratio as the displayed 756 x 546 reference.
    fig, axs = plt.subplots(2, 2, figsize=(7.56, 5.46), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.105, right=0.980, bottom=0.130, top=0.855,
                        wspace=0.150, hspace=0.300)
    axs = axs.ravel()
    records = []
    for index, (ax, (dataset, k, letter)) in enumerate(zip(axs, PANELS)):
        ax.set_title(dataset + r', $k$ = ' + str(k), pad=8)
        ax.text(0.035, 0.955, letter, ha='left', va='top', transform=ax.transAxes,
                fontsize=11, fontweight='bold', color='black')
        for method in METHODS:
            row = next(r for r in rows if r['input'] == dataset and int(r['k']) == k and r['method'] == method)
            x = float(row['mean_runtime_ms']); y = float(row['sampling_density_percent'])
            sd = float(row['runtime_sd_ms'])
            assert math.isfinite(sd) and sd >= 0
            assert 250 <= x - sd <= x + sd <= 375 and 7.3 <= y <= 9.9
            # First draw the original hollow marker with its white face.
            marker = ax.plot(x, y, marker=MARKERS[method], markersize=5.5,
                             markerfacecolor='white', markeredgecolor=COLORS[method],
                             markeredgewidth=1.1, linestyle='none', zorder=4)[0]
            # Then put the TRUE horizontal SD interval and its small end caps
            # above that white face. Do not enlarge or displace a small SD.
            error = ax.errorbar(x, y, xerr=sd, yerr=None, fmt='none',
                                ecolor=COLORS[method], elinewidth=0.8,
                                capsize=2.2, capthick=0.8, zorder=5)
            assert error.has_xerr and not error.has_yerr
            for cap in error.lines[1]:
                assert cap.get_zorder() > marker.get_zorder()
            for collection in error.lines[2]:
                assert collection.get_zorder() > marker.get_zorder()
            segments = error.lines[2][0].get_segments()
            assert len(segments) == 1
            assert math.isclose(float(segments[0][0][0]), x - sd, rel_tol=1e-12)
            assert math.isclose(float(segments[0][1][0]), x + sd, rel_tol=1e-12)
            assert all(math.isclose(float(point[1]), y, rel_tol=1e-12) for point in segments[0])
            records.append(dict(input=dataset, k=k, method=method, x=x, y=y,
                                unchanged_sample_sd_ms=sd, true_x_interval=[x-sd, x+sd],
                                marker_zorder=4, error_zorder=5,
                                capsize_pt=2.2, sd_multiplier=1.0))
        ax.set_xlim(250, 375); ax.set_ylim(7.3, 9.9)
        ax.set_xticks([250, 275, 300, 325, 350, 375])
        ax.set_yticks([7.5, 8.0, 8.5, 9.0, 9.5])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(axis='x', bottom=True, labelbottom=index >= 2,
                       direction='out', length=3.5, width=0.7, color='#333333', pad=3)
        ax.tick_params(axis='y', left=True, labelleft=index % 2 == 0,
                       direction='out', length=3.5, width=0.7, color='#333333', pad=3)
        ax.grid(True, color='#ececec', linewidth=0.7)
        ax.set_axisbelow(True)
    xlabel = fig.text(0.5, 0.048, 'Mean runtime (ms)', fontsize=11, ha='center', va='center')
    ylabel = fig.text(0.023, 0.495, 'Sampling density (%)', fontsize=11,
                      rotation=90, ha='center', va='center')
    handles = [Line2D([], [], linestyle='none', color=COLORS[m], marker=MARKERS[m],
                      markerfacecolor='white', markeredgecolor=COLORS[m],
                      markeredgewidth=1.1, markersize=5.5, label=m) for m in METHODS]
    legend = fig.legend(handles=handles, labels=METHODS, loc='upper center',
                        bbox_to_anchor=(0.545, 0.995), ncol=3, frameon=False,
                        fontsize=10.5, handlelength=1.1, handletextpad=0.5,
                        columnspacing=1.6, borderaxespad=0.6)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    width, height = fig.canvas.get_width_height()
    artists = [xlabel, ylabel, legend]
    for ax in axs:
        artists += [ax.title] + list(ax.texts) + ax.get_xticklabels() + ax.get_yticklabels()
    for artist in artists:
        if artist.get_visible():
            box = artist.get_window_extent(renderer)
            assert min(box.x0, box.y0) >= 0 and box.x1 <= width and box.y1 <= height, 'Text clipped'
    for ext in ['png', 'svg', 'pdf']:
        fig.savefig(str(out / ('Figure3_runtime_density.' + ext)), format=ext,
                    dpi=600, transparent=False)
    validation = dict(status='PASS', data_sha256=sha(source), manifest=str(args.manifest.resolve()),
                      points=12, canvas_inches=[7.56, 5.46], reference_display_pixels=[756,546],
                      PNG_pixels=[4536,3276], dpi=600,
                      visual_style_only_from_reference=True, scientific_values_only_from_saved_CSV=True,
                      errorbar_layering='white marker first, true xerr and caps above marker',
                      added_threshold_or_baseline_lines=False, vertical_errors=False,
                      caption_created=False, per_point=records,
                      source_script_sha256=sha(Path(__file__)), output=str(out))
    (out / 'Figure3_redraw_validation.json').write_text(json.dumps(validation, indent=2)+'\n')
    plt.close(fig)
    print(json.dumps(dict(status='PASS', output=str(out), points=12,
                         SD_rescaled=False, data_sha256=sha(source)), indent=2))


if __name__ == '__main__':
    main()
