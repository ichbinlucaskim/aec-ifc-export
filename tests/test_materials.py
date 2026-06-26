def test_material_exists(sample_walls, sample_framing, sample_panels):
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls, framing=sample_framing, panels=sample_panels)
    assert model.by_type("IfcMaterial"), "no IfcMaterial created"


def test_members_have_material(sample_walls, sample_framing, sample_panels):
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls, framing=sample_framing, panels=sample_panels)
    assocs = model.by_type("IfcRelAssociatesMaterial")
    assert assocs, "no material associations"
    associated = [obj for a in assocs for obj in a.RelatedObjects]
    assert any(o.is_a("IfcMember") for o in associated)


def test_material_marked_placeholder(sample_walls, sample_framing, sample_panels):
    """The material name/description must signal it is a placeholder."""
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls, framing=sample_framing, panels=sample_panels)
    mat = model.by_type("IfcMaterial")[0]
    text = (mat.Name or "") + (getattr(mat, "Description", "") or "")
    assert (
        "PLACEHOLDER" in text.upper()
        or "TBD" in text.upper()
        or "softwood" in text.lower()
    )


def test_single_shared_material(sample_walls, sample_framing, sample_panels):
    """One shared placeholder material, not one per member."""
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls, framing=sample_framing, panels=sample_panels)
    assert len(model.by_type("IfcMaterial")) == 1
