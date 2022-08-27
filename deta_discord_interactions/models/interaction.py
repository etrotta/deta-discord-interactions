import dataclasses

from deta_discord_interactions.models.utils import LoadableDataclass
from deta_discord_interactions.models.user import User


@dataclasses.dataclass
class MessageInteraction(LoadableDataclass):
    """
    Partial data of the interaction that a message is a reply to.

    Attributes
    ----------
    id
        The ID (snowflake) of that Interaction.
    name
        The name of the Interaction's application command, as well as the subcommand and subcommand group, where applicable
    type
        The type of the Interaction.
    user
        The User that invoked the interaction.
"""
    id: str
    name: str
    type: int
    user: User
    
    def __post_init__(self):
        if isinstance(self.user, dict):
            self.user = User.from_dict(self.user)
