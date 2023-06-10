import json
from deta_discord_interactions.utils.database import Drive


from deta_discord_interactions import (
    DiscordInteractionsBlueprint,
    Context,

    Message,
    Modal,

    ActionRow,
    TextInput,
    TextStyles,

    SelectMenu,
    SelectMenuOption,

    Autocomplete,
    Option,
    Choice,
)
from deta_discord_interactions.enums.permissions import PERMISSION

drive = Drive("tags")

blueprint = DiscordInteractionsBlueprint()
manage_group = blueprint.command_group(
    "managetags",
    "Create, Update and Delete bot tags.",
    dm_permission=False,
    default_member_permissions=PERMISSION.ADMINISTRATOR,
)


# Modal to create / edit
def modal(name: str, description: str) -> Modal:
    return Modal(
        "tags_modal",
        "Create or edit a Tag",
        [
            ActionRow(
                [TextInput("tag_name", "Name", value=name)],
            ),
            ActionRow(
                [TextInput("tag_body", "Body", style=TextStyles.PARAGRAPH, value=description)],
            ),
        ]
    )


@blueprint.custom_handler("tags_modal")
def save_modal_tag(ctx: Context):
    name = ctx.get_component("tag_name").value
    description = ctx.get_component("tag_body").value.strip()

    if not description.startswith("{"):
        description = json.dumps({"content": description})

    try:
        Message.from_dict(json.loads(description)).encode()
    except Exception as err:
        return Message(f"Aborted operation - body content validation raised an error: ```\n{err}```", ephemeral=True)

    (drive / f'{name}.json').write_text(description)

    return Message(f"Set tag {name}", ephemeral=True)


# Create / Update - Admin only
@manage_group.command("manage", "Add or edit a bot tag.")
def manage_tag(ctx: Context, name: Autocomplete[str]):
    body = (drive / f'{name}.json').read_text()  # Returns an empty string if the file was not found
    if len(body) > 4000:
        return Message("This tag's body is too large to edit via Discord!", ephemeral=True)
    return modal(name, body)

# Read - Public
@blueprint.command("tag", "Retrieve a bot tag.")
def get_tag(ctx: Context, name: Autocomplete[str]):
    tag = (drive / f'{name}.json').read_text()
    if not tag:
        return Message("Tag not found.", ephemeral=True)
    msg = json.loads(tag)
    return Message.from_dict(msg)


# Delete - Admin only
@manage_group.command("delete", "Delete a bot tag.")
def delete_tag(ctx: Context, name: Autocomplete[str]):
    (drive / f'{name}.json').delete()
    return Message(f"Tag {name} deleted (or already didn't exist)", ephemeral=True)


# List - Public
@blueprint.command("tags", "List all tags from this bot")
def list_tags(ctx: Context, ephemeral: bool = False):
    bot_tags = [path.stem for path in drive.iterdir()]
    if not bot_tags:
        return Message("There are no tags.", ephemeral=ephemeral)

    # If it fits in a Select Menu
    if len(bot_tags) <= 25:
        options = [SelectMenuOption(name, name) for name in bot_tags]
        return Message(
            "Select a tag to see it:",
            components=[ActionRow([SelectMenu("tags_list", options)])],
            ephemeral=ephemeral,
        )
    else:
        # Put in a normal message.
        result = "```\n" + ", ".join(bot_tags) + "```"
        return Message(result, ephemeral=ephemeral, allowed_mentions={"parse": []})


@blueprint.custom_handler("tags_list")
def show_full_tag(ctx: Context):
    name = ctx.values[0]
    tag = (drive / f"{name}.json").read_text()
    if not tag:
        return Message("Tag not found.", ephemeral=True)
    data = json.loads(tag)
    msg = Message.from_dict(data)
    if data.get("ephemeral") is None:
        msg.ephemeral = True
    return msg


@manage_tag.autocomplete()
@get_tag.autocomplete()
@delete_tag.autocomplete()
def tag_name_autocomplete_handler(ctx, name: Option = None, **_):
    if name is None or not name.focused:
        return []
    tags = sorted(stem for path in drive.iterdir() if (stem := path.stem).startswith(name.value))
    options = [Choice(tag, tag) for tag in tags[:25]]
    return options
