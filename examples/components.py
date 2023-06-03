
import uuid
from dataclasses import dataclass

from deta_discord_interactions import (
    DiscordInteractionsBlueprint,
    Message,
    ActionRow,
    Button,
    ButtonStyles,
    Embed,
    SelectMenu,
    SelectMenuOption,
)

from deta_discord_interactions.utils.database import Database, LoadableDataclass

bp = DiscordInteractionsBlueprint()

# You can return a normal message
@bp.custom_handler("handle_upvote")
def handle_upvote(ctx):
    return f"Upvote by {ctx.author.display_name}!"


@bp.custom_handler("handle_downvote")
def handle_downvote(ctx):
    return f"Downvote by {ctx.author.display_name}!"


@bp.command()
def voting(ctx, question: str):
    "Vote on something!"

    return Message(
        content=f"The question is: {question}",
        components=[
            ActionRow(
                components=[
                    Button(
                        style=ButtonStyles.SUCCESS,
                        custom_id="handle_upvote",
                        emoji={"name": "⬆️"},
                    ),
                    Button(
                        style=ButtonStyles.DANGER,
                        custom_id="handle_downvote",
                        emoji={
                            "name": "⬇️",
                        },
                    ),
                ]
            )
        ],
    )


# Ephemeral messages and embeds work
@bp.custom_handler("avatar_view")
def handle_avatar_view(ctx):
    return Message(
        embed=Embed(
            title=f"{ctx.author.display_name}",
            description=f"{ctx.author.username}",
        ),
        ephemeral=True,
    )


@bp.command()
def username(ctx):
    "Show your username and discriminator"

    return Message(
        content="Show user info!",
        components=[
            ActionRow(
                components=[
                    Button(
                        style=ButtonStyles.PRIMARY,
                        custom_id="avatar_view",
                        label="View User!",
                    )
                ]
            )
        ],
    )


# Return nothing for no action
@bp.custom_handler("noop")
def handle_do_nothing(ctx):
    print("Doing nothing...")


@bp.command()
def do_nothing(ctx):
    return Message(
        content="Do nothing",
        components=[
            ActionRow(
                components=[
                    Button(
                        style=ButtonStyles.PRIMARY,
                        custom_id="noop",
                        label="Nothing at all!",
                    )
                ]
            )
        ],
    )


# Link buttons don't need a handler
@bp.command()
def google(ctx):
    return Message(
        content="search engine",
        components=[
            ActionRow(
                components=[
                    Button(
                        style=ButtonStyles.LINK,
                        url="https://www.google.com/",
                        label="Go to google",
                    )
                ]
            )
        ],
    )


# Reminder: Global variables ***will not work*** on Deta. Use Deta Base or Deta Drive instead.
# Assume that your entire app may be reset every request (every command)
@dataclass
class ClicksCounter(LoadableDataclass):
    clicks: int

database = Database("clicky_counter", ClicksCounter)
# Use a list with the Custom ID to include additional state information


# The handler can edit the original message by setting update=True
# It sets the action for the button with custom_id

bp = DiscordInteractionsBlueprint()

@bp.custom_handler("clicky")
def handle_click(ctx, custom_id: str):
    counter = database[custom_id]
    counter.clicks += 1
    # Remember to save changes back
    database[custom_id] = counter
    return Message(
        content=f"The button has been clicked {counter.clicks} times",
        components=[
            ActionRow(
                components=[
                    Button(
                        style=ButtonStyles.PRIMARY,
                        custom_id=("clicky", custom_id),
                        label="Click Me!",
                    )
                ]
            )
        ],
        update=True,
    )


# The main command sends the initial message
@bp.command()
def click_counter(ctx, custom_id: str = None):
    "Count the number of button clicks"
    if not custom_id:
        custom_id = str(uuid.uuid4())
    counter = database.get(custom_id)
    if counter is None:
        counter = ClicksCounter(0)
        database[custom_id] = counter
    return Message(
        content=f"The button {custom_id} has been clicked {counter.clicks} times",
        components=[
            ActionRow(
                components=[
                    Button(
                        style=ButtonStyles.PRIMARY,
                        custom_id=('clicky', custom_id),
                        label="Click Me!",
                    )
                ]
            )
        ],
    )


# (Note that below the entire state is being tracked by the button ID on discord, it is not stored on Deta Base at all)
# Optionally specify the type (e.g. int) to automatically convert
@bp.custom_handler("count_converter")
def handle_converter(ctx, interaction_id, current_count: int):
    current_count += 1
    return Message(
        content=(
            f"This button has been clicked {current_count} times. "
            "Try calling this command multiple times to see--each button "
            "count is tracked separately!"
        ),
        components=[
            ActionRow(
                components=[
                    Button(
                        style=ButtonStyles.PRIMARY,
                        custom_id=["count_converter", interaction_id, current_count],
                        label="Click Me!",
                    )
                ]
            )
        ],
        update=True,
    )


@bp.command()
def stateful_click_counter(ctx):
    "Count the number of button clicks for this specific button."

    return Message(
        content="Click the button!",
        components=[
            ActionRow(
                components=[
                    Button(
                        style=ButtonStyles.PRIMARY,
                        custom_id=["count_converter", ctx.id, 0],
                        label="Click Me!",
                    )
                ]
            )
        ],
    )


@bp.custom_handler("parser")
def handle_parse_message(ctx):
    return f"I told you, {ctx.message.content}!"


@bp.command()
def message_parse_demo(ctx):
    "Demonstrate the ability to parse the original message in a handler."
    return Message(
        content="The answer is 42",
        components=[
            ActionRow(
                components=[
                    Button(
                        style=ButtonStyles.PRIMARY,
                        custom_id="parser",
                        label="What is the answer?",
                    )
                ]
            )
        ],
    )
