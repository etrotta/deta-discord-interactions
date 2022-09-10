from __future__ import annotations

import functools
import json
import pathlib
from typing import Callable, Optional

from deta.base import Util

from deta_discord_interactions.utils.database.bound_meta import BoundMeta

# In the future: Perhaps get rid of this and use pytest fixtures instead?

operations = {
    # no prefix = eq
    "ne": lambda key, value, record: record.get(key) != value,

    "lt": lambda key, value, record: record.get(key) < value,
    "lte": lambda key, value, record: record.get(key) <= value,
    "gt": lambda key, value, record: record.get(key) > value,
    "gte": lambda key, value, record: record.get(key) >= value,

    "pfx": lambda key, value, record: record.get(key).startswith(value),
    "r": lambda key, value, record: record.get(key) in range(*value),
    "contains": lambda key, value, record: value in record.get(key),
    "not_contains": lambda key, value, record: value not in record.get(key),
}

def parse_filter(filter_: dict) -> Callable[[dict], bool]:
    result = []
    for condition, value in filter_.items():
        if isinstance(value, list):
            raise Exception("Nested queries are not supported for local base yet")

        if "?" in condition:
            key, operation = condition.rsplit("?", 1)
            result.append(functools.partial(operations[operation], key, value))
        else:
            key = condition
            result.append(lambda record, _key=key, _value=value: record.get(_key) == _value)

    def match_record(record: dict) -> bool:
        return all(function(record) for function in result)
    return match_record

def parse_filters(filters: Optional[list[dict]]) -> Callable[[dict], bool]:
    if filters is None:
        return lambda _: True
    parsed_filters = [parse_filter(filter_) for filter_ in filters]

    def match_record(record: dict) -> bool:
        return any(filter_(record) for filter_ in parsed_filters)

    return match_record

class FetchResponse:
    def __init__(self, count=0, last=None, items=[]):
        self.count = count
        self.last = last
        self.items = items


_memory_inventory = {}
class Base:
    def __init__(self, name: str, sync_disk: bool = False):
        self.name = name
        if sync_disk:
            self.inventory = DiskBaseBackend(name)
        else:
            self.inventory = _memory_inventory.setdefault(name, {})

    def get(self, key):
        obj = self.inventory.get(key)
        if obj:
            obj = json.loads(obj)
        return obj

    def insert(self, data, key):
        if key in self.inventory:
            raise Exception(f"Item with key '{key}' already exists")
        self.inventory[key] = json.dumps(data)

    def update(self, updates, key):
        if key not in self.inventory:
            raise Exception(f"Key '{key}' not found")

        obj = json.loads(self.inventory[key])

        for attribute, value in updates.items():
            if isinstance(value, Util.Trim):
                del obj[attribute]
            elif isinstance(value, Util.Increment):
                obj[attribute] += value.val
            elif isinstance(value, Util.Append):  # Despite the name, value.val is always a list here
                obj[attribute].extend(value.val)
            elif isinstance(value, Util.Prepend):
                obj[attribute] = (
                    value.val + obj[attribute]
                )
            else:
                obj[attribute] = value
        
        self.inventory[key] = json.dumps(obj)

    def put_many(self, items):
        items = {record.pop('key'): json.dumps(record) for record in (item.copy() for item in items)}
        self.inventory.update(items)

    def put(self, item, key):
        self.inventory[key] = json.dumps(item)

    def fetch(self, query, limit, last):
        results = []
        match_condition = parse_filters(query)
        for key, value in self.inventory.items():
            obj = json.loads(value)
            obj["key"] = key
            if match_condition(obj):
                results.append(obj)
        if isinstance(last, str):
            index = next((i for i, record in enumerate(results) if record['key'] == last), None)
            results = results[index:]
        if limit and limit > 0:
            results = results[:limit]
        return FetchResponse(items=results)




bind_methods = [
    '__delitem__', '__setitem__', 'clear', 'get', 'pop', 'popitem', 'update', 'setdefault'
]

import pathlib
import os


class DiskBaseBackend(dict, metaclass=BoundMeta, bind_methods=bind_methods):
    """Database backend that saves to disk whenever it's modified."""
    def __init__(self, database_name: str):
        try:
            with (pathlib.Path(os.getenv("DISCORD_INTERACTIONS_DATABASE_FOLDER")) / database_name).open('r') as file:
                super().__init__(json.load(file))
        except Exception:
            super().__init__()
        self._file_name = database_name
        if os.getenv("DISCORD_INTERACTIONS_DATABASE_FORMAT_NICELY", False):
            self._options = {
                "indent": 4,
                "sort_keys": True,
            }
        else:
            self._options = {
                "indent": None,
                "separators": (',', ':'),
            }


    def _sync(self, method, value, *args, **kwargs):
        with (pathlib.Path(os.getenv("DISCORD_INTERACTIONS_DATABASE_FOLDER")) / self._file_name).open('w') as file:
            json.dump(dict(self), file, **self._options)
        return value
