"""
Normalization engine: converts arbitrary JSON payloads from any external system
into a standard LogEntry-compatible dict using a configurable FieldMapping.
"""
from typing import Any, Dict, Optional
from app.models.endpoint import FieldMapping
from app.models.log import LogCategory


CATEGORY_MAP: Dict[str, LogCategory] = {
    # ERROR-like
    "error": LogCategory.ERROR,
    "err": LogCategory.ERROR,
    "critical": LogCategory.ERROR,
    "fatal": LogCategory.ERROR,
    "exception": LogCategory.ERROR,
    "failure": LogCategory.ERROR,
    "failed": LogCategory.ERROR,
    # AUTH-like
    "auth": LogCategory.AUTH,
    "authentication": LogCategory.AUTH,
    "authorization": LogCategory.AUTH,
    "login": LogCategory.AUTH,
    "logout": LogCategory.AUTH,
    "security": LogCategory.AUTH,
    "token": LogCategory.AUTH,
    # CRUD-like
    "crud": LogCategory.CRUD,
    "create": LogCategory.CRUD,
    "created": LogCategory.CRUD,
    "update": LogCategory.CRUD,
    "updated": LogCategory.CRUD,
    "delete": LogCategory.CRUD,
    "deleted": LogCategory.CRUD,
    "write": LogCategory.CRUD,
    "mutation": LogCategory.CRUD,
    "insert": LogCategory.CRUD,
    "patch": LogCategory.CRUD,
    "put": LogCategory.CRUD,
    "post": LogCategory.CRUD,
    # QUERY-like
    "query": LogCategory.QUERY,
    "read": LogCategory.QUERY,
    "search": LogCategory.QUERY,
    "get": LogCategory.QUERY,
    "fetch": LogCategory.QUERY,
    "list": LogCategory.QUERY,
    "find": LogCategory.QUERY,
    "select": LogCategory.QUERY,
    # API-like
    "api": LogCategory.API,
    "http": LogCategory.API,
    "request": LogCategory.API,
    "webhook": LogCategory.API,
    "external": LogCategory.API,
    "callback": LogCategory.API,
    # SYSTEM-like (default)
    "info": LogCategory.SYSTEM,
    "information": LogCategory.SYSTEM,
    "debug": LogCategory.SYSTEM,
    "trace": LogCategory.SYSTEM,
    "verbose": LogCategory.SYSTEM,
    "system": LogCategory.SYSTEM,
    "monitor": LogCategory.SYSTEM,
    "health": LogCategory.SYSTEM,
    "warn": LogCategory.SYSTEM,
    "warning": LogCategory.SYSTEM,
    "notice": LogCategory.SYSTEM,
}


def resolve_path(data: Dict[str, Any], path: str) -> Any:
    """Resolve a dot-notation path in a nested dict. Returns None if not found."""
    if not path:
        return None
    parts = path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
        if current is None:
            return None
    return current


def normalize_category(raw: Any) -> LogCategory:
    """Map arbitrary category strings/HTTP codes to LogCategory enum."""
    if raw is None:
        return LogCategory.SYSTEM
    # Handle numeric HTTP status codes
    try:
        code = int(raw)
        if code >= 400:
            return LogCategory.ERROR
        elif code >= 200:
            return LogCategory.CRUD
        return LogCategory.SYSTEM
    except (ValueError, TypeError):
        pass
    key = str(raw).lower().strip()
    return CATEGORY_MAP.get(key, LogCategory.SYSTEM)


def normalize(source: Dict[str, Any], mapping: FieldMapping, app_name: str = "") -> Dict[str, Any]:
    """
    Normalize an arbitrary JSON payload into a LogEntry-compatible dict.

    - Fields are extracted using dot-notation paths from the mapping config.
    - Category values are mapped to LogCategory enum via CATEGORY_MAP.
    - Description is auto-generated from available fields if not mapped.
    - Unmapped top-level keys are folded into metadata.
    - Original category string and source app are stored in system_context.
    """
    def extract(path: Optional[str]) -> Any:
        if not path:
            return None
        return resolve_path(source, path)

    user_id_val = extract(mapping.user_id)
    module_val = extract(mapping.module) or app_name or "unknown"
    action_val = extract(mapping.action) or "event"
    entity_val = extract(mapping.entity)
    raw_category = extract(mapping.category)
    description_val = extract(mapping.description)
    metadata_val = extract(mapping.metadata)

    category = normalize_category(raw_category)

    # Auto-generate description if not mapped
    if not description_val:
        parts = [str(action_val)]
        if entity_val:
            parts.append(f"on {entity_val}")
        if raw_category:
            parts.append(f"[{raw_category}]")
        description_val = " ".join(parts)

    # Collect top-level keys that are NOT consumed by any mapping path
    mapped_top_keys = {
        path.split(".")[0]
        for path in [
            mapping.user_id, mapping.module, mapping.action,
            mapping.entity, mapping.category, mapping.description, mapping.metadata,
        ]
        if path
    }
    extra = {k: v for k, v in source.items() if k not in mapped_top_keys}

    # Merge extra unmapped fields into the metadata dict
    if isinstance(metadata_val, dict):
        metadata_val = {**metadata_val, **extra}
    elif metadata_val is not None:
        metadata_val = {"value": metadata_val, **extra}
    else:
        metadata_val = extra

    return {
        "user_id": str(user_id_val) if user_id_val is not None else "unknown",
        "module": str(module_val),
        "action": str(action_val),
        "entity": str(entity_val) if entity_val is not None else None,
        "category": category,
        "description": str(description_val)[:500] if description_val else None,
        "metadata": metadata_val,
        "system_context": {
            "source_app": app_name,
            "raw_category": str(raw_category) if raw_category is not None else None,
        },
    }
