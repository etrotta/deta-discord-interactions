# Permissions overwrites may not work at the moment

from deta_discord_interactions import DiscordInteractionsBlueprint, Member
from deta_discord_interactions.enums import PERMISSION


bp = DiscordInteractionsBlueprint()


@bp.command(default_member_permissions=PERMISSION.BAN_MEMBERS)
def blacklist(ctx, user: Member):
    "Only members with the 'Ban members' permission can use this command"
    return f"{user.username} has been blacklisted!"

