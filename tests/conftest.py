"""Shared fixtures — walls, openings, and framing assemblies.

Two panels on walls at DIFFERENT world locations and orientations (one wall
running along X at the origin, one running along Y at x=5000) so geometry tests
can assert real world-spread, not just schema validity. The framing dict mirrors
framing-synth output (framing.schema.json): panel-LOCAL member coordinates.
"""
import pytest


def _members(prefix: str) -> list[dict]:
    """A panel's framing in panel-local coords (plates, studs, opening members)."""
    return [
        {"id": f"{prefix}-m1", "type": "plate", "role": "bottom_plate",
         "start": {"x": 0, "y": 0, "z": 0}, "end": {"x": 3000, "y": 0, "z": 0},
         "section": "2x6", "length": 3000},
        {"id": f"{prefix}-m2", "type": "plate", "role": "top_plate",
         "start": {"x": 0, "y": 0, "z": 2362}, "end": {"x": 3000, "y": 0, "z": 2362},
         "section": "2x6", "length": 3000},
        {"id": f"{prefix}-m3", "type": "stud", "role": "standard_stud",
         "start": {"x": 0, "y": 0, "z": 38}, "end": {"x": 0, "y": 0, "z": 2362},
         "section": "2x6", "length": 2324},
        {"id": f"{prefix}-m4", "type": "stud", "role": "standard_stud",
         "start": {"x": 400, "y": 0, "z": 38}, "end": {"x": 400, "y": 0, "z": 2362},
         "section": "2x6", "length": 2324},
        {"id": f"{prefix}-m5", "type": "king", "role": "king_stud",
         "start": {"x": 843, "y": 0, "z": 38}, "end": {"x": 843, "y": 0, "z": 2362},
         "section": "2x6", "length": 2324},
        {"id": f"{prefix}-m6", "type": "jack", "role": "jack_stud",
         "start": {"x": 881, "y": 0, "z": 38}, "end": {"x": 881, "y": 0, "z": 2138},
         "section": "2x6", "length": 2100},
        {"id": f"{prefix}-m7", "type": "header", "role": "header",
         "start": {"x": 843, "y": 0, "z": 2138}, "end": {"x": 2157, "y": 0, "z": 2138},
         "section": "2x6", "length": 1314},
        {"id": f"{prefix}-m8", "type": "sill", "role": "sill",
         "start": {"x": 900, "y": 0, "z": 938}, "end": {"x": 2100, "y": 0, "z": 938},
         "section": "2x4", "length": 1200},
        {"id": f"{prefix}-m9", "type": "cripple", "role": "cripple_stud",
         "start": {"x": 1200, "y": 0, "z": 2278}, "end": {"x": 1200, "y": 0, "z": 2362},
         "section": "2x6", "length": 84},
    ]


@pytest.fixture
def sample_walls():
    """Two exterior walls at different locations/orientations (X-run, Y-run)."""
    return [
        {
            "schema_version": "0.1.0", "id": "wall-000",
            "start": {"x": 0, "y": 0}, "end": {"x": 3000, "y": 0},
            "thickness": 171.0, "type": "exterior", "load_bearing": True,
            "adjacent_rooms": ["living_0"], "hosted_openings": ["window_0"],
        },
        {
            "schema_version": "0.1.0", "id": "wall-001",
            "start": {"x": 5000, "y": 0}, "end": {"x": 5000, "y": 4000},
            "thickness": 171.0, "type": "exterior", "load_bearing": True,
            "adjacent_rooms": ["living_0", "bed_0"], "hosted_openings": [],
        },
    ]


@pytest.fixture
def sample_openings():
    """One window hosted on wall-000 (wall-relative position)."""
    return {
        "window_0": {
            "schema_version": "0.1.0", "id": "window_0", "type": "window",
            "host_wall": "wall-000", "position": 1500, "width": 1200,
            "height": 1200, "swing_direction": "none",
        }
    }


@pytest.fixture
def sample_panels():
    """panel-001 on the X-running wall, panel-002 on the Y-running wall at x=5000."""
    return {
        "panel-001": {
            "schema_version": "0.1.0", "id": "panel-001", "parent_wall": "wall-000",
            "start": {"x": 0, "y": 0}, "end": {"x": 3000, "y": 0},
            "length": 3000, "height": 2438, "openings": [],
            "panel_type": "exterior", "load_bearing": True,
        },
        "panel-002": {
            "schema_version": "0.1.0", "id": "panel-002", "parent_wall": "wall-001",
            "start": {"x": 5000, "y": 0}, "end": {"x": 5000, "y": 3000},
            "length": 3000, "height": 2438, "openings": [],
            "panel_type": "exterior", "load_bearing": True,
        },
    }


@pytest.fixture
def sample_framing():
    """Two panels' framing (panel-local coords); each exercises every member type."""
    return [
        {"schema_version": "0.1.0", "panel_id": "panel-001",
         "members": _members("a"), "member_count": len(_members("a"))},
        {"schema_version": "0.1.0", "panel_id": "panel-002",
         "members": _members("b"), "member_count": len(_members("b"))},
    ]
