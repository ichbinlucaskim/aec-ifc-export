# ADR-006: Authoritative placement in tests + golden end-to-end

**Status:** Accepted (2026-06-16)

## Context

Defects A (NULL wall bodies) and B (framing stacked at origin) were fixed
(ADR-005) and verified. But a follow-up "Defect B is still broken" report sent the
project on a round-trip — and the report was **wrong**: it was a *measurement* bug,
not a placement bug.

The false alarm came from reading IfcOpenShell's `shape.transformation.matrix` as
**row-major** (`np.array(shape.transformation.matrix).reshape(4, 4)[:3, 3]`). That
matrix is **column-major** — the translation lives at flat indices 12–14. Read
row-major, the translation is misread and members appear to collapse to the origin,
while walls (whose extent is baked into local verts by `create_2pt_wall`) still
look spread. The authoritative resolver
(`ifcopenshell.util.placement.get_local_placement`) showed members were correct all
along (e.g. wall-005's framing at world `[6840, …]`, following its Y-running wall).

This is the project's recurring failure mode in a new guise: a *hand-rolled* check
disagreed with the real artifact. Previously it was schema-validation-as-proxy
(units, NULL walls); this time it was an ad-hoc matrix read.

## Decision

1. **Authoritative placement only.** All world-coordinate assertions use
   `ifcopenshell.util.placement.get_local_placement(element.ObjectPlacement)`
   (returns a 4×4 matrix, translation in column 3) — never a hand-rolled
   `transformation.matrix` reshape. The shared helper
   `floorplan-pipeline/tests/_world.py` (`world_origin`, `world_box`) is the only
   sanctioned path. Where full geometric extent is needed (verts), the
   `transformation.matrix` must be treated as **column-major** (`reshape(4,4).T`)
   and 0-vert shapes skipped.

2. **Golden end-to-end test on the REAL artifact.** `floorplan-pipeline/tests/
   test_golden_endtoend.py` runs the actual pipeline to `model.ifc` on disk and
   asserts, via the authoritative resolver: no NULL wall representation; members
   occupy the wall world footprint (per-axis span ≥ 60% of the walls' — ~1.0 on the
   example, so a true collapse to ~0.02 fails hard); panel assemblies at distinct
   world locations; building span > 3 m; IFC validates 0 errors. This closes the
   long-standing "the real end-to-end output is never asserted" gap.

3. **m017 empty-tessellation quirk: tracked, not fixed.** `…wall-005-panel-000-m017`
   is a **valid 760 mm 2x4 sill** — valid `IfcExtrudedAreaSolid` (Depth 760, dir
   (0,0,1), profile 38×89) and an orthonormal placement at world `[6840,1140,938]` —
   yet `ifcopenshell.geom.create_shape` returns 0 verts for it (1/155, an engine
   quirk). The data is sound, so we do **not** alter geometry. Instead:
   (a) all verts-based tooling skips 0-vert shapes (no NaN/crash), and
   (b) a characterization test bounds empty tessellations (≤ 2) and asserts the
   affected members still have valid placements — so a regression that grows the
   count is caught.

## Consequences

- The "is it really fixed?" question is now answerable by a single test on the real
  artifact, using the convention-proof resolver.
- The column-major gotcha is documented in `_world.py` and `DEFECT_B_DIAGNOSIS.md`,
  so the false alarm cannot recur via a copy-pasted reshape.
- One IfcOpenShell geom-engine quirk (m017) is bounded and visible rather than
  silently load-bearing.

## References

- IfcOpenShell `ifcopenshell.util.placement.get_local_placement` (4×4, column-3
  translation); `shape.transformation.matrix` (flat 16, column-major).
- aec-ifc-export ADR-005 (geometry placement fix); `DEFECT_B_DIAGNOSIS.md`.
