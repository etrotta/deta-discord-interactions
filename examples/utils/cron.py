# NOTE: Remember to set the Scheduled Actions on the Spacefile
# https://deta.space/docs/en/basics/micros#scheduled-actions

from typing import Optional
from dataclasses import dataclass
from deta_discord_interactions import DiscordInteractionsBlueprint
from deta_discord_interactions import Message
from deta_discord_interactions import Context

from deta_discord_interactions import Autocomplete, Option, Choice

from deta_discord_interactions.enums import PERMISSION

from deta_discord_interactions.utils.database import Database, LoadableDataclass
from deta_discord_interactions.utils.database import Query, Field

from deta_discord_interactions.utils.oauth import OAuthToken, Webhook
from deta_discord_interactions.utils.oauth import create_webhook, remember_callback

@dataclass
class Repeater(LoadableDataclass):
    internal_name: str
    webhook: Webhook
    message: str

database = Database(name="scheduled_webhooks", record_type=Repeater)

blueprint = DiscordInteractionsBlueprint()


hooks = blueprint.command_group(
    name="repeat",
    description="Webhooks automatically invoked", 
    default_member_permissions=PERMISSION.MANAGE_MESSAGES | PERMISSION.MANAGE_WEBHOOKS,
    dm_permission=False,
)

@remember_callback
def save_webhook(oauth: Optional[OAuthToken], ctx: Context, internal_name: str, message: str):
    if oauth is None:
        return f"Canceled creation of webhook {internal_name}"
    webhook = oauth.webhook
    key = f'webhook_{ctx.author.id}_{internal_name}'
    database[key] = Repeater(internal_name, webhook, message)
    # Do NOT return a Message - this is what the end user will see in their browser
    return f"Registered webhook {internal_name} with message {message}"


@hooks.command("register")
def register_webhook(ctx, internal_name: str, message: str):
    "Create a repeating Webhook with a message"
    message = create_webhook(ctx, internal_name, callback=save_webhook, args=(internal_name, message))
    return message


@blueprint.action("trigger_repeaters")
def run_all_webhooks(event):
    errors = []
    records = database.fetch()
    if not records:
        print("No active repeaters found. Consider disabling the Scheduled action if you do not wish to use them.")
    for record in records:
        try:
            record.webhook.send(record.message)
        except Exception as err:
            print(f"Failed to send a message to webhook {record.internal_name!r}", flush=True)
            errors.append(err)
    if errors:
        raise Exception(errors)


@hooks.command("invoke")
def invoke_webhook(ctx, internal_name: Autocomplete[str], message: str):
    "Send a message via an existing Webhook"
    key = f'webhook_{ctx.author.id}_{internal_name}'
    repeater: Optional[Repeater] = database.get(key)
    if repeater is None:
        return Message("Webhook not found", ephemeral=True)
    try:
        repeater.webhook.send(message)
        return Message("Sent message", ephemeral=True)
    except Exception:
        import traceback
        traceback.print_exc()
        return Message("Somethign went wrong", ephemeral=True)

@hooks.command("delete")
def delete_webhook(ctx, internal_name: Autocomplete[str], reason: str = None):
    "Delete a repeating Webhook"
    key = f'webhook_{ctx.author.id}_{internal_name}'
    repeater: Optional[Repeater] = database.get(key)
    if repeater is None:
        return Message("Webhook not found", ephemeral=True)
    try:
        del database[key]
        repeater.webhook.delete(reason=reason)
    except Exception:
        return Message("Failed to delete webhook, probably was already deleted", ephemeral=True)
    else:
        return Message("Deleted Webhook", ephemeral=True)


@delete_webhook.autocomplete()
def webhook_name_autocomplete_handler(ctx, internal_name: Option = None, **_):
    if internal_name is None or not internal_name.focused:
        return []
    key_prefix = f'webhook_{ctx.author.id}_{internal_name.value}'

    options = []
    records = database.fetch(Query(Field("key").startswith(key_prefix)))
    for record in records:
        display = f"{record.internal_name}: {record.webhook.name}"
        value = record.internal_name
        options.append(Choice(name=display, value=value))

    options.sort(key=lambda option: option.name)
    return options[:25]
