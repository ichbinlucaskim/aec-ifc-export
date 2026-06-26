# ADR-002 — Framing as IfcElementAssembly + IfcMember (the key mapping)

**Status:** Accepted (2026-06-16)

## Context

Representing a wall as a set of *discrete framing members* (studs, plates,
headers) is a genuinely non-trivial topic in IFC. There are two standard
options:

1. **`IfcWallElementedCase`** — the wall is itself a container that decomposes
   into its parts. The framing members become sub-parts of the wall element.
2. **`IfcElementAssembly`** — the panel is a standalone assembly that aggregates
   its members; the wall (if present) is a separate element.

The pipeline's unit of fabrication is the **panel** (panel-decompose output),
not the wall — a wall may split into several transport panels, and panels are
manufactured off-site as discrete prefabricated units.

## Decision

- **Panel → `IfcElementAssembly`.** buildingSMART IFC4.3 names *"premanufactured
  or precast elements"* as the canonical example of `IfcElementAssembly`. A
  panelized stud wall is exactly a premanufactured assembly, so this is the
  natural fit and keeps the panel independent of any wall container.
- **Member → `IfcMember`** with `PredefinedType` from `IfcMemberTypeEnum`:
  - `stud` → **`STUD`** ("vertical element in wall framing" — real enum value)
  - `plate` → **`PLATE`** ("head piece or sole plate" — real enum value)
  - `header` / `king` / `jack` / `sill` / `cripple` → **`MEMBER`**
    (no dedicated enum value exists; `MEMBER` is the generic linear element)
- **Members aggregate into the assembly** via
  `ifcopenshell.api.aggregate.assign_object` (`IfcRelAggregates`).
- **Assembly `PredefinedType` is left `NOTDEFINED`.** `IfcElementAssemblyTypeEnum`
  has no value naming a stud-wall panel (RIGID_FRAME, TRUSS, …); rather than
  force `USERDEFINED` (which also requires an `ObjectType`), the type is left
  unset. The assembly's identity is carried by its `Name` (= panel id).

This mapping matches the *intended* type tags documented in framing-synth's
`framing_rules.md §6`, so no remapping happens at the export boundary — the
member `type`/`role` tags map 1:1 onto `IfcMemberTypeEnum`.

## Trade-off vs. `IfcWallElementedCase`

`IfcWallElementedCase` would tie the framing to a wall-as-container. But the
fabrication unit is the panel, a wall can span multiple panels, and a panel is
cleanly a *premanufactured assembly* — so `IfcElementAssembly` is the more
faithful and more portable standalone representation. Walls are still exported
as `IfcWall` (with their openings) in the same model; the two views coexist.

## Consequences

- Real ResPlan export: 58 panel assemblies, 637 `IfcMember`s
  (327 STUD / 174 PLATE / 136 MEMBER), aggregated via `IfcRelAggregates`,
  validating with 0 errors.
- A consumer wanting wall-centric decomposition (`IfcWallElementedCase`) would
  need a different mapping; documented as out of scope.

## References

- buildingSMART IFC4.3: `IfcElementAssembly` (premanufactured/precast example),
  `IfcMember` + `IfcMemberTypeEnum` (STUD, PLATE), `IfcWall` (ElementedCase)
- `ifcopenshell.api.aggregate.assign_object`, `ifcopenshell.api.root.create_entity`
