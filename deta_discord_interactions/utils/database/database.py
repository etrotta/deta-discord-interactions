import os
import itertools
import json
from typing import Callable, Optional, Type, Union, overload, TypeVar
from collections.abc import Generator, MutableMapping
from datetime import datetime
import inspect

from deta import Base

from deta_discord_interactions.models.utils import LoadableDataclass
from deta_discord_interactions.utils.database.exceptions import KeyNotFound, UnexpectedEscapeString, UnexpectedFunction
from deta_discord_interactions.utils.database.query import Query

from deta_discord_interactions.utils.database._local_base import Base as LocalBase

# Instructions for encoding / decoding data not supported by deta base
EMPTY_LIST_STRING = "$EMPTY_LIST"  # Setting a field to an empty list sets it to `null`
EMPTY_DICTIONARY_STRING = "$EMPTY_DICT"  # Setting a field to an empty dictionaries seems to set it to `null`
DATETIME_STRING = "$ENCODED_DATETIME"  # Ease datetime conversion
SET_STRING = "$ENCODED_SET"  # Allow storing sets
INT_STRING = "$ENCODED_INTEGER"  # Allow using integers in dictionary keys
FUNCTION_STRING = "$ENCODED_FUNCTION"  # Allow storing functions
ESCAPE_STRING = "$NOOP"  # Do not mess up if the user input 'just happen' to start with a $COMMAND

Record = TypeVar("Record", bound=LoadableDataclass)

