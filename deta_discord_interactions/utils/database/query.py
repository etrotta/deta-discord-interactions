"""Query utilities

Example usage:
# Minimal usage
query = Query(Field('name') == 'bob')

query = Query('gaming' in Field('hobbies'))

query = Query(Field('key').startswith('discord_interactions_user_'))

# Combining multiple statements:
# AND
query = Query(
  Field('name') == 'bob',
  Field('age').in_range(10, 18)
)
# Alternatively for AND:
query = Query(Field('person.name') == 'bob') & Query(Field('age') > 10)  # Combine as AND

# OR
q1 = Query(  
  Field('name') == 'bob'
) 
q2 = Query(
  Field('age').in_range(10, 18)
)
query = q1 | q2

# To evaluate a query
results = database.fetch(query)
"""

from typing import NoReturn

class Field:
    "Proxy class for setting filters"
    def __init__(self, attribute: str):
        self.attribute = attribute

    def __eq__(self, other) -> dict:
        return {
            self.attribute: other
        }

    def __ne__(self, other) -> dict:
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
        return {
            f'{self.attribute}?contains': other
        }
    def contains(self, other) -> dict:
        return {
            f'{self.attribute}?contains': other
        }

    def not_contains(self, other) -> dict:
        return {
            f'{self.attribute}?not_contains': other
        }


class Query:
    """Query class for querying Deta Base.
    
    Example usage:
    >>> Query(Field("key").startswith("bird_"))  # Key starts with bird_
    >>> Query(Field("species") == "cat", Field("age") < 5)  # Cat AND less than 5 years old
    >>> Query(Field("species") == "cat") | Query(Field("species") == "dog")  # Dog OR Cat
    """
    def __init__(self, *operations: dict):
        self.operations = {}
        for operation in operations:
            if not isinstance(operation, dict):
                raise TypeError("All operations passed to Query() must be dictionaries")
            # Check if there are any operations already in use
            if repeated := (self.operations.keys() & operation.keys()):
                _repeated = {k: (self.operations.get(k), operation.get(k)) for k in repeated}
                raise ValueError(f"Repeated operations found in Query: {_repeated}")
            self.operations.update(operation)

    def __and__(self, other: 'Query') -> 'Query':  # &
        # if isinstance(other, Query):
        if type(other) == Query:
            return Query(self.operations, other.operations)
            # raise NotImplementedError()
        raise TypeError("Can only AND a query with another Query")

    def __or__(self, other: 'Query') -> 'ORQuery':  # |
        # if isinstance(other, Query):
        if type(other) == Query:
            return ORQuery(self, other)
            # raise NotImplementedError()
        raise TypeError("Can only OR a query with another Query")

    def to_list(self) -> list[dict]:
        "Returns a list of length 1 containing this Query's operations"
        return [self.operations]


# tbh it only subclasses so that it may pass isinstance() checks,
# maybe I should be using a Protocol instead
class ORQuery(Query):
    """OR'ed Query class for querying Deta Bases. 
    Do not create directly - use Query(...) | Query(...) instead"""
    def __init__(self, *queries: Query):
        self.queries = queries

    def __and__(self, _) -> NoReturn:  # &
        raise Exception("Cannot add an AND statement to an OR query")

    def __or__(self, other: 'Query') -> 'ORQuery':  # |
        if isinstance(other, ORQuery):
            return ORQuery(*self.queries, *other.queries)
        elif isinstance(other, Query):
            return ORQuery(*self.queries, other)
        raise TypeError("Can only OR with another Query")

    def to_list(self) -> list[list[dict]]:
        "Returns a 1D list containing this queries's operations"
        return [query.operations for query in self.queries]
