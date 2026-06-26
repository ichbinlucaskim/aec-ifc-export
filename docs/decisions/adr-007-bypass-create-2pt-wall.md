# ADR-007: Bypass create_2pt_wall; set wall placement ourselves

**Status:** Accepted (2026-06-16)

## Context

IfcOpenShell 0.8.x `create_2pt_wall` mixes units when `is_si=False` on a
millimetre model: it converts `p1` to SI metres but leaves `p2` in millimetres,
so the wall axis `v = p2 − p1` is computed across mixed units and collapses to the
world-origin→endpoint direction. Result: 6 of 10 walls in the end-to-end model
rendered **diagonal** (e.g. `[0.781, 0.625]`) although the input floor plan is
orthogonal. Our `walls.py` passed correct endpoints; the bug is inside the
library. Full evidence and reproduction: `docs/KNOWN_LIBRARY_ISSUES.md` LIB-001.

Wall *positions* were correct; only the *rotation* was wrong. Framing members were
already correct (they use our own `_panel_world_matrix`), so walls and framing
disagreed.

## Decision

Stop calling `create_2pt_wall`. Set the wall `ObjectPlacement` ourselves:

- origin = `wall.start` (world mm),
- local X = `(end − start)` normalized (the wall length direction),
- local Z = world up `(0,0,1)`, local Y = Z × X,

via `edit_object_placement(..., is_si=False)` with a millimetre matrix — the
**same** consistent mm placement path the framing members already use. The wall
body is built with `add_wall_representation`, whose length/height/thickness are SI
metres (the API scales to the file unit), so they are passed as `mm / 1000`
(plain `float` — numpy floats break its point-list builder).

## Consequences

- Walls are axis-aligned for orthogonal input; **walls and framing now agree**.
- One fewer reliance on a fragile library placement helper; placement logic is
  uniform across walls and framing (a single mental model: our own explicit mm
  matrices).
- Openings still void correctly (`IfcRelVoidsElement` is a relationship to the
  wall element, unaffected by swapping the body-representation call).
- Guarded by a golden orthogonality + agreement assertion
  (`test_walls_are_axis_aligned`, `test_framing_matches_wall_direction`).
- **This is the second IfcOpenShell 0.8.x placement quirk we have bypassed** (the
  first was the relative-placement 1000× issue, ADR-005). The emerging pattern:
  **prefer our own explicit mm placement matrices over the library's placement
  helpers in 0.8.x**, and verify any geometry-API unit behavior in isolation
  first (here, `add_wall_representation` takes SI metres — confirmed before use).

## Sources

- IfcOpenShell source `ifcopenshell/api/geometry/create_2pt_wall.py` (the
  `is_si=False` branch; see LIB-001).
- buildingSMART IFC4.3 `IfcWallStandardCase` — the wall axis must be parallel to
  the X or Y axis for an orthogonal wall.
