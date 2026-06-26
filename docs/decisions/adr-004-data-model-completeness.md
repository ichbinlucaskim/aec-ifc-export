# ADR-004: Data-model completeness vs. engineering scope

**Status:** Accepted (2026-06-16)

## Context

Inspecting the exported IFC found three gaps that separate a "demo" file from a
professionally complete one:

1. **Panel assemblies floated free** — each `IfcElementAssembly` (panel) was
   spatially contained in the storey but not related to its parent `IfcWall`,
   even though `panel["parent_wall"]` carries that link in our JSON.
2. **No material** — 0 `IfcMaterial`; members were typed (STUD/PLATE) but carried
   no material.
3. **No authoring metadata** — 0 `IfcOwnerHistory` / `IfcApplication`.

These are **data-integrity** gaps, distinct from structural-engineering
decisions.

## Decision

Fix the data-model completeness gaps that fall within the ML/SWE responsibility:

1. **Aggregate the panel `IfcElementAssembly` under its parent `IfcWall`** via
   `IfcRelAggregates` — the `IfcWall` *ElementedCase* decomposition pattern. The
   full chain becomes `IfcWall → IfcElementAssembly(panel) → IfcMember`. The
   parent is resolved from `panel["parent_wall"]`; an orphan (no matching wall)
   warns and falls back to storey containment so the file still validates.
2. **Add `IfcMaterial` + `IfcRelAssociatesMaterial`** with a clearly-marked
   PLACEHOLDER lumber material (`"Softwood Lumber"`, description
   `"PLACEHOLDER — species/grade TBD by engineer"`), shared by all framing
   members. The *structure* is real; the *value* is a documented default.
3. **Add `IfcOwnerHistory` + `IfcApplication`** ("aec-ifc-export"). Exactly one
   shared owner history is created *after* all entities exist (IfcOpenShell's API
   change-tracking would otherwise stamp a duplicate history per mutation), then
   assigned to every root object by direct attribute write.

## Explicit non-goals (engineering scope, out of bounds)

- Structural adequacy / load-bearing capacity of members — PE-stamped.
- Engineered species/grade selection — architect / structural engineer.
- Header sizing beyond the prescriptive IRC simplification already documented in
  framing-synth (`framing_rules.md`).

This ADR records the boundary: the exporter guarantees a complete, internally
consistent IFC **data model**; it does not make **engineering** judgments. The
material slot and a clearly-marked placeholder are exactly that boundary — we
provide where the engineered spec attaches, not the spec itself.

## Consequences

- Real ResPlan demo: 56 panel assemblies, **0 floating**, chain
  `IfcWall → IfcElementAssembly → IfcMember`; 1 `IfcMaterial`, 1
  `IfcRelAssociatesMaterial`, 1 `IfcOwnerHistory`; both files validate 0 errors.
- Viewers show a clean Wall → Panel → Member tree.

## Sources

- buildingSMART IFC4.3: `IfcWall` (ElementedCase decomposition),
  `IfcRelAggregates`, `IfcRelAssociatesMaterial`, `IfcMaterial`,
  `IfcOwnerHistory`, `IfcApplication`.
- IfcOpenShell 0.8.x: `ifcopenshell.api.aggregate.assign_object`,
  `ifcopenshell.api.material.add_material` / `assign_material`,
  `ifcopenshell.api.owner.*`.
