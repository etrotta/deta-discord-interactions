from deta_discord_interactions import DiscordInteractionsBlueprint, Message

bp = DiscordInteractionsBlueprint

# You can use a decorator syntax to define subcommands
comic = bp.command_group("comic")


@comic.command()
def xkcd(ctx, number: int):
    return f"https://xkcd.com/{number}/"


@comic.command()
def homestuck(ctx, number: int):
    return f"https://homestuck.com/story/{number}"


# Subcommand groups are also supported
base = bp.command_group("base", "Convert a number between bases")

base_to = base.subgroup("to", "Convert a number into a certain base")
base_from = base.subgroup("from", "Convert a number out of a certian base")


@base_to.command(name="bin")
def base_to_bin(ctx, number: int):
    "Convert a number into binary"
    return Message(bin(number), ephemeral=True)


@base_to.command(name="hex")
def base_to_hex(ctx, number: int):
    "Convert a number into hexadecimal"
    return Message(hex(number), ephemeral=True)


@base_from.command(name="bin")
def base_from_bin(ctx, number: str):
    "Convert a number out of binary"
    return Message(int(number, base=2), ephemeral=True)


@base_from.command(name="hex")
def base_from_hex(ctx, number: str):
    "Convert a number out of hexadecimal"
    return Message(int(number, base=16), ephemeral=True)


# Subcommands have the same access to context
whatismy = bp.command_group("whatismy")


@whatismy.command()
def name(ctx):
    return ctx.author.display_name


@whatismy.command()
def discriminator(ctx):
    return ctx.author.discriminator


# And so do subcommands in subcommand groups
top_level = bp.command_group("toplevel")
second_level = top_level.subgroup("secondlevel")


@second_level.command()
def thirdlevel(ctx):
    return Message(f"Hello, {ctx.author.display_name}!")
