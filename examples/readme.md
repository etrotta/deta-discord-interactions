## Important Notes
- Most examples define only blueprints and would not work on their own. See the `main.py` example for actually running the bot, and `update_commands.py` for updating it
- Not all examples have been fully tested - Please open an Issue if anything does not seems to work

## Remember to do the following before running your bot:
- Set the environment variables on the Spacefile (`DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `DISCORD_PUBLIC_KEY`).
    - Either set default values (only if you do not want to release your bot publicly) or set them on the app configs
- If you are using any scheduled actions, register those as well
- Set the URL to receive interactions on https://discord.com/developers to `https://example.deta.app/discord`
- If it requries OAuth and/or Webhooks
    - add the `https://example.deta.dev/oauth` redirect URL on the OAuth
    - use `enable_oauth` from the oauth utils

- You must call `app.update_commands()` to update the commands.
    - I recommend running it locally, but if you really want to run it from the app, just set the `from_inside_a_micro` keyword argument to True


## Known issues
- No good way to defer nor follow up (any spawned threads are killed as soon as the main function returns)
- The Deta Space changes made it a quite few times more complicated to setup than Cloud used to be
- Not particularly beginner friendly
- Poorly documented

## As far as security goes
The `http.server` module of the standard library that `deta_discord_interactions.http` relies on is not recommended for production usage. Use it at your own risk.
Any server that supports [PEP 3333](https://peps.python.org/pep-3333/) and works in serverless environments should work, so you may want to use something like https://gunicorn.org/ instead of `deta_discord_interactions.http`
