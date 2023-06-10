import json
from typing import Union
from dataclasses import dataclass

from deta_discord_interactions.models.message import ResponseType
from deta_discord_interactions.models.option import Choice

class _MetaAutocomplete(type):
    def __getitem__(self, t: type):
        return self(t)


class Autocomplete(metaclass=_MetaAutocomplete):
    """
    Represents the type of an option that can be autocompleted.

    Parameters
    ----------
    t
        The underlying type of the option.
    """

    def __init__(self, t: type):
        self.t = t
    
    # "Using __class_getitem__() on any class for purposes other than type hinting is discouraged."
    # def __class_get_item__(cls, t: type) -> 'Autocomplete':
    #     return cls(t)


@dataclass
class AutocompleteResult:
    """
    Represents the result of an autocomplete handler.

    Parameters
    ----------
    choices
        A list of dicts representing the choices to be presented to the user.
    """
    choices: list[Choice]

    def encode(self):
        """
        Return this result as a complete interaction response.

        Returns
        -------
        bytes
            The encoded JSON object.
        str
            The mimetype of the response (``application/json``).
        """
        data = {
            "type": ResponseType.APPLICATION_COMMAND_AUTOCOMPLETE_RESULT,
            "data": {"choices": [choice.dump() for choice in self.choices]},
        }

        return json.dumps(data).encode("UTF-8"), "application/json"

    @classmethod
    def from_return_value(cls, value: Union[dict, list, "AutocompleteResult"]):
        """
        Converts the return value of an autocomplete handler to an
        AutocompleteResult.

        Parameters
        ----------
        value
            The return value of an autocomplete handler.

        Returns
        -------
        AutocompleteResult
            The AutocompleteResult that corresponds to the return value.
        """
        if isinstance(value, AutocompleteResult):
            return value
        elif isinstance(value, dict):
            return cls([Choice(name=key, value=val) for key, val in value.items()])
        elif isinstance(value, list):
            if all(isinstance(x, Choice) for x in value):
                return cls(value)
            elif all(isinstance(x, dict) for x in value):
                return cls([Choice(d["name"], d["value"], d.get("name_localizations")) for d in value])
        
        return cls(
            [Choice(str(choice), choice) for choice in value]
        )
