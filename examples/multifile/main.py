import os

try:  # Only for syncing the commands - you should use `deta update -e` for the Micro environment variables
    from dotenv import load_dotenv
    load_dotenv('.env')
except ImportError:
    pass

from deta_discord_interactions import DiscordInteractions  # noqa: E402


app = DiscordInteractions()


from echo import bp as echo_bp  # noqa: E402
from reverse import bp as reverse_bp  # noqa: E402
from subcommands import bp as subcommands_bp  # noqa: E402


app.register_blueprint(echo_bp)
app.register_blueprint(reverse_bp)
app.register_blueprint(subcommands_bp)


if __name__ == "__main__":
    app.update_commands(guild_id=os.environ["TESTING_GUILD"])
