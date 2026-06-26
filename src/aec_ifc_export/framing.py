"""
Panel framing -> IfcElementAssembly + IfcMember (the flagship mapping).

A panelized wall is a premanufactured assembly — the canonical use of
IfcElementAssembly per buildingSMART IFC4.3. Each framing member becomes an
IfcMember; studs/plates carry the real IfcMemberTypeEnum values STUD/PLATE,
while header/king/jack/sill/cripple use MEMBER (no dedicated enum). Members
aggregate into the assembly via IfcRelAggregates. See ADR-002.
"""
from __future__ import annotations

import math
import warnings

import ifcopenshell
import ifcopenshell.api.aggregate
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import numpy as np

from ._geom import axis_from_points, placement_matrix, point_xyz, rectangle_extrusion
from ._materials import assign_lumber_to_members

# Nominal section -> (xdim_mm, ydim_mm). From framing_rules.md §5 / aec-schema.
# Emitted in millimetres to match the rest of the model (ADR-003) — these were
# previously in metres (SECTION_DIMS_M), which made members ~0.2mm thick and
# invisible in viewers (the mm/m mix bug).
SECTION_DIMS_MM: dict[str, tuple[float, float]] = {
    "2x3": (38.0, 64.0),
    "2x4": (38.0, 89.0),
    "2x6": (38.0, 140.0),
    "2x8": (38.0, 184.0),
    "2x10": (38.0, 235.0),
    "2x12": (38.0, 286.0),
}

# Framing member type -> IfcMemberTypeEnum. STUD and PLATE are real enum values;
# the rest have no dedicated enum and use MEMBER (ADR-002).
MEMBER_PREDEFINED: dict[str, str] = {
    "stud": "STUD",
    "plate": "PLATE",
    "header": "MEMBER",
    "king": "MEMBER",
    "jack": "MEMBER",
    "sill": "MEMBER",
    "cripple": "MEMBER",
}


def _panel_world_matrix(panel: dict | None) -> np.ndarray:
    """World placement of a panel's local frame (ADR-005).

    Framing members are laid out in panel-LOCAL coordinates (x along the panel,
    z up); the panel's world position lives in panel["start"]/["end"]. This 4x4
    maps panel-local -> world: origin at the panel start, local X along the wall
    direction (start->end), local Z up. The rotation matters — a panel on a
    Y-running wall must have its members turned into that direction, not just
    translated. Identity when no panel geometry is available.
    """
    if not panel:
        return np.eye(4)
    sx, sy = float(panel["start"]["x"]), float(panel["start"]["y"])
    ex, ey = float(panel["end"]["x"]), float(panel["end"]["y"])
    dx, dy = ex - sx, ey - sy
    n = math.hypot(dx, dy)
    x_axis = np.array([dx / n, dy / n, 0.0]) if n > 1e-9 else np.array([1.0, 0.0, 0.0])
    z_axis = np.array([0.0, 0.0, 1.0])
    y_axis = np.cross(z_axis, x_axis)
    m = np.eye(4)
    m[:3, 0] = x_axis
    m[:3, 1] = y_axis
    m[:3, 2] = z_axis
    m[:3, 3] = [sx, sy, 0.0]
    return m


def _export_member(
    model: ifcopenshell.file,
    body_ctx: ifcopenshell.entity_instance,
    member: dict,
    panel_world: np.ndarray,
) -> ifcopenshell.entity_instance:
    """One framing member -> IfcMember with extruded body + WORLD placement.

    Members come in panel-LOCAL coordinates; the placement is the member's local
    frame composed with the panel's world transform, so members land at the
    wall's real location and orientation (ADR-005). The placement is set here,
    before the member is aggregated under the assembly, so it is an absolute
    world placement (this avoids a relative-placement unit quirk in 0.8.x).
    """
    predefined = MEMBER_PREDEFINED.get(member["type"], "MEMBER")
    entity = ifcopenshell.api.root.create_entity(
        model, ifc_class="IfcMember", predefined_type=predefined, name=member["id"]
    )

    xdim, ydim = SECTION_DIMS_MM[member["section"]]
    start = point_xyz(member["start"])
    end = point_xyz(member["end"])

    # Profile dims, extrusion depth, and coordinates are all millimetres.
    rep = rectangle_extrusion(model, body_ctx, xdim, ydim, float(member["length"]))
    ifcopenshell.api.geometry.assign_representation(model, product=entity, representation=rep)

    # Member's panel-local frame (extrude along the member axis) lifted into the
    # panel's world frame, set as an absolute world placement.
    local = placement_matrix(origin=start, z_axis=tuple(axis_from_points(start, end)))
    world = panel_world @ local
    ifcopenshell.api.geometry.edit_object_placement(
        model, product=entity, matrix=world, is_si=False
    )
    return entity


def export_panel_framing(
    model: ifcopenshell.file,
    body_ctx: ifcopenshell.entity_instance,
    storey: ifcopenshell.entity_instance,
    panel: dict | None,
    framing: dict,
    *,
    wall_entity: ifcopenshell.entity_instance | None = None,
    material: ifcopenshell.entity_instance | None = None,
) -> ifcopenshell.entity_instance:
    """Create an IfcElementAssembly for a panel and its aggregated IfcMembers.

    The assembly has no IfcElementAssemblyTypeEnum that names a stud-wall panel,
    so PredefinedType is left unset (NOTDEFINED) rather than forced — see ADR-002.

    Decomposition (ADR-004): the panel assembly is aggregated *under its parent
    IfcWall* (IfcWall ElementedCase) via IfcRelAggregates, giving the chain
    IfcWall -> IfcElementAssembly -> IfcMember. If no parent wall is supplied the
    assembly falls back to storey containment so the file still validates.
    """
    name = framing.get("panel_id") or (panel or {}).get("id", "panel")
    assembly = ifcopenshell.api.root.create_entity(
        model, ifc_class="IfcElementAssembly", name=name
    )

    # Members get their absolute WORLD placement (panel-local lifted into the
    # panel's world frame) before aggregation (ADR-005).
    panel_world = _panel_world_matrix(panel)
    members = [_export_member(model, body_ctx, m, panel_world) for m in framing["members"]]

    # Members are the parts of the assembly (IfcRelAggregates).
    if members:
        ifcopenshell.api.aggregate.assign_object(
            model, products=members, relating_object=assembly
        )
        if material is not None:
            assign_lumber_to_members(model, material, members)

    # The panel decomposes its parent wall; otherwise it lives in the storey.
    if wall_entity is not None:
        ifcopenshell.api.aggregate.assign_object(
            model, products=[assembly], relating_object=wall_entity
        )
    else:
        warnings.warn(
            f"panel assembly {name!r} has no parent wall — containing in storey",
            stacklevel=2,
        )
        ifcopenshell.api.spatial.assign_container(
            model, products=[assembly], relating_structure=storey
        )

    return assembly
