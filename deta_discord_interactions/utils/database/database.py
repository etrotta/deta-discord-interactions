from __future__ import annotations

from typing import Optional, Union
import typing
import os
from deta_discord_interactions.utils.database.exceptions import KeyNotFound
from deta_discord_interactions.utils.database.record import Record
from deta_discord_interactions.utils.database.adapters import transform_identifier
from deta_discord_interactions.utils.database.query import Query

from datetime import datetime

try:
    from deta import Base
    from deta.base import Util
    HAS_BASE = True
except ImportError:
    # import warnings
    # warnings.warn("Failed to import deta. Any database operations will fail.")
    HAS_BASE = False

if os.getenv("DO_NOT_SYNC_DETA_BASE"):
    HAS_BASE = True
    from deta_discord_interactions.utils.database._local_base import Base

# Instructions for encoding / decoding data not supported by deta base
EMPTY_DICTIONARY_STRING = "$EMPTY_DICT"  # Setting a field to an empty dictionaries seems to set it to `null`
DATETIME_STRING = "$ENCODED_DATETIME"  # Ease datetime conversion
ESCAPE_STRING = "$NOOP"  # Do not mess up if the user input 'just happen' to start with a $COMMAND


class Database:
    def __init__(self, *, name: str = "_discord_interactions"):
        if HAS_BASE:
            self.__base = Base(name)
        else:
            self.__base = None

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
            if isinstance(value, (list, dict)):  # Make sure we hit nested fields
                record[key] = self.encode_entry(value)
            elif value == {}:  # Empty dict becomes `null` on deta base
                record[key] = EMPTY_DICTIONARY_STRING
            elif isinstance(value, str) and value.startswith("$"):  # essentially escape '$'
                record[key] = ESCAPE_STRING + value
            elif isinstance(value, datetime):  # Ease datetime conversion
                record[key] = DATETIME_STRING + datetime.toisoformat()
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
            elif isinstance(value, str):  # Ease datetime conversion
                if value.startswith(ESCAPE_STRING):
                    record[key] = value.removeprefix(ESCAPE_STRING)
                elif value == EMPTY_DICTIONARY_STRING:  # Empty dict becomes `null` on deta base
                    record[key] = {}
                elif value.startswith(DATETIME_STRING):
                    record[key] = datetime.fromisoformat(value.removeprefix(DATETIME_STRING))
        return record


    def get(self, key: str) -> Record:
        "Retrieve a record based on it's key."
        if self.__base is None:
            raise AssertionError("Cannot access the Database without deta installed!")
        key = transform_identifier(key)
        data = self.__base.get(key)
        if data is None:
            data = {}
        return Record(key, self, self.decode_entry(data))

    def insert(self, key: str, data: dict) -> Record:
        "Insert a record and return it."
        if self.__base is None:
            raise AssertionError("Cannot access the Database without deta installed")
        key = transform_identifier(key)
        self.__base.insert(self.encode_entry(data), key)
        return Record(key, self, data)
    
    def put(self, key: str, data: dict) -> Record:
        "Insert or update a record and return it."
        if self.__base is None:
            raise AssertionError("Cannot access the Database without deta installed")
        key = transform_identifier(key)
        self.__base.put(self.encode_entry(data), key)
        return Record(key, self, data)
    
    def put_many(self, data: list[dict]) -> list[Record]:
        "Insert or update multiple records and return them."
        if self.__base is None:
            raise AssertionError("Cannot access the Database without deta installed")
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
        if self.__base is None:
            raise AssertionError("Cannot access the Database without deta installed")
        if isinstance(query, Query):
            query = query.to_list()
        result = self.__base.fetch(query, limit=limit, last=last)
        return [
            Record(record['key'], self, self.decode_entry(record))
            for record in result.items
        ]
    
    def update(self, key: str, updates: dict) -> Record:
        """Updates a Record.
        
        Special operations supported:
            $increment, to increase or reduce a value
            $append, to add to the end of a list
            $prepend, to add to the start of a list
            $trim, to remove an attribute. Still requires any value for consistency.
        Example usage:
            update(key, {"name": "bob"})
            update(key, {"last_seen": datetime.datetime.now().isoformat()})
            update(key, {"$append": {"notes": "Uses deta"}})
            update(key, {"$increment": {"commands_used": 1}})
            update(key, {"$increment": {"warning_chances_left": -1}})
            update(key, {"$trim": {"warning_chances_left": 1}})
        
        Note: The returned Record must fetch back the updated data
        """
        if self.__base is None:
            raise AssertionError("Cannot access the Database without deta installed")
        key = transform_identifier(key)
        special = ('$increment', '$append', '$prepend', '$trim')
        def parse_special(dict_key, value):
            "Parse special operations"
            if dict_key == '$increment':
                return Util.Increment(value)
            elif dict_key == '$append':
                return Util.Append(value)
            elif dict_key == '$prepend':
                return Util.Prepend(value)
            elif dict_key == '$trim':
                return Util.Trim()

        def travel(dictionary: dict):
            "Modify the dictionary to replace special keys"
            for dict_key, value in dictionary.items():
                if dict_key in special:
                    dictionary.pop(dict_key)
                    for col, val in value.items():
                        dictionary[col] = parse_special(dict_key, val)
                elif isinstance(value, dict):
                    travel(value)
                elif isinstance(value, list):
                    for sub in value:
                        travel(sub)
        
        travel(updates)
        self.encode_entry(updates)
        try:
            self.__base.update(updates, key)
        except Exception as err:
            import re
            reason = err.args[0] if err.args else ''
            if re.fullmatch(r"Key \'.*\' not found", reason):
                raise KeyNotFound(reason)
            else:
                raise
        return Record(key, self, None)