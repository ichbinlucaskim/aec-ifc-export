"""
Room -> IfcSpace (optional).

The current pipeline JSON carries room *ids* on walls (adjacent_rooms) but no
room polygons, so spaces are not part of the default export. This helper is
provided for callers that do have a room footprint (a list of (x_mm, y_mm)
points): it creates an IfcSpace as an extruded polygon, contained in the storey.
All values are millimetres, consistent with the rest of the model (ADR-003).
"""
from __future__ import annotations

import ifcopenshell
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import ifcopenshell.api.spatial

DEFAULT_SPACE_HEIGHT_MM: float = 2438.0


def export_space(
    model: ifcopenshell.file,
    body_ctx: ifcopenshell.entity_instance,
    storey: ifcopenshell.entity_instance,
    space_id: str,
    footprint_mm: list[tuple[float, float]],
    *,
    height_mm: float = DEFAULT_SPACE_HEIGHT_MM,
) -> ifcopenshell.entity_instance:
    """Create an IfcSpace from a polygonal footprint (list of (x_mm, y_mm))."""
    space = ifcopenshell.api.root.create_entity(model, ifc_class="IfcSpace", name=space_id)

    points = [model.createIfcCartesianPoint((float(x), float(y))) for x, y in footprint_mm]
    if points and points[0].Coordinates != points[-1].Coordinates:
        points.append(points[0])  # close the ring
    profile = model.createIfcArbitraryClosedProfileDef(
        ProfileType="AREA", OuterCurve=model.createIfcPolyline(points)
    )
    solid = model.createIfcExtrudedAreaSolid(
        SweptArea=profile,
        Position=model.createIfcAxis2Placement3D(model.createIfcCartesianPoint((0.0, 0.0, 0.0))),
        ExtrudedDirection=model.createIfcDirection((0.0, 0.0, 1.0)),
        Depth=height_mm,
    )
    rep = model.createIfcShapeRepresentation(
        ContextOfItems=body_ctx,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[solid],
    )
    ifcopenshell.api.geometry.assign_representation(model, product=space, representation=rep)
    ifcopenshell.api.spatial.assign_container(model, products=[space], relating_structure=storey)
    return space
