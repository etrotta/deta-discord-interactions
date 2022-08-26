"""Query utilities

Example usage:
# Minimal usage
query = Query(Field('name') == 'bob')

query = Query('gaming' in Field('hobbies'))

query = Query(Field('key').startswith('discord_interactions_user_'))

# Combining multiple statements:
query = Query(  # AND
  Field('name') == 'bob',
  Field('age').in_range(10, 18)
)
query = Query([  # AND
  Field('name') == 'bob',
  Field('age').in_range(10, 18)
])
query = Query(  # OR
  [Field('name') == 'bob'],
  [Field('age').in_range(10, 18)]
)
query = Query(Field('name') == 'bob') | Query(Field('age') > 10)  # Combine as OR
query = Query(Field('person.name') == 'bob') & Query(Field('age') > 10)  # Combine as AND
query = Query(Field('name') == 'bob') & Query(Field('age') > 10)

# To evaluate a query
results = database.fetch(query)
"""

from typing import Union
from flask_discord_interactions.utils.database.adapters import transform_identifier

class Field:
    "Proxy class for setting filters"
    def __init__(self, attribute: str):
        self.attribute = attribute

    def __eq__(self, other) -> dict:
        other = transform_identifier(other, error='ignore')
        return {
            self.attribute: other
        }

    def __ne__(self, other) -> dict:
        other = transform_identifier(other, error='ignore')
        return {
            f'{self.attribute}?ne': other
        }

    def __lt__(self, other) -> dict:
        return {
            f'{self.attribute}?lt': other
        }

    def __gt__(self, other) -> dict:
        return {
            f'{self.attribute}?gt': other
        }

    def __lte__(self, other) -> dict:
        return {
            f'{self.attribute}?lte': other
        }

    def __gte__(self, other) -> dict:
        return {
            f'{self.attribute}?gte': other
        }

    def startswith(self, other) -> dict:
        return {
            f'{self.attribute}?pfx': other
        }
    def prefix(self, other) -> dict:
        return {
            f'{self.attribute}?pfx': other
        }

    def in_range(self, start: int, stop: int) -> dict:
        return {
            f'{self.attribute}?r': [start, stop]
        }

    def __contains__(self, other) -> dict:
        other = transform_identifier(other, error='ignore')
        return {
            f'{self.attribute}?contains': other
        }
    def contains(self, other) -> dict:
        other = transform_identifier(other, error='ignore')
        return {
            f'{self.attribute}?contains': other
        }

    def not_contains(self, other) -> dict:
        other = transform_identifier(other, error='ignore')
        return {
            f'{self.attribute}?not_contains': other
        }


class Query:
    """Query class for querying Deta Base.
    the `operations` may be either lists of dictionaries or just dictionaries, but not mixed
    """
    def __init__(self, *operations: Union[list[dict], dict]):
        if len(operations) == 1 and all(isinstance(op, dict) for op in operations):
            operations = [operations]
        self.operations = operations
    
    def __and__(self, other: 'Query') -> 'Query':  # &
        return Query([*self.operations, *other.operations])

    def __or__(self, other: 'Query') -> 'Query':  # |
        return Query([*self.operations, *other.operations])

    def to_list(self) -> list[dict]:
        return self.operations