"""
Opening JSON -> IfcOpeningElement, voided into its host wall.

An opening is real geometry attached to the wall via IfcRelVoidsElement (a
boolean subtraction). We build a box (width x through-wall-depth x height) at the
opening's position and void it with ifcopenshell.api.feature.add_feature (the
0.8.x name for the void/opening relation). All values are in millimetres
(ADR-003).

Two things this module gets right (see ADR-008 / OPENING_VOID_DIAGNOSIS.md):
- **Through-hole, not a notch:** add_wall_representation offsets the wall body to
  one face (thickness band local Y in [0, thickness]), so the opening is centred
  on the wall thickness centre (+thickness/2 along the through-wall normal) and
  made deep enough to exceed BOTH faces — the void cuts cleanly through.
- The cut is also **baked** into the wall body in walls.py (IfcBooleanResult,
  using ``wall_local_cutout``) so the hole shows even in IFC4 Reference-View
  viewers that ignore the implicit boolean. This relationship is kept for
  semantics; the two together render a clean through-hole (verified via the
  ifcopenshell geometry iterator). Source: buildingSMART IFC4.3 IfcRelVoidsElement.
"""
from __future__ import annotations

import ifcopenshell
import ifcopenshell.api.feature
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import numpy as np

from ._geom import axis_from_points, placement_matrix, point_xyz, rectangle_extrusion

# Typical window sill height (mm); doors run from the floor. Plans carry no sill
# datum, so this mirrors the assumption documented upstream (framing-synth).
WINDOW_SILL_MM: float = 900.0
# Margin (mm) the void extends BEYOND EACH wall face, for a clean through-cut.
_VOID_MARGIN_MM: float = 50.0


def opening_sill_mm(opening: dict) -> float:
    """Bottom (z) of the opening: a sill for windows, the floor for doors."""
    return WINDOW_SILL_MM if opening.get("type") == "window" else 0.0


def opening_void_depth_mm(wall: dict) -> float:
    """Through-wall depth of the void: full thickness + margin on both faces."""
    return float(wall["thickness"]) + 2.0 * _VOID_MARGIN_MM


def wall_local_cutout(
    model: ifcopenshell.file,
    opening: dict,
    wall: dict,
) -> ifcopenshell.entity_instance:
    """Opening cut-out solid in the WALL's LOCAL frame, for baking the wall body
    boolean (walls.py). Local X = along the wall, Y = through-wall (centred on the
    wall thickness band [0, thickness], full-penetration depth), Z = up.
    """
    thickness = float(wall["thickness"])
    profile = model.createIfcRectangleProfileDef(
        ProfileType="AREA",
        XDim=float(opening["width"]),
        YDim=opening_void_depth_mm(wall),
        Position=model.createIfcAxis2Placement2D(
            model.createIfcCartesianPoint((float(opening["position"]), thickness / 2.0))
        ),
    )
    return model.createIfcExtrudedAreaSolid(
        SweptArea=profile,
        Position=model.createIfcAxis2Placement3D(
            model.createIfcCartesianPoint((0.0, 0.0, opening_sill_mm(opening)))
        ),
        ExtrudedDirection=model.createIfcDirection((0.0, 0.0, 1.0)),
        Depth=float(opening["height"]),
    )


def export_opening(
    model: ifcopenshell.file,
    body_ctx: ifcopenshell.entity_instance,
    wall_entity: ifcopenshell.entity_instance,
    opening: dict,
    wall: dict,
) -> ifcopenshell.entity_instance:
    """Create an IfcOpeningElement and void it into ``wall_entity`` (mm)."""
    p1 = np.array(point_xyz(wall["start"]), dtype=float)
    p2 = np.array(point_xyz(wall["end"]), dtype=float)
    along = axis_from_points(tuple(p1), tuple(p2))  # wall direction (unit)
    # Through-wall normal = wall local +Y (the side the body is offset onto).
    normal = np.array([-along[1], along[0], 0.0])

    thickness = float(wall["thickness"])
    # Centre the opening on the wall thickness band [0, thickness] (not the
    # placement line / face), so the void cuts through both faces (ADR-008).
    centre = p1 + float(opening["position"]) * along + (thickness / 2.0) * normal
    z_bottom = opening_sill_mm(opening)

    width_mm = float(opening["width"])
    height_mm = float(opening["height"])
    depth_mm = opening_void_depth_mm(wall)

    entity = ifcopenshell.api.root.create_entity(
        model, ifc_class="IfcOpeningElement", name=opening["id"]
    )
    # Profile: width (along wall, local X) x through-wall depth (local Y), extruded up.
    rep = rectangle_extrusion(model, body_ctx, width_mm, depth_mm, height_mm)
    ifcopenshell.api.geometry.assign_representation(model, product=entity, representation=rep)

    matrix = placement_matrix(
        origin=(centre[0], centre[1], z_bottom),
        z_axis=(0.0, 0.0, 1.0),     # extrude vertically
        x_hint=tuple(along),        # width runs along the wall
    )
    ifcopenshell.api.geometry.edit_object_placement(
        model, product=entity, matrix=matrix, is_si=False  # mm matrix
    )

    # IfcRelVoidsElement (boolean subtraction) — 'feature' is the 0.8.x API name.
    ifcopenshell.api.feature.add_feature(model, feature=entity, element=wall_entity)
    return entity
