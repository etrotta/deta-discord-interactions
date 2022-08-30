from __future__ import annotations

import typing
from deta.base import Util
from deta_discord_interactions.utils.database.bound_meta import BoundMeta
if typing.TYPE_CHECKING:
    from deta_discord_interactions.utils.database.record import Record


bind_methods = [
    '__add__', '__delitem__', '__iadd__', '__imul__', '__setitem__',
    # 'append',
    'clear', 'extend', 'insert', 'pop', 'remove', 'reverse', 'sort',
]

class BoundList(list, metaclass=BoundMeta, bind_methods=bind_methods):
    """List which updates the database when modified.
    If you wish to make changes without affecting the database, use list.copy()
    """
    def __init__(self, bound_key: str, bound_record: 'Record', *argument):
        super().__init__(*argument)
        self._bound_key = bound_key
        self._bound_record = bound_record

    def append(self, item):
        super().append(item)
        if self._bound_record._preparing_statement:
            self._bound_record._prepared_statement[
                self._bound_key
            ] = list(self)
        else:
            self._bound_record._database.update(
                self._bound_record.key,
                {self._bound_key: Util.Append(item)}
            )

    def _sync(self, method, value, *args, **kwargs):
        if method.startswith("__i") and isinstance(value, BoundList):
            self = value
        if self._bound_record._preparing_statement:
            self._bound_record._prepared_statement[
                self._bound_key
            ] = list(self)
        else:
            self._bound_record._database.update(
                self._bound_record.key,
                {self._bound_key: list(self)}
            )
        return value

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