class Database(MutableMapping[str, Record]):
    def __init__(self, name: str, record_type: Type[Record], *, base_mode: Optional[str] = None, base_folder: Optional[str] = None):
        """Deta Base wrapper | ORM
        
        Parameters
        ----------
        name : str
            Which name to use for the Deta Base
        record_type : Type[LoadableDataclass]
            Record model (must inherit LoadableDataclass)
        base_mode: Optional[str], support values: "DETA", "MEMORY", "DISK"
            Which mode to use for the database.
            DETA: Uses Deta Base
            DISK: Saves the data to a local file instead of using Deta Base.
            MEMORY: Keep the data in memory but do not save at all.
            By default, uses the `DETA_ORM_DATABASE_MODE` environment variable, or "DETA" if unset
        base_folder : str
            If using `base_mode = "DISK"`, you can use this to specify where the database should be stored.
            If missing, expects for the `DETA_ORM_FOLDER` environment variable to be set.
        """
        if base_mode is None:
            base_mode = os.getenv("DETA_ORM_DATABASE_MODE", "DETA")
        if base_mode.startswith("DETA"):
            self.__base = Base(name)
        elif base_mode == "MEMORY":
            self.__base = LocalBase(name, sync_disk=False)
        elif base_mode == "DISK":
            self.__base = LocalBase(name, sync_disk=True, folder=base_folder)
        else:
            raise Exception("Invalid value for DETA_ORM_DATABASE_MODE")

        self._record_type = record_type
        self.__known_functions = {}
    
    def remember_function(self, function: Callable):
        """Use as a decorator to be able to save/load a function reference in LoadableDataclasses."""
        self.__known_functions[function.__name__] = function
        self.__known_functions[function] = function.__name__
        return function

    def __getitem__(self, key: str) -> Record:
        """Retrieves an item from the database.
        If the key if not found, raises a KeyError.
        """
        result = self.get(key)
        if result is None:
            raise KeyError(key)
        return result

    def __setitem__(self, key: str, record: Record) -> None:
        self.put(key, record)
    
    def __delitem__(self, key: str) -> None:
        self.delete(key)

    @overload  # Nested (2d+) lists
    def encode_entry(self, record: Union[list, tuple]) -> list: ...
    @overload
    def encode_entry(self, record: dict) -> dict: ...
    def encode_entry(self, record):
        "Converts values so that we can store it properly in Deta Base. Does not modifies in-place."
        # List of known unsupported things: 
        # - lists of sets
        # - sets containing anything other than strings/integers
        # - dict keys other than strings, integers and datetimes
        if isinstance(record, (list, tuple)):
            result, items = [None] * len(record), enumerate(record)
        else:
            result, items = dict(), record.items()
        for key, value in items:
            # Encode key if needed
            if isinstance(key, str) and key.startswith("$"):
                key = ESCAPE_STRING + key
            elif isinstance(record, dict) and isinstance(key, int) and not isinstance(key, bool):
                key = INT_STRING + str(key)
            elif isinstance(key, datetime):
                key = DATETIME_STRING + key.isoformat()
            # Encode value
            if isinstance(value, dict) and dict(value) == {}:  # Empty dict becomes `null` on deta base on update
                result[key] = EMPTY_DICTIONARY_STRING
            elif isinstance(value, (list, tuple)) and list(value) == []:  # Empty lists becomes `null` on deta base on update
                result[key] = EMPTY_LIST_STRING
            elif isinstance(value, dict):  # Convert nested fields 
                result[key] = self.encode_entry(value)
            elif isinstance(value, (list, tuple)):  # Convert all list elements
                result[key] = [
                    self.encode_entry(element)
                    if isinstance(element, (dict, list, tuple))
                    else element 
                    for element in value
                ]
            elif isinstance(value, set):  # Convert all set elements, and turn it into a list
                result[key] = SET_STRING + json.dumps([
                    self.encode_entry(element)
                    if isinstance(element, (dict, list, tuple))
                    else element 
                    for element in value
                ])
            elif inspect.isfunction(value):  # Allow storing functions
                if value in self.__known_functions:
                    result[key] = FUNCTION_STRING + self.__known_functions[value]
                else:
                    raise UnexpectedFunction(f"""Unexpected function: {value}. \
                    If you want to save it in the database, please use the `Database.remember_function` decorator.""")
                # This should only be used if this record is only going to be stored for a short amount of time
                # And even then, it should be using sparingly
            elif isinstance(value, datetime):  # Ease datetime conversion
                result[key] = DATETIME_STRING + value.isoformat()
            elif isinstance(value, str) and value.startswith("$"):  # essentially escape '$'
                result[key] = ESCAPE_STRING + value
            else:
                result[key] = value
        return result

    @overload
    def decode_entry(self, record: list) -> list: ...
    @overload
    def decode_entry(self, record: dict) -> dict: ...
    def decode_entry(self, record):
        "Converts back some changes that we may make when storing. Does not modifies in-place."
        if isinstance(record, list):
            result, items = [None]*len(record), enumerate(record)
        else:
            result, items = {}, record.items()

        for key, value in items:
            if isinstance(key, str) and key.startswith("$"):  # Decode key
                if key.startswith(ESCAPE_STRING):
                    key = key.removeprefix(ESCAPE_STRING)
                elif key.startswith(DATETIME_STRING):
                    key = datetime.fromisoformat(key.removeprefix(DATETIME_STRING))
                elif key.startswith(INT_STRING):
                    key = int(key.removeprefix(INT_STRING))
                else:
                    raise UnexpectedEscapeString(f"Unexpected escape string on key: {key}")
            # Decode value
            if isinstance(value, dict):  # Make sure we hit nested fields
                result[key] = self.decode_entry(value)
            elif isinstance(value, list):  # Convert all list elements.
                result[key] = [
                    self.decode_entry(element) 
                    if isinstance(element, (dict, list)) 
                    else element
                    for element in value
                ]
            elif isinstance(value, str) and value.startswith("$"):  # Revert our custom 'special' strings
                if value == EMPTY_DICTIONARY_STRING:  # Empty dict may become `null` on deta base
                    result[key] = {}
                elif value == EMPTY_LIST_STRING:  # Empty lists may become `null` on deta base
                    result[key] = []
                elif value.startswith(SET_STRING):  # Load sets
                    result[key] = set(json.loads(value.removeprefix(SET_STRING)))
                elif value.startswith(FUNCTION_STRING):  # Allow storing functions
                    if (fun := value.removeprefix(FUNCTION_STRING)) in self.__known_functions:
                        result[key] = self.__known_functions[fun]
                    else:
                        raise UnexpectedFunction(f"Missing previously stored function {fun}, cannot decode record")
                elif value.startswith(DATETIME_STRING):  # Ease datetime conversion
                    result[key] = datetime.fromisoformat(value.removeprefix(DATETIME_STRING))
                elif value.startswith(ESCAPE_STRING):  # Escape strings starting with `$`
                    result[key] = value.removeprefix(ESCAPE_STRING)
                else:
                    raise UnexpectedEscapeString(f"Unexpected escape string on key: {key}")
            else:
                result[key] = value
        return result

    def get(self, key: str) -> Optional[Record]:
        """Retrieve a record based on it's key. 
        If it does not exists, returns None"""
        data: Optional[dict] = self.__base.get(str(key))
        if data is None:
            return None
        result = self.decode_entry(data)
        result = self._record_type.from_dict(result)
        return result

    def insert(self, key: str, data: Record, *, expire_in: Optional[int] = None, expire_at: Optional[datetime] = None) -> None:
        "Insert a record. Errors if it already exists."
        assert isinstance(data, self._record_type), "You may only insert records of the type you passed when creating the database"
        data = data.to_dict()
        self.__base.insert(self.encode_entry(data), str(key), expire_in=expire_in, expire_at=expire_at)
    
    def put(self, key: str, data: Record, *, expire_in: Optional[int] = None, expire_at: Optional[datetime] = None) -> None:
        "Insert a record, or overwrite it if it already exists."
        assert isinstance(data, self._record_type), "You may only insert records of the type you passed when creating the database"
        data = data.to_dict()
        self.__base.put(self.encode_entry(data), str(key), expire_in=expire_in, expire_at=expire_at)
    
    def delete(self, key: str) -> None:
        "Deletes a record."
        self.__base.delete(str(key))

    def _put_many_list(self, data: list[list[Record]], key_source: Callable[[Record], str], **kwargs) -> None:
        for sub_list in data:
            records: list[dict] = []
            for record in sub_list:
                assert isinstance(record, self._record_type), "You may only insert records of the type you passed when creating the database"
                _key = key_source(record)
                record = self.encode_entry(record.to_dict())
                record['key'] = _key
                records.append(record)
            if records:
                self.__base.put_many(records, **kwargs)

    def _put_many_dict(self, data: list[list[tuple[str, Record]]], **kwargs) -> None:
        for sub_dict_items in data:
            records: list[dict] = []
            for k, record in sub_dict_items:
                assert isinstance(record, self._record_type), "You may only insert records of the type you passed when creating the database"
                record = self.encode_entry(record.to_dict())
                record['key'] = k
                records.append(record)
            if records:
                self.__base.put_many(records, **kwargs)

    @overload  # Putting a dictionary of str -> Record
    def put_many(
        self,
        data: dict[str, Record],
        *,
        iter: bool = False,
        **kwargs
    ) -> None: ...
    @overload  # Putting a list of Records
    def put_many(
        self,
        data: list[Record],
        *,
        key_source: Union[str, Callable[[Record], str]] = None,
        iter: bool = False,
        **kwargs
    ) -> None: ...
    def put_many(  # Actual definition
        self,
        data,
        *,
        key_source = None,
        iter = False,
        **kwargs,
    ) -> None:
        """Insert or overwrite multiple records and return them. 
        Deta Base has a limit of up to 25 records at once without `iter`

        Parameters
        ----------
        data : list of records or dictionary
            If a list of records: 
                If key_source is a string: Use that record attribute as the key
                If the key_source is a function: Calls it for each Record
            If a dictionary: Uses the dictionary's keys for their respective records
        key_source: str, function or None
            Which field to use as the `key` for each record in data.
            If it's callable, it will be called for each record
            Ignored when using a dictionary
        iter : bool, default False
            Automatically split the data into sublists of up to 25 items and put multiple times.
            If set to True, this function may use multiple HTTPS requests.

        other kwargs: expire_in / expire_at
        """
        if isinstance(data, list):
            if iter:
                data_chain = itertools.chain(data[offset:offset+25] for offset in range(0, len(data), 25))
            else:
                data_chain = [data]
            if isinstance(key_source, str):
                key_field = key_source
                key_source = lambda record: str(getattr(record, key_field))  # noqa: E731
            self._put_many_list(data_chain, key_source, **kwargs)
        elif isinstance(data, dict):
            if iter:
                _it = iter(data.items())
                data_chain = (itertools.islice(_it, 25) for _ in range(((len(data)-1) // 25) + 1))
            else:
                data_chain = [data.items()]
            self._put_many_dict(data_chain, **kwargs)
        else:
            raise TypeError(f"Unsupported type {type(data)} passed to {self}.put_many: {data!r}")

    def fetch(
        self,
        query: Union[Query, dict, list[dict], None] = None,
        limit: Optional[int] = 1000,
        last: Optional[str] = None,
        follow_last: bool = False,
    ) -> list[Record]:
        """Returns multiple items from the database based on a query.

        Parameters
        ----------
        query : Query
            See the `Query` and `Field` classes as well as https://docs.deta.sh/docs/base/queries/ for more information.
        limit : Optional[int], default 1000
            Maximum number of records to fetch. None to fetch all.
            NOTE: Deta Base will only retrieve up to 1MB of data at a time, and that is before applying the filters
        last : str, default None
            Equivalent to `offset` in normal databases, but key based instead of position based
        follow_last : bool, default False
            Automatically fetch more records up to `limit` if the query returns a `last` element
        """
        if isinstance(query, Query):
            query = self.encode_entry(query.to_list())
        result = self.__base.fetch(query, limit=limit, last=last)
        records = result.items
        if follow_last:
            while (result.last is not None) and (limit is None or len(records) < limit):
                result = self.__base.fetch(query, limit=limit, last=result.last)
                records.extend(result.items)

        result = []
        for record in records:
            loaded = self.decode_entry(record)
            loaded = self._record_type.from_dict(loaded)
            result.append(loaded)
        return result

    def __iter__(self) -> Generator[Record, None, None]:
        "I strongly recommend using fetch() instead"
        yield from self.fetch(
            query=None,
            limit=None,
            follow_last=True,
        )

    def __len__(self):
        "Not supported - there are no documented methods in the Deta Base API for the document count."
        raise NotImplementedError()

    def update(self, key: str, updates: dict) -> None:
        """Updates a LoadableDataclass in the database. Local representations of it might become outdated."""
        updates = self.encode_entry(updates)
        try:
            self.__base.update(updates, key)
        except Exception as err:  # They just use a normal Exception instead of a custom type, which is pretty annoying
            import re
            reason = err.args[0] if err.args else ''
            if isinstance(reason, str) and re.fullmatch(r"Key \'.*\' not found", reason):
                raise KeyNotFound(reason)
            else:
                raise
