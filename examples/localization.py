from deta_discord_interactions import DiscordInteractionsBlueprint

bp = DiscordInteractionsBlueprint()

answers_localized = {"de": "Welt", "fr": "monde", "da": "verden"}


@bp.command(
    name_localizations={"de": "hallo", "fr": "bonjour", "da": "hej"},
    description_localizations={
        "de": "Hallo Welt",
        "fr": "Bonjour le monde",
        "da": "Hej verden",
    },
)
def hello(ctx):
    """Hello world"""
    return answers_localized.get(ctx.locale, "World")
