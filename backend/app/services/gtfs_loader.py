import logging
import os
import shutil
import urllib.parse
import zipfile
from pathlib import Path

import pandas as pd
import requests
from app.core.config import ALLOWED_FILES
from app.db.session import DatabaseManager
from app.services.gtfs_static import GTFSParser
from sqlalchemy import text

logger = logging.getLogger("cyprus_bus_tracker.gtfs_loader")


class DatabaseReset:
    def __init__(self, db_manager: DatabaseManager, gtfs_parent_folder: str):
        self.db_manager = db_manager
        self.gtfs_parent_folder = gtfs_parent_folder
        # SQL files live at backend/sql/ (two levels up from services/ → app/ → backend/)
        self._sql_dir = Path(__file__).resolve().parents[2] / "sql"

    async def reset_and_insert(self, gtfs_folder: str) -> None:
        logger.info("Inserting GTFS data for folder %s", gtfs_folder)
        async for session in self.db_manager.get_session():
            parser = GTFSParser(session, gtfs_folder)
            await parser.parse_and_insert()
        logger.info("GTFS data for %s inserted", gtfs_folder)

    async def reset_and_insert_all(self) -> None:
        async with self.db_manager.engine.begin() as conn:
            drop_path = self._sql_dir / "drop_tables.sql"
            logger.info("Dropping all tables")
            with open(drop_path, encoding="utf-8") as f:
                for stmt in [s.strip() for s in f.read().split(";") if s.strip()]:
                    await conn.execute(text(stmt))

            create_path = self._sql_dir / "create_tables.sql"
            logger.info("Recreating tables")
            with open(create_path, encoding="utf-8") as f:
                for stmt in [s.strip() for s in f.read().split(";") if s.strip()]:
                    await conn.execute(text(stmt))

        gtfs_folders = [
            os.path.join(self.gtfs_parent_folder, folder)
            for folder in os.listdir(self.gtfs_parent_folder)
        ]
        for gtfs_folder in gtfs_folders:
            await self.reset_and_insert(gtfs_folder)


class BaseOperations:
    def __init__(self, source_folder: str):
        self.source_folder = source_folder

    def clear_folder(self, folder_path: str) -> None:
        os.makedirs(folder_path, exist_ok=True)
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
        logger.info("Cleared folder: %s", folder_path)

    def unzip_files(self, folder: str) -> None:
        for item in os.listdir(folder):
            if item.endswith(".zip"):
                zip_path = os.path.join(folder, item)
                extract_path = os.path.join(folder, os.path.splitext(item)[0])
                logger.info("Unzipping %s to %s", zip_path, extract_path)
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(extract_path)


