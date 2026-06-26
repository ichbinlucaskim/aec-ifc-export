def test_walls_only_ifc_valid(sample_walls, sample_openings, tmp_path):
    """Walls + openings mode must pass ifcopenshell validation with no errors."""
    import ifcopenshell.validate

    from aec_ifc_export import export_ifc

    out = tmp_path / "walls.ifc"
    export_ifc(sample_walls, openings=sample_openings, out_path=str(out))

    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(str(out), logger)
    errors = [m for m in logger.statements if m.get("level") == "Error"]
    assert errors == [], f"IFC validation errors: {errors}"


def test_framing_ifc_valid(sample_walls, sample_framing, sample_panels, tmp_path):
    """Walls + framing mode must pass ifcopenshell validation with no errors."""
    import ifcopenshell.validate

    from aec_ifc_export import export_ifc

    out = tmp_path / "framing.ifc"
    export_ifc(
        sample_walls,
        framing=sample_framing,
        panels=sample_panels,
        out_path=str(out),
    )

    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(str(out), logger)
    errors = [m for m in logger.statements if m.get("level") == "Error"]
    assert errors == [], f"IFC validation errors: {errors}"
