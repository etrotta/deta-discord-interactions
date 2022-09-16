import os
import importlib
import datetime
from typing import Optional
from dataclasses import dataclass

import requests
from deta_discord_interactions.models.user import User
from deta_discord_interactions.models.message import Message

from deta_discord_interactions.models.utils import LoadableDataclass
from deta_discord_interactions.context import Context


@dataclass
class OAuthApplication(LoadableDataclass):
    id: str
    name: str
    icon: str
    description: str
    bot_public: bool
    bot_require_code_grant: bool
    verify_key: str
    hook: bool = False


@dataclass
class OAuthInfo(LoadableDataclass):
    application: OAuthApplication
    scopes: list[str]
    expires: datetime.datetime
    user: User

    def __post_init__(self):
        if isinstance(self.application, dict):
            self.application = OAuthApplication.from_dict(self.application)
        if isinstance(self.user, dict):
            self.user = User.from_dict(self.user)
        if isinstance(self.expires, str):
            self.expires = datetime.datetime.fromisoformat(self.expires)


@dataclass
class OAuthToken(LoadableDataclass):
    access_token: str
    refresh_token: str
    scope: str
    expires_in: int
    webhook: 'Webhook' = None
    expire_date: datetime.datetime = None

    def __post_init__(self):
        if isinstance(self.expires_in, int) and self.expire_date is None:
            self.expire_date = datetime.datetime.utcnow() + datetime.timedelta(seconds=self.expires_in)
        if isinstance(self.webhook, dict):
            self.webhook = Webhook.from_dict(self.webhook)

    def get_auth_data(self) -> OAuthInfo:
        "Returns information about the authentication, including information about the user"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        response = requests.get(f'https://discord.com/api/v10/oauth2/@me', headers=headers)
        response.raise_for_status()
        return OAuthInfo.from_dict(response.json())

    def get_user_data(self) -> User:
        "Returns detailed information about the user"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        response = requests.get(f'https://discord.com/api/v10/users/@me', headers=headers)
        response.raise_for_status()
        return User.from_dict(response.json())

    def revoke(self) -> None:
        response = requests.post(
            "https://discord.com/api/oauth2/token/revoke",
            data={"token": self.access_token},
            auth=(os.getenv("DISCORD_CLIENT_ID"), os.getenv("DISCORD_CLIENT_SECRET"))
        )
        response.raise_for_status()



@dataclass
class PendingOAuth(LoadableDataclass):
    "A 'promise' of an OAuth process yet to be confirmed"
    ctx: Context
    callback_module: str
    callback_name: str
    callback_args: list
    callback_kwargs: dict

    @property
    def callback(self):
        module = importlib.import_module(self.callback_module)
        function = getattr(module, self.callback_name)
        return function

    def execute_callback(self, oauth_token: Optional[OAuthToken]):
        "Executes the callback when the user finishes or cancels the OAuth process"
        return self.callback(oauth_token, self.ctx, *self.callback_args, **self.callback_kwargs)

    def to_dict(self):
        _discord_interactions = self.ctx.discord
        try:
            self.ctx.discord = None
            return super().to_dict()
        finally:
            self.ctx.discord = _discord_interactions


