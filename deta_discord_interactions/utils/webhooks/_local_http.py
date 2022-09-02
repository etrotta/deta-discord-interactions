"Fake server available for testing, used if DONT_REGISTER_WITH_DISCORD is set."
# In the future: Perhaps get rid of this and use pytest fixtures instead?

from functools import partial
from itertools import zip_longest
import os
import base64
import uuid
import json
from urllib.parse import unquote
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading


class Bind:
    def __init__(self, keyword_arg):
        self.keyword_arg = keyword_arg

class Routes:
    def __init__(self) -> None:
        self.routes = []

    def __getitem__(self, key):
        path = key.split("/")
        for route, function in self.routes:
            kwargs = {}
            for (in_segment, stored_segment) in zip_longest(path, route):
                if isinstance(stored_segment, Bind):
                    kwargs[stored_segment.keyword_arg] = in_segment
                elif stored_segment != in_segment:
                    break
            else:
                return partial(function, **kwargs)

    def __setitem__(self, key, value):
        path = key.split("/")
        for i, segment in enumerate(path):
            if segment.startswith("{") and segment.endswith("}"):
                path[i] = Bind(segment[1:-1])
        self.routes.append((path, value))


functions = {}
def register(path, method):
    def decorator(function):
        functions.setdefault(method, Routes())[path] = function
        return function
    return decorator


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path, *query = self.path.split("?", 1)
        if query:
            query = query[0]
            query = {k: v for k, v in (attr.split("=", 1) for attr in query.split("&"))}
        else:
            query = None

        function = functions['GET'][path]
        code, reason, headers, body = function(self.headers, query)

        self.send_response(code, reason)

        if isinstance(body, dict):
            body = json.dumps(body).encode("UTF-8")
        for (name, value) in headers.items():
            self.send_header(name, value)

        if "Content-Type" not in headers:
            self.send_header("Content-Type", "application/json")
        if "Content-Length" not in headers:
            self.send_header("Content-Length", len(body))

        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.headers['Content-Type'] == "application/json":
            contents = self.rfile.read(int(self.headers['Content-Length']))
            contents = json.loads(contents.decode('UTF-8'))
        elif self.headers['Content-Type'] == "application/x-www-form-urlencoded":
            contents = self.rfile.read(int(self.headers['Content-Length']))
            contents = unquote(contents.decode('UTF-8'))
            contents = {k: v for k, v in (frag.split("=") for frag in contents.split("&"))}
        else:
            raise ValueError(f"Content type {self.headers['Content-Type']} not supported by the fake server")

        path, *query = self.path.split("?", 1)
        if query:
            query = query[0]
            query = {k: v for k, v in (attr.split("=", 1) for attr in query.split("&"))}
        else:
            query = None

        function = functions['POST'][path]
        code, reason, headers, body = function(self.headers, query, contents)

        self.send_response(code, reason)

        if isinstance(body, dict):
            body = json.dumps(body).encode("UTF-8")
        for (name, value) in headers.items():
            self.send_header(name, value)

        if ("Content-Type" not in headers) and body:
            self.send_header("Content-Type", "application/json")
        if ("Content-Length" not in headers):
            if body:
                self.send_header("Content-Length", len(body))
            else:
                self.send_header("Content-Length", 0)

        self.end_headers()
        if body:
            self.wfile.write(body)


is_running = threading.Event()

def _run(port: int):
    # print("\n---Starting fake discord server---\n")
    server_address = ('', port)
    httpd = HTTPServer(server_address, Handler)
    httpd.serve_forever()

def run_local_server(port: int = 8000):
    """Starts a local server that mimics how Discord handles webhooks.
    If it was already started before, do nothing"""
    if os.getenv("DETA_RUNTIME", None) is not None:
        raise Exception("Cannot use local server on deta.")
    if is_running.is_set():
        return
    is_running.set()

    thread = threading.Thread(target=_run, daemon=True, args=(port,))
    thread.start()
    return thread

    # thread = threading.Thread(target=_run, args=(port,))
    # thread.start()
    # thread.join()

    # _run(port)

pending_webhooks = {}
webhooks = {}


