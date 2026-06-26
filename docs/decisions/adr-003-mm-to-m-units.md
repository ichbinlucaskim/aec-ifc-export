# ADR-003: Millimetre length unit throughout

**Status:** Accepted (2026-06-16; supersedes the original "mm→m conversion" decision)

## Context

The initial implementation intended to convert mm→m at the export boundary (the
IFC SI base length unit is the metre). In practice `ifcopenshell.api.unit.assign_unit`
defaults to a **millimetre** unit (`IFCSIUNIT(.LENGTHUNIT.,.MILLI.,.METRE.)`),
and the conversion was applied inconsistently:

- wall coordinates, panel geometry, and extrusion depths ended up in millimetres
  (correct — `create_2pt_wall`/`add_profile_representation` convert SI input to
  the file unit), but
- member profile dimensions came from a metres table (`SECTION_DIMS_M`, e.g.
  2x4 = `(0.038, 0.089)`) and were written **raw** into `IfcRectangleProfileDef`,
  which performs no unit conversion.

Result: profile dims like `0.221` were read as `0.221 mm`, so every stud / plate
/ header had a ~0.2 mm cross-section and rendered as an invisible thin line in
BIM viewers — while sitting at the correct position and length.

## Decision

Author the **entire IFC in millimetres**. Keep
`IFCSIUNIT(.LENGTHUNIT.,.MILLI.,.METRE.)`. Every geometric value — coordinates,
extrusion depths, **and** profile dimensions — is emitted in mm, numerically
identical to the upstream pipeline JSON (which is mm). There is **no mm→m
conversion anywhere** in the geometry path:

- `SECTION_DIMS_MM` (38 × 89 …) replaces `SECTION_DIMS_M`.
- `edit_object_placement(..., is_si=False)` takes the mm placement matrices as-is.
  (Walls originally used `create_2pt_wall(..., is_si=False)`; that helper was later
  replaced by an explicit mm placement matrix — see ADR-007.)
- Member/opening bodies are built with `_geom.rectangle_extrusion`, which creates
  the `IfcRectangleProfileDef` + `IfcExtrudedAreaSolid` directly in mm (rather
  than the high-level `add_profile_representation`, whose `depth` is treated as
  SI metres).

## Rationale

- The pipeline JSON is mm; matching it removes a conversion layer that can (and
  did) drift.
- IFC fully supports a millimetre length unit; many professional BIM tools author
  in mm — this is standard-compliant.
- Fixing the single inconsistent path (profiles) by unifying on mm is lower-risk
  than converting all coordinates/extrusions to metres.

## Consequences

- `IfcRectangleProfileDef` dims are now mm (2x4 → 38 × 89), consistent with
  wall/stud coordinates and 2438 mm extrusions.
- Framing members render at the correct 38 mm cross-section in viewers.
- Any future export code must emit mm; `tests/test_units.py` guards against a
  metres remnant (profile dims ≥ 1.0, unit = MILLI METRE, stud thickness ~38 mm).

## References

- `ifcopenshell.api.unit.assign_unit` (defaults to mm), `create_2pt_wall`,
  `edit_object_placement` `is_si` flag (IfcOpenShell 0.8.x)
- buildingSMART IFC4 `IfcUnitAssignment` / `IfcSIUnit` (MILLI METRE)
