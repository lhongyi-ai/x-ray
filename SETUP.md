# Setup instructions — macOS (Miniforge)

These steps create a Python environment appropriate for running the notebooks (pyFAI/TIFF processing, plotting, and data analysis). GSAS-II is a separate, compiled package with platform-specific binaries and is covered in the GSAS-II section below.

1) Install Miniforge (recommended) for macOS if you don't have conda/mamba:

```bash
# Download and run installer from https://github.com/conda-forge/miniforge
# Example (x86_64 or arm64 as appropriate):
bash ~/Downloads/Miniforge3-MacOSX-$(uname -m).sh
```

2) Create and activate the environment from `environment.yml`:

```bash
cd /path/to/x-ray
conda env create -f environment.yml
conda activate uotexrd
```

3) Install any pip-only packages (optional):

```bash
pip install -r requirements.txt
```

4) Register the environment as a Jupyter kernel (so notebooks can select it):

```bash
python -m ipykernel install --user --name uotexrd --display-name "Python (uotexrd)"
```

5) Validate core imports inside the activated environment:

```bash
python - <<'PY'
import importlib
modules = ['numpy','scipy','pandas','matplotlib','tifffile','pyFAI','fabio']
for m in modules:
    try:
        importlib.import_module(m)
        print(m, 'OK')
    except Exception as e:
        print(m, 'FAIL', e)
PY
```

GSAS-II and refinements
- - -
The notebooks `10a`–`12` and `09` expect an installation of GSAS-II with its compiled binary modules (e.g. `pyspg`, `pypowder`). GSAS-II is platform-specific and may require building or installing prebuilt packages for macOS.

Recommended approach:
- Install GSAS-II following the official instructions: https://subversion.xray.aps.anl.gov/trac/pyGSAS/wiki/Installation
- On macOS you may need to build from source or use a compatible binary distribution. After installing, ensure the GSAS-II package directory (the parent that contains the `GSASII` package and the `GSASII-bin` folder) is discoverable by Python (sys.path) when the `uotexrd` kernel is active.

Once GSAS-II is in place, run the notebooks in `notebooks/10a*` and `notebooks/10b*` to discover and/or repair the GSAS-II kernel and validate imports.

Dioptas
- - -
Dioptas is a GUI tool used by some notebooks for visual QA. It is optional. Install Dioptas separately if you need to open calibration TIFFs interactively.

Notes and troubleshooting
- - -
- If you are on Apple Silicon (arm64), prefer Miniforge for arm64 or create an x86_64 env only if you need x86 builds.
- GSAS-II compiled binaries (.pyd/.so) must match your Python ABI. If refinements fail with import errors, run `notebooks/10a_GSASII_environment_preflight_kernel_finder.ipynb` to locate a compatible kernel, and `notebooks/10b_GSASII_environment_repair_and_kernel_setup.ipynb` for automated environment repair attempts.
- If any import fails during validation, paste the error here and I will help resolve it.

Alternative (community conda package)
- - -
If building from source is difficult on macOS/arm64, there is a community-packaged build you can use that bundles GSAS-II for macOS (arm64) via the `briantoby` channel. This is the fastest way to get GSAS-II working on Apple Silicon.

Commands (creates an isolated env named `gsas2`):

```bash
conda create -n gsas2 -c briantoby -c conda-forge python=3.13 gsas2main -y
conda activate gsas2
conda install -c conda-forge ipykernel -y
python -m ipykernel install --user --name gsas2 --display-name "Python (gsas2 GSAS-II)"
```

If the package directory is not automatically visible to Python (rare), add a `.pth` in the environment `site-packages` pointing to the installed `GSAS-II` directory. Example (adjust path if your conda root differs):

```bash
SITE_PKGS=$(python -c "import site, sys; print(site.getsitepackages()[0])")
echo "/opt/anaconda3/envs/gsas2/GSAS-II" > "$SITE_PKGS/gsas2.pth"
```

Quick import test:

```bash
conda run -n gsas2 python -c "import GSASII.GSASIIfiles; print('GSAS-II OK', GSASII.GSASIIfiles.__file__)"
```

Notes:
- This community package includes a ready-to-run GSAS-II tree and prebuilt `GSASII-bin` for macOS arm64; it avoids the need to compile `pyspg`/`pypowder` locally.
- If you need a pure source build (attempted earlier), expect to compile C/C++ extensions and resolve wxPython and other binary dependencies.

X-ray data finder
- - -
Use `scripts/find_xray_files.py` to browse and classify files in `Data/` by
category, cell, pressure, angle, material, extension, and special state.

List supported categories and aliases:

```bash
python scripts/find_xray_files.py --list-categories
```

Find the main 10 degree Cell 29 TIFF files:

```bash
python scripts/find_xray_files.py raw2d 10deg Cell_29
```

Browse one pressure point without dumping every refinement backup. When
`--pressure` is used, the script defaults to important files only:

```bash
python scripts/find_xray_files.py --pressure 9p8 --group-by category
python scripts/find_xray_files.py --pressure 1 --group-by category
```

Show every file at a pressure point, including backup/intermediate files:

```bash
python scripts/find_xray_files.py --pressure 1 --all --group-by category
```

Find integrated 1D patterns:

```bash
python scripts/find_xray_files.py --category integrated --group-by pressure
```

Find calibration files:

```bash
python scripts/find_xray_files.py calibration
```

