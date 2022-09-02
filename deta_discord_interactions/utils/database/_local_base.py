import functools
from typing import Callable
from deta.base import Util

# In the future: Perhaps get rid of this and use pytest fixtures instead?

operations = {
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

def parse_filter(filter_: dict) -> Callable:
    result = []
    for condition, value in filter_.items():
        if isinstance(value, list):
            raise Exception("Nested queries are not supported yet")

        if "?" in condition:
            key, operation = condition.rsplit("?", 1)
            result.append(functools.partial(operations[operation], key, value))
        else:
            key = condition
            result.append(lambda record: record.get(key) == value)

    def match_record(record: dict) -> bool:
        return all(function(record) for function in result)
    return match_record

def parse_filters(filters: list[dict]) -> Callable:
    filters = [parse_filter(filter_) for filter_ in filters]
    def match_record(record: dict) -> bool:
        return any(filter_(record) for filter_ in filters)
    return match_record


_shared_inventory = {}
class Base:
    def __init__(self, name):
        self.name = name
        self.inventory = _shared_inventory.setdefault(name, {})

    def get(self, key):
        return self.inventory.get(key)

    def insert(self, data, key):
        if key in self.inventory:
            raise Exception(f"Item with key '{key}' already exists")
        self.inventory[key] = data

    def update(self, updates, key):
        if key not in self.inventory:
            raise Exception(f"Key '{key}' not found")

        for attribute, value in updates.items():
            if isinstance(value, Util.Trim):
                del self.inventory[key][attribute]
            elif isinstance(value, Util.Increment):
                self.inventory[key][attribute] += value.val
            elif isinstance(value, Util.Append):  # Despite the name, value.val is always a list here
                self.inventory[key][attribute].extend(value.val)
            elif isinstance(value, Util.Prepend):
                # self.inventory[key][attribute].insert(0, value.val)
                self.inventory[key][attribute] = (
                    value.val + self.inventory[key][attribute]
                )
            else:
                self.inventory[key][attribute] = value

    def put_many(self, items):
        for item in items:
            self.inventory[item.pop('key')] = item

    def put(self, item, key):
        self.inventory[key] = item

    def fetch(self, query, limit, last):
        results = []
        match_condition = parse_filters(query)
        for key, value in self.inventory.items():
            val = value.copy()
            val["key"] = key
            if match_condition(val):
                results.append(val)
        if isinstance(last, str):
            index = next((i for i, record in enumerate(results) if record['key'] == last), None)
            results = results[index:]
        if limit and limit > 0:
            results = results[:limit]
        return results
