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


    logger.info(" Refreshing Dropbox access token...")
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
        logger.error(f" Failed to refresh token: {response.status_code} - {response.text}")
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
        logger.error(f" Error listing folder {remote_path}: {e}")
        return file_paths


    for entry in result.entries:
        entry_path = "/" + os.path.join(remote_path, entry.name).replace("\\", "/").lstrip("/")

        if isinstance(entry, FileMetadata):
            file_paths.append({
                'path': entry_path,
                'client_modified': entry.client_modified.astimezone(IST)
            })
        elif isinstance(entry, FolderMetadata):
            file_paths += list_file_paths(shared_link_url, entry_path)

    return sorted(file_paths, key=lambda x: x['path'])        

def filter_today_files(file_entries):
    today = datetime.now(IST).date()
    return [f for f in file_entries if f['client_modified'].date() == today]



def download_file(shared_link_url, dropbox_path, local_path):
    refresh_if_needed()
    ensure_dir(os.path.dirname(local_path))
    try:
        metadata, response = dbx.sharing_get_shared_link_file(url=shared_link_url, path=dropbox_path)
        with open(local_path, 'wb') as f:
            f.write(response.content)
        logger.info(f"✅ Downloaded: {dropbox_path}")
    except Exception as e:
        logger.error(f" Error downloading {dropbox_path}: {e}")


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
    logger.info(f" Zipped to {zip_path}")




def wait_for_deletion(filepath):
    logger.info(f"⏳ Waiting for deletion of: {filepath}")
    while os.path.exists(filepath):
        # this process should 10 minute
        time.sleep(2)
    logger.info(f"🗑️ File deleted: {filepath}")




def copy_files_one_by_one(source_dir, dest_dir):
    """
    Copy each file from source_dir to dest_dir. Wait until the file is deleted before copying the next.
    """
    files = sorted(os.listdir(source_dir))
    logger.info(f"📋 Preparing to copy {len(files)} files one-by-one...")


    for filename in files:
        src_file = os.path.join(source_dir, filename)
        dest_file = os.path.join(dest_dir, filename)


        if os.path.isfile(src_file):
            logger.info(f"📤 Copying: {filename}")
            shutil.copy2(src_file, dest_file)
            logger.info(f" Waiting for deletion of copied file: {filename}")
            
            # time.sleep(8) #waiting waiting
            
            # try:
            #     os.remove(dest_file)
            #     logger.info(f"deleted:{filename}")
            # except Exception as e:
            #     logger.error(f" Failed to delete {filename}: {e}")
                
            
        
            wait_for_deletion(dest_file)     #this is static right now




if __name__ == '__main__':
    try:
        TARGET_DIR = os.path.join(os.path.expanduser("~"), "Documents")
        ensure_dir(TARGET_DIR)

        DOWNLOAD_TODAY_ONLY = True
        LIST_ONLY = False 

        downloaded_paths = set()
        refresh_access_token()

        logger.info(" Scanning for today's files...")
        all_files = list_file_paths(SHARED_LINK_URL)

        today = datetime.now(IST).date()
        today_files = [f for f in all_files if f['client_modified'].date() == today]

        if not today_files:
            logger.info("📭 No files modified today found.")
        else:
            logger.info(f"📋 Found {len(today_files)} file(s) modified today:")
            for f in today_files:
                logger.info(f"📝 {f['path']} (modified: {f['client_modified']})")

        if LIST_ONLY:
            logger.info("📄 LIST_ONLY flag is enabled. Exiting after listing.")
            exit(0)

        previous_files = all_files
        logger.info(" Starting monitoring loop...")

        while True:
            now = datetime.now(IST)
            if now >= END_TIME:
                logger.warning("⏰ Run duration expired. Exiting.")
                break

            current_files = list_file_paths(SHARED_LINK_URL)
            today = datetime.now(IST).date()
            today_files = [f for f in current_files if f['client_modified'].date() == today]

            new_today_files = [f for f in today_files if f['path'] not in downloaded_paths]

            if new_today_files:
                logger.info(f" {len(new_today_files)} new file(s) found with today’s timestamp.")
                # logger.info("⏳ Waiting 10 seconds for uploads to settle...")
                # time.sleep(10)

                current_files_after_delay = list_file_paths(SHARED_LINK_URL)
                today_files_after_delay = [
                    f for f in current_files_after_delay
                    if f['client_modified'].date() == today and f['path'] not in downloaded_paths
                ]

                if today_files_after_delay:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    local_folder = f"{LOCAL_BASE_DIR}_{timestamp}"
                    ensure_dir(local_folder)

                    for file_entry in today_files_after_delay:
                        dropbox_path = file_entry['path']
                        local_path = os.path.join(local_folder, dropbox_path.lstrip("/"))
                        download_file(SHARED_LINK_URL, dropbox_path, local_path)
                        downloaded_paths.add(dropbox_path)

                    zip_path = f"{local_folder}.zip"
                    zip_folder(local_folder, zip_path)
                    copy_files_one_by_one(local_folder, TARGET_DIR)

                    logger.info(" New files processed. Monitoring continues...")
                    exit(0)
                else:
                    logger.info(" No new stable files found after waiting.")
            else:
                logger.info("⏳ No new today-timestamped files detected, checking again...")

            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        logger.info(" User interrupted. Exiting.")



















