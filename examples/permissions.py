"NOTICE: Permissions overwrites may not work at the moment, but default permissions work just fine"

import os
os.environ["DISCORD_SCOPE"] = "applications.commands.update applications.commands.permissions.update"

from deta_discord_interactions import DiscordInteractions, Permission, Member
from deta_discord_interactions.enums import PERMISSION


app = DiscordInteractions()


@app.command(default_member_permissions=PERMISSION.BAN_MEMBERS)
def blacklist(ctx, user: Member):
    "Only members with the 'Ban members' permission can use this command"
    return f"{user.username} has been blacklisted!"


@app.command(
    default_member_permissions=8,
)
def command_with_perms(ctx):
    "You need a certain role to access this command"

    return "You have permissions!"


@app.command(default_member_permissions=8)
def locked_command(ctx):
    "Secret command that has to be unlocked"

    return "You have unlocked the secret command!"


@app.command()
def unlock_command(ctx):
    "Unlock the secret command"

    # Note: This may not work right now
    app.set_permission_overwrites(
        permissions=[Permission(user=ctx.author.id)],
        command_id=locked_command.id,
        guild_id=ctx.guild_id,
    )

    return "Unlocked!"


# Permissions can be set on command groups at the top level,
# and will apply to all subcommands.

admin = app.command_group("admin", default_member_permissions=8)


@admin.command()
def restrict_user(ctx, user: Member):
    return f"{user.username} has been restricted!"


@admin.command()
def release_user(ctx, user: Member):
    return f"{user.username} has been released!"


app.set_permission_overwrites(
    [Permission(role="786840072891662336")],
    command_with_perms,
    guild_id=int(os.environ["TESTING_GUILD"]),
)


if __name__ == "__main__":
    app.update_commands(guild_id=os.environ["TESTING_GUILD"])
