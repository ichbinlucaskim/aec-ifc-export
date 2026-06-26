def test_units_are_metric(sample_walls):
    from aec_ifc_export import export_ifc

    model = export_ifc(sample_walls)
    assert model.by_type("IfcUnitAssignment")


def test_unit_is_millimetre(sample_walls, tmp_path):
    import ifcopenshell

    from aec_ifc_export import export_ifc

    out = tmp_path / "m.ifc"
    export_ifc(sample_walls, out_path=str(out))
    model = ifcopenshell.open(str(out))
    length_units = [u for u in model.by_type("IfcSIUnit") if u.UnitType == "LENGTHUNIT"]
    assert length_units
    assert length_units[0].Prefix == "MILLI"
    assert length_units[0].Name == "METRE"


def test_profile_dims_consistent_with_coordinates(
    sample_walls, sample_framing, sample_panels, tmp_path
):
    """Regression for the mm/m mix bug: profile dimensions and coordinate values
    must be the same order of magnitude. A 2x4 stud profile (38mm) must NOT be
    emitted as 0.038 while walls are in thousands of mm.
    """
    import ifcopenshell

    from aec_ifc_export import export_ifc

    out = tmp_path / "m.ifc"
    export_ifc(sample_walls, framing=sample_framing, panels=sample_panels, out_path=str(out))
    model = ifcopenshell.open(str(out))

    profiles = model.by_type("IfcRectangleProfileDef")
    assert profiles, "no profiles found"
    # In a mm model the smaller profile dimension (member thickness 38mm) must be
    # >= 1.0 (tens of mm), never a sub-millimetre metre value.
    for p in profiles:
        assert min(p.XDim, p.YDim) >= 1.0, (
            f"Profile dim {min(p.XDim, p.YDim)} looks like metres in a mm model "
            f"(expected ~38mm). mm/m mix regression."
        )


def test_stud_thickness_realistic(sample_walls, sample_framing, sample_panels, tmp_path):
    """A 2x4/2x6 stud thickness should be ~38mm, not 0.038 and not 0."""
    import ifcopenshell

    from aec_ifc_export import export_ifc

    out = tmp_path / "m.ifc"
    export_ifc(sample_walls, framing=sample_framing, panels=sample_panels, out_path=str(out))
    model = ifcopenshell.open(str(out))
    thicknesses = [min(p.XDim, p.YDim) for p in model.by_type("IfcRectangleProfileDef")]
    assert all(30.0 <= t <= 50.0 for t in thicknesses), (
        f"Unexpected stud thicknesses: {sorted(set(thicknesses))}"
    )