"""ADDING SAME CODE WITH CLASS BASED"""

# import os
# import time
# import logging
# import shutil
# import zipfile
# import dropbox
# from dropbox.files import SharedLink, FileMetadata, FolderMetadata
# from datetime import datetime, timedelta
# import pytz
# import requests
# import sys
# import smtplib
# from email.message import EmailMessage
# from dotenv import load_dotenv


# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC


# load_dotenv()

# class DropboxMonitor:                                                                               
#     def __init__(self, app_key, app_secret, refresh_token, shared_link_url, target_dir, duration_minutes=180, check_interval=1):
#         self.app_key = app_key
#         self.app_secret = app_secret
#         self.refresh_token = refresh_token
#         self.shared_link_url = shared_link_url
#         self.target_dir = target_dir
#         self.check_interval = check_interval
#         self.downloaded_paths = set()

#         self.ist = pytz.timezone('Asia/Kolkata')
#         self.start_time = datetime.now(self.ist)
#         self.end_time = self.start_time + timedelta(minutes=duration_minutes)

#         self.access_token = None
#         self.token_expiry = 0
#         self.dbx = None

#         self.logger = logging.getLogger(self.__class__.__name__)
#         logging.basicConfig(level=logging.INFO)

#         self.refresh_access_token()

#     def refresh_access_token(self):
#         self.logger.info("🔄 Refreshing Dropbox access token...")
#         token_url = 'https://api.dropbox.com/oauth2/token'
#         data = {
#             'grant_type': 'refresh_token',
#             'refresh_token': self.refresh_token,
#             'client_id': self.app_key,
#             'client_secret': self.app_secret,
#         }
#         response = requests.post(token_url, data=data)

#         if response.status_code != 200:
#             self.logger.error(f"❌ Failed to refresh token: {response.status_code} - {response.text}")
#             response.raise_for_status()

#         token_data = response.json()
#         self.access_token = token_data['access_token']
#         self.token_expiry = time.time() + (4 * 60 * 60 ) - 10  #this ius token expirary time that is 4 hours
#         self.dbx = dropbox.Dropbox(self.access_token)
#         self.logger.info("✅ Access token refreshed.")

#     def refresh_if_needed(self):
#         if time.time() > self.token_expiry:
#             self.refresh_access_token()

#     def ensure_dir(self, path):
#         os.makedirs(path, exist_ok=True)

# #this is used to send message to particular user if task has found eror
#     def send_email_alert(self,subject,body,to_email=None):
#         to_email = to_email or os.getenv("EMAIL_TO")
#         msg=EmailMessage()
#         msg['Subject'] =subject
#         msg['From'] = os.getenv("EMAIL_FROM")
#         msg['To']=to_email
#         msg.set_content(body)

#         try:
#             with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
#                 smtp.starttls()
#                 smtp.login(os.getenv("EMAIL_FROM"), os.getenv("EMAIL_PASSWORD"))
#                 smtp.send_message(msg)
#                 self.logger.info(f"📧 Alert email sent to {to_email}")


#         except Exception as e:
#              self.logger.error(f"❌ Failed to send email: {e}")


#     def list_file_paths(self, remote_path=''):
#         self.refresh_if_needed()
#         file_paths = []

