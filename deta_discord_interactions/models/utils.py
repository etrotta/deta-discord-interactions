import dataclasses
from dataclasses import fields, MISSING
import copy
import typing


def resolve_fancy_annotation(origin: typing.Optional[type], args: tuple, value: typing.Any):
    if isinstance(origin, type) and issubclass(origin, LoadableDataclass):
        return origin.from_dict(value)
    elif origin is list and args != ():
        assert isinstance(value, list), f"Stored {value=} must be a list when type hinting as list[...]"
        if issubclass(args[0], LoadableDataclass):
            return [args[0].from_dict(val) for val in value]
        return value
    elif origin is dict and args != ():
        assert isinstance(value, dict), f"Stored {value=} must be a dict when type hinting as dict[...]"
        if issubclass(args[-1], LoadableDataclass):
            return {k: args[-1].from_dict(val) for k, val in value.items()}
        return value
    elif origin is typing.Optional:
        if value is None:
            return None
        else:
            nested_origin = typing.get_origin(args[0])
            nested_args = typing.get_args(args[0])
            return resolve_fancy_annotation(nested_origin, nested_args, value)
    elif origin is typing.Union:
        # TODO improve Union[] support
        if type(None) in args and value is None:
            return None
        for arg in args:
            if isinstance(arg, type) and issubclass(arg, LoadableDataclass):
                return arg.from_dict(value)
        return value
    else:
        return value


# TODO: Update this to use typing.Self once deta supports 3.11+
Self = typing.TypeVar("Self", bound="LoadableDataclass")

class LoadableDataclass:
    """Base class that provides methods to load and encode the data.
    Also used to interface with the `deta_discord_interactions.utils.database` module.

    When using the database module, directly instanciating this class is not recommended. Either:
    - Subclass and use with dataclasses @dataclass.
    - Subclass and overwrite `__init__`, `to_dict` and (@classmethod) `from_dict`
    """
    def __init__(self, **kwargs):
        "Direct usage of the LoadableDataclass class is not advisable."
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def from_dict(cls: type[Self], data: dict) -> Self:
        """
        Construct the LoadableDataclass from a dictionary
        """
        if dataclasses.is_dataclass(cls):
            result = {}
            for field in fields(cls):
                if field.name in data or (field.default is MISSING and field.default_factory is MISSING):
                    origin = typing.get_origin(field.type) or field.type
                    args = typing.get_args(field.type)
                    value = data.get(field.name)
                    result[field.name] = resolve_fancy_annotation(origin, args, value)
        else:
            result = {k: v for k, v in data.items()}
        return cls(**result)

    def to_dict(self) -> dict:
        "Converts into a dictionary fit for storing in the Deta Base"
        data = copy.copy(self)
        for attr, val in vars(data).items():
            if isinstance(val, LoadableDataclass):
                setattr(data, attr, val.to_dict())
        if dataclasses.is_dataclass(data):
            data = dataclasses.asdict(data)
        else:
            data = {k: v for k, v in vars(data).items() if not k.startswith("_")}
        return data
