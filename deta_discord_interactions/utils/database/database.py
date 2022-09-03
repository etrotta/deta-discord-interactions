from __future__ import annotations

import os
import typing
import importlib
from typing import Optional, Union
from datetime import datetime
import inspect

from deta_discord_interactions.utils.database.exceptions import KeyNotFound
from deta_discord_interactions.utils.database.record import Record
from deta_discord_interactions.utils.database.adapters import transform_identifier
from deta_discord_interactions.utils.database.query import Query

from deta_discord_interactions.models.utils import LoadableDataclass

from deta import Base

if os.getenv("DO_NOT_SYNC_DETA_BASE"):
    from deta_discord_interactions.utils.database._local_base import Base

# Instructions for encoding / decoding data not supported by deta base
EMPTY_DICTIONARY_STRING = "$EMPTY_DICT"  # Setting a field to an empty dictionaries seems to set it to `null`
DATETIME_STRING = "$ENCODED_DATETIME"  # Ease datetime conversion
ESCAPE_STRING = "$NOOP"  # Do not mess up if the user input 'just happen' to start with a $COMMAND


class Database:
    def __init__(self, name: str = "_discord_interactions"):
        self.__base = Base(name)

    def __getitem__(self, key: str) -> Record:
        key = transform_identifier(key)
        return Record(key, database=self, data=None)

    def __setitem__(self, key: str, data: dict) -> None:
        key = transform_identifier(key)
        self.put(key, data)
    
    @typing.overload
    def encode_entry(self, record: dict) -> dict: ...
    @typing.overload
    def encode_entry(self, record: list) -> list: ...
    def encode_entry(self, record: Union[dict, list]) -> Union[dict, list]:
        "Converts values so that we can store it properly in Deta Base"
        if isinstance(record, dict):
            it = record.items()
        else:
            it = enumerate(record)
        for key, value in it:
            if isinstance(value, dict) and dict(value) == {}:  # Empty dict becomes `null` on deta base
                record[key] = EMPTY_DICTIONARY_STRING
            elif isinstance(value, LoadableDataclass):  # Convert our dataclasses
                record[key] = value.to_dict()
            elif inspect.isfunction(value):  # Converts functions to references based on their source file and name
                # This should only be used if this record is only going to be stored for a short amount of time
                # And even then, it should be using sparingly
                record[key] = {
                    "__database_load_method": False,
                    "__module": value.__module__,
                    "__name": value.__name__,
                }
            elif isinstance(value, (list, dict)):  # Make sure we hit nested fields
                record[key] = self.encode_entry(value)
            elif isinstance(value, str) and value.startswith("$"):  # essentially escape '$'
                record[key] = ESCAPE_STRING + value
            elif isinstance(value, datetime):  # Ease datetime conversion
                record[key] = DATETIME_STRING + value.isoformat()
        return record

    @typing.overload
    def decode_entry(self, record: dict) -> dict: ...
    @typing.overload
    def decode_entry(self, record: list) -> list: ...
    def decode_entry(self, record):
        "Converts back some changes that we have to make when storing"
        if isinstance(record, dict):
            it = record.items()
        else:
            it = enumerate(record)
        for key, value in it:
            if isinstance(value, (list, dict)):  # Make sure we hit nested fields
                record[key] = self.decode_entry(value)
                try:  # Try to convert into a python object. Ignore if it isns't one or if it fails to load
                    method = value['__database_load_method']
                    module = value['__module']
                    name = value['__name']
                    py_obj = getattr(importlib.import_module(module), name)
                    if method:
                        record[key] = getattr(py_obj, method)(record[key])
                    else:
                        record[key] = py_obj
                except Exception:
                    pass
            elif isinstance(value, str):
                if value == EMPTY_DICTIONARY_STRING:  # Empty dict becomes `null` on deta base
                    record[key] = {}
                elif value.startswith(DATETIME_STRING):  # Ease datetime conversion
                    record[key] = datetime.fromisoformat(value.removeprefix(DATETIME_STRING))
                elif value.startswith(ESCAPE_STRING):  # Escape strings starting with `$`
                    record[key] = value.removeprefix(ESCAPE_STRING)
        return record


    def get(self, key: str) -> Record:
        "Retrieve a record based on it's key."
        key = transform_identifier(key)
        data = self.__base.get(key)
        if data is None:
            data = {}
        return Record(key, self, self.decode_entry(data))

    def insert(self, key: str, data: dict) -> Record:
        "Insert a record and return it."
        key = transform_identifier(key)
        self.__base.insert(self.encode_entry(data), key)
        return Record(key, self, data)
    
    def put(self, key: str, data: dict) -> Record:
        "Insert or update a record and return it."
        key = transform_identifier(key)
        self.__base.put(self.encode_entry(data), key)
        return Record(key, self, data)
    
    def put_many(self, data: list[dict]) -> list[Record]:
        "Insert or update multiple records and return them."
        for record in data:
            if 'key' not in record:
                raise ValueError("All dictionaries must have a `key` when using put_many.")
            self.encode_entry(record)
        self.__base.put_many(data)
        return [Record(record['key'], self, self.decode_entry(record)) for record in data]

    def fetch(
        self,
        query: Union[Query, dict, list[dict], None] = None,
        limit: int = 1000,
        last: Optional[str] = None,
    ) -> list[Record]:
        """Returns multiple items from the database based on a query.
        See the `Query` class and https://docs.deta.sh/docs/base/queries/ for more information
        """
        if isinstance(query, Query):
            query = query.to_list()
        result = self.__base.fetch(query, limit=limit, last=last)
        return [
            Record(record['key'], self, self.decode_entry(record))
            for record in result.items
        ]
    
    def update(self, key: str, updates: dict) -> Record:
        """Updates a Record.

        Note: The returned Record may have to fetch back the updated data
        """
        key = transform_identifier(key)

        self.encode_entry(updates)

        try:
            self.__base.update(updates, key)
        except Exception as err:
            import re
            reason = err.args[0] if err.args else ''
            if isinstance(reason, str) and re.fullmatch(r"Key \'.*\' not found", reason):
                raise KeyNotFound(reason)
            else:
                raise
        return Record(key, self, None)