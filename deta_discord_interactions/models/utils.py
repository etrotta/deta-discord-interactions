import inspect


class LoadableDataclass:
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
            k: getattr(self, k, None) for k in inspect.signature(cls).parameters
        }
        for key, value in dictionary.items():
            if isinstance(value, LoadableDataclass):
                dictionary[key] = value.to_dict()
        dictionary["__database_load_method"] = "from_dict"
        dictionary["__module"] = cls.__module__
        dictionary["__name"] = cls.__name__
        return dictionary