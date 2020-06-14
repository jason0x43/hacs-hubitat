import sys

if sys.version_info[:2] < (3, 8):
    from asynctest.mock import (
        Mock,
        NonCallableMock,
        CoroutineMock as AsyncMock,
        call,
        patch,
    )
else:
    from unittest.mock import Mock, NonCallableMock, call, patch

__all__ = ["Mock", "AsyncMock", "NonCallableMock", "call", "patch"]
