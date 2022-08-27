import dataclasses

from flask_discord_interactions.models.utils import LoadableDataclass
from flask_discord_interactions.models.user import User


@dataclasses.dataclass
class MessageInteraction(LoadableDataclass):
    """
    Represents the interaction that a :class:`Message` is a response to.

    Attributes
    ----------
    id
        The ID (snowflake) of that Interaction.
    name
        The name of the Interaction's application command, as well as the subcommand and subcommand group, where applicable
    type
        The type of the Interaction.
    user
        The :class:`User` that invoked the interaction.
    """
    id: str
    name: str
    type: int
    user: User
    
    def __post_init__(self):
        if isinstance(self.user, dict):
            self.user = User.from_dict(self.user)
