"""Data schemas, validation utilities, and protocol contracts."""

import json
import os
from typing import Dict, Any, Optional

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "schemas")


def load_schema(schema_name: str) -> Dict[str, Any]:
    """Load JSON schema from the schemas directory."""
    if not schema_name.endswith(".json"):
        schema_name += ".json"
    path = os.path.join(SCHEMA_DIR, schema_name)
    if not os.path.exists(path):
        root_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "interfaces", "schemas", schema_name)
        if os.path.exists(root_path):
            path = root_path
        else:
            raise FileNotFoundError(f"Schema not found: {schema_name}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_payload(payload: Dict[str, Any], schema_name: str) -> bool:
    """Basic structural validation against required keys in schema."""
    schema = load_schema(schema_name)
    required = schema.get("required", [])
    return all(key in payload for key in required)
