"""DataClassLoader definition"""

import dataclasses
import itertools
import typing as t

from . import exceptions
from ...logging import WithLogger

try:
    from types import UnionType  # type: ignore[attr-defined]  # pylint: disable=no-name-in-module
except ImportError:
    UnionType = None  # type: ignore[assignment, misc]

NoneType = type(None)
T = t.TypeVar("T")

__all__ = [
    "DataClassLoader",
]


class TypeSentinel:
    """Types sentinel"""


@dataclasses.dataclass
class DataClassLoader(WithLogger):
    """Constructs data classes by type and data"""

    validate_types: bool = True
    cast_types_list: list[type] = dataclasses.field(default_factory=list)
    NUMERIC_TYPES: t.ClassVar[list[type]] = [int, float, complex]

    def from_dict(self, data_type: type[T], data: t.Mapping) -> T:
        """Create an instance from a dict."""
        return self._internal_from_dict(data_type=data_type, data=data, path="")

    def _internal_from_dict(self, data_type: type[T], data: t.Mapping, path: str) -> T:
        # Get a list of init fields
        dataclass_init_fields: list[dataclasses.Field] = [
            f for f in dataclasses.fields(data_type) if f.init  # type: ignore[arg-type]
        ]
        # Check unexpected fields
        if unexpected_field_names := set(data.keys()) - {f.name for f in dataclass_init_fields}:
            raise exceptions.UnexpectedDataError(keys=unexpected_field_names, path=path)

        dataclass_type_hints = t.get_type_hints(data_type)
        init_values: t.MutableMapping[str, t.Any] = {}
        for field in dataclass_init_fields:
            field_path: str = f"{path}/{field.name}"
            if field.name not in data:
                # Check if default is set for the field
                if any(attr != dataclasses.MISSING for attr in (field.default, field.default_factory)):
                    continue
                raise exceptions.MissingValueError(field_path)
            field_type_hint = dataclass_type_hints[field.name]
            value = self._make_value_for_type(
                data_type=field_type_hint,
                data=data[field.name],
                path=field_path,
            )
            if self.validate_types and not self._is_instance(value, field_type_hint):
                raise exceptions.TypeMatchError(path=field_path, data_type=field_type_hint, value=value)
            init_values[field.name] = value

        return data_type(**init_values)

    def _make_value_for_type(self, data_type: type, data: t.Any, path: str) -> t.Any:
        if self._is_optional(data_type) and data is None:
            return data
        if self._is_union(data_type):
            data = self._make_value_for_union_type(union_data_type=data_type, data=data, path=path)
        elif self._extract_origin_from_generic_collection(data_type) is not TypeSentinel:
            data = self._make_value_for_collection_type(collection_data_type=data_type, data=data, path=path)
        elif dataclasses.is_dataclass(self._get_origin_for_dataclass(data_type)) and isinstance(data, t.Mapping):
            data = self._internal_from_dict(data_type=data_type, data=data, path=path)
        for cast_type in self.cast_types_list:
            if self._is_subclass(data_type, cast_type):
                return data_type(data)
        return data

    def _make_value_for_union_type(self, union_data_type: type, data: t.Any, path: str) -> t.Any:
        union_types = self._extract_generic_args(union_data_type)
        if self._is_optional(union_data_type) and len(union_types) == 2:
            for sub_type in union_types:
                if sub_type is not NoneType:
                    return self._make_value_for_type(data_type=sub_type, data=data, path=path)
            raise ValueError(f"Only None types found for union: {union_data_type!r}")
        union_matches = {}
        for inner_type in union_types:
            try:
                value = self._make_value_for_type(data_type=inner_type, data=data, path=path)
            except Exception as e:
                self.logger.debug(f"Non-successful union member type attempt: {e!r}")
                continue
            if self._is_instance(value, inner_type):
                union_matches[inner_type] = value
        if len(union_matches) > 1:
            raise exceptions.StrictUnionTypeMatchError(matches=union_matches, path=path)
        if union_matches:
            _, value = union_matches.popitem()
            return value
        if not self.validate_types:
            return data
        raise exceptions.UnionTypeMatchError(data_type=union_data_type, value=data, path=path)

    def _make_value_for_collection_type(self, collection_data_type: type, data: t.Any, path: str) -> t.Any:
        data_type = data.__class__
        if isinstance(data, t.Mapping) and self._is_subclass(collection_data_type, t.Mapping):
            if mapping_subscription := self._extract_generic_args(collection_data_type):
                _, value_type = mapping_subscription
            else:
                value_type = t.Any
            return data_type(
                (
                    key,
                    self._make_value_for_type(
                        data_type=value_type,
                        data=value,
                        path=f"{path}/{key}",
                    ),
                )
                for key, value in data.items()
            )
        if isinstance(data, tuple) and self._is_subclass(collection_data_type, tuple):
            # Check empty tuple
            if not data:
                return data_type()
            collection_types: tuple = self._extract_generic_args(collection_data_type)
            if len(collection_types) == 2 and collection_types[1] == Ellipsis:
                return data_type(
                    self._make_value_for_type(
                        data_type=collection_types[0],
                        data=item,
                        path=f"{path}@{num}",
                    )
                    for num, item in enumerate(data)
                )
            return data_type(
                self._make_value_for_type(
                    data_type=data_type,
                    data=item,
                    path=f"{path}@{num}",
                )
                for num, (item, data_type) in enumerate(itertools.zip_longest(data, collection_types))
            )
        if isinstance(data, t.Collection) and self._is_subclass(collection_data_type, t.Collection):
            value_type_hints: tuple = self._extract_generic_args(collection_data_type) or (t.Any,)
            return data_type(
                self._make_value_for_type(
                    data_type=value_type_hints[0],
                    data=item,
                    path=f"{path}@{num}",
                )
                for num, item in enumerate(data)
            )
        return data

    @classmethod
    def _get_origin_for_dataclass(cls, data_type: type) -> t.Any:
        if dataclasses.is_dataclass(data_type):
            return data_type
        return t.get_origin(data_type)

    @classmethod
    def _is_optional(cls, data_type: type) -> bool:
        return cls._is_union(data_type) and NoneType in cls._extract_generic_args(data_type)

    @classmethod
    def _is_union(cls, data_type: type) -> bool:
        # Check "A | B" form
        if UnionType is not None and isinstance(data_type, UnionType):
            return True
        return cls._extract_origin_from_generic(data_type) == t.Union

    @classmethod
    def _extract_origin_from_generic(cls, data_type: type) -> type:
        return getattr(data_type, "__origin__", TypeSentinel)

    @classmethod
    def _extract_origin_from_generic_collection(cls, data_type: type) -> type:
        if (origin := cls._extract_origin_from_generic(data_type)) is not TypeSentinel:
            try:
                if issubclass(origin, t.Collection):
                    return origin
            except (TypeError, AttributeError):
                pass
        return TypeSentinel

    @classmethod
    def _extract_generic_args(cls, data_type: type) -> tuple:
        if getattr(data_type, "_special", False):
            return ()
        return getattr(data_type, "__args__", ())

    @classmethod
    def _is_subclass(cls, sub_type: type, base_type: type) -> bool:
        if (origin := cls._extract_origin_from_generic_collection(sub_type)) is not TypeSentinel:
            sub_type = origin
        try:
            return issubclass(sub_type, base_type)
        except TypeError:
            return False

    # pylint: disable=too-many-return-statements
    @classmethod
    def _is_instance(cls, value: t.Any, data_type: type) -> bool:
        # typing.Any is always good
        if data_type == t.Any:
            return True
        # Check built-in isinstance
        try:
            if isinstance(value, data_type):
                return True
        except TypeError:
            # E.g. when data_type is not a type
            pass
        # Check numbers
        if data_type in cls.NUMERIC_TYPES and (value_type := type(value)) in cls.NUMERIC_TYPES:
            return cls.NUMERIC_TYPES.index(value_type) <= cls.NUMERIC_TYPES.index(data_type)
        # Check unions
        if cls._is_union(data_type):
            return any(cls._is_instance(value, tp) for tp in cls._extract_generic_args(data_type))
        # Check generic collections
        if (origin := cls._extract_origin_from_generic_collection(data_type)) is not TypeSentinel:
            # Upper-level check first
            if not isinstance(value, origin):
                return False
            if not cls._extract_generic_args(data_type):
                return True
            # Tuple case
            if isinstance(value, tuple) and cls._is_subclass(data_type, tuple):
                tuple_types = cls._extract_generic_args(data_type)
                # Empty tuple
                if len(tuple_types) == 1 and tuple_types[0] == ():
                    return len(value) == 0
                # Tuple with `...`
                if len(tuple_types) == 2 and tuple_types[1] is Ellipsis:
                    return all(cls._is_instance(item, tuple_types[0]) for item in value)
                if len(tuple_types) != len(value):
                    return False
                return all(cls._is_instance(item, item_type) for item, item_type in zip(value, tuple_types))
            # Mapping case
            if isinstance(value, t.Mapping):
                key_type, val_type = cls._extract_generic_args(data_type) or (t.Any, t.Any)
                for key, val in value.items():
                    if not cls._is_instance(key, key_type) or not cls._is_instance(val, val_type):
                        return False
                return True
            # Other iterables
            if not isinstance(value, t.Iterable):
                return False
            value_type_hints: tuple = cls._extract_generic_args(data_type) or (t.Any,)
            return all(cls._is_instance(item, value_type_hints[0]) for item in value)
        # Check for generic over type (e.g. type[MyClass])
        if cls._extract_origin_from_generic(data_type) in (type, t.Type):
            type_subscription: type = cls._extract_generic_args(data_type)[0]
            return cls._is_subclass(value, type_subscription)
        return False
