# ADR-001 — Mandatory spatial structure: Project → Site → Building → Storey

**Status:** Accepted (2026-06-16)

## Context

IFC is not a flat list of geometry; every physical element must be *contained*
in a spatial structure. A wall or member with no spatial container is invalid
and many viewers will silently drop it. IFC defines the containment hierarchy as
`IfcProject` → `IfcSite` → `IfcBuilding` → `IfcBuildingStorey` → elements.

## Decision

`_setup.create_model()` + `create_spatial_structure()` always build the full
chain before any element is exported:

- `IfcProject` is created **first**, because `ifcopenshell.api.unit.assign_unit`
  attaches the unit assignment to the project (creating units before the project
  raises `IndexError`).
- Site/Building/Storey are linked with `ifcopenshell.api.aggregate.assign_object`
  (`IfcRelAggregates`).
- Walls and panel assemblies are placed in the storey with
  `ifcopenshell.api.spatial.assign_container` (`IfcRelContainedInSpatialStructure`).

A single default storey ("Level 0") is used — the pipeline is single-storey
(see framing-synth baseline load case).

## Consequences

- Output is a well-formed spatial tree that opens in any IFC4 viewer.
- Multi-storey plans would need storey assignment per element; out of scope here.

## References

- `ifcopenshell.api.spatial`, `ifcopenshell.api.aggregate` (IfcOpenShell 0.8.x)
- buildingSMART IFC4 spatial composition (IfcSpatialStructureElement)
