import asyncio
import threading
from asyncio.base_events import Server as AsyncioServer
from socket import socket as Socket
from ssl import SSLContext
from typing import Any, Callable, Dict, List, Optional, cast

from aiohttp import web

EventCallback = Callable[[Dict[str, Any]], None]


class Server:
    """A handle to a running server."""

    def __init__(
        self,
        handle_event: EventCallback,
        host: str,
        port: int,
        ssl_context: Optional[SSLContext] = None,
    ):
        """Initialize a Server."""
        self.host = host
        self.port = port
        self.handle_event = handle_event
        self.ssl_context = ssl_context
        self._main_loop = asyncio.get_event_loop()

    @property
    def url(self) -> str:
        scheme = "http" if self.ssl_context is None else "https"
        return f"{scheme}://{self.host}:{self.port}"

    def start(self) -> None:
        """Start a new server running in a background thread."""
        app = web.Application()
        app.add_routes([web.post("/", self._handle_request)])
        self._runner = web.AppRunner(app)

        self._startup_event = threading.Event()
        self._server_loop = asyncio.new_event_loop()
        t = threading.Thread(target=self._run)
        t.start()

        # Wait for server to startup
        self._startup_event.wait()

    def stop(self) -> None:
        """Gracefully stop a running server."""
        # Call the server shutdown functions and wait for them to finish. These
        # must be called on the server thread's event loop.
        future = asyncio.run_coroutine_threadsafe(self._stop(), self._server_loop)
        future.result(5)

        # Stop the server thread's event loop
        self._server_loop.call_soon_threadsafe(self._server_loop.stop)

    async def _handle_request(self, request: web.Request) -> web.Response:
        """Handle an incoming request."""
        event = await request.json()
        # This handler will be called on the server thread. Call the external
        # handler on the app thread.
        self._main_loop.call_soon_threadsafe(self.handle_event, event)
        return web.Response(text="OK")

    def _run(self) -> None:
        """Execute the server in its own thread with its own event loop."""
        asyncio.set_event_loop(self._server_loop)
        self._server_loop.run_until_complete(self._runner.setup())

        site = web.TCPSite(
            self._runner, self.host, self.port, ssl_context=self.ssl_context
        )
        self._server_loop.run_until_complete(site.start())

        # If the Server was initialized with port 0, determine what port the
        # underlying server ended up listening on
        if self.port == 0:
            site_server = cast(AsyncioServer, site._server)
            sockets = cast(List[Socket], site_server.sockets)
            socket = sockets[0]
            self.port = socket.getsockname()[1]

        self._startup_event.set()
        self._server_loop.run_forever()

    async def _stop(self) -> None:
        """Stop the server."""
        await self._runner.shutdown()
        await self._runner.cleanup()


def create_server(
    handle_event: EventCallback,
    host: str = "0.0.0.0",
    port: int = 0,
    ssl_context: Optional[SSLContext] = None,
) -> Server:
    """Create a new server."""
    return Server(handle_event, host, port, ssl_context)
