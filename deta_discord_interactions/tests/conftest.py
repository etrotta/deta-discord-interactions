import os
os.environ["DISCORD_CLIENT_ID"] = "123"
os.environ["DISCORD_PUBLIC_KEY"] = "123"
os.environ["DISCORD_CLIENT_SECRET"] = "123"

os.environ["DONT_REGISTER_WITH_DISCORD"] = "True"
os.environ["DONT_VALIDATE_SIGNATURE"] = "True"

os.environ["DETA_ORM_DATABASE_MODE"] = "MEMORY"
os.environ["DETA_ORM_FORMAT_NICELY"] = "1"

os.environ["DETA_PROJECT_KEY"] = ""

import pytest

from deta_discord_interactions import DiscordInteractions, Client
from deta_discord_interactions.utils.oauth import enable_oauth

@pytest.fixture(scope="module")
def discord():
    return DiscordInteractions()


@pytest.fixture(scope="module")
def oauth_discord():
    app = DiscordInteractions()
    enable_oauth(app)
    return app


@pytest.fixture(scope="module")
def client(discord):
    return Client(discord)

@pytest.fixture(scope="module")
def oauth_client(oauth_discord):
    return Client(oauth_discord)


@pytest.fixture(autouse=True)
def no_http_requests(monkeypatch):
    def urlopen_mock(self, method, url, *args, **kwargs):
        raise RuntimeError(
            f"The test was about to {method} {self.scheme}://{self.host}{url}"
        )

    monkeypatch.setattr(
        "urllib3.connectionpool.HTTPConnectionPool.urlopen", urlopen_mock
    )