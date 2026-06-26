"""
Opening void geometry: real through-holes baked into the wall body (ADR-008).

IMPORTANT: these use the ifcopenshell geometry ITERATOR, not create_shape.
create_shape returns 0 verts for these add_wall_representation bodies (an
unreliable single-element path); the iterator is how viewers actually consume
the geometry and resolves the booleans correctly.
"""
import ifcopenshell
import ifcopenshell.geom
import numpy as np


def _wall_local_verts(model, wall) -> np.ndarray:
    """Wall body local verts (mm) via the geometry iterator (applies voids)."""
    settings = ifcopenshell.geom.settings()
    it = ifcopenshell.geom.iterator(settings, model, include=[wall])
    if not it.initialize():
        return np.empty((0, 3))
    return np.array(it.get().geometry.verts).reshape(-1, 3) * 1000.0


def test_wall_body_is_boolean_when_voided(sample_walls, sample_openings):
    """A voided wall's body is baked as an IfcBooleanResult (viewer-independent)."""
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls, openings=sample_openings)
    hosts = [w for w in model.by_type("IfcWall") if w.HasOpenings]
    assert hosts, "no host walls"
    for w in hosts:
        item = w.Representation.Representations[0].Items[0]
        assert item.is_a("IfcBooleanResult"), f"{w.Name} body not baked: {item.is_a()}"


def test_openings_are_through_holes(sample_walls, sample_openings):
    """A hosted opening must cut through the FULL wall thickness, not a notch.

    A notch reaches only one face; a through-hole's rim verts appear at BOTH
    thickness faces (local Y min and max).
    """
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls, openings=sample_openings)
    hosts = [w for w in model.by_type("IfcWall") if w.HasOpenings]
    assert hosts
    for w in hosts:
        lv = _wall_local_verts(model, w)
        assert len(lv) > 8, f"{w.Name}: no hole (plain box / not tessellated)"
        ymin, ymax = lv[:, 1].min(), lv[:, 1].max()
        near_min = np.any(np.isclose(lv[:, 1], ymin, atol=3.0))
        near_max = np.any(np.isclose(lv[:, 1], ymax, atol=3.0))
        assert near_min and near_max, f"{w.Name}: opening is a notch, not a through-hole"


def test_voided_wall_still_renders(sample_walls, sample_openings):
    """The voided wall body must tessellate to real geometry (not vanish)."""
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls, openings=sample_openings)
    for w in model.by_type("IfcWall"):
        if w.HasOpenings:
            assert len(_wall_local_verts(model, w)) > 0, f"{w.Name}: no geometry"
