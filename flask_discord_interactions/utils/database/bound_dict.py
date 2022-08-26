import typing
from typing import Any
if typing.TYPE_CHECKING:
    from flask_discord_interactions.utils.database.record import Record
from functools import wraps


class BoundDict(dict):
    """Dictionary which updates the database when modified.
    If you wish to make changes without affecting the database, use dict.copy()
    Most magic methods are not supported yet.
    Avoid using `del dict[key]`, `dict |= something` etc for now.
    """
    __BOUND_DICT_METHODS = ('pop', 'clear', 'update', 'popitem', 'setdefault') # and __setitem__
    __TRACKED_DICT_METHODS = ('get', 'setdefault')  # and __getitem__

    def __init__(self, bound_key: str, bound_record: 'Record', *argument):
        super().__init__(*argument)
        self.__bound_key = bound_key
        self.__bound_record = bound_record

    def __check_bind(self, obj, key):
        if isinstance(obj, list):
            from flask_discord_interactions.utils.database.bound_list import BoundList
            obj = BoundList(
                f'{self.__bound_key}.{key}',
                self.__bound_record,
                obj,
            )
        elif isinstance(obj, dict):
            obj = BoundDict(
                f'{self.__bound_key}.{key}',
                self.__bound_record,
                obj,
            )
        return obj

    def __getitem__(self, key):
        result = super().__getitem__(key)
        return self.__check_bind(result, key)
    
    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if self.__bound_record.__preparing_statement:
            self.__bound_record.__prepared_statement[
                self.__bound_key
            ] = dict(self)
        else:
            self.__bound_record.__database.update(
                self.__bound_record.key,
                {self.__bound_key: dict(self)}
            )

    def __getattribute__(self, __name: str) -> Any:
        if __name in self.__TRACKED_DICT_METHODS or __name in self.__BOUND_DICT_METHODS:
            function = super().__getattribute__(__name)
            @wraps(function)
            def wrapped(*args, **kwargs):
                result = function(*args, **kwargs)
                if __name in self.__BOUND_LIST_METHODS:
                    if self.__bound_record.__preparing_statement:
                        self.__bound_record.__prepared_statement[
                            self.__bound_key
                        ] = dict(self)
                    else:
                        self.__bound_record.__database.update(
                            self.__bound_record.key,
                            {self.__bound_key: dict(self)}
                        )
                if __name in self.__TRACKED_DICT_METHODS:
                    result = self.__check_bind(result, args[0])
                return result
            return wrapped
        else:
            return super().__getattribute__(__name)
