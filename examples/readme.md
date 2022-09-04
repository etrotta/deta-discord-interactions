Remember to do the following before running your bot:
- Update with Micro's environment variables (DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DISCORD_PUBLIC_KEY).
    For that, I recommend copying a .env file, removing the "comments" and using `deta update -e .env`

- Set the URL to receive interactions on https://discord.com/developers to `https://example.deta.dev/discord`
- If it requries OAuth and/or Webhooks, add the `https://example.deta.dev/oauth` redirect URL on the OAuth

- Before or after using `deta deploy`, you also have to run the `main.py` file directly to update the commands if you made any changes to the commands or their parameters
You also have to update your own environment variables for that, such as by using [python-dotenv](https://pypi.org/project/python-dotenv/). Preferably before importing anything from deta_discord_interactions.


Some extra quirks from deta:
- Your main file **must** be called `main.py`
- Your bot **must** be called `app`

Known issues
- No good way to defer nor follow up (any spawned threads are killed as soon as the main function returns)