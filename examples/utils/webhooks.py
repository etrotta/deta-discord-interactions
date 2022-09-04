from deta_discord_interactions import DiscordInteractionsBlueprint
from deta_discord_interactions import Message
from deta_discord_interactions import Context

from deta_discord_interactions import Autocomplete, Option, Choice

from deta_discord_interactions.enums import PERMISSION

from deta_discord_interactions.utils.database import Database
from deta_discord_interactions.utils.database import Query, Field

from deta_discord_interactions.utils.webhooks import Webhook
from deta_discord_interactions.utils.webhooks import create_webhook


database = Database(name="webhooks")

blueprint = DiscordInteractionsBlueprint()


hooks = blueprint.command_group(
    name="webhook",
    description="Manage this bot's Webhooks", 
    default_member_permissions=PERMISSION.MANAGE_MESSAGES + PERMISSION.MANAGE_WEBHOOKS,
    dm_permission=False,
)


def save_webhook(webhook: Webhook, ctx: Context, internal_name: str):
    key = f'webhook_{ctx.author.id}_{internal_name}'
    with database[key] as record:
        record["internal_name"] = internal_name
        record["hook"] = webhook
    # Do NOT return a Message - this is what the end user will see in their browser
    return f"Registered webhook {internal_name}"


@hooks.command("register")
def register_webhook(ctx, internal_name: str):
    message = create_webhook(ctx, internal_name, callback=save_webhook, args=(internal_name,))
    return message


@hooks.command("invoke")
def invoke_webhook(ctx, internal_name: Autocomplete[str], message: str):
    "Send a message via an existing Webhook"
    key = f'webhook_{ctx.author.id}_{internal_name}'
    webhook: Webhook = database.get(key).get("hook")
    if webhook is None:
        return Message("Webhook not found", ephemeral=True)
    webhook.send(message)
    return Message("Sent message", ephemeral=True)


@hooks.command("delete")
def delete_webhook(ctx, internal_name: Autocomplete[str], reason: str = None):
    "Delete a Webhook"
    key = f'webhook_{ctx.author.id}_{internal_name}'
    webhook: Webhook = database.get(key).get("hook")
    if webhook is None:
        return Message("Webhook not found", ephemeral=True)
    try:
        del database[key]
        webhook.delete(reason=reason)
    except Exception:
        return Message("Failed to delete webhook, probably was already deleted", ephemeral=True)
    else:
        return Message("Deleted Webhook", ephemeral=True)


@invoke_webhook.autocomplete()
@delete_webhook.autocomplete()
def webhook_name_autocomplete_handler(ctx, internal_name: Option = None, **_):
    if internal_name is None or not internal_name.focused:
        return []
    key_prefix = f'webhook_{ctx.author.id}_{internal_name.value}'

    options = []
    records = database.fetch(Query(Field("key").startswith(key_prefix)))
    for record in records:
        display = f"{record['internal_name']}: {record['hook'].name}"
        value = record["internal_name"]
        options.append(Choice(name=display, value=value))

    options.sort(key=lambda option: option.name)
    return options[:25]
