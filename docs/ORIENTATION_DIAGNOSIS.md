# Wall Orientation Diagnosis (diagonal walls)

## Symptom
6/10 walls in the real `model.ifc` have a **diagonal** local X-axis (length
direction), e.g. wall-001 `[0.781, 0.625]`, despite the input floor plan being
orthogonal. buildingSMART IFC4.3 / `IfcWallStandardCase` expects the wall axis to
be a straight line; for an orthogonal plan it must be X- or Y-aligned. In a viewer
these walls lean at an angle and rooms don't close.

(The prompt sampled 5; the full set is **6** diagonal — it missed wall-006.)

## Step 1 — Are the input walls orthogonal? YES.

Every wall in `walls.json` (wall-extract → pipeline output) is exactly
axis-aligned (off-axis 0.00°): each has `dx == 0` or `dy == 0`. So the corruption
is **in export**, not upstream.

## Step 2 — Input direction vs IFC output xaxis

The IFC xaxis matches **`p2 / |p2|`** (direction from the *world origin* to the end
point) in **every** wall — NOT the true `(p2 − p1)` direction:

| wall | p1 (start) | p2 (end) | (p2−p1)norm (correct) | p2/\|p2\| | IFC xaxis | diag? |
|---|---|---|---|---|---|---|
| 000 | (0,0) | (3800,0) | (1,0) | (1,0) | (1.00,0.00) | ok |
| 001 | (3800,0) | (3800,3040) | (0,1) | (0.78,0.62) | (0.78,0.63) | **DIAG** |
| 002 | (0,3040) | (3800,3040) | (1,0) | (0.78,0.62) | (0.78,0.62) | **DIAG** |
| 003 | (0,0) | (0,3040) | (0,1) | (0,1) | (0.00,1.00) | ok |
| 004 | (3800,0) | (6840,0) | (1,0) | (1,0) | (1.00,0.00) | ok |
| 005 | (6840,0) | (6840,3040) | (0,1) | (0.91,0.41) | (0.91,0.41) | **DIAG** |
| 006 | (3800,3040) | (6840,3040) | (1,0) | (0.91,0.41) | (0.91,0.41) | **DIAG** |
| 007 | (3800,3040) | (3800,5700) | (0,1) | (0.55,0.83) | (0.55,0.83) | **DIAG** |
| 008 | (0,5700) | (3800,5700) | (1,0) | (0.56,0.83) | (0.56,0.83) | **DIAG** |
| 009 | (0,3040) | (0,5700) | (0,1) | (0,1) | (0.00,1.00) | ok |

The 4 "OK" walls are coincidences: their start sits on the relevant zero-axis, so
the corruption leaves the direction unchanged (see root cause).

## Step 3 — walls.py / create_2pt_wall orientation handling

`walls.py` passes the **correct** absolute endpoints:
`create_2pt_wall(..., p1=(start.x, start.y), p2=(end.x, end.y), is_si=False)`.
Reproduced in isolation: wall-001 with `p1=(3800,0), p2=(3800,3040)` → xaxis
`[0.781,0.625]` (diagonal). So the endpoints are right; the bug is **inside
`create_2pt_wall`**.

Reading `ifcopenshell/api/geometry/create_2pt_wall.py` (0.8.x):

```python
length = norm(p2_ - p1_)
if not is_si:
    length = convert_unit_to_si(length, si_conversion)
    ...
    # "No need to convert p2 as length is already calculated."
    p1_ = convert_unit_to_si(p1_, si_conversion)   # p1_ converted; p2_ NOT
    ...
v = p2_ - p1_                                       # MIXED UNITS
v /= norm(v)
matrix = [[v[0], -v[1], 0, p1_[0]], [v[1], v[0], 0, p1_[1]], ...]
```

**Root cause: an IfcOpenShell 0.8.x bug.** With `is_si=False`, it unit-converts
`p1_` to SI (× `si_conversion`) but **leaves `p2_` in project units**, then builds
the direction `v = p2_ − p1_` from **mixed units**. For a millimetre model
`si_conversion = 0.001`, so:

```
v = p2(mm) − p1×0.001  →  for wall-001: (3800,3040) − (3.8,0) = (3796.2, 3040)
                          normalized = (0.781, 0.625)   ← exactly the IFC xaxis
```

