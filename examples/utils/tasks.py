# NOTE: Remember to run `deta cron set "..."`
# See https://docs.deta.sh/docs/micros/cron for the supported intervals

from deta_discord_interactions import DiscordInteractionsBlueprint
from deta_discord_interactions import Message
from deta_discord_interactions import Context

from deta_discord_interactions import Autocomplete, Option, Choice

from deta_discord_interactions.enums import PERMISSION

from deta_discord_interactions.utils.database import Database
from deta_discord_interactions.utils.database import Query, Field

from deta_discord_interactions.utils.oauth import OAuthToken, Webhook
from deta_discord_interactions.utils.oauth import create_webhook


database = Database(name="webhooks_tasks")

blueprint = DiscordInteractionsBlueprint()


hooks = blueprint.command_group(
    name="repeat",
    description="Webhooks automatically invoked", 
    default_member_permissions=PERMISSION.MANAGE_MESSAGES | PERMISSION.MANAGE_WEBHOOKS,
    dm_permission=False,
)

def save_webhook(oauth: OAuthToken, ctx: Context, internal_name: str, message: str):
    webhook = oauth.webhook
    key = f'webhook_{ctx.author.id}_{internal_name}'
    with database[key] as record:
        record["hook"] = webhook
        record["internal_name"] = internal_name
        record["message"] = message
    # Do NOT return a Message - this is what the end user will see in their browser
    return f"Registered webhook {internal_name} with message {message}"


@hooks.command("register")
def register_webhook(ctx, internal_name: str, message: str):
    "Create a repeating Webhook with a message"
    message = create_webhook(ctx, internal_name, callback=save_webhook, args=(internal_name, message))
    return message


@blueprint.task()
def run_all_webhooks():
    for record in database.fetch():
        try:
            record["hook"].send(record["message"])
        except Exception:
            print("Failed to send a message to webhook {record.key!r}")


@hooks.command("delete")
def delete_webhook(ctx, internal_name: Autocomplete[str], reason: str = None):
    "Delete a repeating Webhook"
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
