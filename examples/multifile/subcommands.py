from deta_discord_interactions import DiscordInteractionsBlueprint, Message


bp = DiscordInteractionsBlueprint()
group = bp.command_group("group", "First Group")
sub = group.subgroup("sub", "Sub Group")


@sub.command()
def echo(ctx, text: str):
    "Repeat a string"
    return Message(f"*Echooo 1!!!* {text}")
