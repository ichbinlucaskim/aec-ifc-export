"""Validate an IFC file with ifcopenshell.validate and print any errors."""
from __future__ import annotations

import sys

import ifcopenshell.validate


def main(path: str) -> int:
    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(path, logger)
    errors = [m for m in logger.statements if m.get("level") == "Error"]
    print(f"{path}: {len(errors)} errors")
    for e in errors[:20]:
        print("  ", e)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
