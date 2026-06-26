def test_model_is_ifc4():
    from aec_ifc_export._setup import create_model

    model = create_model()
    assert model.schema == "IFC4"


def test_spatial_hierarchy_complete():
    from aec_ifc_export._setup import create_model, create_spatial_structure

    model = create_model()
    create_spatial_structure(model)
    assert model.by_type("IfcProject")
    assert model.by_type("IfcSite")
    assert model.by_type("IfcBuilding")
    assert model.by_type("IfcBuildingStorey")
