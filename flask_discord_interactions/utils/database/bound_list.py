from __future__ import annotations

import typing
from typing import Any
if typing.TYPE_CHECKING:
    from flask_discord_interactions.utils.database.record import Record
from functools import wraps


class BoundList(list):
    """List which updates the database when modified.
    If you wish to make changes without affecting the database, use list.copy()
    Magic methods not supported yet. 
    Avoid using `del list[i]`, `dict += something` etc for now.
    """
    _BOUND_LIST_METHODS = ('pop', 'clear', 'extend', 'remove', 'reverse', 'sort')
    def __init__(self, bound_key: str, bound_record: 'Record', *argument):
        self._bound_key = bound_key
        self._bound_record = bound_record
        super().__init__(*argument)

    def append(self, item):
        super().append(item)
        if self._bound_record._preparing_statement:
            self._bound_record._prepared_statement[
                self._bound_key
            ] = list(self)
        else:
            self._bound_record._database.update(
                self._bound_record.key,
                {"$append": {self._bound_key: item}}
            )
    
    # def __getitem__(self, index):
    #     result = super().__getitem__(index)
    #     if not isinstance(index, int):
    #         return result
    #     if isinstance(result, list):
    #         result = BoundList(
    #             f'{self._bound_key}.{index}',
    #             self._bound_record,
    #             result,
    #         )
    #     elif isinstance(result, dict):
    #         from flask_discord_interactions.utils.database.bound_dict import BoundDict
    #         result = BoundDict(
    #             f'{self._bound_key}.{index}',
    #             self._bound_record,
    #             result,
    #         )
    #     return result

    def __getattribute__(self, __name: str) -> Any:
        if __name in self._BOUND_LIST_METHODS:
            function = super().__getattribute__(__name)
            @wraps(function)
            def wrapped(*args, **kwargs):
                result = function(*args, **kwargs)
                if self._bound_record._preparing_statement:
                    self._bound_record._prepared_statement[
                        self._bound_key
                    ] = list(self)
                else:
                    self._bound_record._database.update(
                        self._bound_record.key,
                        {self._bound_key: list(self)}
                    )
                return result
            return wrapped
        else:
            return super().__getattribute__(__name)
