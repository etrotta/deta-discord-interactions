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
    __BOUND_LIST_METHODS = ('pop', 'clear', 'extend', 'remove', 'reverse', 'sort')
    def __init__(self, bound_key: str, bound_record: 'Record', *argument):
        self.__bound_key = bound_key
        self.__bound_record = bound_record
        super().__init__(*argument)

    def append(self, item):
        super().append(item)
        if self.__bound_record.__preparing_statement:
            self.__bound_record.__prepared_statement[
                self.__bound_key
            ] = list(self)
        else:
            self.__bound_record.__database.update(
                self.__bound_record.key,
                {"$append": {self.__bound_key: item}}
            )
    
    # def __getitem__(self, index):
    #     result = super().__getitem__(index)
    #     if not isinstance(index, int):
    #         return result
    #     if isinstance(result, list):
    #         result = BoundList(
    #             f'{self.__bound_key}.{index}',
    #             self.__bound_record,
    #             result,
    #         )
    #     elif isinstance(result, dict):
    #         from flask_discord_interactions.utils.database.bound_dict import BoundDict
    #         result = BoundDict(
    #             f'{self.__bound_key}.{index}',
    #             self.__bound_record,
    #             result,
    #         )
    #     return result

    def __getattribute__(self, __name: str) -> Any:
        if __name in self.__BOUND_LIST_METHODS:
            function = super().__getattribute__(__name)
            @wraps(function)
            def wrapped(*args, **kwargs):
                result = function(*args, **kwargs)
                if self.__bound_record.__preparing_statement:
                    self.__bound_record.__prepared_statement[
                        self.__bound_key
                    ] = list(self)
                else:
                    self.__bound_record.__database.update(
                        self.__bound_record.key,
                        {self.__bound_key: list(self)}
                    )
                return result
            return wrapped
        else:
            return super().__getattribute__(__name)
