# Warning: Most examples are not up to date!

## Remember to do the following before running your bot:
- Set the environment variables on the Spacefile (`DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `DISCORD_PUBLIC_KEY`).
- If you are using any scheduled actions, register those as well
- Set the URL to receive interactions on https://discord.com/developers to `https://example.deta.app/discord`
- If it requries OAuth and/or Webhooks, add the `https://example.deta.dev/oauth` redirect URL on the OAuth

- You must call `app.update_commands()` to update the commands.
    - I recommend running it locally, but if you really want to run it from the app, just set the `from_inside_a_micro` keyword argument to True


## Known issues
- No good way to defer nor follow up (any spawned threads are killed as soon as the main function returns)
- The Deta Space changes made it a quite few times more complicated to setup than Cloud used to be
- Poorly documented