"""Not sure if particularly useful without any asserts, but at least checks that no exceptions are raised while creating and dumping stuff."""
from deta_discord_interactions import DiscordInteractions
from deta_discord_interactions.context import ApplicationCommandType

def test_register_command(discord: DiscordInteractions):
    @discord.command()
    def ping(ctx):
        return "pong"

    discord.update_commands()


def test_register_user_command(discord: DiscordInteractions):
    @discord.command(type=ApplicationCommandType.USER)
    def ping(ctx):
        return "pong"

    @discord.command(type=ApplicationCommandType.USER)
    def ping2(ctx):
        return "pong"

    @discord.command(name="user test", type=ApplicationCommandType.USER)
    def ping3(ctx):
        return "pong"

    discord.update_commands()


def test_register_message_command(discord: DiscordInteractions):
    @discord.command(type=ApplicationCommandType.MESSAGE)
    def ping(ctx):
        return "pong"

    @discord.command(type=ApplicationCommandType.MESSAGE)
    def ping2(ctx):
        return "pong"

    @discord.command(name="user test", type=ApplicationCommandType.MESSAGE)
    def ping3(ctx):
        return "pong"

    discord.update_commands()


def test_register_subcommand(discord: DiscordInteractions):
    group = discord.command_group("group")

    @group.command()
    def subcommand(ctx):
        return "pong"

    discord.update_commands()


def test_register_options(discord: DiscordInteractions):
    @discord.command()
    def ping(ctx, option1: str, option2: float, option3: str = ""):
        return f"pong"

    discord.update_commands()


def test_register_subcommand_options(discord: DiscordInteractions):
    group = discord.command_group("group")

    @group.command()
    def subcommand(ctx, option1: str, option2: float, option3: str = ""):
        return "pong"

    discord.update_commands()
