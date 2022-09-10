import inspect
from typing import Optional


class LoadableDataclass:
    _known_database_models = {}
    _database_model_name = None

    def __init_subclass__(cls, database_model_name: Optional[str] = None) -> None:
        "Register known Loadable Dataclasses as models for encoding/decoding database records"
        # Intentionally not using `__qualname__` to make it not care about where it is defined
        name = database_model_name or cls.__name__
        if (existing_model := LoadableDataclass._known_database_models.get(name)) is not None:
            raise Exception(f"Cannot create class {cls} with same database model name as {existing_model=}")
        LoadableDataclass._known_database_models[name] = cls
        cls._database_model_name = name

    @classmethod
    def from_dict(cls, data):
        """
        Construct the dataclass from a dictionary, skipping any keys
        in the dictionary that do not correspond to fields of the class.

        Parameters
        ----------
        data: dict
            A dictionary of fields to set on the dataclass.
        """
        return cls(
            **{k: v for k, v in data.items() if k in inspect.signature(cls).parameters}
        )

    def to_dict(self):
        """
        Construct a dictionary from the dataclass.
        """
        cls = type(self)
        dictionary = {
            # If we ever feel like reducing the amount of data stored: that + make sure all model fields have ...=None
            # k: value for k in inspect.signature(cls).parameters
            # if (value := getattr(self, k, None)) is not None
            k: getattr(self, k, None) for k in inspect.signature(cls).parameters
        }
        for key, value in dictionary.items():
            if isinstance(value, LoadableDataclass):
                dictionary[key] = value.to_dict()
        dictionary["__database_load_method"] = "LoadableDataclass.from_dict"
        dictionary["__class_name"] = cls._database_model_name
        return dictionary
