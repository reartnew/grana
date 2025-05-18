"""Actions-related constants"""

__all__ = [
    "ACTION_RESERVED_FIELD_NAMES",
]

ACTION_RESERVED_FIELD_NAMES: set[str] = {
    "name",
    "type",
    "description",
    "expects",
    "selectable",
    "severity",
    "locals",
}
