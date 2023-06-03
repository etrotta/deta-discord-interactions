import os
from main import app

app.update_commands(os.getenv('TESTING_GUILD'))
