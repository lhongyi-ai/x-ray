#!/usr/bin/env python3
"""Search and categorize X-ray diffraction files in the Data folder.

Examples:
  python scripts/find_xray_files.py raw2d 10deg Cell_29
  python scripts/find_xray_files.py --pressure 9p8 --important
  python scripts/find_xray_files.py --category integrated --pressure 1p5
  python scripts/find_xray_files.py --list-categories
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


MATERIALS = ("UOTe", "CeO2", "Al2O3", "Ne", "UTeO", "W")
SPECIAL_FLAGS = ("rot", "noNe", "decomp", "2min", "firstfit", "firstpass", "refined", "refine")
REFINEMENT_EXTS = {
    ".fou",
    ".gpx",
    ".l51",
    ".l61",
    ".l62",
    ".l63",
    ".l64",
    ".l65",
    ".l66",
    ".l69",
    ".l70",
    ".lst",
    ".m40",
    ".m41",
    ".m50",
    ".m70",
    ".m80",
    ".m81",
    ".m83",
    ".m85",
    ".m90",
    ".m91",
    ".m95",
    ".prf",
    ".r40",
    ".r41",
    ".r50",
    ".r51",
    ".r90",
    ".ref",
    ".s40",
    ".s41",
    ".s70",
    ".s83",
    ".tmp",
    ".usd",
    ".z51",
    ".z90",
}

CATEGORY_ALIASES = {
    "raw": "raw2d",
    "raw2d": "raw2d",
    "2d": "raw2d",
    "image": "raw2d",
    "images": "raw2d",
    "ring": "ring_filter",
    "spot": "ring_filter",
    "filter": "ring_filter",
    "ring_filter": "ring_filter",
    "main": "ring_filter",
    "10deg": "10deg",
    "10degree": "10deg",
    "5deg": "5deg",
    "5degree": "5deg",
    "0deg": "no_angle",
    "no_angle": "no_angle",
    "base": "no_angle",
    "calib": "calibration",
    "calibration": "calibration",
    "integrated": "integrated",
    "xy": "integrated",
    "refinement": "refinement",
    "refinements": "refinement",
    "gsas": "gsas",
    "jana": "jana",
    "cif": "cif",
    "mask": "mask",
    "preview": "preview",
    "png": "preview",
    "peaks": "peaks",
    "reflections": "peaks",
}

CATEGORY_DESCRIPTIONS = {
    "raw2d": "Raw 2D detector images: Data/Cell_*/*/*.tif",
    "ring_filter": "Main ring/spot filtering inputs: UOTe TIFF files",
    "10deg": "Files with 10deg in the filename",
    "5deg": "Files with 5deg in the filename",
    "no_angle": "TIFF files without an explicit *deg angle marker",
    "calibration": "Calibration files: Calibration folder, CeO2, .poni",
    "integrated": "Integrated 1D patterns: *_integrated/*.xy",
    "refinement": "Refinement outputs: GSAS/Jana/refined folders and refinement extensions",
    "gsas": "GSAS-II refinement files",
    "jana": "Jana refinement files",
    "cif": "Reference phase CIF files",
    "mask": "Detector mask files",
    "preview": "PNG preview/plot files",
    "peaks": "Calculated reflection/peak files",
}


@dataclass
class FileRecord:
    path: str
    category: str
    tags: list[str]
    material: str | None
    cell: str | None
    pressure: str | None
    pressure_value: float | None
    angle: str | None
    ext: str
    important: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find categorized X-ray diffraction files under Data/."
    )
    parser.add_argument(
        "query",
        nargs="*",
        help=(
            "Free keywords/categories, e.g. raw2d 10deg Cell_29 UOTe. "
            "All query terms must match."
        ),
    )
    parser.add_argument("--data-root", type=Path, default=Path("Data"))
    parser.add_argument("--category", action="append", default=[], help="Category filter; repeatable.")
    parser.add_argument("--material", action="append", default=[], help="Material filter; repeatable.")
    parser.add_argument("--cell", action="append", default=[], help="Cell filter, e.g. Cell_29.")
    parser.add_argument("--pressure", action="append", default=[], help="Pressure filter, e.g. 9p8 or 9p8GPa.")
    parser.add_argument("--angle", action="append", default=[], help="Angle filter: 10deg, 5deg, no_angle.")
    parser.add_argument("--ext", action="append", default=[], help="Extension filter, e.g. tif or .xy.")
    parser.add_argument(
        "--important",
        action="store_true",
        help="Show only key files, useful for pressure-based browsing.",
    )
    parser.add_argument("--all", action="store_true", help="Disable automatic important-only pressure view.")
    parser.add_argument(
        "--group-by",
        choices=("none", "pressure", "cell", "category", "ext"),
        default="none",
    )
    parser.add_argument("--limit", type=int, default=0, help="Limit number of printed files.")
    parser.add_argument("--json", action="store_true", help="Print JSON records.")
    parser.add_argument("--list-categories", action="store_true")
    return parser.parse_args()


def normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def pressure_to_value(token: str) -> float | None:
    text = token.lower().replace(",", "p").replace("gpa", "").replace("goa", "")
    text = text.replace(" ", "")
    if not re.fullmatch(r"\d+(?:p\d+|\.\d+)?", text):
        return None
    return float(text.replace("p", "."))


def pressure_label_from_token(token: str, value: float) -> str:
    token = token.lower().replace(",", "p").replace(".", "p")
    if "p" in token:
        return f"{token}GPa"
    if abs(value - round(value)) < 1e-9:
        return f"{int(round(value))}GPa"
    return f"{str(value).replace('.', 'p')}GPa"


def parse_pressure(path: Path) -> tuple[str | None, float | None]:
    text = str(path).replace(",", "p")
    matches = re.findall(r"(\d+(?:p\d+|\.\d+)?)\s*G[PpOo][Aa]", text)
    if not matches:
        return None, None
    value = pressure_to_value(matches[-1])
    if value is None:
        return None, None
    return pressure_label_from_token(matches[-1], value), value


def parse_cell(path: Path) -> str | None:
    for part in path.parts:
        match = re.fullmatch(r"Cell[_-](\d+).*", part)
        if match:
            return f"Cell_{match.group(1)}"
    return None


def parse_material(path: Path) -> str | None:
    text = str(path)
    for material in MATERIALS:
        pattern = rf"(?<![A-Za-z0-9]){re.escape(material)}(?![A-Za-z0-9])"
        if re.search(pattern, text, re.IGNORECASE):
            return material
    return None


def parse_angle(path: Path) -> str | None:
    name = path.name.lower()
    if "10deg" in name:
        return "10deg"
    if "5deg" in name:
        return "5deg"
    if path.suffix.lower() in {".tif", ".tiff"}:
        return "no_angle"
    return None


def is_refinement(path: Path) -> bool:
    text = str(path).lower()
    return (
        "refinement" in text
        or "refined" in text
        or "refine" in text
        or "gsas" in text
        or "jana" in text
        or path.suffix.lower() in REFINEMENT_EXTS
    )


def choose_category(path: Path) -> str:
    ext = path.suffix.lower()
    text = str(path).lower()
    parts = {part.lower() for part in path.parts}
    if "calibration" in parts or "ceo2" in text or ext == ".poni":
        return "calibration"
    if path.name == "UOTe-calc_reflections.txt":
        return "peaks"
    if ext == ".cif":
        return "cif"
    if ext == ".mask":
        return "mask"
    if ext == ".xy" and any(part.endswith("_integrated") for part in path.parts):
        return "integrated"
    if is_refinement(path):
        return "refinement"
    if ext in {".tif", ".tiff"} and parse_cell(path):
        return "raw2d"
    if ext == ".png":
        return "preview"
    return ext.lstrip(".") or "other"


def build_tags(path: Path, category: str) -> list[str]:
    tags = {category, path.suffix.lower().lstrip(".")}
    text = str(path)
    material = parse_material(path)
    cell = parse_cell(path)
    pressure, _ = parse_pressure(path)
    angle = parse_angle(path)
    if material:
        tags.add(material)
    if cell:
        tags.add(cell)
    if pressure:
        tags.add(pressure)
    if angle:
        tags.add(angle)
    if path.suffix.lower() in {".tif", ".tiff"} and material == "UOTe":
        tags.add("ring_filter")
    for flag in SPECIAL_FLAGS:
        if re.search(re.escape(flag), text, re.IGNORECASE):
            tags.add(flag)
    if "gsas" in text.lower():
        tags.add("GSAS")
    if "jana" in text.lower():
        tags.add("jana")
    if "integrated" in text.lower():
        tags.add("integrated")
    if "calibration" in text.lower():
        tags.add("calibration")
    if "refinement" in text.lower() or "refined" in text.lower() or "refine" in text.lower():
        tags.add("refinement")
    return sorted(tags, key=str.lower)


def is_important(path: Path, category: str) -> bool:
    ext = path.suffix.lower()
    name = path.name.lower()
    if category in {"raw2d", "calibration", "integrated", "cif", "mask", "peaks", "preview"}:
        return True
    if category == "refinement":
        if ".bak" in name or name.endswith("_useonly.tmp"):
            return False
        if ext in {".gpx", ".lst", ".prf", ".ref"}:
            return True
        return False
    return False


def index_files(root: Path) -> list[FileRecord]:
    records: list[FileRecord] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == ".DS_Store":
            continue
        category = choose_category(path)
        pressure, pressure_value = parse_pressure(path)
        record = FileRecord(
            path=str(path),
            category=category,
            tags=build_tags(path, category),
            material=parse_material(path),
            cell=parse_cell(path),
            pressure=pressure,
            pressure_value=pressure_value,
            angle=parse_angle(path),
            ext=path.suffix.lower(),
            important=is_important(path, category),
        )
        records.append(record)
    return records


def canonical_category(value: str) -> str:
    return CATEGORY_ALIASES.get(normalize_text(value), value)


def term_matches(record: FileRecord, term: str) -> bool:
    raw = term
    norm = normalize_text(term)
    category = canonical_category(term)
    if category in record.tags or category == record.category:
        return True
    p_value = pressure_to_value(term)
    if p_value is not None and record.pressure_value is not None:
        return abs(record.pressure_value - p_value) < 1e-6
    haystacks = [record.path, record.category, record.material or "", record.cell or "", record.pressure or ""]
    haystacks.extend(record.tags)
    return any(norm in normalize_text(value) or raw.lower() in value.lower() for value in haystacks)


def filter_records(records: list[FileRecord], args: argparse.Namespace) -> list[FileRecord]:
    out = records
    categories = [canonical_category(x) for x in args.category]
    if categories:
        out = [r for r in out if any(c == r.category or c in r.tags for c in categories)]
    if args.material:
        wanted = {normalize_text(x) for x in args.material}
        out = [r for r in out if r.material and normalize_text(r.material) in wanted]
    if args.cell:
        wanted = {normalize_text(x) for x in args.cell}
        out = [r for r in out if r.cell and normalize_text(r.cell) in wanted]
    if args.pressure:
        wanted_values = [pressure_to_value(x) for x in args.pressure]
        out = [
            r
            for r in out
            if r.pressure_value is not None
            and any(v is not None and abs(r.pressure_value - v) < 1e-6 for v in wanted_values)
        ]
    if args.angle:
        wanted = {canonical_category(x) for x in args.angle}
        out = [r for r in out if r.angle in wanted or any(w in r.tags for w in wanted)]
    if args.ext:
        wanted_ext = {x if x.startswith(".") else f".{x}" for x in args.ext}
        out = [r for r in out if r.ext in wanted_ext]
    for term in args.query:
        out = [r for r in out if term_matches(r, term)]
    if args.important or (args.pressure and not args.all):
        out = [r for r in out if r.important]
    return sorted(out, key=sort_key)


def sort_key(record: FileRecord) -> tuple:
    pressure = record.pressure_value if record.pressure_value is not None else 1e9
    category_rank = {
        "raw2d": 0,
        "integrated": 1,
        "preview": 2,
        "calibration": 3,
        "peaks": 4,
        "cif": 5,
        "mask": 6,
        "refinement": 7,
    }.get(record.category, 99)
    angle_rank = {"10deg": 0, "5deg": 1, "no_angle": 2, None: 3}.get(record.angle, 3)
    return (record.cell or "", pressure, category_rank, angle_rank, record.path)


def group_key(record: FileRecord, group_by: str) -> str:
    if group_by == "pressure":
        return record.pressure or "[no pressure]"
    if group_by == "cell":
        return record.cell or "[no cell]"
    if group_by == "category":
        return record.category
    if group_by == "ext":
        return record.ext or "[no ext]"
    return ""


def print_categories() -> None:
    print("Available categories / aliases:")
    for category, description in CATEGORY_DESCRIPTIONS.items():
        aliases = sorted(k for k, v in CATEGORY_ALIASES.items() if v == category)
        alias_text = ", ".join(aliases)
        print(f"  {category:12s} {description}")
        print(f"               aliases: {alias_text}")


def print_records(records: list[FileRecord], group_by: str, limit: int) -> None:
    shown = records[:limit] if limit else records
    print(f"Matched {len(records)} file(s).")
    if limit and len(records) > limit:
        print(f"Showing first {limit}.")
    last_group = None
    for record in shown:
        if group_by != "none":
            current = group_key(record, group_by)
            if current != last_group:
                print(f"\n[{current}]")
                last_group = current
        bits = [record.category]
        if record.cell:
            bits.append(record.cell)
        if record.pressure:
            bits.append(record.pressure)
        if record.angle:
            bits.append(record.angle)
        if record.material:
            bits.append(record.material)
        if record.important:
            bits.append("important")
        print(f"{record.path}    # {', '.join(bits)}")


def main() -> None:
    args = parse_args()
    if args.list_categories:
        print_categories()
        return
    records = index_files(args.data_root)
    matches = filter_records(records, args)
    if args.json:
        print(json.dumps([asdict(record) for record in matches], indent=2))
    else:
        print_records(matches, args.group_by, args.limit)


if __name__ == "__main__":
    main()
