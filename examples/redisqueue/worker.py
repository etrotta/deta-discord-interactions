import sys

from redis import Redis
from rq import Worker

sys.path.insert(1, ".")

import deta_discord_interactions

worker = Worker(["default"], connection=Redis())
worker.work()
