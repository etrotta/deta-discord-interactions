"""
- Remember to set the environment variables
- Run the script locally to update commands before deploying
"""
try:  # Only for syncing the commands - you should use `deta update -e` for the Micro environment variables
    from dotenv import load_dotenv
    load_dotenv('.env')
except ImportError:
    pass


import os
from deta_discord_interactions import DiscordInteractions
from deta_discord_interactions.utils.oauth import enable_oauth

app = DiscordInteractions()
enable_oauth(app)

@app.command("hello")
def hello_world(ctx):
    return f"Hello world!"


from database import blueprint as database_example_blueprint
from webhooks import blueprint as webhooks_example_blueprint
from tasks import blueprint as tasks_example_blueprint

app.register_blueprint(database_example_blueprint)
app.register_blueprint(webhooks_example_blueprint)
app.register_blueprint(tasks_example_blueprint)

if __name__ == "__main__":
    print("Updating commands")
    app.update_commands(guild_id=os.getenv("GUILD_ID"))
