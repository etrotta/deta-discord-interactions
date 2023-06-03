from deta_discord_interactions import (
    DiscordInteractions,
    Client,
    Message,
    CommandOptionType,
    Context,
    Member,
)
from deta_discord_interactions.models.embed import Embed


discord = DiscordInteractions()

test_client = Client(discord)

# Simplest type of command: respond with a string
@discord.command()
def ping(ctx, pong: str = "pong"):
    "Respond with a friendly 'pong'!"
    return f"Pong {pong}!"


print(test_client.run("ping"))
print(test_client.run("ping", pong="spam"))

groupy = discord.command_group("groupy")

@groupy.command()
def group(ctx, embed: bool):
    if embed:
        return Message(Embed(title="Group"))
    else:
        return "Groupy group"


print(test_client.run("groupy", "group", True))
print(test_client.run("groupy", "group", False))


@discord.command()
def uses_context(ctx):
    return f"Your name is {ctx.author.display_name}"


context = Context(author=Member(username="Bob"))

with test_client.context(context):
    print(test_client.run("uses_context"))

# For more examples, see the Tests
