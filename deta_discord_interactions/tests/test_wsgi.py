import json
import io
import pytest
import requests

from deta_discord_interactions import (
    DiscordInteractions,
    ResponseType,
    InteractionType,
)

def test_raises_on_http_request():
    "Make sure that the conftest that blocks http requests is working"
    with pytest.raises(RuntimeError):
        _ = requests.get("http://localhost:80")
    with pytest.raises(RuntimeError):
        _ = requests.get("https://google.com")


def test_wsgi(discord: DiscordInteractions):

    @discord.command()
    def ping(ctx, pong: str = "ping"):
        return f"Ping {pong}!"

    _json = {
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

    environ = {
        "wsgi.input": io.BytesIO(json.dumps(_json).encode('UTF-8')),
        "PATH_INFO": "/discord",
        'QUERY_STRING': '',
    }

    def _start_response(status, headers):
        assert status == "200 OK"
        assert headers == [('Content-Type', 'application/json')]

    response = discord(
        environ,
        _start_response
    )

    resp = json.loads(response[0].decode('UTF-8'))
    assert resp["type"] == ResponseType.CHANNEL_MESSAGE_WITH_SOURCE

    assert resp["data"]["content"] == "Ping Pong!"
