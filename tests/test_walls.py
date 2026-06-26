def test_wall_exported(sample_walls):
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls)
    assert len(model.by_type("IfcWall")) == len(sample_walls)


def test_wall_names_preserved(sample_walls):
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls)
    names = {w.Name for w in model.by_type("IfcWall")}
    assert names == {"wall-000", "wall-001"}


def test_opening_voids_wall(sample_walls, sample_openings):
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls, openings=sample_openings)
    assert model.by_type("IfcOpeningElement")
    assert model.by_type("IfcRelVoidsElement")


def test_wall_common_pset(sample_walls):
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls)
    assert any(p.Name == "Pset_WallCommon" for p in model.by_type("IfcPropertySet"))
