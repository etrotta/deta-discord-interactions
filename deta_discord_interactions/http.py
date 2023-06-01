"""Minimal HTTP to WSGI adapter.
WARNING: Appropriated only for local testing and deta space.
Does not supports HTTPS on it's own, amongst other security negligences"""

import functools
import os
from io import BytesIO
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Callable, NoReturn, Optional

class RequestHandler(BaseHTTPRequestHandler):
    def __init__(self, app: Callable, log_requests: bool, should_flush: bool, *args, **kwargs):
        self.app = app
        self.__should_log_requests = log_requests
        self.__should_flush = should_flush
        super().__init__(*args, **kwargs)

    def send_request_to_app(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        query = self.path.rsplit('?', 1)[-1] if '?' in self.path else ''
        headers = {f"HTTP_{header}".upper().replace("-", "_"): value for header, value in self.headers.items()}
        environ = {
            "wsgi.input": BytesIO(body),
            "CONTENT_LENGTH": str(len(body)),
            "PATH_INFO": self.path,
            "REMOTE_ADDR": "127.0.0.1",
            'QUERY_STRING': query,
            **headers,
        }
        def _start_response(code: str, headers: list[tuple[str, str]]):
            code_number, code_reason = code.split(' ', 1)
            code_number = int(code_number)
            self.send_response(code_number, code_reason)
            for header in headers:
                self.send_header(*header)
        try:
            output = self.app(environ, _start_response)
            self.end_headers()
            for out in output:
                self.wfile.write(out)
        finally:
            if self.__should_flush:
                import sys
                sys.stdout.flush()
                sys.stderr.flush()

    def do_GET(self):
        return self.send_request_to_app()

    def do_POST(self):
        return self.send_request_to_app()

    def log_request(self, *args, **kwargs):
        if self.__should_log_requests:
            return super().log_request(*args, **kwargs)

def get_server(app: Callable, port: Optional[int] = None, log_requests: bool = False, should_flush: bool = True):
    """Prepares a HTTP Server that calls the app for each request.
    
    Parameters:
    -----------
    app : WSGI compliant callable
        In other words, a `DiscordInteractions` instance.
    port : int, optional
        Which port to serve the app in. Leave it blank to fill in from the environment.
        If not passed and missing from the environment, defaults to 8080.
    log_requests : bool, default False
        If set to False, supresses the http.server default messages that log every request.
        In other words, set it to True if you want to log every request and command.
    should_flush : bool, default True
        If set to True, flushes the sys.stdout and sys.stderr after each request.
        In other words, leave it as True to fix common logging problems.
    """
    if port is None:
        port = int(os.getenv("PORT", "8080"))
    server_address = ('', port)
    handler = functools.partial(RequestHandler, app, log_requests, should_flush)
    server = HTTPServer(server_address, handler)
    return server

def run_server(app: Callable, port: Optional[int] = None, log_requests: bool = False, should_flush: bool = True) -> NoReturn:
    """Starts a HTTP Server that calls the app for each request.

    Parameters:
    -----------
    app : WSGI compliant callable
        In other words, a `DiscordInteractions` instance.
    port : int, optional
        Which port to serve the app in. Leave it blank to fill in from the environment.
        If not passed and missing from the environment, defaults to 8080.
    log_requests : bool, default False
        If set to False, supresses the http.server default messages that log every request.
        In other words, True = log every request and command.
    should_flush : bool, default True
        If set to True, flushes the sys.stdout and sys.stderr after each request.
        In other words, True fixes common logging problems.
    """
    server = get_server(app, port=port, log_requests=log_requests, should_flush=should_flush)
    server.serve_forever()
