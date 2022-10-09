from dataclasses import dataclass
import random
from deta_discord_interactions import (
    DiscordInteractionsBlueprint,
    Context,
    Message,
    Autocomplete,
    Option,
    Choice,
)
from deta_discord_interactions.utils import Database, AutoSyncRecord, Record
from deta_discord_interactions.utils.cooldown import cooldown
from deta_discord_interactions.utils.database.query import Field, Query

# kwarg to pass to all non-ephemeral Messages that might contain user inputted text
no_mentions = {"allowed_mentions": {"parse": []}}

blueprint = DiscordInteractionsBlueprint()
notes_db = Database(name="user_notes", record_type=AutoSyncRecord)

notes = blueprint.command_group("notes", "Create and manage your notes")


@notes.command("create", "Add a new note to your collection.")
def add_note(ctx: Context, name: str, description: str):
    user = notes_db[ctx.author]
    user_notes = user.setdefault("notes", {})
    if name in user_notes:
        return Message(f"Note {name} already exists, use `/notes update` or `/notes set` if you want to change it", ephemeral=True)
    user_notes[name] = description
    return Message(f"Registered note {name}", ephemeral=True)


@notes.command("get", "Retrieve a note from collection.")
def get_note(ctx: Context, name: Autocomplete[str], ephemeral: bool = True):
    user = notes_db[ctx.author]
    return Message(
        user.setdefault("notes", {}).get(name, f"Note {name} not found"),
        ephemeral=ephemeral,
        **no_mentions,
    )


@notes.command("update")
def update_note(ctx: Context, name: Autocomplete[str], description: str):
    "Updates an existing note"
    user = notes_db[ctx.author]
    user_notes = user.setdefault("notes", {})
    if name not in user_notes:
        return Message(f"Note {name} not found. Use `/note create` or `/note set` to add a new one", ephemeral=True)
    elif user_notes[name] == description:
        return Message(f"Note {name} was already set to that", ephemeral=True)
    else:
        user_notes[name] = description
        return Message(f"Note {name} updated", ephemeral=True)


@notes.command("delete")
def delete_note(ctx: Context, name: Autocomplete[str]):
    "Delete an existing note"
    user = notes_db[ctx.author]
    user_notes = user.setdefault("notes", {})
    if name not in user_notes:
        return Message(f"Note {name} not found", ephemeral=True)
    else:
        user_notes.pop(name)
        return Message(f"Note {name} deleted", ephemeral=True)


@get_note.autocomplete()
@update_note.autocomplete()
@delete_note.autocomplete()
def note_name_autocomplete_handler(ctx, name: Option = None, **_):
    if name is None or not name.focused:
        return []
    user = notes_db[ctx.author]
    user_notes = user.setdefault("notes", {})
    options = []
    for key, description in user_notes.items():
        if key.startswith(name.value):
            display = f"{key}: {description}"
            if len(display) > 100:
                display = display[:97] + '...'
            options.append(Choice(name=display, value=key))
            # It will visually fill in the command with the `name` if you click it, 
            # but it will send with the correct `value` even then
    options.sort(key=lambda option: option.name)
    return options[:25]


@dataclass
class PetRecord(Record):
    # owner: User
    owner_id: str
    name: str
    species: str
    id: str

pets_database = Database("user_pets", record_type=PetRecord)

pets = blueprint.command_group("pets", "Raise Pets")

@pets.command("hatch", "Hatch a new pet")
@cooldown("user", 24*60*60)
def hatch_pet(ctx, name: str):
    species = random.choice(("cat", "dog", "bird"))
    import uuid
    pet = PetRecord(ctx.author.id, name, species, str(uuid.uuid4()))
    pets_database[pet.id] = pet
    return f"Hatched a new {species} pet!"

@pets.command("list", "List your pets")
def list_pets(ctx):
    msg = ''
    for pet in pets_database.fetch(Query(Field("owner_id") == ctx.author.id)):
        msg += f'({pet.species}) {pet.name}\n'
    return Message(msg, ephemeral=True)
