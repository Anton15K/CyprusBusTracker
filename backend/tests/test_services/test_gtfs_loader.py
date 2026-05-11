from unittest.mock import AsyncMock, MagicMock, mock_open

import pytest
from app.services.gtfs_loader import BaseOperations, DatabaseReset, GraphBuild, Updater


@pytest.mark.asyncio
async def test_database_reset_and_insert(mocker):
    mock_db = MagicMock()
    mock_session = AsyncMock()

    # Mock the async generator get_session
    async def mock_get_session():
        yield mock_session

    mock_db.get_session = mock_get_session

    mock_parser = MagicMock()
    mock_parser.parse_and_insert = AsyncMock()
    mocker.patch("app.services.gtfs_loader.GTFSParser", return_value=mock_parser)

    dr = DatabaseReset(mock_db, "/tmp/gtfs")
    await dr.reset_and_insert("feed1")

    mock_parser.parse_and_insert.assert_called_once()


@pytest.mark.asyncio
async def test_reset_and_insert_all(mocker):
    mock_db = MagicMock()
    mock_conn = AsyncMock()
    # Mock engine.begin() context manager
    mock_db.engine.begin.return_value.__aenter__.return_value = mock_conn

    mocker.patch("os.listdir", return_value=["feed1"])
    mocker.patch("os.path.isdir", return_value=True)
    mocker.patch("builtins.open", mock_open(read_data="DROP TABLE test; CREATE TABLE test;"))

    dr = DatabaseReset(mock_db, "/tmp/gtfs")
    mocker.patch.object(dr, "reset_and_insert", new_callable=AsyncMock)

    await dr.reset_and_insert_all()
    assert mock_conn.execute.call_count >= 2
    dr.reset_and_insert.assert_called_once()


def test_base_operations_clear_folder(mocker):
    mocker.patch("os.makedirs")
    mocker.patch("os.listdir", return_value=["file1", "dir1"])
    mocker.patch("os.path.isdir", side_effect=[False, True])
    mock_rm = mocker.patch("shutil.rmtree")
    mock_remove = mocker.patch("os.remove")

    bo = BaseOperations("/tmp/src")
    bo.clear_folder("/tmp/target")
    mock_rm.assert_called_once()
    mock_remove.assert_called_once()


def test_graph_build_copy_osm(mocker):
    mocker.patch("os.listdir", return_value=["map.osm"])
    mock_copy = mocker.patch("shutil.copy2")

    gb = GraphBuild("/tmp/src", "/tmp/target", "/tmp/osm", "otp.jar")
    gb.copy_osm_data()
    mock_copy.assert_called_once()


def test_graph_build_create_merged_gtfs(mocker):
    mocker.patch("os.makedirs")
    mocker.patch("os.listdir", side_effect=[["feed1"], ["stops.txt"]])
    mocker.patch("os.path.isdir", return_value=True)
    mocker.patch("os.path.exists", return_value=True)

    mock_df = MagicMock()
    mocker.patch("pandas.read_csv", return_value=mock_df)
    mocker.patch("pandas.concat", return_value=mock_df)
    mock_df.drop_duplicates.return_value = mock_df

    mock_zip = MagicMock()
    mocker.patch("zipfile.ZipFile", return_value=mock_zip)
    mock_zip.__enter__.return_value = mock_zip

    gb = GraphBuild("/tmp/src", "/tmp/target", "/tmp/osm", "otp.jar")
    gb.create_merged_gtfs_in_target_folder()

    mock_df.to_csv.assert_called()
    mock_zip.write.assert_called()


def test_updater_download_files(mocker):
    mock_get = mocker.patch("requests.get")
    mock_get.return_value.content = b"data"
    mocker.patch("builtins.open", mock_open())

    updater = Updater(
        "/tmp/src", "/tmp/target", "/tmp/osm", "otp.jar", ["http://test.com?file=gtfs.zip"]
    )
    updater.download_files()
    mock_get.assert_called_once()
