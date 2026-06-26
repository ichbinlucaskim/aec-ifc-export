def test_panel_is_element_assembly(sample_walls, sample_framing, sample_panels):
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls, framing=sample_framing, panels=sample_panels)
    assert model.by_type("IfcElementAssembly")


def test_members_are_ifcmember(sample_walls, sample_framing, sample_panels):
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls, framing=sample_framing, panels=sample_panels)
    members = model.by_type("IfcMember")
    assert len(members) == sum(f["member_count"] for f in sample_framing)


def test_studs_have_stud_predefined_type(sample_walls, sample_framing, sample_panels):
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls, framing=sample_framing, panels=sample_panels)
    studs = [m for m in model.by_type("IfcMember") if m.PredefinedType == "STUD"]
    assert len(studs) > 0


def test_plates_have_plate_predefined_type(sample_walls, sample_framing, sample_panels):
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls, framing=sample_framing, panels=sample_panels)
    plates = [m for m in model.by_type("IfcMember") if m.PredefinedType == "PLATE"]
    assert len(plates) > 0


def test_members_aggregated_into_assembly(sample_walls, sample_framing, sample_panels):
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls, framing=sample_framing, panels=sample_panels)
    rels = model.by_type("IfcRelAggregates")
    assert any(r.RelatingObject.is_a("IfcElementAssembly") for r in rels)


def test_framing_off_produces_no_assembly(sample_walls):
    """Walls-only mode must not emit any framing assembly (framing on/off)."""
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls)
    assert not model.by_type("IfcElementAssembly")
    assert not model.by_type("IfcMember")
