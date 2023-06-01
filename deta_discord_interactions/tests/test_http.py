import json
import threading
from urllib.request import Request, urlopen

import pytest

from deta_discord_interactions import (
    DiscordInteractions,
    ResponseType,
    InteractionType,
)
from deta_discord_interactions.http import run_server

HOST = '127.0.0.1'
PORT = 1234
URL = f'http://{HOST}:{PORT}{{PATH}}'

JSON_DATA = {
    "type": InteractionType.APPLICATION_COMMAND,
    "id": 1,
    "channel_id": "",
    "guild_id": "",
    "token": "",
    "data": {
        "id": 1,
        "name": "ping",
        "options": [{"type": 1, "name": "Pong"}],
    },
    "member": {"id": 1, "nick": "", "user": {"id": 1, "username": "test"}},
}


def test_http(discord: DiscordInteractions, capsys: pytest.CaptureFixture):
    "Make sure that the requests work"

    @discord.command()
    def ping(ctx, pong: str = "ping"):
        return f"Ping {pong}!"

    request = Request(
        URL.format(PATH="/discord"),
        data=json.dumps(JSON_DATA).encode(),
        headers={},
        method='POST',
    )
    server_thread = threading.Thread(target=run_server, args=(discord, PORT), daemon=True)
    server_thread.start()

    response = json.loads(urlopen(request).read().decode())
    assert response["type"] == ResponseType.CHANNEL_MESSAGE_WITH_SOURCE
    assert response["data"]["content"] == "Ping Pong!"
    # Make sure that it is not producing any undesired output
    captured = capsys.readouterr()
    assert captured.out == ''
    assert captured.err == ''

@pytest.mark.xfail(strict=True)
def test_fail_http(discord: DiscordInteractions):
    "A negative test to make sure that it is not just somehow cheating to just pass or ignore all Assertions everywhere"

    @discord.command()
    def ping(ctx, pong: str = "ping"):
        return f"Ping {pong}!"

    request = Request(
        URL.format(PATH="/discord"),
        data=json.dumps(JSON_DATA).encode(),
        headers={},
        method='POST'
    )
    server_thread = threading.Thread(target=run_server, args=(discord, PORT), daemon=True)
    server_thread.start()

    response = json.loads(urlopen(request).read().decode())
    # Intentionally False assertion
    assert response["type"] == ResponseType.PONG

## Deta Scheduled Actions


def test_action(discord, client):
    @discord.action("test")
    def _(event):
        assert event["id"] == "test"
        return 42

    assert client.run_action("test") == 42


def test_action_http(discord: DiscordInteractions):
    @discord.action("test")
    def _(event):
        assert event["id"] == "test"
        return 42

    _json = {
        "event": {
            "id": "test",
            "trigger": "schedule",
        }
    }

    request = Request(
        URL.format(PATH="/__space/v0/actions"),
        data=json.dumps(_json).encode(),
        headers={},
        method='POST',
    )
    server_thread = threading.Thread(target=run_server, args=(discord, PORT), daemon=True)
    server_thread.start()

    response = json.loads(urlopen(request).read().decode())
    assert response["result"] == 42
