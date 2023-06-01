"Deals with OAuth2, creating and saving Webhooks"
import json
import os
from typing import Callable, NoReturn, Optional, Protocol
from urllib.parse import quote, unquote
from dataclasses import dataclass

import requests
from deta_discord_interactions.models.component import ActionRow, Button, ButtonStyles

from deta_discord_interactions.models.message import Message

from deta_discord_interactions.discord import DiscordInteractions
from deta_discord_interactions.context import Context

from deta_discord_interactions.utils.database import Database, LoadableDataclass
from deta_discord_interactions.utils.oauth.model import OAuthToken, PendingOAuth


DISCORD_BASE_URL = 'https://discord.com/api/v10'

@dataclass
class PendingRecord(LoadableDataclass):
    redirect_uri: str
    pending_oauth: PendingOAuth


pending_oauths = Database(name="_discord_interactions_pending_oauths", record_type=PendingRecord)
remember_callback = pending_oauths.remember_function

def enable_oauth(app: DiscordInteractions, /, *, path: str = "/oauth") -> None:
    "Allows for the app to receive and process OAuth and create Webhooks"
    app.route(path)(_handle_oauth)


class Callback(Protocol):
    "Just to make it easier to identifity the signature the callback must have"
    def __call__(self, token: Optional[OAuthToken], ctx: Context, *args, **kwargs) -> str: ...


def request_oauth(
    ctx: Context,
    /,
    internal_id: str,
    *,
    domain: Optional[str] = None,
    path: str = "/oauth",
    scope: str,
    callback: Callback,
    args: list = [],
    kwargs: dict = {},
    message_content: str = "Use the button to register with OAuth",
    button_label: str = "Grant OAuth",
) -> Message:
    """Utility function to make OAuth creation and usage easier
    
    Returns a Message with a link the user must visit to grant an OAuth Token,
    and save a PendingOAuth in the internal database.

    See https://discord.com/developers/docs/topics/oauth2 for the list of available scopes and more information

    Parameters
    ----------
    ctx : Context
        The Context this function is being called from
    internal_id : str
        ID to be used internally. Will be shown in the link.
    domain : str, automatically set
        Base URL for the Micro running the bot
        If not set, uses the `DETA_SPACE_APP_HOSTNAME` environment variable
    path : str, default '/oauth'
        Path that the user will be sent back to. 
        Must match what has been passed to `enable_webhooks` and be set on the Discord Developer Portal
    scope : str
        OAuth scopes to request, separated by spaces.
    callback : Callable
        Must have been registered using the `remember_callback` decorator.
        Args passed: (token or None, ctx, *args, **kwargs). 
        If the user refuses the consent form, passes None instead of an OAuthToken
    args : tuple|list
    kwargs : dict
        Arguments and Keyword arguments to be passed onto callback
        The created newly created OAuthToken and Context passed to request_oauth are always passed first.
    message_content : str
        Message content, besides the button with the URL
    button_label : str
        The URL Button's label

    If the user never finishes the authorization process, the callback will not be called
    If they create one , it will be called with ctx, webhook, `args` and `kwargs`
    The link will only work for one authorization
    """
    promise = PendingOAuth(
        ctx,
        callback,
        args,
        kwargs,
    )
    if domain is None:
        if os.getenv("DETA_SPACE_APP"):
            domain = f"""https://{os.getenv("DETA_SPACE_APP_HOSTNAME")}"""
        else:
            raise Exception("Cannot identify which domain to use for OAuth redirection")
    redirect_uri = quote(domain + path, safe='')

    pending_oauths[internal_id] = PendingRecord(redirect_uri, promise)

    link = (
        f"{DISCORD_BASE_URL}/oauth2/authorize?"
        "response_type=code&"
        f"scope={quote(scope)}&"
        f"guild_id={ctx.guild_id}&"
        f"client_id={os.getenv('DISCORD_CLIENT_ID')}&"
        f"state={internal_id}&"
        f"redirect_uri={redirect_uri}"
    )

    return Message(
        message_content,
        components=[ActionRow([
            Button(
                style=ButtonStyles.LINK,
                url=link,
                label=button_label,
            )
        ])],
        ephemeral=True,
    )


# Mostly for convenience and more... idk, semantic
def create_webhook(
    ctx: Context,
    /,
    internal_id: str,
    domain: Optional[str] = None,
    path: str = "/oauth",
    *,
    callback: Callback,
    args: list = [],
    kwargs: dict = {},
    message_content: str = "Use the button to register the Webhook",
    button_label: str = "Create Webhook",
) -> Message:
    """Utility function to make Webhook creation and usage easier
    
    Returns a Message with a link the user must visit to create a webhook,
    and save a PendingWebhook in the internal database.

    Parameters
    ----------
    ctx : Context
        The Context this function is being called from
    internal_id : str
        ID to be used internally. Will be shown in the link.
    domain : str, automatically set
        Base URL for the Micro running the bot
        If not set, uses the `DETA_SPACE_APP_HOSTNAME` environment variable
    path : str, default '/oauth'
        Path that the user will be sent back to. 
        Must match what has been passed to `enable_webhooks` and be set on the Discord Developer Portal
    callback : Callable
        Must be a normal function, not a lambda, partial nor a class method.
        You must use the `remember_callback` decorator when defining the function
        Args passed: (token or None, ctx, *args, **kwargs). 
        If the user refuses the consent form, passes None instead of an OAuthToken
    args : tuple|list
    kwargs : dict
        Arguments and Keyword arguments to be passed onto callback.
        The created newly created OAuthToken and Context passed to create_webhook are always passed first.
    message_content : str
        Message content, besides the button with the URL
    button_label : str
        The Label of the button

    If the user never finishes creating a webhook, the callback will not be called
    If they create one , it will be called with ctx, webhook, `args` and `kwargs`
    The link will only work for one webhook
    """
    return request_oauth(
        ctx,
        internal_id,
        domain=domain,
        path=path,
        scope='webhook.incoming',
        callback=callback,
        args=args,
        kwargs=kwargs,
        message_content=message_content,
        button_label=button_label,
    )


def _handle_oauth(
    request: dict,
    start_response: Callable[[str, list], None],
    abort: Callable[[int, str], NoReturn],
) -> list[str]:
    state = request["query_dict"].get("state")  # Must always be present
    code = request["query_dict"].get("code")  # Only on Success
    error = request["query_dict"].get("error")  # Only on Cancelled
    if state is None or (error is None and code is None):
        abort(400, 'Invalid URL')

    url = DISCORD_BASE_URL + "/oauth2/token"

    try:
        record = pending_oauths.get(state)

        if record is None:
            abort(400, "State not found")

        redirect_uri: str = record.redirect_uri
        pending_oauth: PendingOAuth = record.pending_oauth

        del pending_oauths[state]

        if error is not None:
            oauth_token = None

        else:  # if code is not None:
            data = {
                'client_id': os.getenv("DISCORD_CLIENT_ID"),
                'client_secret': os.getenv("DISCORD_CLIENT_SECRET"),
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': unquote(redirect_uri),
            }
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            response = requests.post(url, data=data, headers=headers)
            response.raise_for_status()
            result = response.json()

            oauth_token = OAuthToken.from_dict(result)

        callback_response = pending_oauth.execute_callback(oauth_token)

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
        try:
            print('response content', response.content, flush=True)
        except Exception:
            pass
        abort(500, "Something went wrong")
