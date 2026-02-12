import os
import asyncio
from models import Base
from GTFS_Parsing import GTFSParser
from db_manager import DatabaseManager
from db_manager import db_manager as Manager
import shutil
import requests
import zipfile
import urllib.parse
import subprocess
import pandas as pd
from constants import ZIP_URLS, SOURCE, TARGET, ALLOWED_FILES, OSM_FOLDER
from pathlib import Path
from sqlalchemy import text

class DatabaseReset:
    def __init__(self, db_manager: DatabaseManager, gtfs_parent_folder: str):
        self.db_manager = db_manager
        self.gtfs_parent_folder = gtfs_parent_folder

    async def reset_and_insert(self, gtfs_folder: str):
        # Insert new data from GTFSParser
        print(f"Inserting GTFS data for folder {gtfs_folder}...")
        async for session in self.db_manager.get_session():
            parser = GTFSParser(session, gtfs_folder)
            await parser.parse_and_insert()
            print(f"GTFS data for {gtfs_folder} inserted successfully!")

    async def reset_and_insert_all(self):
        async with self.db_manager.engine.begin() as conn:
            sql_dir = Path(__file__).parent

            print(f"Dropping all tables for folder {self.gtfs_parent_folder}...")
            drop_path = os.path.join(sql_dir, 'drop_tables.sql')
            with open(drop_path, 'r', encoding='utf-8') as f:
                raw_sql = f.read()
                statements = [stmt.strip() for stmt in raw_sql.split(';') if stmt.strip()]
                for stmt in statements:
                    await conn.execute(text(stmt))
            print("Recreating tables...")
            create_path = os.path.join(sql_dir, 'create_tables.sql')
            with open(create_path, 'r', encoding='utf-8') as f:
                raw_sql = f.read()
                statements = [stmt.strip() for stmt in raw_sql.split(';') if stmt.strip()]
                for stmt in statements:
                    await conn.execute(text(stmt))
            
        gtfs_folders = [os.path.join(self.gtfs_parent_folder, folder) for folder in os.listdir(self.gtfs_parent_folder)]
        for gtfs_folder in gtfs_folders:
            await self.reset_and_insert(gtfs_folder)

