"""
Wall JSON -> IfcWall.

We set the wall's ObjectPlacement ourselves — origin at the wall start, local X
along (end - start), local Z up — in millimetres (is_si=False), the SAME
consistent mm placement path the framing members use. This deliberately avoids
ifcopenshell.api.geometry.create_2pt_wall, whose is_si=False branch unit-converts
p1 but not p2 and rotates walls to diagonal directions (see
docs/KNOWN_LIBRARY_ISSUES.md LIB-001 and ADR-007).

The wall body is built with add_wall_representation, whose length/height/thickness
are SI metres (it scales to the file unit internally) — so they are passed as
mm / 1000. exterior/interior and load_bearing are carried as Pset_WallCommon
properties (IsExternal / LoadBearing).
"""
from __future__ import annotations

import math

import ifcopenshell
import ifcopenshell.api.geometry
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import numpy as np

from ._geom import point_xyz
from .openings import wall_local_cutout

DEFAULT_WALL_HEIGHT_MM: float = 2438.0  # standard 8ft storey (matches panel height)
_MM_PER_M: float = 1000.0


def _wall_placement_matrix(wall: dict) -> np.ndarray:
    """4x4 wall placement in MILLIMETRES (consistent with framing's panel frame).

    origin = wall.start (world mm); local X = (end - start) normalized
    (the wall length direction); local Z = world up; local Y = Z x X. Avoids the
    create_2pt_wall is_si unit-mixing bug (ADR-007 / LIB-001).
    """
    s = np.array([wall["start"]["x"], wall["start"]["y"], 0.0], dtype=float)
    e = np.array([wall["end"]["x"], wall["end"]["y"], 0.0], dtype=float)
    direction = e - s
    n = np.linalg.norm(direction)
    if n == 0:
        raise ValueError(f"degenerate wall {wall.get('id')!r}: start == end")
    x_axis = direction / n
    z_axis = np.array([0.0, 0.0, 1.0])
    y_axis = np.cross(z_axis, x_axis)
    m = np.eye(4)
    m[:3, 0] = x_axis
    m[:3, 1] = y_axis
    m[:3, 2] = z_axis
    m[:3, 3] = s
    return m


def export_wall(
    model: ifcopenshell.file,
    body_ctx: ifcopenshell.entity_instance,
    storey: ifcopenshell.entity_instance,
    wall: dict,
    *,
    openings: list[dict] | None = None,
    height_mm: float = DEFAULT_WALL_HEIGHT_MM,
) -> ifcopenshell.entity_instance:
    """Create an IfcWall from a wall dict (aec-schema wall.schema.json).

    Openings hosted on this wall are **baked** into the body as an
    IfcBooleanResult (DIFFERENCE) of wall-local cut-out solids, so the hole shows
    even in viewers that ignore the IfcRelVoidsElement implicit boolean (e.g. IFC4
    Reference View). The IfcRelVoidsElement relationship is still added separately
    (openings.py) for semantics; together they render a clean through-hole with no
    double-cut, verified via the ifcopenshell geometry iterator (ADR-008).
    """
    entity = ifcopenshell.api.root.create_entity(model, ifc_class="IfcWall", name=wall["id"])

    p1 = point_xyz(wall["start"])
    p2 = point_xyz(wall["end"])
    length_mm = math.dist((p1[0], p1[1]), (p2[0], p2[1]))

    # Body: footprint (length x thickness) extruded up by height. Inputs are SI
    # metres (the API scales to the mm file unit), so pass mm / 1000 as plain
    # floats (numpy floats break the IfcCartesianPointList2D builder).
    representation = ifcopenshell.api.geometry.add_wall_representation(
        model,
        context=body_ctx,
        length=length_mm / _MM_PER_M,
        height=float(height_mm) / _MM_PER_M,
        thickness=float(wall["thickness"]) / _MM_PER_M,
    )
    ifcopenshell.api.geometry.assign_representation(
        model, product=entity, representation=representation
    )
    # Placement: our own mm matrix (correct axis-aligned direction); is_si=False.
    ifcopenshell.api.geometry.edit_object_placement(
        model, product=entity, matrix=_wall_placement_matrix(wall), is_si=False
    )

    # Bake the opening cut-outs into the wall body (wall-local solids).
    if openings:
        cutouts = [wall_local_cutout(model, op, wall) for op in openings]
        ifcopenshell.api.geometry.add_boolean(
            model, first_item=representation.Items[0], second_items=cutouts, operator="DIFFERENCE"
        )

    ifcopenshell.api.spatial.assign_container(
        model, products=[entity], relating_structure=storey
    )

    # Standard IFC location for these facts (Pset_WallCommon).
    pset = ifcopenshell.api.pset.add_pset(model, product=entity, name="Pset_WallCommon")
    ifcopenshell.api.pset.edit_pset(
        model,
        pset=pset,
        properties={
            "IsExternal": wall.get("type") == "exterior",
            "LoadBearing": bool(wall.get("load_bearing", False)),
        },
    )
    return entity
