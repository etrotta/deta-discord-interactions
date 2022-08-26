from __future__ import annotations

import typing
from typing import Any, Optional
from flask_discord_interactions.utils.database.bound_list import BoundList
from flask_discord_interactions.utils.database.bound_dict import BoundDict
if typing.TYPE_CHECKING:
    from flask_discord_interactions.utils.database.database import Database


class Record:
    def __init__(
        self,
        key: str,
        /,
        database: 'Database',
        data: Optional[dict] = None,
    ):
        self.key = key
        self.__database = database
        self.__data = data
        self.__preparing_statement = False
        self.__prepared_statement = {}

    def __enter__(self):
        self.__preparing_statement = True
        return self

    def __exit__(self, *args):
        self.__preparing_statement = False
        self.__database.update(self.key, self.__prepared_statement)
        self.__prepared_statement = {}

    def __dict__(self):
        if self.__data is None:
            self.__data = self.__database.get(self.key).__data
        return dict(self.__data)

    def __getattr__(self, attribute: str) -> Any:
        if self.__data is None:
            self.__data = self.__database.get(self.key).__data
        try:
            result = self.__data[attribute]
        except KeyError:
            raise AttributeError
        if isinstance(result, list):
            result = BoundList(attribute, self, result)
        elif isinstance(result, dict):
            result = BoundDict(attribute, self, result)
        return result

    def __setattr__(self, attribute: str, value: Any) -> None:
        if self.__preparing_statement:
            self.__prepared_statement[attribute] = value
        else:
            self.__database.update(self.key, {attribute: value})
            self.__data = None

    def __getitem__(self, key: str) -> Any:
        if self.__data is None:
            self.__data = self.__database.get(self.key).__data
        result = self.__data[key]
        if isinstance(result, list):
            result = BoundList(key, self, result)
        elif isinstance(result, dict):
            result = BoundDict(key, self, result)
        return result

    def __setitem__(self, key: str, value: Any) -> None:
        if self.__preparing_statement:
            self.__prepared_statement[key] = value
        else:
            self.__database.update(self.key, {key: value})
            self.__data = None

    def __delattr__(self, attribute: str) -> None:
        del self.__data[attribute]
        self.__database.update(self.key, {"$trim": {attribute: 1}})

    def setdefault(self, key: str, value: Any) -> Any:
        try:
            return self[key]
        except KeyError:
            if isinstance(value, list):
                value = BoundList(key, self, value)
            elif isinstance(value, dict):
                value = BoundDict(key, self, value)
            self[key] = value
            return value