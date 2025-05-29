import os
import time
import zipfile
import shutil
import pytz
import logging
import dropbox
from datetime import datetime,timedelta
# import json
from dropbox.files import FileMetadata, FolderMetadata, SharedLink

# === CONFIG ===
ACCESS_TOKEN = 'sl.u.AFzychJe218Q1ONGZmIFCvOH1_0_BRAE3pyZVx0DE-B5ZHX-X4a22s64XU064NriTr5CSpN14yC-F8aVV_sZBU95Ex8dPrcsmWM4k4y4utCtL60WgyjD-6UUa4yQPUAEr16btSCspc_v1_MQXfjh2rFV-nu4WstqRf62d3alW6ajR4d05DaBCAWk8Uyec8Z29Hzmaz7rJhstH5HPPNrJYuoKByG_qHJHbY2QK2SOUEFH9585MrADhjQVFTZ0X1Cd3rwinTkiLbE1RT-OvytADXV13qAfXTizD5rx3IyGGXKV4-hNzOINJMkXyyOZtyvY1EW6KEVqnWsZmvFoHK1p1zMXn0VDmg0lrtBcy0Bu7vusXDkUCX0Wn5PML7XGEMDAJKZ820KW3s8He5TnxzA0vx2aK5aYxK4ouJhGb1Orpi0pFEqj-8QwGDNekDMON0DORynCiykbzjf2mywH8D84mCPsyf9Dn2LlnvWZsWatFtTxea4-FkOxRKwwuXoxRVNTgesTn84FLmpxRUYUmjQeBXf-MsjwapQlu14fTpBhmchvaCjWIbiYa1RMXraDRTdpfGgnviwnhry5XN6EBUm5mIVSo1ugxO_ZxbYdkQg8WJAIxfCIDxS4oO63kFjpbzWLp6QWds5f8nNIkcMwDtOY8XUFj8ItlJ0qJdloJyLrPY9Q3QARm4LldGScduKXRjCXRFO8LeK4cYH-K_3Hl7nV3K1-nXT9SQD63zOqT6FbQNMDM837rV0c8VMpTAmMBrCX8503gW2ctcxEdj5nTRbMAmOlBH8ZrlLI0QSNo0bkfbM6xYaiFr3-yKDDU_30A3Rt1RTvuOyFOUmalZcuHBcQ3fwjHk8jXwJnBUxsF3QC-o1JKoF-uX0B9JwEE4KYKrrBKGWmyaT3o9YBYu2NW3CB3eL73Um3dFkx_iRgzWkm07-_PPayVXagHz6qnJ9Dq5REaHhtgjRDrTdx4klAvG5GsXkcr1CiD7CuB3i3dGHOEAHoBYzT8FxJYe9NsFnxioShbcEyLs2Xv5tMFeqGfozj2sDHNygRBHSrr-nFo5xDl2XTHaK6iRzZHnOLRkyxTtSP2MTUWZaToQC4QI_RF4eZ8JzE4_yF6aPFXoXqnNlFMgbnRPBkBmhbp-mR33ceA3d1oxoCD_qxgixUF5NL208MywKxdwm2K9eM185r_kNISw4dVrMWlYLNoD8K65o9rmg48qnU3iGUs-fzyJQNBSZd_MvEFm6d-ZXTnW6LE4sH29_TA0ACgO2w_mbYtt2KV3M_14HWsJcmiUE0L-vB6COKtCA5ftOh9ymbJ_5z57JEtOAPvNI938R2K2NFU0mOauVSuHZ9bdJpA2bbrSecYDNsUuGvvQVHQkxVj4LYmR82WCJUL2DGQM8QAJW2TAfaPbAKzk-XH1y1xmVbBdpDpBriFGYj'
SHARED_LINK_URL = 'https://www.dropbox.com/scl/fo/pabt32xxzlddnt2zv5ubb/AIqGQDnm7GnF7e-WCEb_rPo?rlkey=nxebp23z122xd7bmmc4qgpqqs&st=c1xtjfu1&dl=0'
LOCAL_BASE_DIR = 'downloaded_dropbox'
CHECK_INTERVAL = 1  # seconds


# with open('config.json', 'r') as f:
#     config = json.load(f)

# access_token = config['ACCESS_TOKEN']
# shared_link_url = config['SHARED_LINK_URL']
# local_base_dir = config['LOCAL_BASE_DIR']
# check_interval = config['CHECK_INTERVAL']


# === Setup ===
# IST = pytz.timezone('Asia/Kolkata')
# END_TIME = datetime.now(IST).replace(hour=17, minute=30, second=0, microsecond=0)

IST = pytz.timezone('Asia/Kolkata')
START_TIME = datetime.now(IST)
RUN_DURATION = timedelta(minutes=2)
END_TIME = START_TIME + RUN_DURATION




logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

dbx = dropbox.Dropbox(ACCESS_TOKEN)


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def list_file_paths(shared_link_url, remote_path=''):
    # Recursively list all file paths from shared folder using supported method.
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
            # Recurse into folders
            file_paths += list_file_paths(shared_link_url, entry_path)

    return sorted(file_paths)


def download_file(shared_link_url, dropbox_path, local_path):
    ensure_dir(os.path.dirname(local_path))
    try:
        metadata, response = dbx.sharing_get_shared_link_file(url=shared_link_url, path=dropbox_path)
        with open(local_path, 'wb') as f:
            f.write(response.content)
        logger.info(f"✅ Downloaded: {dropbox_path}")
    except Exception as e:
        logger.error(f"❌ Error downloading {dropbox_path}: {e}")


def list_and_download(shared_link_url, remote_path='', local_dir=''):
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


# === MAIN LOOP ===
if __name__ == '__main__':

    try:
        previous_files = list_file_paths(SHARED_LINK_URL)
        logger.info(f"📂 Initial file count: {len(previous_files)}")

        while True:
            now = datetime.now(IST)
            if now >= END_TIME:
                logger.warning("⏰ 3 hours passed since start. Exiting.")
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

                # Update previous_files to the current list so you don't download the same files again
                previous_files = current_files            
                logger.info("✅ Downloaded, zipped new files. Continuing to monitor...")
                break
            else:
                logger.info("⏳ No new files detected, checking again...")

            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        logger.info("User interrupted. Exiting.")

