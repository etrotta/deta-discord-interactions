from datetime import datetime
import dataclasses
import functools
from typing import Callable, Literal
from deta_discord_interactions.models.message import Message

from deta_discord_interactions.context import Context

from deta_discord_interactions.utils.database import Database, LoadableDataclass

@dataclasses.dataclass
class CooldownRecord(LoadableDataclass):
    # command_name: str
    # bucket_type: str
    # cooldown_identifier: str
    expire_timestamp: int

database = Database("_discord_interactions_cooldown", record_type=CooldownRecord)

def cooldown(
    bucket_type: Literal["user", "guild", "channel"],
    duration: int,
    cooldown_message: str = "This command is in cooldown {cd_type_detail}. Try again in <t:{expire_timestamp}:R>.",
):
    """Add a Cooldown to a command.
    Parameters
    ----------
    bucket_type : str
        Who this cooldown applies to (each user, each channel or each guild)
    duration : int
        Cooldown duration in seconds
    cooldown_message: str 
        String to return if it is in cooldown.
        Default: "This command is in cooldown {cd_type_detail}. Try again in <t:{expire_timestamp}:R>.",
        expire_timestamp is the moment in which the cooldown will expire
        cd_type_detail is defined as:
        - "for you" if bucket_type == "user"
        - "for this channel" if bucket_type == "channel"
        - "for this discord server" if bucket_type == "guild"

    Example Usage:
    @command("work")
    @cooldown("user", 3600)
    def hourly_command(ctx):
        ...
    """
    def decorator(function: Callable) -> Callable:
        @functools.wraps(function)
        def wrapper(ctx: Context, *args, **kwargs):

            if bucket_type == "user":
                key = f"{ctx.command_name}_{ctx.author.id}"
                cd_detail = "for you"
            elif bucket_type == "guild":
                key = f"{ctx.command_name}_{ctx.guild_id}"
                cd_detail = "for this discord server"
            elif bucket_type == "channel":
                key = f"{ctx.command_name}_{ctx.channel_id}"
                cd_detail = "for this channel"

            record = database.get(key)
            now = round((datetime.now()).timestamp())

            if record is not None and record.expire_timestamp > now:
                msg = cooldown_message.format(cd_type_detail=cd_detail, expire_timestamp=record.expire_timestamp)
                return Message(msg, ephemeral=True)

            database.put(key, CooldownRecord(now + duration), expire_in=duration)

            return function(ctx, *args, **kwargs)
        return wrapper
    return decorator

__all__ = [
    "cooldown"
]