#         try:
#             result = self.dbx.files_list_folder(path=remote_path, shared_link=SharedLink(url=self.shared_link_url))
#         except Exception as e:
#             self.logger.error(f"❌ Error listing folder {remote_path}: {e}")
#             return file_paths

#         for entry in result.entries:
#             entry_path = "/" + os.path.join(remote_path, entry.name).replace("\\", "/").lstrip("/")

#             if isinstance(entry, FileMetadata):
#                 file_paths.append({
#                     'path': entry_path,
#                     'client_modified': entry.client_modified.astimezone(self.ist)
#                 })
#             elif isinstance(entry, FolderMetadata):
#                 file_paths += self.list_file_paths(entry_path)

#         return sorted(file_paths, key=lambda x: x['path'])

#     def download_file(self, dropbox_path, local_path):
#         """
#         this will downlaod fill first using shared link if it fails it will use public raw link
#         """
#         self.refresh_if_needed()
#         self.ensure_dir(os.path.dirname(local_path))
#         try:
#             _, response = self.dbx.sharing_get_shared_link_file(url=self.shared_link_url, path=dropbox_path)
#             with open(local_path, 'wb') as f:
#                 f.write(response.content)
#             self.logger.info(f"✅ Downloaded: {dropbox_path}")
#         except Exception as e:
#             self.logger.error(f"XX Error downloading {dropbox_path}: {e}")

#             self.logger.warning("TRYING VIA PUBLIC LINK")
            
#             try:
#                 dl_url = self.shared_link_url.replace("?dl=0", "?dl=1")
#                 r = requests.get(dl_url)
#                 r.raise_for_status()
#                 with open(local_path, "wb") as f:
#                     f.write(r.content)
#                 self.logger.info(f"Downloaded via public raw link: {dropbox_path}")
#             except Exception as e:
#                 self.logger.error(f"❌ Final fallback failed for {dropbox_path}: {e}")


#     def zip_folder(self, source_dir, zip_path):
#         with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
#             for root, _, files in os.walk(source_dir):
#                 for file in files:
#                     filepath = os.path.join(root, file)
#                     arcname = os.path.relpath(filepath, source_dir)
#                     zipf.write(filepath, arcname)
#         self.logger.info(f"📦 Zipped to {zip_path}")


#     def wait_for_deletion(self, filepath):
#         self.logger.info(f"⏳ Waiting for deletion of: {filepath}")
#         max_wait_second= 5*60  #t set to 5min
#         start_time=time.time()

#         while os.path.exists(filepath):
#             if time.time()- start_time> max_wait_second:
#                 self.logger.warning(f"⏰ File not deleted after 5 minutes: {filepath}")

#                 self.send_email_alert(
#                 subject="XX File Not Deleted",
#                 body=f"The file {filepath} was not deleted after 5 minutes."    
#                 )
#                 sys.exit(1) 
#             time.sleep(5) 
#         self.logger.info(f"🗑️ File deleted: {filepath}")

#     def copy_files_one_by_one(self, source_dir):
#         files = sorted(os.listdir(source_dir))
#         self.logger.info(f" Preparing to copy {len(files)} files one-by-one...")

#         for filename in files:
#             src_file = os.path.join(source_dir, filename)
#             dest_file = os.path.join(self.target_dir, filename)

#             if os.path.isfile(src_file):
#                 self.logger.info(f"📤 Copying: {filename}")
#                 shutil.copy2(src_file, dest_file)
#                 self.logger.info(f"📂 Waiting for deletion of copied file: {filename}")
#                 self.wait_for_deletion(dest_file)

    

#     def run_selenium_download(self):
#         EMAIL = os.getenv("EMAIL")
#         PASSWORD = os.getenv("PASSWORD")
#         URL = os.getenv("URL")


#         driver = webdriver.Chrome()
#         wait = WebDriverWait(driver, 20)

#         try:
#             driver.get(URL)
#             wait.until(EC.visibility_of_element_located((By.NAME, "email"))).send_keys(EMAIL)
#             driver.find_element(By.NAME, "password").send_keys(PASSWORD)

#             sign_in = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Sign in']]")))
#             sign_in.click()
#             self.logger.info("✅ Logged into Homebase.")

