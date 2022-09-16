# Deta-Discord-Interactions

This is a small web framework that lets you write Discord Application Commands using a decorator syntax similar to Flask's `@app.route()` or Discord.py's `@bot.command()`, specialized for usage in https://deta.sh

It is a fork of [flask-discord-interactions](https://pypi.org/project/Flask-Discord-Interactions/), but without requiring Flask and with some added features to make the usage of the library simpler.

```
@app.command()
def ping(ctx):
    "Respond with a friendly 'pong'!"
    return "Pong!"
```

The documentation of the original library is available on [readthedocs](https://flask-discord-interactions.readthedocs.io/).
The documentation of the Fork is still Work in Progress.