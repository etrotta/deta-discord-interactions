from deta_discord_interactions import DiscordInteractions

bp = DiscordInteractions()

# Simplest type of command: respond with a string
@bp.command()
def ping(ctx):
    "Respond with a friendly 'pong'!"
    return "Pong!"


# See main.py for how to actually run a bot