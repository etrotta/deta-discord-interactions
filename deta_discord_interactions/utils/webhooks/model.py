import os
import importlib
from dataclasses import dataclass
from typing import Optional

import requests

from deta_discord_interactions.models.utils import LoadableDataclass
from deta_discord_interactions.models.message import Message
from deta_discord_interactions.context import Context


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
            from deta_discord_interactions.utils.webhooks._local_http import run_local_server
            run_local_server()
            return f"http://localhost:8000/api/webhooks/{self.id}/{self.token}"

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
        response = requests.post(self.url,data=encoded.encode("UTF-8"),headers={"Content-Type": mimetype},params={"wait": wait_for_response})
        response.raise_for_status()
        if wait_for_response:
            return Message.from_dict(response.json())

    def get(self) -> 'Webhook':
        "Returns the updated Discord data for this Webhook"
        response = requests.get(self.url)
        response.raise_for_status()
        return Webhook.from_dict(response.json())

    def patch(self, *, name: str = None, avatar: str = None, reason: str = None):
        """Updates this webhook

        Parameters
        ----------
        reason : str
            Audit Log reason explaining why it was deleted

        NOTE: Does not updates the library's database automatically
        """
        if name is None and avatar is None:
            raise ValueError("You must provide at least one of `name` and `avatar` to Webhook.patch()")
        if avatar is not None:
            raise NotImplementedError("Updating the Avatar is not supported yet")
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
        
        NOTE: Does not removes from the library's database automatically
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



@dataclass
class PendingWebhook(LoadableDataclass):
    "A 'promise' of a Webhook yet to be created"
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

    def execute_callback(self, webhook: Webhook):
        "Executes the callback for registering this Webhook"
        return self.callback(webhook, self.ctx, *self.callback_args, **self.callback_kwargs)

    def to_dict(self):
        _discord_interactions = self.ctx.discord
        try:
            self.ctx.discord = None
            return super().to_dict()
        finally:
            self.ctx.discord = _discord_interactions