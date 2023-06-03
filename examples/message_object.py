from deta_discord_interactions import (
    DiscordInteractionsBlueprint,
    Message,
    Embed,
    embed,
)

bp = DiscordInteractionsBlueprint()

@bp.command()
def just_content(ctx):
    "Just normal string content"
    return "Just return a string to send it as a message"


@bp.command()
def markdown(ctx):
    "Fancy markdown tricks"
    return "All *the* **typical** ~~discord~~ _markdown_ `works` ***too.***"


@bp.command(name="embed")
def embed_(ctx):
    "Embeds!"

    return Message(
        embed=Embed(
            title="Embeds!",
            description="Embeds can be specified as Embed objects.",
            fields=[
                embed.Field(
                    name="Can they use markdown?",
                    value="**Yes!** [link](https://google.com/)",
                ),
                embed.Field(
                    name="Where do I learn about how to format this object?",
                    value=(
                        "[Try this visualizer!]"
                        "(https://leovoel.github.io/embed-visualizer/)"
                    ),
                ),
            ],
        )
    )


@bp.command()
def dict_embed(ctx):
    "Embeds as dict objects!"

    return Message(
        embed={
            "title": "Embeds!",
            "description": "Embeds can also be specified as JSON objects.",
            "fields": [
                {
                    "name": "Can they use markdown?",
                    "value": "**Yes!** [link](https://google.com/)",
                },
                {
                    "name": "Where do I learn about how to format this object?",
                    "value": (
                        "[Try this visualizer!]"
                        "(https://leovoel.github.io/embed-visualizer/)"
                    ),
                },
            ],
        }
    )


@bp.command()
def ephemeral(ctx):
    "Ephemeral Message"

    return Message(
        "Ephemeral messages are only sent to the user who ran the command, "
        "and they go away after a short while.\n\n",
        ephemeral=True,
    )

# See also: Components, Embeds
