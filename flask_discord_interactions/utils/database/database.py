from __future__ import annotations

import typing
from typing import Optional, Union
from flask_discord_interactions.utils.database.record import Record
from flask_discord_interactions.utils.database.adapters import transform_identifier

if typing.TYPE_CHECKING:
    from flask_discord_interactions.utils.database.query import Query

try:
    from deta import Base
    from deta.base import Util
    HAS_BASE = True
except ImportError:
    # import warnings
    # warnings.warn("Failed to import deta. Any database operations will fail.")
    HAS_BASE = False


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
    
    def get(self, key: str) -> Record:
        "Retrieve a record based on it's key."
        if self.__base is None:
            raise AssertionError("Cannot access the Database without deta installed!")
        key = transform_identifier(key)
        return Record(key, self, self.__base.get(key) or {})

    def insert(self, key: str, data: dict) -> Record:
        "Insert a record and return it."
        if self.__base is None:
            raise AssertionError("Cannot access the Database without deta installed")
        key = transform_identifier(key)
        self.__base.insert(data, key)
        return Record(key, self, data)
    
    def put(self, key: str, data: dict) -> Record:
        "Insert or update a record and return it."
        if self.__base is None:
            raise AssertionError("Cannot access the Database without deta installed")
        key = transform_identifier(key)
        self.__base.put(data, key)
        return Record(key, self, data)
    
    def put_many(self, data: list[dict]) -> list[Record]:
        "Insert or update multiple records and return them."
        if self.__base is None:
            raise AssertionError("Cannot access the Database without deta installed")
        if not all('key' in record for record in data):
            raise ValueError("All dictionaries must have a `key` when using put_many.")
        self.__base.put_many(data)
        return [Record(record['key'], self, record) for record in data]

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
            Record(record['key'], self, record)
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
        self.__base.update(updates, key)
        return Record(key, self, None)