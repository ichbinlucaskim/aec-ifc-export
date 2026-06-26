"""
World-coordinate geometry regression tests (Defects A + B, ADR-005).

These guard the exact blind spot that let the collapse through: schema-valid but
geometrically collapsed. They inspect WORLD coordinates (local verts × the
shape's world transform), not local verts (which always sit near the origin).
"""
import contextlib

import ifcopenshell
import ifcopenshell.geom
import numpy as np


def _world_verts(shape) -> np.ndarray:
    """Local verts × world transformation matrix → world coordinates (metres).

    Returns an empty (0, 3) array when the geom engine yields no verts (e.g. the
    known m017-class sill quirk) so callers can skip it instead of producing NaN.
    """
    v = np.array(shape.geometry.verts).reshape(-1, 3)
    if len(v) == 0:
        return v
    m = np.array(shape.transformation.matrix).reshape(4, 4).T
    vh = np.hstack([v, np.ones((len(v), 1))])
    return (vh @ m.T)[:, :3]


def _member_world_centers(model, settings):
    """World centroid of each member, skipping 0-vert (untessellatable) members."""
    centers = []
    for mem in model.by_type("IfcMember"):
        wv = _world_verts(ifcopenshell.geom.create_shape(settings, mem))
        if len(wv):
            centers.append(wv.mean(0))
    return np.array(centers)


def test_no_null_wall_representation(sample_walls, sample_framing, sample_panels):
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls, framing=sample_framing, panels=sample_panels)
    nulls = [w for w in model.by_type("IfcWall") if w.Representation is None]
    assert nulls == [], f"{len(nulls)} walls have NULL representation (Defect A)"


def test_walls_render(sample_walls, sample_framing, sample_panels, tmp_path):
    """Every wall must produce geometry via the geom engine (a viewer would show it)."""
    from aec_ifc_export import export_ifc

    out = tmp_path / "m.ifc"
    export_ifc(sample_walls, framing=sample_framing, panels=sample_panels, out_path=str(out))
    model = ifcopenshell.open(str(out))
    settings = ifcopenshell.geom.settings()
    rendered = 0
    for w in model.by_type("IfcWall"):
        try:
            ifcopenshell.geom.create_shape(settings, w)
            rendered += 1
        except Exception:
            pass
    assert rendered == len(model.by_type("IfcWall")), "some walls produce no geometry"


def test_framing_spread_in_world(sample_walls, sample_framing, sample_panels):
    """Members must span the building in WORLD coordinates, not stack at origin."""
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls, framing=sample_framing, panels=sample_panels)
    settings = ifcopenshell.geom.settings()
    c = _member_world_centers(model, settings)
    span_x = c[:, 0].max() - c[:, 0].min()
    span_y = c[:, 1].max() - c[:, 1].min()
    # Two panels ~5m apart (one on a Y-running wall at x=5000) → world spread must
    # far exceed one panel footprint, and Y must not be a single thin band.
    assert max(span_x, span_y) > 4.0, f"members not spread in world: x={span_x}, y={span_y}"
    assert span_y > 0.5 or span_x > 4.0, "framing appears stacked at origin (Defect B)"


def test_panels_at_distinct_locations(sample_walls, sample_framing, sample_panels):
    """Two panels on different walls must have distinct world positions."""
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls, framing=sample_framing, panels=sample_panels)
    settings = ifcopenshell.geom.settings()
    asm_centers = []
    for asm in model.by_type("IfcElementAssembly"):
        pts = []
        if asm.IsDecomposedBy:
            for mem in asm.IsDecomposedBy[0].RelatedObjects:
                with contextlib.suppress(Exception):
                    pts.append(_world_verts(ifcopenshell.geom.create_shape(settings, mem)).mean(0))
        if pts:
            asm_centers.append(np.mean(pts, axis=0))
    c = np.array(asm_centers)
    assert np.ptp(c, axis=0).max() > 1.0, "all panel assemblies stacked at one location"


def test_panel_orientation_follows_wall(sample_walls, sample_framing, sample_panels):
    """A panel on a Y-running wall must lay its framing along Y, not X."""
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls, framing=sample_framing, panels=sample_panels)
    settings = ifcopenshell.geom.settings()
    # panel-002 sits on wall-001 (x=5000, runs along Y); its members should span Y.
    asm = next(a for a in model.by_type("IfcElementAssembly") if a.Name == "panel-002")
    member_verts = [
        _world_verts(ifcopenshell.geom.create_shape(settings, mem))
        for mem in asm.IsDecomposedBy[0].RelatedObjects
    ]
    verts = np.vstack([wv for wv in member_verts if len(wv)])  # skip 0-vert members
    span_x = verts[:, 0].max() - verts[:, 0].min()
    span_y = verts[:, 1].max() - verts[:, 1].min()
    assert span_y > span_x, f"Y-wall panel not oriented along Y (x={span_x:.2f}, y={span_y:.2f})"
    assert verts[:, 0].min() > 4.0, "panel-002 not near its wall at x=5000m"
