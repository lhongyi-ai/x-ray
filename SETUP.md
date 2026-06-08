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
