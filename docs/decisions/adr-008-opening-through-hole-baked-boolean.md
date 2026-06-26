# ADR-008: Opening voids — through-hole + baked boolean for viewer independence

**Status:** Accepted (2026-06-16)

## Context

Diagnosis (`OPENING_VOID_DIAGNOSIS.md`) found two issues with how openings cut
walls:

1. **Viewer mismatch.** `IfcRelVoidsElement` *implies* a boolean subtraction, which
   full IFC processors apply — but the **IFC4 Reference View** (what lightweight
   viewers like Open IFC Viewer implement) deliberately avoids implicit booleans
   and renders the wall's plain `Body` as-is, so the wall looks solid over the
   opening.
2. **Notch, not a through-hole.** `add_wall_representation` offsets the wall body
   to one face (thickness band local Y ∈ [0, thickness]), so the placement origin
   is the wall *face*. The opening was placed at that origin and centred
   through-wall, so it overlapped only ~half the thickness — a 60 mm notch leaving
   the far face solid.

## Decision

1. **Through-hole (openings.py).** Centre the opening on the wall thickness band
   (`+thickness/2` along the through-wall normal) and give the void a depth that
   exceeds **both** faces (`thickness + 2·margin`). The void now cuts cleanly
   through. Verified: hole-rim verts appear at **both** thickness faces (local Y
   min and max), not one.

2. **Bake the boolean (walls.py).** Subtract each opening's wall-local cut-out
   solid from the wall body via `ifcopenshell.api.geometry.add_boolean`
   (DIFFERENCE), so the body is an `IfcBooleanResult` with the hole **in the
   geometry** — visible even in Reference-View viewers that ignore the implicit
   boolean. The `IfcRelVoidsElement` relationship is kept for semantics; the two
   together render a clean through-hole with **no double-cut** (the second
   subtraction of an already-removed region is idempotent).

## The key lesson — `create_shape` is not the oracle; use the iterator

This fix took far longer than it should have because
`ifcopenshell.geom.create_shape(settings, wall)` returns **0 verts** for these
`add_wall_representation` bodies — making walls *look* invisible and booleans
*look* broken. That is an artifact of the single-element `create_shape` path, not
the data. The geometry **iterator**
(`ifcopenshell.geom.iterator(settings, model, include=[wall])`) — the path viewers
actually use — tessellates the same walls correctly (16–20 verts, true
through-holes). **All geometry assertions and debugging must use the iterator (or
`ifcopenshell.util.placement` for placement), never `create_shape` vert counts.**
This is the same class of measurement trap as the column-major matrix bug
(ADR-006): the artifact was fine; the *measurement* lied.

## Consequences

- Wall bodies of voided walls are `IfcBooleanResult` (3 in the example); openings
  are true through-holes (rim at both faces); `IfcRelVoidsElement` kept.
- `make validate` stays at 0 errors; units untouched (mm); walls still
  axis-aligned (ADR-007); no NULL wall representations.
- Regression tests (`tests/test_openings_geometry.py`, and the floorplan-pipeline
  golden `test_openings_cut_through_walls`) assert, **via the iterator**, that
  voided wall bodies are baked booleans and the holes reach both faces — a notch
  or a vanished wall fails.

## Sources

- buildingSMART IFC4.3 — `IfcRelVoidsElement` (implies boolean subtraction;
  Reference-View no-implicit-boolean alternative).
- IfcOpenShell 0.8.x — `ifcopenshell.api.feature.add_feature` docstring ("your
  wall will still be a rectangular prism with no hole in it… automatically perform
  a geometric boolean operation"); `ifcopenshell.api.geometry.add_boolean`;
  `ifcopenshell.geom.iterator`.
