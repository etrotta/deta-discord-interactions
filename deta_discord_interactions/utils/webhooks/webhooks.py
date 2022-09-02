"Deals with OAuth2, creating and saving Webhooks"
import datetime
import io
import json
import os
from typing import Any, Callable, NoReturn
from urllib.parse import quote

import requests
from deta_discord_interactions.models.component import ActionRow, Button, ButtonStyles

from deta_discord_interactions.models.message import Message

from deta_discord_interactions.discord import DiscordInteractions
from deta_discord_interactions.context import Context

from deta_discord_interactions.utils.database import Database

from deta_discord_interactions.utils.webhooks.model import Webhook, PendingWebhook


if os.getenv("DONT_REGISTER_WITH_DISCORD"):
    DISCORD_BASE_URL = 'http://localhost:8000'
    DEFAULT_MICRO_PATH = "RUN_APP_METHODS_INSTEAD"
else:
    DISCORD_BASE_URL = 'https://discord.com/api/v10'
    DEFAULT_MICRO_PATH = "https://{MICRO}.deta.dev"

pending_webhooks = Database(name="_discord_interactions_pending_webhooks")
confirmed_webhooks = Database(name="_discord_interactions_confirmed_webhooks")


def enable_webhooks(app: DiscordInteractions, /, *, path: str = "/oauth") -> None:
    "Allows for the app to receive and process OAuth webhooks"
    app.route(path)(_handle_oauth)


def create_webhook(
    ctx: Context,
    /,
    internal_id: str,
    domain: str = DEFAULT_MICRO_PATH,
    path: str = "/oauth",
    *,
    callback: Callable,
    args: tuple = (),
    kwargs: dict = {},
) -> Message:
    """Utility function to make Webhook creation and usage easier
    
    Returns a Message with a link the user must visit to create a webhook,
    and save a PendingWebhook in the internal database.

    Parameters
    ----------
    ctx : Context
        The Context this function is being called from
    internal_id : str
        ID to be used internally
    domain : str, default https://{MICRO}.deta.dev
-        Base URL for the Micro running the bot
        {MICRO} is filled automatically from the environment variables
    path : str, default '/oauth'
        Path that the user will be sent back to. 
        Must match what has been passed to `enable_webhooks` and be set on the Developer Portal
    callback : Callable
        Must be a normal function, not a lambda, partial nor a class method.
    args : tuple|list
    kwargs : dict
        Arguments and Keyword arguments to be passed onto callback


    If the user never finishes creating a webhook, the callback will not be called
    If they create one , it will be called with ctx, webhook, `args` and `kwargs`
    The link will only work for one webhook
    """
    promise = PendingWebhook(
        ctx,
        callback.__module__,
        callback.__name__,
        args,
        kwargs,
    )
    redirect_uri = (
        quote(
            domain.format(MICRO = os.getenv("DETA_PATH")) + path,
            safe=''
        )
    )

    with pending_webhooks[internal_id] as record:
        record["pending_webhook"] = promise
        record["redirect_uri"] = redirect_uri
        record["__expires_in"] = 600

    link = (
        f"{DISCORD_BASE_URL}/oauth2/authorize?"
        "response_type=code&"
        "scope=webhook.incoming&"
        f"client_id={os.getenv('DISCORD_CLIENT_ID')}&"
        f"state={internal_id}&"
        f"redirect_uri={redirect_uri}"
    )

    return Message(
        "Use the button to register the Webhook",
        components=[ActionRow([
            Button(
                style=ButtonStyles.LINK,
                url=link,
            )
        ])],
        # ephemeral=True,
    )


def _handle_oauth(
    request: dict,
    start_response: Callable[[str, list], None],
    abort: Callable[[int, str], NoReturn],
) -> list[str]:
    code = request["query_dict"].get("code")
    state = request["query_dict"].get("state")
    guild_id = request["query_dict"].get("guild_id")

    if code is None or state is None or guild_id is None:
        abort(400, 'Invalid URL')

    url = DISCORD_BASE_URL + "/oauth2/token"

    try:

        with pending_webhooks[state] as record:
            redirect_uri: str = record["redirect_uri"]
            pending_webhook: PendingWebhook = record["pending_webhook"]

        data = {
            'client_id': os.getenv("DISCORD_CLIENT_ID"),
            'client_secret': os.getenv("DISCORD_CLIENT_SECRET"),
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        response = requests.post(url, data=data, headers=headers)
        response.raise_for_status()
        result = response.json()

        webhook = Webhook(
            id=result["webhook"]["id"],
            token=result["webhook"]["token"],
            name=result["webhook"]["name"],
            avatar=result["webhook"]["avatar"],
            guild_id=result["webhook"]["guild_id"],
            channel_id=result["webhook"]["channel_id"],
        )

        with confirmed_webhooks[state] as record:
            record["access_token"] = result["access_token"]
            record["refresh_token"] = result["refresh_token"]
            record["expires_at"] = datetime.datetime.utcnow() + datetime.timedelta(seconds=604800)
            record["webhook"] = webhook

        callback_response = pending_webhook.execute_callback(webhook)

        if isinstance(callback_response, (dict, list, int, str)):
            callback_response = json.dumps(callback_response)
        if isinstance(callback_response, str):
            callback_response = callback_response.encode("UTF-8")
        if not isinstance(callback_response, bytes):
            raise Exception("The Callback response should be a dictionary, a string or bytes")


        start_response("200 OK", [('Content-Type', 'application/json')])
        return [callback_response]
    
    except Exception:
        import traceback
        traceback.print_exc()
        abort(500, "Something went wrong")
 

def fake_user_webhook_confirmation(
    app: DiscordInteractions,
    message: Message,
) -> tuple[Any, Any]:
    """
    Pretends that the user visited the app and selected a channel to send Webhooks to,
    for developing and testing locally

    Parameters
    ----------
    app : DiscordInteractions
        The main app receiving requests
    message : Message
        The message returned by `create_webhook`

    Returns
    -------
    fake server response : Any
        JSON data returned by the fake server when making the fake user interaction
    app response : Any
        JSON data returned by the app when making the fake rediction
    """
    action_row: ActionRow = message.components[0]
    button: Button = action_row.components[0]
    url: str = button.url

    from deta_discord_interactions.utils.webhooks._local_http import run_local_server
    run_local_server()

    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    query_string = "&".join(f"{key}={data[key]}" for key in ('code', 'state', 'guild_id'))

    # redirect_to = f"{data['redirect_uri']}?{query_string}"

    result = app(
        {
            "wsgi.input": io.BytesIO(),
            "PATH_INFO": "/oauth",
            "QUERY_STRING": query_string,
        },
        lambda code, headers: None
    )

    return data, json.loads(result[0].decode('UTF-8'))