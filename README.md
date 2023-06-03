# Deta-Discord-Interactions

This is a small web framework that lets you write Discord Application Commands using a decorator syntax similar to Flask's `@app.route()` or Discord.py's `@bot.command()`, specialized for usage in https://deta.space

It is a fork of [flask-discord-interactions](https://pypi.org/project/Flask-Discord-Interactions/), but without requiring Flask and with some added features to make the usage of the library better on deta.

```
@app.command()
def ping(ctx):
    "Respond with a friendly 'pong'!"
    return "Pong!"
```

The documentation of the original library is available on [readthedocs](https://flask-discord-interactions.readthedocs.io/).
The documentation of the Fork is still Work in Progress.



## Known issues
- No good way to defer nor follow up (any spawned threads are killed as soon as the main function returns)
- The Deta Space changes made it a quite few times more complicated to setup than Cloud used to be
- Not particularly beginner friendly
- Poorly documented

## As far as security goes
The `http.server` module of the standard library that `deta_discord_interactions.http` relies on is not recommended for production usage. Use it at your own risk.
Any server that supports [PEP 3333](https://peps.python.org/pep-3333/) and works in serverless environments should work, so you may want to use something like https://gunicorn.org/ instead of the `deta_discord_interactions.http` used in Examples.
