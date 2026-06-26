"""
Demo: pipeline JSON -> two IFC4 files (framing off / framing on), then validate.

Source priority:
  1. Upstream pipeline demo outputs if present (wall-extract / panel-decompose /
     framing-synth examples) — the real end-to-end chain.
  2. The bundled examples/input_walls.json + input_framing.json (self-contained).

Writes examples/demo_walls.ifc (walls + openings) and examples/demo_framing.ifc
(walls + framing assemblies), and reports ifcopenshell validation for both.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from validate_ifc import main as validate_ifc  # noqa: E402

from aec_ifc_export import export_ifc  # noqa: E402

HERE = Path(__file__).parent.parent
EXAMPLES_DIR = HERE / "examples"
ROOT = HERE.parent


def _load_inputs() -> tuple[list[dict], dict, list[dict], dict]:
    """Return (walls, openings_map, framings, panels_map) from upstream or bundled."""
    we_walls = ROOT / "wall-extract" / "examples" / "demo_output.json"
    we_open = ROOT / "wall-extract" / "examples" / "demo_openings.json"
    pd_panels = ROOT / "panel-decompose" / "examples" / "demo_panels.json"
    fs_framing = ROOT / "framing-synth" / "examples" / "demo_framing.json"

    if we_walls.exists() and pd_panels.exists() and fs_framing.exists():
        print("Using upstream pipeline demo outputs.")
        walls = json.loads(we_walls.read_text())
        openings = json.loads(we_open.read_text()) if we_open.exists() else {}
        panels = {p["id"]: p for p in json.loads(pd_panels.read_text())["panels"]}
        framings = json.loads(fs_framing.read_text())["framings"]
        return walls, openings, framings, panels

    print("Upstream outputs not found — using bundled examples/.")
    walls_data = json.loads((EXAMPLES_DIR / "input_walls.json").read_text())
    fr_data = json.loads((EXAMPLES_DIR / "input_framing.json").read_text())
    return (
        walls_data["walls"],
        walls_data.get("openings", {}),
        fr_data["framings"],
        fr_data["panels"],
    )


def main() -> None:
    walls, openings, framings, panels = _load_inputs()

    # Keep only framings whose panel resolves to a wall in this dataset, so the
    # Wall -> Panel -> Member decomposition is complete (no floating assemblies).
    # The upstream framing-synth demo bundles a couple of synthetic panels whose
    # parent walls are not part of the real ResPlan wall set; drop those here.
    wall_ids = {w["id"] for w in walls}
    framings = [
        f for f in framings
        if (panels.get(f.get("panel_id")) or {}).get("parent_wall") in wall_ids
    ]
    print(f"{len(walls)} walls, {len(openings)} openings, {len(framings)} framing assemblies")

    walls_ifc = EXAMPLES_DIR / "demo_walls.ifc"
    export_ifc(walls, openings=openings, out_path=str(walls_ifc))
    print(f"Wrote {walls_ifc} (walls + openings)")

    framing_ifc = EXAMPLES_DIR / "demo_framing.ifc"
    export_ifc(walls, openings=openings, framing=framings, panels=panels, out_path=str(framing_ifc))
    print(f"Wrote {framing_ifc} (walls + framing assemblies)")

    print("\nValidating:")
    rc = validate_ifc(str(walls_ifc)) + validate_ifc(str(framing_ifc))
    if rc:
        raise SystemExit("IFC validation reported errors")


if __name__ == "__main__":
    main()
