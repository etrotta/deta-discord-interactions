import pytest
import dataclasses
import datetime
import typing

from deta_discord_interactions.utils.database import Database, LoadableDataclass, Query, Field

@dataclasses.dataclass
class Mini(LoadableDataclass):
    a: int
    b: float

@dataclasses.dataclass
class MyTestRecord(LoadableDataclass):
    name: str
    number: int
    date: datetime.datetime
    func: typing.Callable
    nested: Mini

@dataclasses.dataclass
class WeirdTestRecord(LoadableDataclass):
    name: typing.Optional[str]
    alt: typing.Optional[str]
    number: typing.Union[int, float]
    size: typing.Literal[1, 2, 3]
    nested_list: list[Mini]
    keys: set
    nested_dict: dict[str, Mini]


@pytest.fixture()
def database():
    return Database("test_database", record_type=MyTestRecord, base_mode="MEMORY")

@pytest.fixture()
def disk_database(tmp_path):
    return Database("test_database", record_type=MyTestRecord, base_mode="DISK", base_folder=tmp_path)

@pytest.fixture()
def weird_disk_database(tmp_path):
    return Database("weird_test_database", record_type=WeirdTestRecord, base_mode="DISK", base_folder=tmp_path)

@pytest.fixture()
def foo_func(database: Database, disk_database: Database):
    @disk_database.remember_function
    @database.remember_function
    def foo():
        return 1
    return foo

@pytest.fixture()
def mini_rec():
    return Mini(1, 2.0)

@pytest.fixture()
def foo_rec(foo_func, mini_rec):
    foo = MyTestRecord(
        "foo",
        1,
        datetime.datetime.fromisoformat("2020-01-01"),
        foo_func,
        mini_rec,
    )
    return foo

@pytest.fixture()
def weird_rec(mini_rec):
    rec = WeirdTestRecord(
        "existing",
        None,
        2.5,
        3,
        [mini_rec] * 3,
        {1, "a", "b"},
        {1: mini_rec, "a": mini_rec, "b": mini_rec},
    )
    return rec

DATE = datetime.datetime.fromisoformat("2020-01-01")

def test_encode_decode(
        database: Database[str, MyTestRecord],
        mini_rec: Mini,
        foo_func: typing.Callable,
        foo_rec: MyTestRecord,
        weird_rec: WeirdTestRecord,
    ):
    # Part 1) to_dict()
    assert mini_rec.to_dict() == {"a": 1, "b": 2.0}
    assert foo_rec.to_dict() == {
        "name": "foo",
        "number": 1,
        "date": DATE,
        "func": foo_func,
        "nested": mini_rec.to_dict(),
    }
    assert weird_rec.to_dict() == {
        "name": "existing",
        "alt": None,
        "number": 2.5,
        "size": 3,
        "nested_list": [mini_rec.to_dict()] * 3,
        "keys": {1, "a", "b"},
        "nested_dict": {1: mini_rec.to_dict(), "a": mini_rec.to_dict(), "b": mini_rec.to_dict()},
    }

    # Part 2) database encoding
    assert database.encode_entry(mini_rec.to_dict()) == {"a": 1, "b": 2.0}
    assert database.encode_entry(foo_rec.to_dict()) == {
        "name": "foo",
        "number": 1,
        "date": f"$ENCODED_DATETIME{DATE.isoformat()}",
        "func": "$ENCODED_FUNCTIONfoo",
        "nested": mini_rec.to_dict(),
    }
    _encoded_weird = database.encode_entry(weird_rec.to_dict())
    # The order may be different since it depends on the string hashes (thanks, sets...)
    assert sorted(_encoded_weird.pop("keys")) == sorted('$ENCODED_SET[1, "a", "b"]')
    assert _encoded_weird == {
        "name": "existing",
        "alt": None,
        "number": 2.5,
        "size": 3,
        "nested_list": [mini_rec.to_dict()] * 3,
        # "keys": '$ENCODED_SET[1, "a", "b"]',
        "nested_dict": {'$ENCODED_INTEGER1': mini_rec.to_dict(), "a": mini_rec.to_dict(), "b": mini_rec.to_dict()},
    }

    # Part 3) database decoding
    assert database.decode_entry(database.encode_entry(mini_rec.to_dict())) == mini_rec.to_dict()
    assert database.decode_entry(database.encode_entry(foo_rec.to_dict())) == foo_rec.to_dict()
    assert database.decode_entry(database.encode_entry(weird_rec.to_dict())) == weird_rec.to_dict()

