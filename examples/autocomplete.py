import os

from deta_discord_interactions import DiscordInteractions, Autocomplete


app = DiscordInteractions()


@app.command()
def autocomplete_example(ctx, country: Autocomplete[str], city: Autocomplete[str]):
    return f"You selected **{city}, {country}**!"


COUNTRIES = ["Germany", "Canada", "United States", "United Kingdom"]
CITIES = {
    "Germany": ["Berlin", "Munich", "Frankfurt"],
    "Canada": ["Toronto", "Montreal", "Vancouver"],
    "United States": ["New York", "Chicago", "Los Angeles"],
    "United Kingdom": ["London", "Manchester", "Liverpool"],
}


@autocomplete_example.autocomplete()
def autocomplete_handler(ctx, country=None, city=None):
    if country.focused:
        return [c for c in COUNTRIES if c.lower().startswith(country.value.lower())]
    elif city.focused:
        if country.value in CITIES:
            return CITIES[country.value]
        else:
            return []


@app.command()
def more_autocomplete(ctx, value: Autocomplete[int]):
    return f"Your number is **{value}**."


@more_autocomplete.autocomplete()
def more_autocomplete_handler(ctx, value=None):
    # Note that even though this option is an int,
    # the autocomplete handler still gets passed a str.
    try:
        value = int(value.value)
    except ValueError:
        return []

    return [i for i in range(value, value + 10)]


if __name__ == "__main__":
    app.update_commands(guild_id=os.environ["TESTING_GUILD"])
