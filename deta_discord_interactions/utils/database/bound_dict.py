from __future__ import annotations

import typing
from deta_discord_interactions.utils.database.bound_meta import BoundMeta
if typing.TYPE_CHECKING:
    from deta_discord_interactions.utils.database.record import Record


bind_methods = [
    '__delitem__', '__ior__', '__setitem__', 'clear', 'get', 'pop', 'popitem', 'update',
    'setdefault',
    'get', '__getitem__',
]

class BoundDict(dict, metaclass=BoundMeta, bind_methods=bind_methods):
    """Dictionary which updates the database when modified.
    If you wish to make changes without affecting the database, use dict.copy()
    """
    def __init__(self, bound_key: str, bound_record: 'Record', *argument):
        super().__init__(*argument)
        self._bound_key = bound_key
        self._bound_record = bound_record

    def _sync(self, method, value, *args, **kwargs):
        # 'Getter' methods
        if method in ('get', '__getitem__', 'setdefault'):
            key = kwargs.get('key') if 'key' in kwargs else args[0]
            if isinstance(value, list):
                from deta_discord_interactions.utils.database.bound_list import BoundList
                value = BoundList(
                    f'{self._bound_key}.{key}',
                    self._bound_record,
                    value,
                )
            elif isinstance(value, dict):
                value = BoundDict(
                    f'{self._bound_key}.{key}',
                    self._bound_record,
                    value,
                )

        # Make sure we keep up with inplace methods
        if method.startswith("__i") and isinstance(value, BoundDict):
            self = value

        # 'Setter' methods
        if method not in ('get', '__getitem__'):
            if self._bound_record._preparing_statement:
                self._bound_record._prepared_statement[
                    self._bound_key
                ] = dict(self)
            else:
                self._bound_record._database.update(
                    self._bound_record._key,
                    {self._bound_key: dict(self)}
                )
        return value
