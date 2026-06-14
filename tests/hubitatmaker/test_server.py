from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.hubitat.hubitatmaker.server import Server, create_server


@pytest.mark.asyncio
async def test_server_url_and_factory() -> None:
    callback = Mock()
    server = create_server(callback, "127.0.0.1", 1234)
    assert server.url == "http://127.0.0.1:1234"

    server.ssl_context = Mock()
    assert server.url == "https://127.0.0.1:1234"


@pytest.mark.asyncio
async def test_handle_request_and_stop() -> None:
    callback = Mock()
    server = Server(callback, "127.0.0.1", 1234)
    server._main_loop = Mock()
    request = Mock()
    request.json = AsyncMock(return_value={"name": "event"})

    response = await server._handle_request(request)
    assert response.text == "OK"
    server._main_loop.call_soon_threadsafe.assert_called_once_with(
        callback, {"name": "event"}
    )

    server._runner = Mock(shutdown=AsyncMock(), cleanup=AsyncMock())
    await server._stop()
    server._runner.shutdown.assert_awaited_once()
    server._runner.cleanup.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_and_stop_delegate_to_thread_and_loop() -> None:
    server = Server(Mock(), "127.0.0.1", 1234)
    startup_event = Mock()
    with (
        patch(
            "custom_components.hubitat.hubitatmaker.server.threading.Thread"
        ) as thread,
        patch(
            "custom_components.hubitat.hubitatmaker.server.threading.Event",
            return_value=startup_event,
        ),
    ):
        server.start()
    thread.return_value.start.assert_called_once()
    startup_event.wait.assert_called_once()
    assert server._runner is not None

    server._server_loop = Mock()
    future = Mock()
    stop_result = Mock()
    with (
        patch.object(server, "_stop", new=Mock(return_value=stop_result)),
        patch(
            "custom_components.hubitat.hubitatmaker.server.asyncio.run_coroutine_threadsafe",
            return_value=future,
        ) as run_coroutine,
    ):
        server.stop()
    run_coroutine.assert_called_once_with(stop_result, server._server_loop)
    future.result.assert_called_once_with(5)
    server._server_loop.call_soon_threadsafe.assert_called_once()
