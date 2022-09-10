from __future__ import annotations

import typing
import dataclasses
from typing import Any, Optional
from typing import TypeVar
from deta.base import Util
from deta_discord_interactions.utils.database.bound_list import BoundList
from deta_discord_interactions.utils.database.bound_dict import BoundDict
from deta_discord_interactions.utils.database.exceptions import FieldNotFoundError, KeyNotFound
if typing.TYPE_CHECKING:
    from deta_discord_interactions.utils.database.database import Database


class Record:
    """Base class used to interface with the Database.

    Direct usage is not recommended. Either:
    - Use AutoSyncRecord
    - Subclass and use with dataclasses @dataclass
    - Subclass and overwrite `__init__`, (classmethod) `from_database`, `to_dict`
    """
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def from_database(cls, key: str, database: 'Database', record: Optional[dict]) -> 'RecordType':
        if record is None:
            record = {}
        if dataclasses.is_dataclass(cls):
            data = {
                field.name: value for field in dataclasses.fields(cls)
                if (value := record.get(field.name)) is not None
            }
        else:
            data = {k: v for k, v in record if not k.startswith("_")}
        try:
            return cls(**data)
        except TypeError:
            raise TypeError(f"Error while loading class {cls!r}, parameters supplied: {data}")

    def to_dict(self) -> dict:
        if dataclasses.is_dataclass(self):
            data = dataclasses.asdict(self)
        else:
            data = {k: v for k, v in vars(self).items() if not k.startswith("_")}
        return data

# Typing stuff
Key = TypeVar("Key")
RecordType = TypeVar("RecordType", bound=Record)

RAISE_ERROR = object()  # Sentinel

class AutoSyncRecord(Record):
    "Record subclass that syncs database changes automatically"

    def __init__(self, key: Key, database: 'Database', data: Optional[dict]):
        self._key = key
        self._database = database
        self._data = data
        self._preparing_statement = False
        self._prepared_statement = {}

    @classmethod
    def from_database(cls, key: Key, database: 'Database', record: Optional[dict]) -> 'AutoSyncRecord':
        return cls(key, database, record)

    def to_dict(self) -> dict:
        self.sync_fields()
        return self._data.copy()

    def sync_fields(self, *, force: bool = False) -> None:
        if (self._data is None) or force:
            self._data = self._database.get(self._key)._data

    def convert_value(self, field: str, value: Any) -> Any:
        if isinstance(value, list):
            result = BoundList(field, self, value)
        elif isinstance(value, dict):
            result = BoundDict(field, self, value)
        else:
            result = value
        return result

    def set_field(self, field: str, value: Any) -> None:
        if self._preparing_statement:
            self._prepared_statement[field] = value
        else:
            try:
                self._database.update(self._key, {field: value})
            except KeyNotFound:
                self._database.put(self._key, {field: value})
            self._data = None

    def get_field(self, field: str, default: Any = RAISE_ERROR) -> Any:
        if field in self._prepared_statement:
            raise Exception("Cannot retrieve back prepared values before syncing with the database.")
        self.sync_fields()
        try:
            result = self._data[field]
        except KeyError:
            if default is RAISE_ERROR:
                raise FieldNotFoundError
            else:
                result = default
        result = self.convert_value(field, result)
        return result

    def delete_field(self, field: str) -> None:
        if self._preparing_statement:
            self._prepared_statement[field] = Util.Trim()
        else:
            del self._data[field]
            self._database.update(self._key, {field: Util.Trim()})

    def __enter__(self):
        self._preparing_statement = True
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._preparing_statement = False
        if exc_type is not None:
            import warnings
            warnings.warn("Aborting prepared operation since an Exception was raised.")
        elif self._prepared_statement:
            try:
                self._database.update(self._key, self._prepared_statement)
            except KeyNotFound:
                self._database.put(self._key, {})
                self._database.update(self._key, self._prepared_statement)
        self._prepared_statement = {}

    def __iter__(self):
        self.sync_fields()
        yield from self._data.items()

    def __getattr__(self, attribute: str) -> Any:
        if attribute.startswith("_"):
            raise Exception("Record fields must not start with `_`")
        try:
            return self.get_field(attribute)
        except KeyError:
            raise AttributeError

    def __setattr__(self, attribute: str, value: Any) -> None:
        if attribute.startswith("_"):
            return super().__setattr__(attribute, value)
        self.set_field(attribute, value)

    def __delattr__(self, attribute: str) -> None:
        self.delete_field(attribute)

    def __getitem__(self, key: str) -> Any:
        return self.get_field(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self.set_field(key, value)

    def __delitem__(self, key: str) -> None:
        self.delete_field(key)

    def setdefault(self, key: str, value: Any) -> Any:
        try:
            return self.get_field(key)
        except FieldNotFoundError:
            value = self.convert_value(key, value)
            self.set_field(key, value)
            return value