class GraphBuild(BaseOperations):
    def __init__(self, source_folder: str, target_folder: str, osm_folder: str, otp_jar: str):
        super().__init__(source_folder)
        self.target_folder = target_folder
        self.osm_folder = osm_folder
        self.otp_jar = otp_jar

    def copy_osm_data(self) -> None:
        for file_name in os.listdir(self.osm_folder):
            src = os.path.join(self.osm_folder, file_name)
            dst = os.path.join(self.target_folder, file_name)
            shutil.copy2(src, dst)
            logger.info("Copied %s to %s", file_name, self.target_folder)

    def delete_zip_files(self) -> None:
        os.makedirs(self.target_folder, exist_ok=True)
        for item in os.listdir(self.source_folder):
            if item.endswith(".zip"):
                path = os.path.join(self.source_folder, item)
                os.remove(path)
                logger.info("Deleted %s", path)

    def create_merged_gtfs_in_target_folder(self) -> None:
        os.makedirs(self.target_folder, exist_ok=True)
        temp_folder = os.path.join(self.target_folder, "temp")
        os.makedirs(temp_folder, exist_ok=True)

        feed_dirs = [
            os.path.join(self.source_folder, d)
            for d in os.listdir(self.source_folder)
            if os.path.isdir(os.path.join(self.source_folder, d))
        ]

        for filename in ALLOWED_FILES:
            merged = []
            for feed_dir in feed_dirs:
                file_path = os.path.join(feed_dir, filename)
                if os.path.exists(file_path):
                    try:
                        merged.append(pd.read_csv(file_path, dtype=str))
                    except Exception as exc:
                        logger.error("Error reading %s: %s", file_path, exc)
            if merged:
                combined = pd.concat(merged, ignore_index=True).drop_duplicates()
                out_path = os.path.join(temp_folder, filename)
                combined.to_csv(out_path, index=False)
                logger.info("Merged %s: %d rows", filename, len(combined))
            else:
                logger.warning("No %s found in any feed directory", filename)

        output_zip = os.path.join(self.target_folder, "merged_gtfs.zip")
        with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for file in os.listdir(temp_folder):
                zf.write(os.path.join(temp_folder, file), arcname=file)
        logger.info("Created merged GTFS zip: %s", output_zip)

    def build_graph(self) -> None:
        self.clear_folder(self.target_folder)
        self.delete_zip_files()
        self.create_merged_gtfs_in_target_folder()
        self.copy_osm_data()
        import subprocess

        cmd = f"java -Xmx2G -jar {self.otp_jar} --build {self.target_folder} --save"
        logger.info("Running OTP build: %s", cmd)
        subprocess.check_call(cmd, shell=True)


class Updater(BaseOperations):
    def __init__(
        self,
        source_folder: str,
        target_folder: str,
        osm_folder: str,
        otp_jar: str,
        zip_urls: list[str],
    ):
        super().__init__(source_folder)
        self.zip_urls = zip_urls
        self.graph_builder = GraphBuild(source_folder, target_folder, osm_folder, otp_jar)

    def download_files(self) -> None:
        for url in self.zip_urls:
            parsed = urllib.parse.urlparse(url)
            params = urllib.parse.parse_qs(parsed.query)
            file_name = params["file"][0].split("\\")[-1]
            filename = os.path.join(self.source_folder, file_name)
            logger.info("Downloading %s", url)
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            with open(filename, "wb") as f:
                f.write(response.content)

    def prepare_data(self) -> None:
        """Download + unzip + build merged GTFS zip without running OTP graph build."""
        self.clear_folder(self.source_folder)
        self.download_files()
        self.unzip_files(self.source_folder)
        self.graph_builder.delete_zip_files()
        self.graph_builder.create_merged_gtfs_in_target_folder()
        self.graph_builder.copy_osm_data()
        logger.info("GTFS data prepared (OTP graph build skipped)")

    def run_all(self) -> None:
        self.clear_folder(self.source_folder)
        self.download_files()
        self.unzip_files(self.source_folder)
        self.graph_builder.build_graph()
        logger.info("All GTFS data updated and graph built")


class GTFSDataReloader:
    def __init__(
        self,
        db_manager: DatabaseManager,
        gtfs_source_folder: str,
        gtfs_target_folder: str,
        gtfs_osm_folder: str,
        otp_jar: str,
        zip_urls: list[str],
        manage_otp: bool = True,
    ):
        self.manage_otp = manage_otp
        self.updater = Updater(
            source_folder=gtfs_source_folder,
            target_folder=gtfs_target_folder,
            osm_folder=gtfs_osm_folder,
            otp_jar=otp_jar,
            zip_urls=zip_urls,
        )
        self.db_reset = DatabaseReset(db_manager, gtfs_source_folder)

    def update_data_files(self) -> None:
        logger.info("Starting GTFS file update")
        if self.manage_otp:
            self.updater.run_all()
        else:
            self.updater.prepare_data()

    async def reload_database(self) -> None:
        logger.info("Starting database reset and insertion")
        await self.db_reset.reset_and_insert_all()

    async def run_all(self) -> None:
        self.update_data_files()
        await self.reload_database()
