from typing import Union
from deta_discord_interactions import DiscordInteractionsBlueprint, Autocomplete, Choice, Option

bp = DiscordInteractionsBlueprint()

COUNTRIES = ["Germany", "Canada", "United States", "United Kingdom"]
CITIES = {
    "Germany": ["Berlin", "Munich", "Frankfurt"],
    "Canada": ["Toronto", "Montreal", "Vancouver"],
    "United States": ["New York", "Chicago", "Los Angeles"],
    "United Kingdom": ["London", "Manchester", "Liverpool"],
}

@bp.command()
def city_from_country(ctx, country: Autocomplete[str], city: Autocomplete[str]):
    return f"You selected **{city}, {country}**!"

@city_from_country.autocomplete()
def autocomplete_handler(ctx, country: Union[Option, None] = None, city: Union[Option, None] = None):
    if country is not None and country.focused:
        return [c for c in COUNTRIES if c.lower().startswith(country.value.lower())]
    elif city is not None and city.focused:
        if country.value in CITIES:
            return CITIES[country.value]
        else:
            return []


@bp.command()
def country_and_city(ctx, selection: Autocomplete[str]):
    return f"You selected **{selection}**!"

@country_and_city.autocomplete()
def other_autocomplete_handler(ctx, selection: Union[Option, None] = None):
    # Alternatively, you can return a list of Choices if you want to alias the value:
    if selection is not None and selection.focused:
        val = selection.value.casefold()
        choices: list[Choice] = []
        for country, cities in CITIES.items():
            for city in cities:
                if val in city.casefold() or val in country.casefold():
                    choices.append(Choice(f"{country}, {city}", city))
        choices.sort(key=lambda choice: choice.name)  # Optionally sort however you want
        return choices
    return []


@bp.command()
def more_autocomplete(ctx, value: Autocomplete[int]):
    return f"Your number is **{value}**."


@more_autocomplete.autocomplete()
def more_autocomplete_handler(ctx, value: Union[Option, None] = None):
    # Note that even though this option is an int,
    # the autocomplete handler still gets passed a str.
    try:
        value = int(value.value)
    except ValueError:
        return []

    return [i for i in range(value, value + 10)]
