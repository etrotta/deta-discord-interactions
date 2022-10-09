"""You must import the Database and at least one of 
- Record (to make your own classes)
- AutoSyncRecord (if you want simplicity over clarity and control)"""

"""If you want to subclass Record, 
you are recommended to use a dataclass"""
from dataclasses import dataclass  

from deta_discord_interactions.utils.database import Database
from deta_discord_interactions.utils.database import Record, AutoSyncRecord
from deta_discord_interactions.utils.database import Query, Field

@dataclass
class MyRecord(Record):
    name: str
    age: int

database_with_schema = Database("mydb", record_type=MyRecord)
database_without_schema = Database("myotherdb", record_type=AutoSyncRecord)

# To fetch via key:
database_with_schema.get("record_key")  # missing -> returns None
database_with_schema["record_key"]  # missing -> raises KeyError

# To set or update:
database_with_schema["record_key"] = MyRecord("bob", 100)
# To set many at a time:
records = [MyRecord("dog", 10), MyRecord("cat", 11), MyRecord("bird", 5)]

"""
You must use either
- one dictionary
- a list of records + a key_source (function or string)
- - When passing a string, it will use that field in the record, so these two are equivalent:"""
database_with_schema.put_many(records, key_source=lambda record: record.name)
database_with_schema.put_many(records, key_source="name")
# When using a dictionary, it will instead use the dictionary's keys and ignore key_source
records = {"dog": MyRecord("dog", 10), "cat": MyRecord("cat", 11), "bird": MyRecord("bird", 5)}
database_with_schema.put_many(records)
# Avoid using put() or insert() directly, these expect dictionaries and will not encode the data.

# Differences when using AutoSyncRecord:
# Neither of these actually fetches until you try to access an field from the returned record:
database_with_schema.get("record_key")  
database_with_schema["record_key"]
# If it is not present on the database, it will be like an empty dictionary instead of returning None / raising KeyError

# Updates to the record are automatically saved: 
database_without_schema["bird"].name = "bird"
database_without_schema["bird"].age = 10
database_without_schema["bird"].get("age")
database_without_schema["bird"].setdefault("nicknames", []).append("tori")
# In order to avoid making multiple unecessary requests, you should use a Context Manager to execute multiple updates at the same time:
with database_without_schema["dog"] as record:
    record.name = "bird"
    record.age = 10

# put_many should work the same, but I would generally recommend using a database with schema if you need to work with many records

# In order to fetch via queries:
database_with_schema.fetch(Query(Field("name") == "bird"))
database_with_schema.fetch(Query(Field("name").startswith("bird")))
database_with_schema.fetch(Query("bird" in Field("name")))
# OR operations:
database_with_schema.fetch(Query("bird" == Field("name")) | Query("cat" == Field("name")))
# AND operations:
database_with_schema.fetch(Query("bird" == Field("name"), Field("age") < 10))
# some arbitrary operations to demonstrate using AND & OR on the same query
x = 'd' in Field("name")
y = Field("age") > 5
z = Field("age") < 10
# (x AND y) OR (z):
database_with_schema.fetch(
    Query(
        x,
        y
    ) | Query(
        z,
    ),
)
# It's not possible to do (x OR y) AND (z), you must do (x AND z) OR (y AND z) instead
database_with_schema.fetch(
    Query(
        x,
        z,
    ) | Query(
        y,
        z,
    ),
)
# Should work the same for AutoSyncRecord, but again, 
# I would generally recommend using a database with schema if you need to work with many records

# (Both do use Deta Base, which is technically schemaless anyway, but using dataclasses to enforce a schema can help keep things concise)

"""
You can store most deta_discord_interactions models in Deta Base, such as Users or Webhooks, which are automatically encoded/decoded.
Some objects such as Users may also be used as database keys, which are converted to strings.
One notable exception is that you may need to remove the Context's discord field if you want to store it. 

You can also use deta_discord_interactions.models.utils.LoadableDataclass to create your own nested classes,
but the record type must be a record, and you cannot nest records.
"""
from deta_discord_interactions.context import Context
from deta_discord_interactions.models.utils import LoadableDataclass
@dataclass
class Animal(LoadableDataclass):
    name: str
    age: int

@dataclass
class Example(Record):
    ctx: Context
    animal: Animal

    def to_dict(self):
        _discord_interactions = self.ctx.discord
        try:
            self.ctx.discord = None
            return super().to_dict()
        finally:
            self.ctx.discord = _discord_interactions

# Queries on nested fields are not expliclty supported yet, I'm not sure if they would work*

"""
You can manually check the database data in deta.sh, but you may notice some things like
- fields names such as "__database_load_method" 
- or field values such as "$EMPTY_LIST"
Do not worry - these are required to encode/decode the data in a way that deta doesn't breaks.

Also, keep in mind the Deta's limitations
- Each individual record must not exceed 400KB

- Queries may only process up to 1MB at a time, before applying filters
-- You can use `follow_last=True` to automatically go through all records, 
   but keep in mind that it will execute ceil(database total size / 1MB) requests to do so

- You can only insert up to 25 records per put_many call
-- You can use `iterate=True` to separate into multitple calls automatically,
   but keep in mind that it will execute ceil(len(records)/25) requests to do so
"""
