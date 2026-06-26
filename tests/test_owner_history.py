def test_owner_history_exists(sample_walls):
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls)
    assert model.by_type("IfcOwnerHistory"), "no IfcOwnerHistory"


def test_single_owner_history(sample_walls):
    """Exactly one shared owner history, not one per entity."""
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls)
    assert len(model.by_type("IfcOwnerHistory")) == 1


def test_application_named(sample_walls):
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls)
    apps = model.by_type("IfcApplication")
    assert apps
    assert any(
        "aec-ifc-export" in (a.ApplicationFullName or "").lower()
        or "aec-ifc-export" in (a.ApplicationIdentifier or "").lower()
        for a in apps
    )


def test_root_objects_reference_owner_history(sample_walls):
    """Walls (root objects) must carry the owner history."""
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls)
    walls = model.by_type("IfcWall")
    assert walls
    assert all(w.OwnerHistory is not None for w in walls)
