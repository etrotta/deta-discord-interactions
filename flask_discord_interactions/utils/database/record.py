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
        self._database = database
        self._data = data
        self._preparing_statement = False
        self._prepared_statement = {}

    def __enter__(self):
        self._preparing_statement = True
        return self

    def __exit__(self, *args):
        self._preparing_statement = False
        self._database.update(self.key, self._prepared_statement)
        self._prepared_statement = {}

    def __dict__(self):
        if self._data is None:
            self._data = self._database.get(self.key)._data
        return dict(self._data)

    def __getattr__(self, attribute: str) -> Any:
        if self._data is None:
            self._data = self._database.get(self.key)._data
        try:
            result = self._data[attribute]
        except KeyError:
            raise AttributeError
        if isinstance(result, list):
            result = BoundList(attribute, self, result)
        elif isinstance(result, dict):
            result = BoundDict(attribute, self, result)
        return result

    def __setattr__(self, attribute: str, value: Any) -> None:
        if attribute in ('key', 'setdefault') or attribute.startswith("_"):
            return super().__setattr__(attribute, value)
        if self._preparing_statement:
            self._prepared_statement[attribute] = value
        else:
            self._database.update(self.key, {attribute: value})
            self._data = None

    def __getitem__(self, key: str) -> Any:
        if self._data is None:
            self._data = self._database.get(self.key)._data
        result = self._data[key]
        if isinstance(result, list):
            result = BoundList(key, self, result)
        elif isinstance(result, dict):
            result = BoundDict(key, self, result)
        return result

    def __setitem__(self, key: str, value: Any) -> None:
        if self._preparing_statement:
            self._prepared_statement[key] = value
        else:
            self._database.update(self.key, {key: value})
            self._data = None

    def __delattr__(self, attribute: str) -> None:
        del self._data[attribute]
        self._database.update(self.key, {"$trim": {attribute: 1}})

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