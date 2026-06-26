# Defect B — Diagnosis (on the REAL pipeline output)

## Headline: Defect B is actually FIXED. The "still broken" symptom is a
## measurement bug (matrix major-order) in the inspection script.

Members **are** placed at correct world positions on the real 13-panel pipeline
output. The reported "members collapse to Y≈63mm" comes from reading IfcOpenShell's
`shape.transformation.matrix` in the **wrong major-order** (row-major) — the exact
code in this prompt's Step 1. Read correctly (column-major), members span the full
building footprint, the same as the walls.

## Authoritative evidence (independent of the geom engine)

`ifcopenshell.util.placement.get_local_placement()` resolves the full
`IfcLocalPlacement` chain — it is the ground truth for where an element sits,
with no geometry-engine or matrix-convention involved:

| element | resolved WORLD placement | expected (from panel/wall) | correct? |
|---|---|---|---|
| `wall-005` | `[6840, 0, 0]` | wall at world x=6840, runs in Y | ✓ |
| `wall-005-panel-000-m001` (plate) | `[6840, 0, 0]` | follows its wall to x=6840 | ✓ |
| `wall-005-panel-000-m017` (sill) | `[6840, 1140, 938]` | x=6840, along Y, z=sill 938 | ✓ |
| `wall-003-panel-000-m003` (stud) | `[0, 0, 2400]` | wall at origin, stud at z | ✓ |

Members follow their parent walls **including orientation** — the sill on the
Y-running wall-005 runs along world Y at x=6840. Defect B's fix works.

## The measurement bug

`shape.transformation.matrix` (IfcOpenShell 0.8.x) is a flat 16-float list in
**column-major** order — the translation is at indices **12,13,14**. For
`wall-005-panel-000-m001`:

```
matrix = [0,0,-1,0,  -1,0,0,0,  0,1,0,0,  6.84,0,0,1]   # translation = [6.84,0,0] at [12:15]
```

