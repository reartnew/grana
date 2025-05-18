"""Actions-related constants"""

__all__ = [
    "COMMON_ACTION_RESERVED_FIELD_NAMES",
    "TOP_LEVEL_ONLY_ACTION_RESERVED_FIELD_NAMES",
    "ACTION_RESERVED_FIELD_NAMES",
]

COMMON_ACTION_RESERVED_FIELD_NAMES: set[str] = {
    "name",
    "type",
}

TOP_LEVEL_ONLY_ACTION_RESERVED_FIELD_NAMES: set[str] = {
    "description",
    "expects",
    "selectable",
    "severity",
    "locals",
}

ACTION_RESERVED_FIELD_NAMES: set[str] = COMMON_ACTION_RESERVED_FIELD_NAMES | TOP_LEVEL_ONLY_ACTION_RESERVED_FIELD_NAMES
