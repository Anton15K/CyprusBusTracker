from unittest.mock import AsyncMock, MagicMock

import pytest
from app.main import lifespan
from fastapi import FastAPI


@pytest.mark.asyncio
async def test_lifespan(mocker):
    # Mock services used in lifespan
    mock_db = MagicMock()
    mock_db.init = AsyncMock()
    mock_session = AsyncMock()
    mock_session_context = MagicMock()
    mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_context.__aexit__ = AsyncMock(return_value=None)
    mock_db.session_factory = MagicMock(return_value=mock_session_context)
    mock_db.engine.dispose = AsyncMock()
    mocker.patch("app.main.db_manager", mock_db)

    mock_reloader = MagicMock()
    mock_reloader.run_all = AsyncMock()
    mocker.patch("app.main.GTFSDataReloader", return_value=mock_reloader)

    mocker.patch("app.main.get_all_stops", new_callable=AsyncMock)
    mocker.patch("subprocess.Popen")

    app = FastAPI()

    # Simulate lifespan
    async with lifespan(app):
        # Verify init calls
        mock_reloader.run_all.assert_called_once()
        assert hasattr(app.state, "all_stops")

    # Verify cleanup
    mock_db.engine.dispose.assert_called_once()