class BaseOperations:
    def __init__(self, folder=SOURCE):
        self.source_folder = folder

    def clear_folder(self, folder_path):
        #clears the folder and creates it again
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
        os.makedirs(folder_path)
        print(f"Cleared and recreated folder: {folder_path}")

    def unzip_files(self, folder):
        # unzips all .zip files in the specified folder
        for item in os.listdir(folder):
            if item.endswith(".zip"):
                zip_path = os.path.join(folder, item)

                # Folder name = filename without .zip
                folder_name = os.path.splitext(item)[0]
                extract_path = os.path.join(folder, folder_name)

                print(f"Unzipping {zip_path} to {extract_path}...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
                print(f"Unzipped to {extract_path}")

    def run_command(self, command):
        # runs command using command line
        try:
            print(f"Running command: {command}")
            subprocess.check_call(command, shell=True)
        except subprocess.CalledProcessError as e:
            print(f"Command failed with error: {e}")
            raise
            
        print("Command completed successfully.")
    


class GraphBuild(BaseOperations):
    def __init__(self, target_folder=TARGET, osm_folder=OSM_FOLDER):
        """
        source_folder: The folder where GTFS .zip files are originally downloaded.
        target_folder: The folder where we want to move the .zip files and then build the graph.
        """
        super().__init__()
        self.osm_folder = osm_folder
        self.target_folder = target_folder

    def copy_osm_data(self):
        """
        Copies any files from the osm_folder to the target_folder.
        """

        for file_name in os.listdir(self.osm_folder):
            source_path = os.path.join(self.osm_folder, file_name)
            destination_path = os.path.join(self.target_folder, file_name)
            shutil.copy2(source_path, destination_path)
            print(f"Copied {file_name} from {self.osm_folder} to {self.target_folder}")

    def delete_zip_files(self):
        """
        Deletes all .zip files in the source folder.
        """

        # Ensure the target folder exists
        if not os.path.exists(self.target_folder):
            os.makedirs(self.target_folder)
            print(f"Created target folder: {self.target_folder}")
            
        for item in os.listdir(self.source_folder):
            if item.endswith(".zip"):
                source_zip_path = os.path.join(self.source_folder, item)
                os.remove(source_zip_path)
                print(f"Deleted original zip: {source_zip_path}")
    def create_merged_gtfs_in_target_folder(self):
        #Prepare GTFS data for OpenTripPlanner (OTP) by merging GTFS files from multiple agencies into a single GTFS bundle.
        if not os.path.exists(self.target_folder):
            os.makedirs(self.target_folder)

        # Temporary folder to write merged text files
        temp_folder = os.path.join(self.target_folder, 'temp')
        if not os.path.exists(temp_folder):
            os.makedirs(temp_folder)

        # Find all extracted GTFS feed directories
        feed_dirs = [
            os.path.join(self.source_folder, d)
            for d in os.listdir(self.source_folder)
            if os.path.isdir(os.path.join(self.source_folder, d))
        ]

        # Merge each allowed file
        for filename in ALLOWED_FILES:
            merged = []
            for feed_dir in feed_dirs:
                file_path = os.path.join(feed_dir, filename)
                if os.path.exists(file_path):
                    try:
                        df = pd.read_csv(file_path, dtype=str)
                        merged.append(df)
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")
            if merged:
                merged = pd.concat(merged, ignore_index=True)
                merged = merged.drop_duplicates()
                out_path = os.path.join(temp_folder, filename)
                merged.to_csv(out_path, index=False)
                print(f"Merged {filename}: {len(merged)} rows written to {out_path}")
            else:
                print(f"No {filename} found in any feed directory.")


        # Zip the merged GTFS bundle
        output_zip_path = os.path.join(self.target_folder, 'merged_gtfs.zip')
        with zipfile.ZipFile(output_zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for file in os.listdir(temp_folder):
                file_path = os.path.join(temp_folder, file)
                zf.write(file_path, arcname=file)
                print(f"Added to zip: {file}")
        print(f"Successfully created merged GTFS zip: {output_zip_path}")

    
    def build_graph(self):
        """
        Clears the target folder, prepares the GTFS data for OTP,
        and then runs the OTP build command.
        """
        self.clear_folder(self.target_folder)
        self.delete_zip_files()
        self.create_merged_gtfs_in_target_folder()
        self.copy_osm_data()
        command = f"java -Xmx2G -jar otp-shaded-2.7.0.jar --build {self.target_folder} --save"
        self.run_command(command)

class Updater(BaseOperations):
    def __init__(self, zip_urls=ZIP_URLS):
        """
        folder: The source folder where GTFS .zip files are downloaded.
        zip_urls: A list of URLs from which to download the .zip files.
        """
        super().__init__(folder=SOURCE)
        self.zip_urls = zip_urls if zip_urls is not None else []
        self.graph_builder = GraphBuild(target_folder=TARGET)

    def download_files(self):
        for url in self.zip_urls:
            parsed_url = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            file_name = query_params['file'][0].split("\\")[-1]
            filename = os.path.join(self.source_folder, file_name)

            print(f"Downloading {url}...")
            response = requests.get(url)
            response.raise_for_status()
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"Saved to {filename}")

    def run_all(self):
        # Download files into the source folder.
        self.clear_folder(self.source_folder)
        self.download_files()
        self.unzip_files(self.source_folder)
        print("GTFS files downloaded.")
        self.graph_builder.build_graph()
        print("All GTFS data updated and graph built.")

class GTFSDataReloader:
    def __init__(self, db_manager: DatabaseManager, gtfs_folder: str, zip_urls: list[str]):
        self.gtfs_folder = gtfs_folder
        self.updater = Updater(zip_urls=zip_urls)
        self.db_reset = DatabaseReset(db_manager, gtfs_folder)

    def update_data_files(self):
        print("Starting GTFS file update...")
        self.updater.run_all()
        print("GTFS files updated.")

    async def reload_database(self):
        print("Starting database reset and insertion...")
        await self.db_reset.reset_and_insert_all()
        print("Database update complete.")

    async def run_all(self):
        # self.update_data_files()
        await self.reload_database()

# Usage example
async def main():
    Reloader = GTFSDataReloader(db_manager=Manager, gtfs_folder=SOURCE, zip_urls=ZIP_URLS)
    await Reloader.run_all()


if __name__ == "__main__":
    
    asyncio.get_event_loop().run_until_complete(main())