Common category keywords include:
`raw2d`, `ring_filter`, `10deg`, `5deg`, `no_angle`, `calibration`,
`integrated`, `refinement`, `gsas`, `jana`, `cif`, `mask`, `preview`, and
`peaks`.

Grouped ring/spot overlays
- - -
`scripts/auto_spot_ring_filter.py` now assigns each detected spot to the
nearest detected ring radius. The spot CSV contains `ring_index`,
`ring_radius_px`, and `ring_delta_px`; `ring_index=-1` means the spot was not
within the configured tolerance of a detected ring.

Run one image and create a colored grouped overlay:

```bash
/opt/anaconda3/envs/uotexrd/bin/python scripts/auto_spot_ring_filter.py \
  "Data/Cell_29/1 GPa/UOTe-1GPa-10deg_rot_054.tif" \
  --poni Data/Calibration/CeO2_30keV_168mm_0deg_001.poni \
  --geometry poni \
  --micro-spot-z 4.2 \
  --ring-half-width 3.0 \
  --out-dir outputs/ring_spot_group_preview_054
```

The grouped overlay is written as `*_ring_spot_groups.png`. Rings are drawn in
different colors, and spots assigned to the same ring radius use the same color
with a different marker style.

Run the Cell 29 10 degree batch:

```bash
/opt/anaconda3/envs/uotexrd/bin/python scripts/batch_auto_spot_ring_filter.py \
  Data/Cell_29 \
  --include 10deg \
  --poni Data/Calibration/CeO2_30keV_168mm_0deg_001.poni \
  --geometry poni \
  --out-dir outputs/auto_ring_filter_batch_grouped_cell29_10deg \
  --micro-spot-z 4.2 \
  --ring-half-width 3.0 \
  --flat-output
```

Use `--spot-ring-tolerance` to control how close a spot radius must be to a
ring radius to be counted as part of that ring group. The default is `10 px`.

Integrated peak similarity matrices
- - -
Use `scripts/compare_integrated_peaks.py` to compare integrated `.xy` patterns
between frames. The script detects peaks in each `2theta-intensity` curve,
matches peaks across frames by 2theta position, then writes four correlation
matrices:

- `A_peak_roi_area_cosine_matrix.csv`: XDI-style peak ROI area correlation,
  using local integrated intensity around each matched peak group.
- `B_peak_presence_jaccard_matrix.csv`: peak exists/does not exist.
- `C_peak_position_rms_shift_matrix_deg.csv`: RMS 2theta shift for shared peaks.
- `D_spot_radius_azimuth_cosine_matrix.csv`: 2D spot radius/azimuth
  correlation using detected spot positions from `all_spots.csv`.
- `E_full_integrated_pattern_pearson_matrix.csv`: full integrated `.xy`
  pattern Pearson correlation using the whole 2theta-intensity curve.

The script also keeps auxiliary outputs with the `aux_*` prefix, such as
`aux_peak_intensity_cosine_matrix.csv`,
`aux_full_pattern_pearson_matrix.csv`, and small-peak-only matrices for
comparison. Main A/B/C/D/E files are no longer duplicated under old names.

Run Cell 29 integrated frames:

```bash
MPLCONFIGDIR=/Users/stanley/x-ray/.matplotlib \
/opt/anaconda3/envs/uotexrd/bin/python scripts/compare_integrated_peaks.py \
  Data/Cell_29_integrated \
  --out-dir outputs/frame_peak_similarity_cell29
```

Run all integrated Cell 14 and Cell 29 frames:

```bash
MPLCONFIGDIR=/Users/stanley/x-ray/.matplotlib \
/opt/anaconda3/envs/uotexrd/bin/python scripts/compare_integrated_peaks.py \
  Data/Cell_14_integrated Data/Cell_29_integrated \
  --out-dir outputs/xdi_style_correlation_graphs \
  --spot-csv outputs/auto_ring_filter_batch_radius_groups_cell29_10deg_by_pressure_legend_outside/all_spots.csv
```

Useful tuning options:

- `--peak-match-tolerance 0.08`: 2theta tolerance, in degrees, for matching
  peaks between frames.
- `--prominence 1.5`: minimum normalized residual peak prominence. Lower this
  if weak peaks are missing; raise it if noise peaks are being included.
- `--bump-prominence 0.6`: minimum smoothed-curve prominence for broad weak
  local bumps. Lower this if shoulder-like small protrusions are still missing.
- `--min-peak-height 0.5`: require every accepted peak or bump to have positive
  residual height above the local background. Raise this if baseline wiggles are
  being marked as peaks.
- `--min-bump-rise 1.0`: require broad bumps to rise above both local sides.
  Raise this if shoulders or valleys near strong peaks are being marked.
- `--micro-prominence 1.5`: local prominence threshold for very fine peaks
  detected with a narrow smoothing window.
- `--min-micro-snr 0.5`: local robust SNR threshold for micro peaks. Raise this
  if noisy wiggles are included; lower it only if very subtle local maxima are
  still missing.
- `--small-peak-max-width 2.0`: maximum width for entries kept in
  `small_peak_table.csv`; this is intentionally wide enough to keep small
  broad bumps, not only sharp peaks.
- `--min-two-theta 2.0`: ignore very-low-angle background before peak finding.
- `--roi-half-width 0.06`: half-width in degrees for integrating peak ROI area.
- `--spot-radius-bin 25` and `--spot-azimuth-bin 30`: binning for 2D spot
  radius/azimuth correlation.
