from typing import Any

from aiohttp import ClientResponse


class ConnectionError(Exception):
    """Error when hub isn't responding."""


class InvalidToken(Exception):
    """Error for invalid access token."""


class InvalidConfig(Exception):
    """Error indicating invalid hub config data."""


class InvalidMode(Exception):
    """Error indicating that a mode is invalid."""

    def __init__(self, mode: str, **kwargs):
        super().__init__(f"Invalid mode '{mode}'")


class RequestError(Exception):
    """An error indicating that a request failed."""

    def __init__(self, resp: ClientResponse, **kwargs):
        # Pyright doesn't like the @reify used on ClientResponse.url
        any_resp: Any = resp
        super().__init__(
            f"{resp.method} {any_resp.url} - [{resp.status}] {resp.reason}"
        )