def test_record_loading(database: Database[str, MyTestRecord], foo_rec: MyTestRecord, mini_rec: Mini, weird_rec: WeirdTestRecord):
    # Part 4) record loading
    assert mini_rec.from_dict(mini_rec.to_dict()) == mini_rec
    assert foo_rec.from_dict(foo_rec.to_dict()) == foo_rec
    assert weird_rec.from_dict(weird_rec.to_dict()) == weird_rec
    
    # Check that the nested things also work
    assert foo_rec.from_dict(foo_rec.to_dict()).nested == foo_rec.nested
    assert foo_rec.from_dict(foo_rec.to_dict()).func() == foo_rec.func()

    # Part 4.1) record loading with encoding/decoding
    # should be redundant, but still helps with peace of mind
    assert mini_rec.from_dict(database.decode_entry(database.encode_entry(mini_rec.to_dict()))) == mini_rec
    assert foo_rec.from_dict(database.decode_entry(database.encode_entry(foo_rec.to_dict()))) == foo_rec
    assert weird_rec.from_dict(database.decode_entry(database.encode_entry(weird_rec.to_dict()))) == weird_rec
    
    # Check that the nested things also work
    assert foo_rec.from_dict(database.decode_entry(database.encode_entry(foo_rec.to_dict()))).nested == foo_rec.nested
    assert foo_rec.from_dict(database.decode_entry(database.encode_entry(foo_rec.to_dict()))).func() == foo_rec.func()

def test_record_storing(database: Database[str, MyTestRecord], foo_rec: MyTestRecord):
    # Part 6) storing and retrieving
    # not gonna lie, may have skipped a few steps, but whatever
    # Currently this uses an in-memory proxy-ish database
    # in the future it may be better to use monkeypatching 
    # and make sure that the requests it makes to the API look right
    database["foo"] = foo_rec
    assert database["foo"] == foo_rec

    # Part 7) Other methods
    del database["foo"]
    assert database.get("foo") is None

    foo_rec.number = 1
    database.put("foo", foo_rec)
    assert database["foo"].number == 1
    
    foo_rec.number = 2
    database.put("foo", foo_rec)
    assert database["foo"].number == 2

    foo_rec.number = 3
    with pytest.raises(Exception):
        database.insert("foo", foo_rec)
    assert database["foo"].number == 2

    del database["foo"]
    database.put_many([foo_rec], key_source="name")
    assert database.get("foo") == foo_rec

    del database["foo"]
    database.put_many({"foo": foo_rec})
    assert database.get("foo") == foo_rec

def test_queries(database: Database[str, MyTestRecord], foo_rec: MyTestRecord):
    # Currently this uses an in-memory proxy-ish database
    # in the future it may be better to use monkeypatching 
    # and make sure that the requests it makes to the API look right
    database["foo"] = foo_rec

    # Basic usage working properly...
    records = database.fetch()
    looped = []
    for record in database:
        looped.append(record)
    assert records == looped == [foo_rec]

    # Some queries that should match it
    records = database.fetch(Query(Field("key") == "foo"))
    assert records == [foo_rec]
    records = database.fetch(Query(Field("name") == "foo"))
    assert records == [foo_rec]
    records = database.fetch(Query(Field("number") == 1, Field("date") == DATE))
    assert records == [foo_rec]
    records = database.fetch(Query(Field("number") == 2) | Query(Field("date") == DATE))
    assert records == [foo_rec]
    
    # Some queries that should NOT match it
    records = database.fetch(Query(Field("key") == "bar"))
    assert records == []
    records = database.fetch(Query(Field("number") == 2, Field("date") == DATE))
    assert records == []


def test_disk_database(
        disk_database: Database[str, MyTestRecord],
        foo_rec: MyTestRecord,
        weird_disk_database: Database[str, WeirdTestRecord],
        weird_rec: MyTestRecord,
):
    disk_database["foo"] = foo_rec
    weird_disk_database["foo"] = weird_rec
    assert disk_database["foo"] == foo_rec
    assert weird_disk_database["foo"] == weird_rec

    # Part 7) Other methods
    del disk_database["foo"]
    assert disk_database.get("foo") is None

    foo_rec.number = 1
    disk_database.put("foo", foo_rec)
    assert disk_database["foo"].number == 1
    
    foo_rec.number = 2
    disk_database.put("foo", foo_rec)

    _path = disk_database._Database__base.inventory._path
    copy = Database("test_database", record_type=MyTestRecord, base_mode="DISK", base_folder=_path.parent)
    copy.remember_function(foo_rec.func)
    assert copy["foo"].number == 2
    del copy

    foo_rec.number = 3
    with pytest.raises(Exception):
        disk_database.insert("foo", foo_rec)
    assert disk_database["foo"].number == 2

    del disk_database["foo"]
    disk_database.put_many([foo_rec], key_source="name")
    assert disk_database.get("foo") == foo_rec

    del disk_database["foo"]
    disk_database.put_many({"foo": foo_rec})
    assert disk_database.get("foo") == foo_rec
