# Opening-Not-Cutting-Wall Diagnosis

## Symptom
`IfcRelVoidsElement` present (3), but each wall body is a plain
`IfcExtrudedAreaSolid` with no baked boolean; a viewer shows the wall covering
the opening. Framing leaves the gap correctly.

## TL;DR — two distinct findings
1. **The void IS applied by full IFC processors and is standard-correct.**
   `IfcRelVoidsElement` *implies* a boolean subtraction; the wall body is meant to
   stay a plain solid. IfcOpenShell's geom engine cuts a real hole (wall-005 →
   16 verts vs 8 for a plain wall). So `boolean: False` in the body is **expected,
   not a bug**. A viewer that shows the wall covering the opening is rendering the
   **IFC4 Reference View** way (no implicit booleans) — see Step 2.
2. **There is a separate real geometric defect: the opening only PARTIALLY
   penetrates the wall** (110 mm of a 171 mm wall → a 60 mm notch, not a
   through-hole), because `add_wall_representation` offsets the wall body to one
   side of the placement line while the opening is centred on that line.

## Step 1 — Opening geometry: VALID

| opening | body | profile (mm) | depth (mm) | world origin | placement |
|---|---|---|---|---|---|
| door_0 | `IfcExtrudedAreaSolid` | 760 × 221 | 2032 | (3800, 1520, 0) | ✓ |
| door_1 | `IfcExtrudedAreaSolid` | 760 × 221 | 2032 | (1900, 3040, 0) | ✓ |
| window_0 | `IfcExtrudedAreaSolid` | 760 × 221 | 1200 | (6840, 1520, 900) | ✓ |

Each opening has a correctly-sized solid (760 along wall × 221 through wall,
extruded by the clear height) and a valid placement on its host wall. The void
volumes exist and are positioned correctly.

## Step 2 — Standard + tool expectation

**buildingSMART IFC4.3 `IfcRelVoidsElement` [[1]](#sources):** *"an objectified
relationship between a building element and one opening element that creates a
void… This relationship **implies a boolean operation of subtraction** between the
geometric bodies."* For `RepresentationIdentifier = 'Body'`, *"the Body shape
representation of the opening **has to be subtracted from the body shape
representation of the voided element** — implicit Boolean difference."*

**IfcOpenShell `add_feature` docstring (installed source) [[2]](#sources):** *"your
wall will still be a rectangular prism with no hole in it, and a separate opening
element will have a box… The opening element will **automatically perform a
geometric boolean operation to cut out the wall's geometry**."*

So the **canonical (implicit-boolean) model** is: wall body = plain solid +
`IfcOpeningElement` Body + `IfcRelVoidsElement`. That is exactly what we emit, and
**IfcOpenShell's geom engine applies it** — wall-005 tessellates to a real window
hole at the correct location (rim verts at y ∈ [1.14, 1.90] m, z ∈ [0.9, 2.1] m):

```
wall-005 (HasOpenings=1): 16 verts / 28 faces   <- hole present
wall-004 (HasOpenings=0):  8 verts / 12 faces   <- plain box
```

**The catch — IFC4 Reference View [[1]](#sources):** *"for use cases where boolean
operations should be avoided (such as in the IFC4 Reference View), an alternative
way of using IfcRelVoidsElement **without implying a Boolean difference** was
defined"* — i.e. the hole is pre-cut into the body (a `NetBody`). Many lightweight
viewers (very likely the one used here) implement the **Reference View**, which
does **not** apply implicit booleans, so they render the wall's plain `Body`
as-is → the wall covers the opening. Full processors (IfcOpenShell, Solibri, etc.)
apply the implicit boolean and show the hole.

## Step 3 — Effect of the create_2pt_wall removal: NONE on this

`create_2pt_wall` *also* called `add_wall_representation` internally for the body,
so the diagonal-wall fix (ADR-007) did **not** change the wall body footprint or
the opening behaviour. The void behaviour (plain Body + relationship) is identical
before and after. The partial-penetration issue below is **pre-existing**.

Op-order is fine: in `export_wall` the body is assigned before
`feature.add_feature` runs in `openings.py` (walls are exported first, then
openings voided), and the implicit-boolean model does not require re-running
anything when the body is set. The void is not lost to ordering.

## Step 4 — Framing cross-check: opening data is CORRECT

wall-005's panel studs sit at world-Y `[0, 400, 800, 2000, 2400, 2800, 3040]` —
**none** in the window band `[1140, 1900]`. Framing correctly leaves the gap, so
the opening position/size is right; only the wall **body-cut** is wrong.

## Root cause

Two things, only the second is a true geometry bug:

1. **Viewer/MVD mismatch (not our bug, but the visible symptom).** We use the
   implicit-boolean model (`Body` + `IfcRelVoidsElement`), which is standard and
   is applied by full processors. Reference-View viewers skip implicit booleans
   and show the plain solid → "wall covers opening." To be viewer-independent the
   hole must be **baked into the body**.
2. **Partial penetration (real defect).** `add_wall_representation` builds the
   footprint at thickness **Y ∈ [0, 171]** — offset to one side, so the wall
   placement **origin is the wall face, not its centreline**. The opening is
   placed at that origin and centred through-wall (depth 221 = 171 + 50 overshoot),
   spanning Y ∈ [−110.5, +110.5]. Overlap with the wall `[0, 171]` is only
   `[0, 110.5]` → **110 mm cut, 60 mm uncut** — a notch, not a through-hole.
   Even where the boolean IS applied, the wall covers the window from the far face.

## Proposed fix (describe — do NOT implement)

- **Make the opening fully penetrate (fixes #2).** Either (a) offset the opening's
  through-wall position to the wall **centreline** (`+thickness/2` along the wall
  normal) so the centred opening spans the full thickness, or (b) make the opening
  through-wall depth clearly exceed the wall on **both** faces (the IfcOpenShell
  canonical example uses opening thickness `0.4` for a `0.2` wall). Option (b) is
  simplest and robust to the body offset.
- **Make the cut viewer-independent (fixes #1).** Bake the subtraction into the
  wall body — represent it as an `IfcBooleanClippingResult` (or a pre-cut
  `NetBody`) subtracting the opening solids — so Reference-View viewers also show
  the hole. The standard permits both; for portfolio "opens-anywhere" robustness,
  baking is the safer choice.
- **Regression assertion (golden).** Tessellate each opening's host wall via the
  geom engine and assert a **true through-hole**: the wall has > 8 verts AND the
  cut spans the **full wall thickness** at the opening (hole rim verts reach
  *both* wall faces, not a partial notch). Optionally assert the wall body is an
  `IfcBooleanClippingResult` if we adopt baking.

## Sources
1. buildingSMART IFC4.3 — `IfcRelVoidsElement` (implies boolean subtraction; Body
   subtracted; Reference-View no-implicit-boolean alternative).
   https://standards.buildingsmart.org/IFC/RELEASE/IFC4/ADD1/HTML/schema/ifcproductextension/lexical/ifcrelvoidselement.htm
2. IfcOpenShell 0.8.x — `ifcopenshell/api/feature/add_feature.py` docstring
   ("your wall will still be a rectangular prism with no hole in it… automatically
   perform a geometric boolean operation").

## Status — no logic changed (diagnosis only).
