import functools

class BoundMeta(type):
    """A class made to ease syncing changes to mutable objects to the database.

    When any of the methods called to `bind_methods` are called, it will:
        - execute that method
        - call self._sync() with:
            the name of that method,
            the value returned by that method
            the arguments and keyword arguments passed to that method
        - return the value returned by _sync
    Note: The 'bound' methods are decorated. Do not further modify them. 

    Example Usage:
        class Test(list, metaclass=BoundMeta, bind_methods=['__iadd__', 'append', 'extend']):
            def _sync(self, method, value, *args, **kwargs):
                print(self, method, value)
                return value
    """

    def __new__(cls, name, bases, namespace, *, bind_methods):
        if '_sync' not in namespace:
            raise ValueError("Classes using `BoundMeta` as a metaclass must define a `_sync` method")

        new_class = super().__new__(cls, name, bases, namespace)

        for field in bind_methods:

            @functools.wraps(getattr(new_class, field))
            def wrapped(self, *args, _field=field, **kwargs):
                value = getattr(super(new_class, self), _field)(*args, **kwargs)
                return self._sync(_field, value, *args, **kwargs)

            setattr(new_class, field, wrapped)

        return new_class