#             # Navigate to Timesheets --> Pay Period Review
#             wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Timesheets"))).click()
#             wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='timesheets-tab-nav-pay_period_review']"))).click()
#             self.logger.info("🧭 Navigated to Timesheets > Pay Period Review.")

#             # Select 'Yesterday' date range
#             wait.until(EC.element_to_be_clickable((By.NAME, "DateRangeInput"))).click()
#             wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'Preset') and text()='Yesterday']"))).click()
#             wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Apply']]"))).click()
#             self.logger.info("📅 Selected 'Yesterday' date range.")

#             # Trigger CSV Download
#             wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(), 'Download')]]"))).click()
#             wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(), 'Customize')]]"))).click()
#             time.sleep(3)  # Wait for the download options to load
#             wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='/timesheets/download.csv']"))).click()
#             self.logger.info("📥 CSV download initiated.")

#             # Close the modal
#             wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="ModalCloseIcon"]'))).click()
#             self.logger.info("✅ Modal closed.")

#         except Exception as e:
#             self.logger.error(f"XX Selenium automation failed: {e}")
#             self.send_email_alert("XX Selenium Automation Failed", str(e))
#         finally:
#             driver.quit()

    

#     def monitor(self):
#         """Main monitoring loop for downloading and processing files."""

#         self.ensure_dir(self.target_dir)
#         self.logger.info("📂 Scanning for today's files...")
#         all_files = self.list_file_paths()
#         today = datetime.now(self.ist).date()

#         today_files = [f for f in all_files if f['client_modified'].date() == today]

#         self.logger.info(f"📋 Found {len(today_files)} file(s) modified today:")
#         for f in today_files:
#             self.logger.info(f"📝 {f['path']} (modified: {f['client_modified']}) [TODAY]")

#         self.logger.info(" Start monitoring...")

#         while datetime.now(self.ist) < self.end_time:
#             current_files = self.list_file_paths()
#             # Filter files modified today
#             today_files = [f for f in current_files if f['client_modified'].date() == today]
#             total_today_files = len(today_files)

#             self.logger.info(f"⏳ Currently found {total_today_files} file(s) modified today.")


#             if total_today_files == 3:               
#                 new_today_files = [f for f in today_files if f['path'] not in self.downloaded_paths]

#                 if new_today_files:
#                     self.logger.info("📥 Exactly 3 files detected for today. Running Selenium download first...")

#                     # self.run_selenium_download()

#                     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#                     local_folder = f"{'downloaded_dropbox'}_{timestamp}"
#                     self.ensure_dir(local_folder)

#                     for file_entry in new_today_files:
#                         dropbox_path = file_entry['path']
#                         local_path = os.path.join(local_folder, dropbox_path.lstrip("/"))
#                         self.download_file(dropbox_path, local_path)
#                         self.downloaded_paths.add(dropbox_path)

#                     zip_path = f"{local_folder}.zip"
#                     self.zip_folder(local_folder, zip_path)
#                     self.copy_files_one_by_one(local_folder)

#                     self.logger.info("✅ 3 files processed. Monitoring ends.")
#                     break
#                 else:
#                     self.logger.info("⏳ All 3 files have already been downloaded. Monitoring ends.")
#                     break
#             else:
#                 self.logger.info(f"⏳ Waiting for total 3 files modified today. Checking again in {self.check_interval} minute")
#                 time.sleep(self.check_interval*60)

#                 #debug
#                 now = datetime.now(self.ist)
#                 self.logger.info(f"⏰ Current Time: {now}, End Time: {self.end_time}")

#                 if now >= self.end_time:
#                     self.send_email_alert(
#                         subject="X File Requirement Not Met",
#                         body="In the last 3 hours, 3 new Dropbox files were not detected. Please check if the required files were uploaded."
#                     )
#                     break


# if __name__ == '__main__':

#     monitor = DropboxMonitor(
#         app_key=os.getenv('APP_KEY'),
#         app_secret=os.getenv('APP_SECRET'),
#         refresh_token=os.getenv('REFRESH_TOKEN'),
#         shared_link_url=os.getenv('SHARED_LINK_URL'),
#         target_dir=os.path.join(os.path.expanduser("~"), "Documents"),
#         duration_minutes=180,
#         check_interval=1
#     )
#     monitor.monitor()
