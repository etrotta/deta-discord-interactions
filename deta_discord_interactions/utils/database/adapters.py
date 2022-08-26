from typing import Any, Literal
from deta_discord_interactions.models import (
    User,
    Channel,
    Message,
)
from deta_discord_interactions.command import Command

def transform_identifier(obj: Any, on_unknown: Literal['raise', 'ignore'] = 'raise') -> str:
    """Transforms a identifier based on a set of rules.
    If it is not recognized, `unknown` defines whenever to `raise` or `ignore`
    `raise`: Raises a `ValueError` Exception
    `ignore`: Returns as-is
    """
    # Discord models -> their identifiers
    if isinstance(obj, User):  # Also applies for Member
        return f'_discord_interactions_user_{obj.id}'
    elif isinstance(obj, Channel):
        return f'_discord_interactions_channel_{obj.id}'
    elif isinstance(obj, Message):
        if obj.id is None:
            raise Exception("Cannot use a Message without an ID")
        return f'_discord_interactions_message_{obj.id}'
    # Commands -> their name.
    # Not sure if I should support that one, but for now I will
    elif isinstance(obj, Command):
        return f'_discord_interactions_command_{obj.name}'
    # Integers and Strings can stay as-is
    elif isinstance(obj, (int, str)):
        return obj
    # Anything else ERROR
    else:
        if on_unknown == 'raise':
            raise Exception(f"Unsupported object: {obj!r}, type {type(obj)}")
        else:
            return obj
