# ADR-005: Geometry placement — wall representations and panel world frames

**Status:** Accepted (2026-06-16)

## Context

The exported IFC passed `ifcopenshell.validate` (0 errors) but was geometrically
collapsed: in a viewer all walls were invisible and every panel's framing stacked
at the origin. Two distinct defects were found (diagnosis:
`floorplan-pipeline/docs/COORDINATE_DIAGNOSIS.md`):

- **Defect A — NULL wall bodies.** `walls.py` called
  `ifcopenshell.api.geometry.create_2pt_wall(...)` and discarded its return. In
  IfcOpenShell 0.8.x that call *returns* an `IfcShapeRepresentation` and does
  **not** attach it, so every `IfcWall.Representation` was `None` — no 3D body.
- **Defect B — framing stacked at the origin.** `framing.py` placed each
  `IfcMember` at its **panel-local** coordinate and never applied the panel's
  **world** position. framing-synth emits panel-local member coordinates (x along
  the panel, z up, y≈0); the panel's world location lives in
  `panel["start"]`/`["end"]`. So every panel's framing landed in the same origin
  band regardless of which wall it belonged to.

## Honest correction to the earlier "renders as solid" claim

The prior ADR-003 work verified the *cross-section* fix by tessellating a member
and reading `shape.geometry.verts`. Those are **local** coordinates (the world
transform lives separately in `shape.transformation`), so they always sit near the
origin — that check could **not** have detected Defects A or B, and the earlier
"renders as solid / production-grade geometry" framing was overstated. Geometry
correctness must be checked in **world** coordinates. The new regression tests do
exactly that.

## Decision

1. **Defect A — assign the wall representation.** Capture the `create_2pt_wall`
   return and attach it:
   ```python
   rep = ifcopenshell.api.geometry.create_2pt_wall(model, element=wall, ..., is_si=False)
   ifcopenshell.api.geometry.assign_representation(model, product=wall, representation=rep)
   ```

2. **Defect B — place members in the panel's world frame.** Build a panel
   world transform `_panel_world_matrix(panel)` (origin = `panel["start"]` in mm,
   local-X = the wall direction `start→end`, local-Z = up — **orientation, not
   just translation**, so panels on Y-running walls turn correctly) and place each
   member at `panel_world @ member_local`.

   Placement is set **before** the member is aggregated under the assembly, which
   makes it an **absolute world placement** (`PlacementRelTo = None`). This was a
   deliberate choice: setting the placement *after* aggregating under an assembly
   whose own placement is relative-to-wall hit a unit quirk in 0.8.x's relative
   placement computation (a 1000× error). Absolute world placements are
   unambiguous, render correctly, and keep the `IfcRelAggregates` decomposition
   (Wall → assembly → members) intact for the tree view.

Units are untouched — millimetres throughout, `is_si=False` (ADR-003).

## Consequences

- 0 walls with NULL representation; every wall renders.
- Framing spreads across the building in world coordinates (verified: members span
  ~6.8 m × 5.7 m on the integrated demo, vs. the collapsed 3.6 m × 0.04 m before).
- Panels on differently-oriented walls are laid out along their wall.
- New regression tests in `tests/test_geometry_placement.py` assert, in **world**
  coordinates: no NULL wall representation, every wall tessellates, framing world-
  spread exceeds a single panel, panel assemblies sit at distinct locations, and a
  Y-wall panel is oriented along Y. These guard the exact blind spot (schema-valid
  but geometrically collapsed) that `ifcopenshell.validate` does not cover — the
  same class as the earlier mm/m unit bug.

## References

- IfcOpenShell 0.8.x `ifcopenshell.api.geometry` (`create_2pt_wall`,
  `assign_representation`, `edit_object_placement`).
- buildingSMART IFC4.3 `IfcLocalPlacement` / `IfcAxis2Placement3D` (relative
  placement chain), `IfcWall`, `IfcElementAssembly`.
