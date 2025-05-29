import os
import time
import logging
import shutil
import zipfile
import dropbox
from dropbox.files import SharedLink
from dropbox.files import FileMetadata, FolderMetadata
from datetime import datetime, timedelta
import pytz
import requests
from dropbox.files import ListFolderArg




# === CONFIG ===
LOCAL_BASE_DIR = 'downloaded_dropbox'
CHECK_INTERVAL = 1  # seconds

APP_KEY = ''
APP_SECRET = ''

# From your JSON token info (save these after initial OAuth flow)
REFRESH_TOKEN = ""
SHARED_LINK_URL = ''

# Timezone and run duration
IST = pytz.timezone('Asia/Kolkata')
START_TIME = datetime.now(IST)
RUN_DURATION = timedelta(minutes=5)
END_TIME = START_TIME + RUN_DURATION

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Global variables to hold token state
access_token = None
token_expiry = 0
dbx = None


def refresh_access_token():
    global access_token, token_expiry, dbx

    logger.info("🔄 Refreshing Dropbox access token...")
    token_url = 'https://api.dropbox.com/oauth2/token'
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': REFRESH_TOKEN,
        'client_id': APP_KEY,
        'client_secret': APP_SECRET,
    }
    response = requests.post(token_url,headers=headers, data=data)

    if response.status_code != 200:
        logger.error(f"❌ Failed to refresh token: {response.status_code} - {response.text}")
        response.raise_for_status()

    token_data = response.json()

    access_token = token_data['access_token']

    # expires_in = token_data.get('expires_in', 14400)  
    # token_expiry = time.time() + expires_in - 60  # refresh 1 minute early
    fixed_expires_in = 60  # 2 minutes
    token_expiry = time.time() + fixed_expires_in - 10 

    dbx = dropbox.Dropbox(access_token)
    logger.info(f"✅ Access token refreshed, expires in {fixed_expires_in} seconds.")
    logger.info(f"{access_token}")


def refresh_if_needed():
    global token_expiry
    if time.time() > token_expiry:
        refresh_access_token()


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def list_file_paths(shared_link_url, remote_path=''):
    refresh_if_needed()
    file_paths = []

    try:
        result = dbx.files_list_folder(path=remote_path, shared_link=SharedLink(url=shared_link_url))
    except Exception as e:
        logger.error(f"❌ Error listing folder {remote_path}: {e}")
        return file_paths

    for entry in result.entries:
        entry_path = "/" + os.path.join(remote_path, entry.name).replace("\\", "/").lstrip("/")

        if isinstance(entry, FileMetadata):
            file_paths.append(entry_path)

        elif isinstance(entry, FolderMetadata):
            file_paths += list_file_paths(shared_link_url, entry_path)

    return sorted(file_paths)


def download_file(shared_link_url, dropbox_path, local_path):
    refresh_if_needed()
    ensure_dir(os.path.dirname(local_path))
    try:
        metadata, response = dbx.sharing_get_shared_link_file(url=shared_link_url, path=dropbox_path)
        with open(local_path, 'wb') as f:
            f.write(response.content)
        logger.info(f"✅ Downloaded: {dropbox_path}")
    except Exception as e:
        logger.error(f"❌ Error downloading {dropbox_path}: {e}")


def list_and_download(shared_link_url, remote_path='', local_dir=''):
    refresh_if_needed()
    try:
        result = dbx.files_list_folder(path=remote_path, shared_link=SharedLink(url=shared_link_url))
    except Exception as e:
        logger.error(f"Failed to list folder: {remote_path}: {e}")
        return

    for entry in result.entries:
        name = entry.name
        if not name:
            continue

        entry_path = "/" + os.path.join(remote_path, name).replace("\\", "/").lstrip("/")
        local_path = os.path.join(local_dir, entry_path.lstrip("/"))

        if isinstance(entry, FileMetadata):
            download_file(shared_link_url, entry_path, local_path)
        elif isinstance(entry, FolderMetadata):
            ensure_dir(local_path)
            list_and_download(shared_link_url, entry_path, local_dir)


def zip_folder(source_dir, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, source_dir)
                zipf.write(filepath, arcname)
    logger.info(f"📦 Zipped to {zip_path}")


if __name__ == '__main__':
    try:
        refresh_access_token()
        previous_files = list_file_paths(SHARED_LINK_URL)
        logger.info(f"📂 Initial file count: {len(previous_files)}")

        while True:
            now = datetime.now(IST)
            if now >= END_TIME:
                logger.warning("⏰ Run duration expired. Exiting.")
                break

            current_files = list_file_paths(SHARED_LINK_URL)

            if current_files != previous_files:
                logger.info("📥 New files or folders detected!")

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                local_folder = f"{LOCAL_BASE_DIR}_{timestamp}"
                ensure_dir(local_folder)

                list_and_download(SHARED_LINK_URL, '', local_folder)

                zip_path = f"{local_folder}.zip"
                zip_folder(local_folder, zip_path)

                shutil.rmtree(local_folder)
                logger.info(f"🧹 Deleted unzipped folder: {local_folder}")

                previous_files = current_files
                logger.info("✅ Downloaded, zipped new files. Continuing to monitor...")
                break
            else:
                logger.info("⏳ No new files detected, checking again...")

            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        logger.info("User interrupted. Exiting.")
