"""
IFC4 model boilerplate: schema, SI units, geometry contexts, spatial hierarchy.

IFC requires a strict spatial structure (Project -> Site -> Building ->
BuildingStorey) before any element can be contained; see ADR-001. Units must be
assigned to the IfcProject, so the project is created *before* assign_unit.
"""
from __future__ import annotations

import time

import ifcopenshell
import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.owner
import ifcopenshell.api.root
import ifcopenshell.api.unit

APPLICATION_NAME = "aec-ifc-export"


def create_model() -> ifcopenshell.file:
    """Create an IFC4 model with SI (metre) units and a Model/Body context.

    IFC4 is used rather than IFC4X3 for maximum BIM-viewer compatibility
    (ADR-003 note). The IfcProject is created first because
    ifcopenshell.api.unit.assign_unit attaches the unit assignment to it.
    """
    model = ifcopenshell.file(schema="IFC4")

    project = ifcopenshell.api.root.create_entity(
        model, ifc_class="IfcProject", name="aec-ifc-export"
    )
    # SI length unit defaults to metres — all coordinates are written in metres.
    ifcopenshell.api.unit.assign_unit(model)

    model_ctx = ifcopenshell.api.context.add_context(model, context_type="Model")
    ifcopenshell.api.context.add_context(
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model_ctx,
    )
    project.RepresentationContexts = [model_ctx]
    return model


def create_owner_history(model: ifcopenshell.file) -> ifcopenshell.entity_instance:
    """Create a single IfcOwnerHistory (person + organisation + application).

    MUST be called AFTER all entities are created: once an IfcPersonAndOrganization
    plus IfcApplication exist, IfcOpenShell's API change-tracking stamps a fresh
    owner history onto every subsequent api mutation. Creating this last (then
    applying it via direct attribute assignment in apply_owner_history) keeps the
    file to exactly one shared authoring record.
    """
    person = ifcopenshell.api.owner.add_person(
        model, identification="aec", family_name="Pipeline", given_name="AEC"
    )
    organisation = ifcopenshell.api.owner.add_organisation(
        model, identification="AEC", name="AEC ML Pipeline"
    )
    user = ifcopenshell.api.owner.add_person_and_organisation(
        model, person=person, organisation=organisation
    )
    application = ifcopenshell.api.owner.add_application(
        model,
        application_developer=organisation,
        version="0.1.0",
        application_full_name=APPLICATION_NAME,
        application_identifier=APPLICATION_NAME,
    )
    return model.createIfcOwnerHistory(
        OwningUser=user,
        OwningApplication=application,
        ChangeAction="ADDED",
        CreationDate=int(time.time()),
    )


def apply_owner_history(model: ifcopenshell.file) -> None:
    """Attach the shared IfcOwnerHistory to every root object that expects one."""
    histories = model.by_type("IfcOwnerHistory")
    if not histories:
        return
    owner_history = histories[0]
    for entity in model.by_type("IfcRoot"):
        entity.OwnerHistory = owner_history


def get_body_context(model: ifcopenshell.file) -> ifcopenshell.entity_instance:
    """Return the Model/Body geometric subcontext created by create_model()."""
    for ctx in model.by_type("IfcGeometricRepresentationSubContext"):
        if ctx.ContextIdentifier == "Body":
            return ctx
    raise ValueError("No Model/Body context found — call create_model() first")


def create_spatial_structure(model: ifcopenshell.file) -> dict:
    """Build Project -> Site -> Building -> BuildingStorey with aggregation.

    Returns {"project", "site", "building", "storey", "body"} — the storey is
    the container for walls and panel assemblies. See ADR-001.
    """
    project = model.by_type("IfcProject")[0]
    site = ifcopenshell.api.root.create_entity(model, ifc_class="IfcSite", name="Site")
    building = ifcopenshell.api.root.create_entity(model, ifc_class="IfcBuilding", name="Building")
    storey = ifcopenshell.api.root.create_entity(
        model, ifc_class="IfcBuildingStorey", name="Level 0"
    )

    ifcopenshell.api.aggregate.assign_object(model, products=[site], relating_object=project)
    ifcopenshell.api.aggregate.assign_object(model, products=[building], relating_object=site)
    ifcopenshell.api.aggregate.assign_object(model, products=[storey], relating_object=building)

    return {
        "project": project,
        "site": site,
        "building": building,
        "storey": storey,
        "body": get_body_context(model),
    }
