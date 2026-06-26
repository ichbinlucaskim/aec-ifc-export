"""
aec-ifc-export — convert AEC pipeline JSON to IFC4 (interoperability layer).

Maps walls -> IfcWall, openings -> IfcOpeningElement (IfcRelVoidsElement),
panels -> IfcElementAssembly, framing members -> IfcMember (IfcRelAggregates).
No Revit required — pure IfcOpenShell. Output opens in any IFC4 BIM viewer.

Usage
-----
    from aec_ifc_export import export_ifc
    model = export_ifc(walls, openings=omap, framing=framings, panels=pmap,
                       out_path="model.ifc")
"""
from __future__ import annotations

from .exporter import export_ifc

__all__ = ["export_ifc"]
__version__ = "0.1.0"