Verified numerically: `(p2 − p1·0.001)/‖·‖ = [0.781, 0.625]`, while the correct
`(p2 − p1)/‖·‖ = [0, 1]`. Since `p1·0.001 ≈ 0`, the result collapses to
**`p2/|p2|`** — the direction from the world origin — which is what the table shows.

The wall **origin** is unaffected (translation uses the fully-converted `p1_`
alone, which round-trips), so positions are correct and only the **rotation** is
wrong — matching the observation.

### What the diagonal walls share
A wall is corrupted unless its start lies on the axis it must stay parallel to:
- **Vertical** wall (dx=0): correct only if `p1.x == 0` (003, 009). Diagonal for
  x≠0 (001 @x3800, 005 @x6840, 007 @x3800).
- **Horizontal** wall (dy=0): correct only if `p1.y == 0` (000, 004). Diagonal for
  y≠0 (002 @y3040, 006 @y3040, 008 @y5700).

i.e. only walls touching the world origin lines `x=0` / `y=0` survive; every other
wall is rotated toward the origin.

## Step 4 — Does framing inherit the same bad direction? NO.

Framing members use a **different** code path — `framing._panel_world_matrix`,
which derives the panel frame from `panel.start→end` directly in NumPy (no
`is_si` conversion). For wall-001's panel the member length-directions are
**axis-aligned and correct**: bottom plate `[0,1,0]` (along the Y wall), studs
`[0,0,1]` (vertical). So:

- **Walls (`create_2pt_wall`) are diagonal/wrong; framing (`_panel_world_matrix`)
  is orthogonal/right.** They currently **disagree** — the framing layer is
  correct, the wall body is not. This is a **single root cause in one path**
  (`create_2pt_wall`), not a shared computation.

## Root cause (one line)
IfcOpenShell 0.8.x `create_2pt_wall(is_si=False)` converts `p1` to SI but not
`p2`, so the wall axis `v = p2 − p1` is computed across mixed units and collapses
to the direction from the world origin (`p2/|p2|`) for any wall not starting on
`x=0`/`y=0`. Walls only; framing is unaffected.

## Why the golden test missed it
`test_golden_endtoend.py` asserts the **bounding-box span** (member footprint ≥
60% of wall footprint) and panel **distinctness/positions** — not per-wall
**orientation**. A diagonal wall still spans a similar bbox, and the test reads
member positions (which are correct). There is **no orthogonality assertion** and
no check that the wall axis matches the input `start→end`.

## Proposed fix (describe — do NOT implement)

The endpoints we pass are correct; only `create_2pt_wall`'s internal unit handling
is broken. Minimal, robust options (do not depend on patching IfcOpenShell):

1. **Set the wall placement ourselves (preferred, mm-consistent).** Keep
   `add_wall_representation` for the body (length/height/thickness in mm), but
   replace the `create_2pt_wall` *placement* with our own
   `edit_object_placement(..., is_si=False)` using a correct mm matrix whose local
   X = `(p2 − p1)/‖p2 − p1‖` and origin = `p1` — exactly the consistent mm path
   already used for members. Verify `add_wall_representation`'s length unit in
   isolation first (it should match the mm model).
2. **Or pre-convert both endpoints to SI and call `is_si=True`** so the buggy
   `if not is_si` branch is skipped (`v = p2 − p1` then uses consistent units) —
   but this also changes how length/height/thickness are interpreted, so it needs
   careful unit verification across the mm model; option 1 is lower-risk.

Framing needs **no** change (it is already correct), but walls and framing should
be made to **agree** — fixing the wall path makes both orthogonal.

### Golden test additions (would have caught it)
- **Wall orthogonality:** for orthogonal input, assert every `IfcWall`'s local
  X-axis is axis-aligned: `min(|x|, |y|) < 1e-3` (via `get_local_placement`,
  authoritative).
- **Path agreement:** assert each wall's axis equals the `start→end` direction of
  its input wall, and that its framing members' length-directions are parallel/
  perpendicular to that same axis (walls and framing must agree).

## Secondary note
This is unrelated to the m017 empty-tessellation quirk (ADR-006); separate issue.

## Status — no logic changed (diagnosis only).
