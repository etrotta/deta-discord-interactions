from deta_discord_interactions import DiscordInteractionsBlueprint, Message
from deta_discord_interactions import embed

bp = DiscordInteractionsBlueprint()

# The "ctx" parameter is an Context object
# it works similarly to Context in Discord.py
@bp.command()
def avatar(ctx):
    "Show your user info"

    return Message(
        embed=embed.Embed(
            title=ctx.author.display_name,
            description="Avatar Info",
            fields=[
                embed.Field("Member Since", ctx.author.joined_at),
                embed.Field("Username", f"**{ctx.author.username}**" f"#{ctx.author.discriminator}"),
                embed.Field("User ID", ctx.author.id),
                embed.Field("Channel ID", ctx.channel_id),
                embed.Field("Guild ID", ctx.guild_id),
            ],
            image=embed.Media(ctx.author.avatar_url),
        )
    )
