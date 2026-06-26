.PHONY: setup test lint demo validate clean

setup:
	cd .. && python scripts/sync_licenses.py
	pip install -e ../aec-schema
	pip install -e ".[dev]"

test:
	python -m pytest tests/ -v

lint:
	ruff check src/ tests/

demo:
	python scripts/demo.py

validate:
	python scripts/validate_ifc.py examples/demo_framing.ifc

clean:
	rm -rf __pycache__ src/aec_ifc_export/__pycache__ tests/__pycache__ \
	       .pytest_cache .ruff_cache *.egg-info src/*.egg-info