@register("/oauth2/authorize", "GET")
def create_webhook(headers, query):
    "Page the user visits to create a Webhook"
    assert query['response_type'] == 'code'
    assert query['scope'] == 'webhook.incoming'
    assert query['client_id'] == os.getenv('DISCORD_CLIENT_ID')
    state = query.get("state")
    redirect_uri = query.get("redirect_uri")
    # I know that uuid4s may not be the best to represent it, but it is good enough 
    webhook_id = str(uuid.uuid4()).replace("-", "")
    webhook_token = str(uuid.uuid4()).replace("-", "")
    webhook_code = str(uuid.uuid4()).replace("-", "")
    pending_webhooks[webhook_code] = {
        '_redirect_uri': redirect_uri,
        'access_token': str(uuid.uuid4()).replace("-", ""),
        'expires_in': 604800, 
        'refresh_token': str(uuid.uuid4()).replace("-", ""),
        'scope': 'applications.commands.permissions.update applications.commands.update',
        'token_type': 'Bearer',
        'webhook': {
            'type': 1,
            'id': webhook_id,
            'name': 'Test Bot',
            'avatar': '4e7bab503c575740fb2f5f9b79a04d87',
            'channel_id': '123123123',
            'guild_id': '123123123',
            'application_id': os.getenv("DISCORD_CLIENT_ID"),
            'token': webhook_token,
            'url': f'https://discord.com/api/webhooks/{webhook_id}/{webhook_token}'
        }
    }

    return (
        200,
        'OK',
        {},
        {
            "result": "Created mock webhook internally",
            # Still requires for you to POST that code to /oauth/token
            "redirect_uri": redirect_uri,
            "code": webhook_code,
            "state": state,
            "guild_id": '123123123',
        }
    )

@register("/oauth2/token", "POST")
def confirm_webhook(headers, query, payload):
    "Route the Bot POSTs to after the user is redirected to the Micro"

    if "Authorization" in headers and headers["Authorization"].startswith("Basic "):
        header_auth = base64.b64decode(headers["Authorization"].removeprefix("Basic "))
        header_client_id, header_client_secret = header_auth.split(":")
        client_id = header_client_id
        client_secret = header_client_secret
    else:
        client_id = payload.get("client_id")
        client_secret = payload.get("client_secret")

    assert client_id == os.getenv("DISCORD_CLIENT_ID")
    assert client_secret == os.getenv("DISCORD_CLIENT_SECRET")
    assert payload.get("grant_type") == "authorization_code"
    redirect_uri = payload.get("redirect_uri")
    webhook_code = payload.get("code")
    if webhook_code not in pending_webhooks:
        raise ValueError("Mock Webhook Code not in pending webhooks!")
    webhook = pending_webhooks.pop(webhook_code)
    assert webhook.pop('_redirect_uri') ==  redirect_uri
    return (
        200,
        'OK',
        {},
        webhook,
    )
    


@register("/api/webhooks/{id}/{token}", "POST")
def post_webhook_message(headers, query, payload, *, id, token):
    "Route that receives incoming webhook Messages"
    print("--- WEBHOOK RECEIVED MESSAGE START ---")
    print(payload)
    print("--- END WEBHOOK RECEIVED MESSAGE ---")
    wait = query.get("wait", "false") != "false"
    payload['id'] = str(uuid.uuid4).replace("-", "")
    msgs = webhooks.setdefault((id, token), {}).setdefault("messages", {})
    msgs[payload["id"]] = payload

    return (
        200 if wait else 204,
        'OK',
        {},
        payload if wait else b'',
    )

@register("/api/webhooks/{id}/{token}/messages/{message_id}", "GET")
def get_webhook_message(headers, query, payload, *, id, token, message_id):
    "Route to get previously sent webhook messages"
    try:
        msg = webhooks[(id, token)]["messages"][message_id]
    except KeyError:
        msg = None

    return (
        200 if msg else 400,
        'OK' if msg else 'ERROR',
        {},
        msg or {"result": "webhook or message not found"},
    )






if __name__ == "__main__":
    import requests
    t = run_local_server()

    CLIENT_ID = "123123123"
    CLIENT_SECRET = "ABC123XYZ"
    os.environ["DISCORD_CLIENT_ID"] = CLIENT_ID
    os.environ["DISCORD_CLIENT_SECRET"] = CLIENT_SECRET

    internal_id = 'test_webhook'
    redirect_uri = 'https://example.deta.dev/oauth'

    user_link = (
        # "https://discord.com/oauth2/authorize?"
        "http://localhost:8000/oauth2/authorize?"
        "response_type=code&"
        "scope=webhook.incoming&"
        f"client_id={os.getenv('DISCORD_CLIENT_ID')}&"
        f"state={internal_id}&"
        f"redirect_uri={redirect_uri}"
    )
    response = requests.get(user_link)
    on_user_redirect = (
        "http://localhost:8000/oauth2/token"
    )
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': response.json()["code"],
        'redirect_uri': redirect_uri
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    API_ENDPOINT = "http://localhost:8000"
    r = requests.post('%s/oauth2/token' % API_ENDPOINT, data=data, headers=headers)
    print(r.json())
    # response = requests.get("http://localhost:8000")
    # print(response)
    # print(response.json())
    # t.join()