@dataclass
class Webhook(LoadableDataclass):
    "Represents an active Discord Webhook"
    id: str
    token: str
    name: str
    avatar: str
    guild_id: str = None
    channel_id: str = None
    # Other fields that we do not store:
    # user: User, does not seems to appear in the data?
    # application_id: str, should always match os.getenv('DISCORD_CLIENT_ID')
    # access_token: str, not required
    # refresh_token: str, not required
    # type: int, always 1 for the ones we support

    @property
    def url(self):
        if os.getenv("DONT_REGISTER_WITH_DISCORD", False):
            raise Exception("Cannot interact with Webhook with `DONT_REGISTER_WITH_DISCORD` env. variable set")

        return f"https://discord.com/api/webhooks/{self.id}/{self.token}"

    def send(
        self,
        message: Message,
        *,
        wait_for_response: bool = False,
        username: str = None,
        avatar_url: str = None,
    ) -> Optional[Message]:
        """Sends a Message through this Webhook.
        Parameters
        ----------
        message: Message | str
            Message to send, converted by `Message.from_return_value` before being sent.
        wait_for_response: bool
            Indicates for Discord to send and return a Message object
        username: str
            Overwrites the default username used for this webhook
        avatar_url: str
            Overwrites the default avatar used for this webhook
        
        Returns
        -------
        Message | None
            If `wait_for_response` is set to True, returns the Message.
            Otherwise returns None
        """
        message = Message.from_return_value(message)

        encode_kwargs = {}
        if username is not None:
            encode_kwargs["username"] = username 
        if avatar_url is not None:
            encode_kwargs["avatar_url"] = avatar_url 

        wait_param = 'true' if wait_for_response else 'false'

        encoded, mimetype = message.encode(followup=True, **encode_kwargs)

        response = requests.post(
            self.url,
            data=encoded.encode("UTF-8"),
            headers={"Content-Type": mimetype},
            params={"wait": wait_param}
        )
        response.raise_for_status()
        if wait_for_response:
            return Message.from_dict(response.json())

    def get(self) -> 'Webhook':
        "Returns the updated Discord data for this Webhook"
        response = requests.get(self.url)
        response.raise_for_status()
        return Webhook.from_dict(response.json())

    def patch(self, *, name: Optional[str] = None, avatar: Optional[str] = None, reason: Optional[str] = None):
        """Updates this webhook

        Parameters
        ----------
        name : str
            Change the default name of the Webhook 
        avatar
            NOT SUPPORTED YET
        reason : str
            Audit Log reason explaining why it was updated

        NOTE: Does not updates any internal databases automatically
        """
        if (name is None) and (avatar is None):
            raise ValueError("You must provide at least one of `name` and `avatar` to Webhook.patch()")
        if avatar is not None:
            raise NotImplementedError("Updating the Avatar is not supported by the library yet")
        data = {}
        headers = {}
        if name is not None:
            data["name"] = name
        if reason is not None:
            headers["X-Audit-Log-Reason"] = reason
        response = requests.patch(
            self.url,
            headers=headers,
            json=data,
        )
        response.raise_for_status()
        return response
    
    def delete(self, *, reason: str = None) -> None:
        """Deletes this Webhook
        
        Parameters
        ----------
        reason : str
            Audit Log reason explaining why it was deleted

        NOTE: Does not removes from any internal databases automatically
        """
        headers = {}
        if reason is not None:
            headers["X-Audit-Log-Reason"] = reason
        response = requests.delete(
            self.url,
            headers=headers,
        )
        response.raise_for_status()
    
    def message_url(self, message_id: str) -> str:
        return f'{self.url}/messages/{message_id}'

    def get_message(self, message_id: str) -> Message:
        "Returns a message previously sent through this Webhook"
        response = requests.get(
            self.message_url(message_id),
        )
        response.raise_for_status()
        return Message.from_dict(response.json())

    def delete_message(self, message_id: str) -> None:
        "Deletes a message previously sent through this Webhook"
        response = requests.delete(
            self.message_url(message_id),
        )
        response.raise_for_status()

    def edit_message(self, message: Message, *, message_id: str = None) -> Message:
        """Edits and returns a message previously sent through this Webhook
        
        Parameters
        ----------
        message : Message
            The message to edit it to
        message_id : str
            If present, use this ID instead of message.id

        Must provide a Message with an ID or a message_id
        """
        message_id = message_id or message.id
        if message_id is None:
            raise ValueError("You must provide a message with an ID or a message_id")

        encoded, _ = message.encode(followup=True)

        response = requests.patch(
            self.message_url(message_id),
            data=encoded,
        )
        response.raise_for_status()
        return Message.from_dict(response.json())
