from __future__ import annotations

import typing
from typing import Any
if typing.TYPE_CHECKING:
    from deta_discord_interactions.utils.database.record import Record
from functools import wraps


class BoundDict(dict):
    """Dictionary which updates the database when modified.
    If you wish to make changes without affecting the database, use dict.copy()
    Most magic methods are not supported yet.
    Avoid using `del dict[key]`, `dict |= something` etc for now.
    """
    _BOUND_DICT_METHODS = ('pop', 'clear', 'update', 'popitem', 'setdefault') # and __setitem__
    _TRACKED_DICT_METHODS = ('get', 'setdefault')  # and __getitem__

    def __init__(self, bound_key: str, bound_record: 'Record', *argument):
        super().__init__(*argument)
        self._bound_key = bound_key
        self._bound_record = bound_record

    def _check_bind(self, obj, key):
        if isinstance(obj, list):
            from deta_discord_interactions.utils.database.bound_list import BoundList
            obj = BoundList(
                f'{self._bound_key}.{key}',
                self._bound_record,
                obj,
            )
        elif isinstance(obj, dict):
            obj = BoundDict(
                f'{self._bound_key}.{key}',
                self._bound_record,
                obj,
            )
        return obj

    def __getitem__(self, key):
        result = super().__getitem__(key)
        return self._check_bind(result, key)
    
    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if self._bound_record._preparing_statement:
            self._bound_record._prepared_statement[
                self._bound_key
            ] = dict(self)
        else:
            self._bound_record._database.update(
                self._bound_record.key,
                {self._bound_key: dict(self)}
            )

    def __getattribute__(self, __name: str) -> Any:
        if __name in ('_TRACKED_DICT_METHODS', '_BOUND_DICT_METHODS'):
            return super().__getattribute__(__name)

        if __name in self._TRACKED_DICT_METHODS or __name in self._BOUND_DICT_METHODS:
            function = super().__getattribute__(__name)
            @wraps(function)
            def wrapped(*args, **kwargs):
                result = function(*args, **kwargs)
                if __name in self._BOUND_DICT_METHODS:  
                    # Methods that modify the dictionary
                    if self._bound_record._preparing_statement:
                        # Prepare a database update operation
                        self._bound_record._prepared_statement[
                            self._bound_key
                        ] = dict(self)
                    else:
                        # Updates the database data right way
                        self._bound_record._database.update(
                            self._bound_record.key,
                            {self._bound_key: dict(self)}
                        )
                    # Updates the in-memory data
                    self._bound_record._data[self._bound_key] = dict(self)
                if __name in self._TRACKED_DICT_METHODS:
                    # Methods that may return something
                    result = self._check_bind(result, args[0])
                return result
            return wrapped
        else:
            return super().__getattribute__(__name)