| convention | how translation is read | member world X (m001) | result |
|---|---|---|---|
| **A** `reshape(4,4)` then `M[:3,3]` (this prompt's Step 1) | indices 3,7,11 = `[0,0,0]` | **−1.5** | collapse (WRONG) |
| **B** `reshape(4,4).T` then `M[:3,3]` (column-major) | indices 12,13,14 = `[6.84,0,0]` | **6.8** | matches placement ✓ |

Whole-model world boxes confirm it:

| convention | WALL span (m) | MEMBER span (m) |
|---|---|---|
| A (buggy) | `[3.8, 3.33, 2.44]` | `[3.67, 0.14, 2.44]` ← "collapsed" |
| **B (correct)** | `[9.79, 8.96, 2.44]` | `[6.98, 5.84, 2.44]` ← **spread, full footprint** |

## Per-panel trace (correct, convention B)

| panel | parent wall dir | panel.start (world) | member m001 world | correct? |
|---|---|---|---|---|
| wall-000-panel-000 | X-run | (0, 0) | [0, 0, 0] | ✓ |
| wall-004-panel-000 | X-run | (3800, 0) | [3800, 0, 0] | ✓ |
| wall-003-panel-000 | Y-run | (0, 0) | [0, 0, …] | ✓ |
| wall-005-panel-000 | Y-run | (6840, 0) | [6840, 0, 0] | ✓ |

`panel["start"]` carries true **world** coordinates (they match the parent wall's
`start`/`end`), so `_panel_world_matrix` builds the right origin + rotation, and
members land correctly.

## Why walls "looked spread" but members "didn't" under the buggy read

The asymmetry that made the bug look real:

- **Walls** (`create_2pt_wall`) bake the wall's extent into the **local verts** —
  `wall-005` local verts span X `0 → 3.04m` (its 3040mm length). So even with the
  translation misread (collapsed to ~0), walls still show ~3m of spread from their
  local geometry alone → "looks spread."
- **Members** (`_export_member` → extruded profile + `edit_object_placement`) have
  **tiny local verts** (profile ±0.019m, extruded along local Z); *all* of their
  world position lives in the transform **translation** (slots 12–14). Misreading
  the translation collapses them to their ~local profile size → "looks collapsed."

So "walls spread, members don't" is a pure artifact of reading the translation from
the wrong matrix slots — not a placement defect.

## Why the test passed — and it's not a fixture fluke

`tests/test_geometry_placement.py::_world_verts` uses
`np.array(shape.transformation.matrix).reshape(4, 4).T` — the **correct**
column-major convention. So the test is valid, not a coincidence of fixture
coordinates: it would also pass on the real pipeline output (members do spread).

The legitimate gap the prompt raises still stands, though: **no test ever opens the
real `floorplan-pipeline/examples/out/model.ifc`.** A golden end-to-end test would
have let anyone confirm spread directly and would pre-empt exactly this kind of
"is it really fixed?" round-trip.

## Empty member m017 (secondary) — re-characterized

The report calls m017 an "empty/too-short member (~84mm)". That is **wrong**:

- `wall-005-panel-000-m017` is a **sill**, section **2x4**, **length 760mm** —
  not degenerate. Its IFC body is a valid `IfcExtrudedAreaSolid` (Depth 760,
  profile 38×89), and its placement is orthonormal (det=1.0) at world
  `[6840, 1140, 938]`. The data is correct.
- Yet `ifcopenshell.geom.create_shape` returns **0 verts** for it (the only such
  member, 1/155). Its sibling sill on an X-wall tessellates fine. This is an
  IfcOpenShell **geom-engine quirk** for this particular valid placement, **not** a
  data defect and **not** a short member. Most viewers will still render it from the
  (valid) IFC.
- The ~84mm members the report conflated this with are `m020`/`m021` —
  `cripple_stud`, 2x6, **84mm** — which are short-but-valid cripples above the
  header; they tessellate fine.

## Proposed fix (describe — NOT implemented)

1. **Defect B: no code fix needed** — members are placed correctly. The fix already
   shipped (`_panel_world_matrix` + absolute world placement, ADR-005) works on the
   real pipeline.
2. **Fix the measurement, not the model.** Any inspection/diagnostic that reads
   `shape.transformation.matrix` must treat it as **column-major**
   (`reshape(4,4).T`, or index translation at `[12:15]`), or better, use
   `ifcopenshell.util.placement.get_local_placement()` which is convention-proof.
   Correct this prompt's Step 1 snippet and any ad-hoc scripts.
3. **GOLDEN regression test (the real gap).** Add a test that runs
   `floorplan-pipeline` end-to-end and asserts, in **world** coordinates (correct
   convention), that the **MEMBER world box overlaps the WALL world box** within a
   tolerance (same footprint) — proving framing follows walls on the real artifact,
   not just a fixture. Put it in floorplan-pipeline (it needs the full chain).
4. **m017 smoke guard.** Add a check that every member tessellates to >0 verts (or
   has positive `Depth` and an orthonormal placement). Since m017's data is valid,
   investigate the IfcOpenShell geom-engine case separately (possibly a version/
   settings issue); track as low-priority — it does not affect the IFC's
   correctness, only the geom iterator.

## Definition of Done (diagnosis) — status
- [x] Discrepancy reproduced on the REAL model.ifc (wall box vs member box) — and
      shown to be a measurement artifact, not a placement defect.
- [x] Per-panel trace for X-running and Y-running walls (authoritative placements).
- [x] Root cause pinned: column-major vs row-major read of
      `shape.transformation.matrix` (translation at indices 12–14).
- [x] Explained why walls' path "looked" right and framing's "didn't" (local-verts
      vs translation-carried world position).
- [x] Explained the test (correct convention, valid) + proposed a real-pipeline
      golden test.
- [x] m017 re-characterized: valid 760mm sill, geom-engine 0-verts quirk, not 84mm.
- [x] No logic changed.
