# aec-ifc-export

**Convert the AEC pipeline's JSON (walls, panels, framing) into a valid IFC4
file that opens in any BIM viewer — no Revit required.**

This is the interoperability layer: it proves the pipeline's output is
consumable by standard BIM / manufacturing systems. The professional workflow is
*synthesise → export to IFC → inspect in a viewer → then sequence assembly* —
this repo is the export-and-inspect step, so framing can be visually verified
before anything downstream builds on it.

```
wall-extract / panel-decompose / framing-synth  →  aec-ifc-export  →  .ifc
        (JSON outputs)                              (IFC4)            (BIM viewer)
```

## The differentiator — framing as `IfcElementAssembly`

A panelized stud wall is a *premanufactured assembly*, the canonical use of
`IfcElementAssembly` in IFC4.3. Each framing member is an `IfcMember`:

| Pipeline member | IFC entity | `PredefinedType` |
|---|---|---|
| stud | `IfcMember` | **STUD** (real `IfcMemberTypeEnum` value) |
| plate (bottom/top) | `IfcMember` | **PLATE** (real enum value) |
| header / king / jack / sill / cripple | `IfcMember` | MEMBER (no dedicated enum) |
| panel | `IfcElementAssembly` | — (members aggregated via `IfcRelAggregates`) |
| opening | `IfcOpeningElement` | voided into the wall via `IfcRelVoidsElement` |

See [`docs/decisions/adr-002-framing-as-elementassembly.md`](docs/decisions/adr-002-framing-as-elementassembly.md)
for the mapping rationale and the `IfcWallElementedCase` trade-off.

## Quick start

```bash
make setup     # sync LICENSE, install aec-schema + this package (+ ifcopenshell)
make test      # pytest — structural validation, no GUI needed
make lint      # ruff
make demo      # write demo_walls.ifc AND demo_framing.ifc, then validate both
make validate  # ifcopenshell.validate on demo_framing.ifc
```

```python
from aec_ifc_export import export_ifc

# Framing OFF — walls + openings only
export_ifc(walls, openings=omap, out_path="walls.ifc")

# Framing ON — also IfcElementAssembly per panel + IfcMember per member
export_ifc(walls, openings=omap, framing=framings, panels=pmap,
           out_path="framing.ifc")
```

Both modes produce IFC that passes `ifcopenshell.validate` with **0 errors**.
On the real ResPlan demo: 53 walls, 15 voided openings, 58 panel assemblies,
637 members (327 STUD / 174 PLATE / 136 MEMBER).

## Install note

`ifcopenshell` ships PyPI wheels for 0.8.x on CPython 3.11/3.12
(`pip install ifcopenshell`). If a platform lacks a wheel, use the conda-forge
build instead: `conda install -c conda-forge ifcopenshell`.

## Design decisions

- [ADR-001](docs/decisions/adr-001-spatial-structure.md) — mandatory
  Project→Site→Building→Storey spatial structure.
- [ADR-002](docs/decisions/adr-002-framing-as-elementassembly.md) — panel →
  `IfcElementAssembly`, members → `IfcMember` (the key mapping).
- [ADR-003](docs/decisions/adr-003-mm-to-m-units.md) — millimetre length unit
  throughout (matches the mm pipeline JSON; no mm→m conversion).
- [ADR-004](docs/decisions/adr-004-data-model-completeness.md) — data-model
  completeness (Wall→Panel→Member decomposition, material slot, owner history)
  vs. engineering scope.
- [ADR-005](docs/decisions/adr-005-geometry-placement.md) — wall representations
  assigned; framing placed in the panel **world** frame. Corrects an earlier
  geometry claim: that check only inspected **local** verts and missed collapsed
  world placement — geometry is now asserted in **world** coordinates.
- [ADR-007](docs/decisions/adr-007-bypass-create-2pt-wall.md) — bypass
  `create_2pt_wall` (an IfcOpenShell 0.8.x unit bug rotated walls diagonal); set
  the wall placement with our own mm matrix. See
  [`docs/KNOWN_LIBRARY_ISSUES.md`](docs/KNOWN_LIBRARY_ISSUES.md) (LIB-001).
- [ADR-008](docs/decisions/adr-008-opening-through-hole-baked-boolean.md) —
  openings cut **through** the wall and are **baked** into the body
  (`IfcBooleanResult`) so the hole shows across viewers. Verify geometry with the
  `ifcopenshell.geom` **iterator**, not `create_shape`.

## Scope boundary (ML/SWE vs. engineering)

This exporter guarantees a **complete, internally consistent IFC data model**; it
does **not** perform structural verification. Specifically:

- **Material is a documented placeholder** (`"Softwood Lumber"`, marked
  *PLACEHOLDER — species/grade TBD by engineer*). Species and structural grade
  are a **domain-expert** (architect / structural engineer) input — we provide
  the `IfcMaterial` slot and association, not an engineered spec.
- **Member sizing follows the prescriptive IRC simplification**
  (framing-synth `framing_rules.md`), not engineered structural design.
- The exporter ensures **decomposition** (`IfcWall → IfcElementAssembly →
  IfcMember`), a **material slot**, and **owner history** — it makes no
  load-bearing-capacity or adequacy judgments (those are PE-stamped). See
  [ADR-004](docs/decisions/adr-004-data-model-completeness.md).

## Limitations

- Geometry is **prismatic extrusions** (rectangle profiles) — accurate cross-
  sections and lengths, not milled detail.
- Placement assumes **axis-aligned** members (extruded along start→end).
- **IFC4**, not IFC4X3, for the widest viewer compatibility.
- Openings void into **walls** (wall-relative position); the framing assemblies
  carry their own member geometry. Rooms → `IfcSpace` is available
  (`spaces.export_space`) but not wired into the default export (the pipeline
  carries room ids, not polygons).

Imports [`aec-schema`](../aec-schema), `ifcopenshell`, `numpy`.
