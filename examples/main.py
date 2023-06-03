from deta_discord_interactions import DiscordInteractions
from deta_discord_interactions.http import run_server

from ping import bp as ping_bp

app = DiscordInteractions()

app.register_blueprint(ping_bp)

if __name__ == "__main__":
    # WARNING: While this server should be safe for usage in Deta Space because there is an intermediate step
    # between the request reaching their servers and the request your app actually receives,
    # It does NOT implements HTTPS on it's own
    # You may want to use a more production ready WSGI-compliant server such as gunicorn
    run_server(app)

# you would have to run `update_commands.py` manually