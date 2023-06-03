import enum
import math
import threading

import requests

from deta_discord_interactions import (
    DiscordInteractionsBlueprint,
    Message,
    Attachment,
    Member,
    Channel,
    Role,
    Option,
    embed,
)

bp = DiscordInteractionsBlueprint

# To specify options, include them with type annotations, just like Discord.py
# The annotations dict is used to provide a description for each option
# (they default to "no description")
@bp.command(annotations={"message": "The message to repeat"})
def repeat(ctx, message: str = "Hello!"):
    "Repeat the message (and escape mentions)"
    return Message(
        f"{ctx.author.display_name} says {message}!",
        allowed_mentions={"parse": []},
    )


# You can use str, int, or bool
@bp.command()
def add_one(ctx, number: int):
    return Message(str(number + 1), ephemeral=True)


@bp.command()
def and_gate(ctx, a: bool, b: bool):
    return f"{a} AND {b} is {a and b}"


@bp.command()
def sin(ctx, x: float):
    return f"sin({x}) = {math.sin(x)}"


# For using the "choices" field, you can use an Enum
class Animal(enum.Enum):
    Dog = "dog"
    Cat = "cat"


@bp.command(annotations={"choice": "Your favorite animal"})
def favorite(ctx, choice: Animal):
    "What is your favorite animal?"
    return f"{ctx.author.display_name} chooses {choice}!"


# This is also handy if you want to use the same options across multiple
# commands
@bp.command(annotations={"choice": "The animal you hate the most"})
def hate(ctx, choice: Animal):
    "What is the animal you hate the most?"
    return f"{ctx.author.display_name} hates {choice}s D:."


# You can also use IntEnum to receive the value as an integer
class BigNumber(enum.IntEnum):
    thousand = 1_000
    million = 1_000_000
    billion = 1_000_000_000
    trillion = 1_000_000_000_000


@bp.command(annotations={"number": "A big number"})
def big_number(ctx, number: BigNumber):
    "Print out a large number"
    return f"One more than the number is {number+1}."


# For User, Channel, and Role options, your function is passed an object
# that provides information about the resource
# You can access data about users with the context object
@bp.command(annotations={"user": "The user to show information about"})
def avatar_of(ctx, user: Member):
    "Show someone else's user info"
    return Message(
        embed=embed.Embed(
            title=user.display_name,
            description="Avatar Info",
            fields=[
                embed.Field("username", f"**{user.username}**#{user.discriminator}"),
                embed.Field("User ID", user.id),
            ],
            image=embed.Media(user.avatar_url),
        )
    )


@bp.command()
def has_role(ctx, user: Member, role: Role):
    if role.id in user.roles:
        return f"Yes, user {user.display_name} has role {role.name}."
    else:
        return f"No, user {user.display_name} does not have role {role.name}."


@bp.command()
def channel_info(ctx, channel: Channel):
    return Message(
        embed={
            "title": channel.name,
            "fields": [{"name": "Channel ID", "value": channel.id}],
        }
    )


# The Attachment object has some information about the attachment, including the URL
@bp.command()
def image(ctx, attachment: Attachment):
    return Message(
        embed={
            "title": attachment.filename,
            "description": "Image Info",
            "fields": [
                {
                    "name": "File Size",
                    "value": f"{attachment.size / 1024} KB",
                },
                {"name": "URL", "value": attachment.url},
            ],
            "image": {"url": attachment.url},
        }
    )


# To handle the attachment body itself, use a library like `requests` to fetch the resource
@bp.command()
def textfile(ctx, attachment: Attachment):
    response = requests.get(attachment.url)
    response.raise_for_status()

    return response.text


# Side note: background threads do not work on deta
# (yet Discord enforces that you give an initial response within 3 seconds)
@bp.command()
def hexdump(ctx, attachment: Attachment):
    response = requests.get(attachment.url)
    response.raise_for_status()

    dump = "```\n"
    for line in response.iter_content(chunk_size=16):
        dump += " ".join(f"{x:02x}" for x in line) + "\n"

        if len(dump) > 1900:
            dump += "...\n"
            break

    dump += "```"
    return dump

# You can also pass in a list of Option objects
@bp.command(
    options=[
        Option(
            name="message",
            type=str,
            description="The message to repeat",
            required=True,
            min_length=2,
            max_length=8,
        ),
        Option(
            name="times",
            type=int,
            description="How many times to repeat the message",
            required=True,
        ),
    ]
)
def repeat_many(ctx, message: str, times: int):
    return " ".join([message] * times)
