from deta.base import Util

class Base:
    def __init__(self, name):
        self.name = name
        self.inventory = {}

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
            elif isinstance(value, Util.Append):
                self.inventory[key][attribute].append(value.val)
            elif isinstance(value, Util.Prepend):
                self.inventory[key][attribute].insert(0, value.val)
            else:
                self.inventory[key][attribute] = value

    def put_many(self, items):
        for item in items:
            self.inventory[item.pop('key')] = item

    def put(self, item, key):
        self.inventory[key] = item

    def fetch(self, query, limit, last):
        raise NotImplementedError()