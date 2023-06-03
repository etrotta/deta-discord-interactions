from deta_discord_interactions import (
    DiscordInteractionsBlueprint,
    Message,
    Modal,
    TextInput,
    TextStyles,
    ActionRow,
    Button,
)
from deta_discord_interactions.context import Context

bp = DiscordInteractionsBlueprint()

@bp.custom_handler("example_modal")
def modal_callback(ctx):
    msg = (
        f"Hello {ctx.get_component('name').value}! "
        f"So you are {ctx.get_component('age').value} years old "
        "and this is how you describe yourself: "
        f"{ctx.get_component('description').value}"
    )
    return Message(msg, ephemeral=True)


@bp.command(name="test_modal", description="Opens a Modal window")
def modal(ctx):
    fields = [
        ActionRow(
            [
                TextInput(
                    custom_id="name",
                    label="What's your name?",
                    placeholder="John Doe",
                    style=TextStyles.SHORT,
                    required=True,
                )
            ]
        ),
        ActionRow(
            [
                TextInput(
                    custom_id="age",
                    label="What's your age?",
                    style=TextStyles.SHORT,
                    min_length=1,
                    max_length=5,
                    required=False,
                )
            ]
        ),
        ActionRow(
            [
                TextInput(
                    custom_id="description",
                    label="Describe yourself:",
                    value="A very interesting person",
                    style=TextStyles.PARAGRAPH,
                    min_length=10,
                    max_length=2000,
                )
            ]
        ),
    ]
    return Modal("example_modal", "Tell me about yourself", fields)


@bp.custom_handler("example_modal_2")
def example_modal_2(ctx: Context):
    return Message(f"Hello {ctx.get_component('name').value}!", update=True)


@bp.custom_handler("launch_modal")
def launch_modal(ctx):
    return Modal(
        "example_modal_2",
        "Tell me about yourself",
        [
            ActionRow(
                [
                    TextInput(
                        custom_id="name",
                        label="What's your name?",
                        placeholder="John Doe",
                        style=TextStyles.SHORT,
                        required=True,
                    )
                ]
            )
        ],
    )


@bp.command()
def launch_modal_from_button(ctx):
    return Message(
        content="Launch Modal",
        components=[ActionRow([Button(custom_id="launch_modal", label="Launch Modal")])],
    )
