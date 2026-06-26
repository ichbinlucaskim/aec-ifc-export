"""
Geometry helpers: placement matrices and extruded rectangle profiles.

The IFC is authored entirely in MILLIMETRES (IfcSIUnit .MILLI. .METRE.),
numerically identical to the upstream pipeline JSON — there is NO mm->m
conversion anywhere in the geometry path (see ADR-003). Linear members are
modelled as a rectangle profile extruded along the member axis, all in mm.
"""
from __future__ import annotations

import ifcopenshell
import numpy as np


def point_xyz(pt: dict) -> tuple[float, float, float]:
    """{'x':mm,'y':mm[,'z':mm]} -> (x, y, z) in mm; z defaults to 0."""
    return (float(pt["x"]), float(pt["y"]), float(pt.get("z", 0.0)))


def axis_from_points(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
) -> np.ndarray:
    """Unit direction start->end; falls back to +Z for a degenerate segment."""
    d = np.array(end, dtype=float) - np.array(start, dtype=float)
    n = np.linalg.norm(d)
    return d / n if n > 1e-9 else np.array([0.0, 0.0, 1.0])


def placement_matrix(
    origin: tuple[float, float, float],
    z_axis: tuple[float, float, float],
    x_hint: tuple[float, float, float] | None = None,
) -> np.ndarray:
    """4x4 placement (mm origin) for edit_object_placement(is_si=False).

    The extrusion runs along the local +Z axis, so ``z_axis`` is the member
    direction. ``x_hint`` fixes the in-plane orientation (e.g. an opening's
    width along the wall); when omitted an arbitrary perpendicular is chosen.
    """
    z = np.array(z_axis, dtype=float)
    z /= np.linalg.norm(z)
    if x_hint is not None:
        x = np.array(x_hint, dtype=float)
        x = x - np.dot(x, z) * z  # project the hint into the plane normal to z
        if np.linalg.norm(x) < 1e-9:
            x_hint = None
    if x_hint is None:
        ref = np.array([1.0, 0.0, 0.0]) if abs(z[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        x = np.cross(ref, z)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)

    m = np.eye(4)
    m[:3, 0] = x
    m[:3, 1] = y
    m[:3, 2] = z
    m[:3, 3] = np.array(origin, dtype=float)
    return m


def rectangle_extrusion(
    model: ifcopenshell.file,
    body_ctx: ifcopenshell.entity_instance,
    xdim_mm: float,
    ydim_mm: float,
    depth_mm: float,
) -> ifcopenshell.entity_instance:
    """Body shape: a centred rectangle profile extruded along local +Z, in mm.

    Built directly (not via the high-level add_profile_representation, which
    treats its depth as SI metres) so every value — profile dims AND depth — is
    emitted in millimetres, consistent with the rest of the model (ADR-003).
    Returns an IfcShapeRepresentation ready for assign_representation.
    """
    profile = model.createIfcRectangleProfileDef(
        ProfileType="AREA",
        XDim=xdim_mm,
        YDim=ydim_mm,
        Position=model.createIfcAxis2Placement2D(model.createIfcCartesianPoint((0.0, 0.0))),
    )
    solid = model.createIfcExtrudedAreaSolid(
        SweptArea=profile,
        Position=model.createIfcAxis2Placement3D(
            model.createIfcCartesianPoint((0.0, 0.0, 0.0))
        ),
        ExtrudedDirection=model.createIfcDirection((0.0, 0.0, 1.0)),
        Depth=depth_mm,
    )
    return model.createIfcShapeRepresentation(
        ContextOfItems=body_ctx,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[solid],
    )
