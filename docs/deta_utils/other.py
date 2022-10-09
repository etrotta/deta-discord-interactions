"""This example uses Webhooks and Cooldowns, but the flow for generic oauth is the same as Webhooks,
with the only difference being that you have to specify which scopes to use for """

from typing import Optional
from deta_discord_interactions import DiscordInteractions, Context
from deta_discord_interactions.utils import (
    create_webhook, enable_oauth,
    OAuthToken,
    cooldown,
    Database, AutoSyncRecord
)

app = DiscordInteractions()

enable_oauth(app)

db = Database("example_webhooks", record_type=AutoSyncRecord)

def save_webhook(token: Optional[OAuthToken], ctx: Context, key: str):
    if token is None:
        # User cancelled the OAuth flow / declined the consent form
        return "Bruh"
    db[key] = {"token": token}
    return "Saved sucessfully"

@app.command("create")
@cooldown('user', 3600)
def create(ctx: Context, name: str):
    key = f'webhook_{ctx.author.id}_{name}'
    msg = create_webhook(ctx, key, callback=save_webhook, args=[key])
    return msg

@app.command("invoke")
@cooldown('user', 10)
def create(ctx: Context, name: str, msg: str):
    key = f'webhook_{ctx.author.id}_{name}'
    record = db[key]
    if record.get("token") is None:
        return "webhook not found"
    try:
        record['token'].webhook.send(msg)
    except Exception:
        return "something went wrong"
    else:
        return "sent sucessfully"
