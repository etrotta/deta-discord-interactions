"""
- Remember to set the environment variables and (if you want to use cron) scheduled action in the Spacefile
- Run the script locally to update commands before deploying
"""
try:  # Only for syncing the commands - you should use the Spacefile for the Micro environment variables
    from dotenv import load_dotenv
    load_dotenv('.env')
except ImportError:
    pass


import os
from deta_discord_interactions import DiscordInteractions
from deta_discord_interactions.utils.oauth import enable_oauth

from deta_discord_interactions.http import run_server

app = DiscordInteractions()
enable_oauth(app)

@app.command("hello")
def hello_world(ctx):
    return f"Hello world!"


from database import blueprint as database_example_blueprint
from cron import blueprint as scheduled_actions_example_blueprint

app.register_blueprint(database_example_blueprint)
app.register_blueprint(scheduled_actions_example_blueprint)

# You can use whichever method you want to decide whenever to run the server or update the server
# this is just one not-so-good example
if os.getenv("DETA_SPACE_APP"):
    run_server(app)
else:
    print("Updating commands")
    app.update_commands(guild_id=os.getenv("GUILD_ID"))
