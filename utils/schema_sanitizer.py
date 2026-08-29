"""
Schema Sanitizer Utility for Google Gemini API Structured Outputs.
Converts Pydantic v2 JSON schemas into clean, OpenAPI 3.0 / Gemini-compliant schema dicts
by inlining nested $defs/$ref pointers and stripping incompatible keys (additionalProperties, title, default, $defs).
"""

import copy
from typing import Type, Any, Dict, Union
from pydantic import BaseModel


def _dereference_refs(node: Any, defs: Dict[str, Any], seen: set = None) -> Any:
    """
    Recursively replaces all '$ref': '#/$defs/ModelName' with the inlined definition.
    Handles self-referential or cyclic definitions safely.
    """
    if seen is None:
        seen = set()

    if isinstance(node, dict):
        if "$ref" in node:
            ref_path = node["$ref"]
            ref_name = ref_path.split("/")[-1]
            if ref_name in defs and ref_name not in seen:
                target_def = copy.deepcopy(defs[ref_name])
                resolved = _dereference_refs(target_def, defs, seen | {ref_name})
                for k, v in node.items():
                    if k != "$ref":
                        resolved[k] = _dereference_refs(v, defs, seen)
                return resolved
            else:
                return {"type": "object"}

        return {k: _dereference_refs(v, defs, seen) for k, v in node.items() if k != "$defs"}

    elif isinstance(node, list):
        return [_dereference_refs(item, defs, seen) for item in node]

    return node


def _clean_unsupported_keys(node: Any) -> Any:
    """
    Recursively strips keys incompatible with Gemini API structured output:
    - additionalProperties
    - $defs / definitions
    - title
    - default
    """
    FORBIDDEN_KEYS = {"additionalProperties", "$defs", "definitions", "title", "default"}

    if isinstance(node, dict):
        cleaned = {}
        for k, v in node.items():
            if k in FORBIDDEN_KEYS:
                continue
            cleaned[k] = _clean_unsupported_keys(v)
        return cleaned

    elif isinstance(node, list):
        return [_clean_unsupported_keys(item) for item in node]

    return node


def sanitize_schema_for_gemini(pydantic_model: Union[Type[BaseModel], Dict[str, Any]]) -> Dict[str, Any]:
    """
    Converts a Pydantic v2 BaseModel into a clean, OpenAPI 3.0 / Gemini-compatible JSON schema.
    Inlines all nested $defs/$ref models and removes additionalProperties, title, default, and $defs.

    Args:
        pydantic_model: The Pydantic model class (or an existing schema dict).

    Returns:
        Dict[str, Any]: A sanitized JSON Schema dictionary ready for types.GenerateContentConfig.
    """
    if isinstance(pydantic_model, dict):
        raw_schema = copy.deepcopy(pydantic_model)
    elif hasattr(pydantic_model, "model_json_schema"):
        raw_schema = pydantic_model.model_json_schema()
    elif hasattr(pydantic_model, "schema"):
        raw_schema = pydantic_model.schema()
    else:
        raise TypeError(f"Expected a Pydantic BaseModel class or dict, got {type(pydantic_model)}")

    defs = raw_schema.get("$defs", raw_schema.get("definitions", {}))

    # 1. Inline all $ref pointers
    inlined_schema = _dereference_refs(raw_schema, defs)

    # 2. Strip all forbidden keys
    sanitized_schema = _clean_unsupported_keys(inlined_schema)

    return sanitized_schema
