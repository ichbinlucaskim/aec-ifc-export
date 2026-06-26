"""
Top-level export: pipeline JSON -> a complete IFC4 model.

Two modes, both producing a viewer-valid IFC ("framing on / off"):
  - walls only      -> IfcWall (+ IfcOpeningElement voids)
  - walls + framing -> also IfcElementAssembly per panel + IfcMember per member
"""
from __future__ import annotations

import ifcopenshell

from ._materials import create_lumber_material
from ._setup import (
    apply_owner_history,
    create_model,
    create_owner_history,
    create_spatial_structure,
)
from .framing import export_panel_framing
from .openings import export_opening
from .walls import DEFAULT_WALL_HEIGHT_MM, export_wall


def export_ifc(
    walls: list[dict],
    *,
    openings: dict[str, dict] | None = None,
    framing: list[dict] | None = None,
    panels: dict[str, dict] | None = None,
    wall_height_mm: float = DEFAULT_WALL_HEIGHT_MM,
    out_path: str | None = None,
) -> ifcopenshell.file:
    """Build a complete IFC4 model from pipeline JSON.

    Parameters
    ----------
    walls:
        Wall dicts (aec-schema wall.schema.json).
    openings:
        Optional {opening_id: opening_dict}; each is voided into its
        ``host_wall`` via IfcRelVoidsElement.
    framing:
        Optional list of framing dicts (one per panel, framing.schema.json);
        each becomes an IfcElementAssembly of IfcMembers.
    panels:
        Optional {panel_id: panel_dict}, used for assembly naming.
    wall_height_mm:
        Storey wall height in millimetres (walls are 2D and carry no height).
    out_path:
        If given, write the model to this path.

    Returns the IfcOpenShell model.
    """
    model = create_model()
    struct = create_spatial_structure(model)
    storey, body = struct["storey"], struct["body"]

    # Group openings by host wall so the wall body can bake their cut-outs.
    openings_by_wall: dict[str, list[dict]] = {}
    for opening in (openings or {}).values():
        host = opening.get("host_wall")
        if host is not None:
            openings_by_wall.setdefault(host, []).append(opening)

    wall_entities: dict[str, tuple] = {}
    for wall in walls:
        entity = export_wall(
            model, body, storey, wall,
            openings=openings_by_wall.get(wall["id"]),
            height_mm=wall_height_mm,
        )
        wall_entities[wall["id"]] = (entity, wall)

    if openings:
        for opening in openings.values():
            host = opening.get("host_wall")
            if host in wall_entities:
                wall_entity, wall = wall_entities[host]
                export_opening(model, body, wall_entity, opening, wall)

    if framing:
        panels = panels or {}
        material = create_lumber_material(model)  # one placeholder material, shared
        for fr in framing:
            panel = panels.get(fr.get("panel_id"))
            parent_wall_id = panel.get("parent_wall") if panel else None
            wall_pair = wall_entities.get(parent_wall_id) if parent_wall_id else None
            export_panel_framing(
                model,
                body,
                storey,
                panel,
                fr,
                wall_entity=wall_pair[0] if wall_pair else None,
                material=material,
            )

    # Authoring metadata LAST: create one owner history (after all api mutations,
    # so change-tracking doesn't stamp duplicates) and attach it to every root
    # object via direct assignment (ADR-004).
    create_owner_history(model)
    apply_owner_history(model)

    if out_path:
        model.write(out_path)
    return model
