def test_panel_aggregated_under_wall(sample_walls, sample_framing, sample_panels):
    """Each panel assembly must decompose its parent wall (IfcRelAggregates)."""
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls, framing=sample_framing, panels=sample_panels)

    assemblies = model.by_type("IfcElementAssembly")
    assert assemblies, "no panel assemblies"

    for asm in assemblies:
        assert asm.Decomposes, f"panel {asm.Name} floats free (no parent)"
        parent = asm.Decomposes[0].RelatingObject
        assert parent.is_a("IfcWall"), (
            f"panel {asm.Name} parent is {parent.is_a()}, expected IfcWall"
        )


def test_full_decomposition_chain(sample_walls, sample_framing, sample_panels):
    """Wall -> panel assembly -> members must form a complete chain."""
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls, framing=sample_framing, panels=sample_panels)
    asm = model.by_type("IfcElementAssembly")[0]
    # has a wall parent
    assert asm.Decomposes[0].RelatingObject.is_a("IfcWall")
    # has member children
    assert asm.IsDecomposedBy
    members = asm.IsDecomposedBy[0].RelatedObjects
    assert all(m.is_a("IfcMember") for m in members)


def test_no_floating_assemblies(sample_walls, sample_framing, sample_panels):
    """Regression: no panel assembly may be left without a parent wall."""
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls, framing=sample_framing, panels=sample_panels)
    floating = [a for a in model.by_type("IfcElementAssembly") if not a.Decomposes]
    assert floating == [], f"{len(floating)} panel assemblies float free"
