import typing
import io
from unittest import mock
import requests

from deta_discord_interactions import DiscordInteractions, Client, Context, Message, Member
from deta_discord_interactions.utils.oauth import (
    create_webhook,
    remember_callback,
    OAuthToken,
)

def test_webhook(oauth_discord: DiscordInteractions, oauth_client: Client):
    @remember_callback
    def callback(token: typing.Optional[OAuthToken], ctx: Context, name: str, num: int):
        assert token is not None
        assert name == "bobert"
        assert num == 1
        assert ctx.author.id == "789"
        return "it worked"

    @oauth_discord.command()
    def testcommand(ctx: Context, name: str):
        message = create_webhook(ctx, "test123", callback=callback, args=[name, 1], message_content="XYZ")
        return message

    with mock.patch.dict("os.environ", {
        "DETA_SPACE_APP": "true",
        "DETA_SPACE_APP_HOSTNAME": "example-1-a1234567.deta.app",
    }), oauth_client.context(Context(author=Member(id="789", username="tester"))):
        result = oauth_client.run("testcommand", "bobert")
    assert isinstance(result, Message)
    assert result.content == "XYZ"
    assert 'test123' in result.components[0].components[0].url

    env = {
        "wsgi.input": io.StringIO(),
        "PATH_INFO": "/oauth",
        'QUERY_STRING': 'state=test123&code=456',
    }
    with mock.patch.object(requests, "post") as req_mock:
        req_mock.return_value.json.return_value = {
            "access_token": "atoken",
            "refresh_token": "rtoken",
            "scope": "testscope",
            "expires_in": 1,
            "webhook": {
                "id": "hook_id",
                "token": "hook_token",
                "name": "hook_name",
                "avatar": "hook_avatar",
                "guild_id": "hook_guild_id",
                "channel_id": "hook_channel_id",
            }
        }
        final = oauth_discord(env, lambda *_: None)
        print(final)
        assert final[0].decode() == '"it worked"'
        req_mock.assert_called_once()
