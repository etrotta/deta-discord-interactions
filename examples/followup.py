import os
import sys
import time
import threading

from flask import Flask

sys.path.insert(1, ".")

from deta_discord_interactions import (
    DiscordInteractions,
    Message,
    ActionRow,
    Button,
    ButtonStyles,
)


app = Flask(__name__)
discord = DiscordInteractions(app)

app.config["DISCORD_CLIENT_ID"] = os.environ["DISCORD_CLIENT_ID"]
app.config["DISCORD_PUBLIC_KEY"] = os.environ["DISCORD_PUBLIC_KEY"]
app.config["DISCORD_CLIENT_SECRET"] = os.environ["DISCORD_CLIENT_SECRET"]

discord.update_commands()


# You can continue to send followup messages from background processes
# You can also send files
@discord.command()
def followup(ctx):
    def do_followup():
        print("Followup task started")
        time.sleep(5)

        print("Editing original message")
        ctx.edit("Editing my original message")
        time.sleep(5)

        print("Sending a file")
        ctx.send(
            Message(
                content="Sending a file",
                file=("README.md", open("README.md", "rb"), "text/markdown"),
            )
        )
        time.sleep(5)

        print("Deleting original message")
        ctx.delete()
        time.sleep(5)

        print("Sending new message")
        new_message = ctx.send("Sending a new message")
        time.sleep(5)

        print("Editing new message")
        ctx.edit("Editing a new message", message=new_message)

    thread = threading.Thread(target=do_followup)
    thread.start()

    return "Sending an original message"


# You can set deferred=True to display a loading state to the user
@discord.command()
def delay(ctx, duration: int):
    def do_delay():
        time.sleep(duration)

        ctx.edit("Hiya!")

    thread = threading.Thread(target=do_delay)
    thread.start()

    return Message(deferred=True)


# This can be useful if you want to send files without worrying about the
# Discord timeout
@discord.command()
def sendfile(ctx):
    def do_sendfile():
        ctx.edit(
            Message(
                file=("README.md", open("README.md", "rb"), "text/markdown"),
            )
        )

    thread = threading.Thread(target=do_sendfile)
    thread.start()

    return Message(deferred=True)


# Followups can also be used to edit any message components
@discord.custom_handler()
def timed_button_handler(ctx, click_count: int):
    click_count += 1

    return Message(
        content=f"The button has been clicked {click_count} times",
        components=[
            ActionRow(
                components=[
                    Button(
                        style=ButtonStyles.PRIMARY,
                        custom_id=[timed_button_handler, click_count],
                        label="Click me before time is up!",
                    )
                ]
            )
        ],
        update=True,
    )


@discord.command()
def timed_button(ctx, duration: int):
    def do_delay():
        time.sleep(duration)

        ctx.edit(
            Message(
                content="Time's up!",
                components=[
                    ActionRow(
                        components=[
                            Button(
                                style=ButtonStyles.PRIMARY,
                                custom_id=[timed_button_handler, 0],
                                label="Time's up!",
                                disabled=True,
                            )
                        ]
                    )
                ],
            )
        )

    thread = threading.Thread(target=do_delay)
    thread.start()

    return Message(
        content=f"You have {duration} seconds to click the button...",
        components=[
            ActionRow(
                components=[
                    Button(
                        style=ButtonStyles.PRIMARY,
                        custom_id=[timed_button_handler, 0],
                        label="Click me before time is up!",
                    )
                ]
            )
        ],
    )


discord.set_route("/interactions")
discord.update_commands(guild_id=os.environ["TESTING_GUILD"])


if __name__ == "__main__":
    app.run()
