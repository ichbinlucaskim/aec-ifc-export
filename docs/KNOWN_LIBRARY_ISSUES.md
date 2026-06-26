# Known Third-Party Library Issues

A log of confirmed bugs in dependencies that we work around, with reproduction
and rationale. Each entry: what, evidence, impact, workaround, status.

---

## LIB-001 — IfcOpenShell 0.8.x `create_2pt_wall` mixes units when `is_si=False`

**Component:** `ifcopenshell.api.geometry.create_2pt_wall`
**Version observed:** IfcOpenShell **0.8.5** (`pip show ifcopenshell`)
**Severity:** High for millimetre-authored models — silently rotates walls to
diagonal directions. Passes `ifcopenshell.validate` (schema-valid), so it is
invisible to schema validation.

### Symptom
On a millimetre model with `is_si=False`, walls whose start is **not** on the
relevant world-origin axis are rotated to a diagonal direction instead of being
axis-aligned. E.g. a vertical wall `start=(3800,0)`, `end=(3800,3040)` (true
direction `[0,1]`) gets local X-axis **`[0.781, 0.625]`**. Wall *positions*
(origins) are correct; only the *rotation* is wrong.

### Root cause (from reading the library source)
`…/ifcopenshell/api/geometry/create_2pt_wall.py`:

```python
length = float(np.linalg.norm(p2_ - p1_))
if not is_si:
    length = convert_unit_to_si(length, si_conversion)
    ...
    # "No need to convert p2 as length is already calculated."
    p1_ = convert_unit_to_si(p1_, si_conversion)   # p1_ converted; p2_ is NOT
    ...
v = p2_ - p1_                                       # <-- MIXED UNITS
v /= float(np.linalg.norm(v))
matrix = np.array([[v[0], -v[1], 0, p1_[0]], [v[1], v[0], 0, p1_[1]], ...])
```

In the `is_si=False` branch `p1_` is converted to SI metres (`× si_conversion`,
= `× 0.001` for a mm model) but **`p2_` is left in millimetres**. The wall axis
`v = p2_ − p1_` therefore subtracts mixed units. Because `p1_ × 0.001 ≈ 0`, the
direction collapses toward `p2 / ‖p2‖` — the world-origin→endpoint direction.

### Reproduction (isolated)
```python
import numpy as np
si = 0.001                      # mm -> SI scale for a mm model
p1 = np.array([3800., 0.]); p2 = np.array([3800., 3040.])
correct = (p2 - p1)        / np.linalg.norm(p2 - p1)         # [0., 1.]   (true)
buggy   = (p2 - p1 * si)   / np.linalg.norm(p2 - p1 * si)    # [0.781, 0.625]
```
`buggy` exactly matches the observed wall-001 local X-axis.

### Impact on this project
6 of 10 walls in the end-to-end `model.ifc` rendered diagonal; rooms did not
close. The 4 unaffected walls were the ones whose start sat on `x=0`/`y=0` (where
`p1 × 0.001 ≈ 0` leaves the direction intact). Framing was **unaffected** — it
uses our own `_panel_world_matrix` — so walls and framing disagreed.

### Workaround
Do **not** use `create_2pt_wall` for placement. We set the wall `ObjectPlacement`
ourselves: origin = `start`, local-X = `(end − start)` normalized, Z = up, in
millimetres via `edit_object_placement(..., is_si=False)` — the same consistent
mm path the framing uses. The body is built with `add_wall_representation`
(length/height/thickness passed as **metres** = mm/1000, since that API scales SI
input to the file unit). See `walls.py` and ADR-007.

### Upstream status
Not yet reported upstream. A minimal report is drafted here for later submission:

> **Title:** `create_2pt_wall(is_si=False)` produces diagonal walls on non-metre
> models — `p1` is unit-converted but `p2` is not.
> **Repro:** mm-unit `IfcProject`; `create_2pt_wall(p1=(3800,0), p2=(3800,3040),
> is_si=False)` → wall local X-axis `[0.781,0.625]` instead of `[0,1]`.
> **Cause:** in the `if not is_si` branch, `p1_` is converted via
> `convert_unit_to_si` but `p2_` is not (comment "No need to convert p2 as length
> is already calculated"); the subsequent `v = p2_ - p1_` mixes units.
> **Fix:** convert `p2_` as well (or compute `v` before converting `p1_`).

### Regression guard
`floorplan-pipeline/tests/test_golden_endtoend.py::test_walls_are_axis_aligned`
asserts every wall's local X-axis is axis-aligned for orthogonal input (a
diagonal regression fails hard), plus `test_framing_matches_wall_direction` for
wall/framing agreement.
