from deta_discord_interactions import (
    DiscordInteractionsBlueprint,
    Message,
    ActionRow,
    SelectMenu,
    SelectMenuOption,
)


bp = DiscordInteractionsBlueprint()


@bp.command()
def favorite_color(ctx):
    "Choose your favorite color!"
    return Message(
        "What is your favorite color?",
        components=[
            ActionRow(
                components=[
                    SelectMenu(
                        placeholder="Choose your favorite!",
                        custom_id="fav_color",
                        options=[
                            SelectMenuOption(
                                label="Red",
                                value="red",
                                description="The color of stop signs 🛑",
                                emoji={"name": "🔴"},
                            ),
                            SelectMenuOption(
                                label="Green",
                                value="green",
                                description="The color of plants 🌿",
                                emoji={"name": "🟢"},
                            ),
                            SelectMenuOption(
                                label="Blue",
                                value="blue",
                                description="The color of the ocean 🌊",
                                emoji={"name": "🔵"},
                            ),
                        ],
                        max_values=2,
                    )
                ]
            )
        ]
    )


@bp.custom_handler()
def handle_favorite_color(ctx):
    return Message(f"Favorite colors: {', '.join(ctx.values)}", ephemeral=True)
