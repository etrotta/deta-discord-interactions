from deta_discord_interactions import DiscordInteractionsBlueprint
from deta_discord_interactions.context import Context, ApplicationCommandType

bp = DiscordInteractionsBlueprint()

# Simple command to mention a friend
# The target user is passed as an argument
# It is also accessible as `ctx.target_user` (and `ctx.target` for legacy reasons)
@bp.command(name="High Five", type=ApplicationCommandType.USER)
def highFive(ctx: Context, target):
    return f"<@{ctx.author.id}> wants to say hello to <@{target.id}>"


# Simple message command to repeat a message in bold
# The target message is passed as an argument
# It is also accessible as `ctx.target_message` (and `ctx.target` for legacy reasons)
@bp.command(name="Make it bold", type=ApplicationCommandType.MESSAGE)
def boldMessage(ctx: Context, message):
    return f"**{message.content}**"
