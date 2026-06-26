"""
Material structure for framing members (placeholder value, real structure).

We add the IFC *structure* to hold material (IfcMaterial +
IfcRelAssociatesMaterial) with a clearly-marked placeholder. The actual species
and structural grade are domain-expert (architect / structural engineer)
decisions and are intentionally NOT specified — see ADR-004. This is the ML/SWE
responsibility boundary: model completeness, not engineered material selection.
"""
from __future__ import annotations

import ifcopenshell
import ifcopenshell.api.material

MATERIAL_NAME = "Softwood Lumber"
MATERIAL_NOTE = "PLACEHOLDER — species/grade TBD by engineer"


def create_lumber_material(model: ifcopenshell.file) -> ifcopenshell.entity_instance:
    """Create one placeholder IfcMaterial for dimensional lumber.

    Species and structural grade are intentionally left to a domain expert; this
    provides the material slot and a documented default, not an engineered spec.
    """
    return ifcopenshell.api.material.add_material(
        model, name=MATERIAL_NAME, category="wood", description=MATERIAL_NOTE
    )


def assign_lumber_to_members(
    model: ifcopenshell.file,
    material: ifcopenshell.entity_instance,
    members: list[ifcopenshell.entity_instance],
) -> None:
    """Associate the lumber material to framing members (IfcRelAssociatesMaterial)."""
    if members:
        ifcopenshell.api.material.assign_material(
            model, products=list(members), type="IfcMaterial", material=material
        )
