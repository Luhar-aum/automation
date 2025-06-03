import os
import time
import logging
import shutil
import zipfile
import dropbox
from dropbox.files import SharedLink, FileMetadata, FolderMetadata
from datetime import datetime, timedelta
import pytz
import requests
import sys
import smtplib
from email.message import EmailMessage

class DropboxMonitor:                                                                                   #180
    def __init__(self, app_key, app_secret, refresh_token, shared_link_url, target_dir, duration_minutes=2, check_interval=1):
        self.app_key = app_key
        self.app_secret = app_secret
        self.refresh_token = refresh_token
        self.shared_link_url = shared_link_url
        self.target_dir = target_dir
        self.check_interval = check_interval
        self.downloaded_paths = set()

        self.ist = pytz.timezone('Asia/Kolkata')
        self.start_time = datetime.now(self.ist)
        self.end_time = self.start_time + timedelta(minutes=duration_minutes)

        self.access_token = None
        self.token_expiry = 0
        self.dbx = None

        self.logger = logging.getLogger(self.__class__.__name__)
        logging.basicConfig(level=logging.INFO)

        self.refresh_access_token()

    def refresh_access_token(self):
        self.logger.info("🔄 Refreshing Dropbox access token...")
        token_url = 'https://api.dropbox.com/oauth2/token'
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': self.app_key,
            'client_secret': self.app_secret,
        }
        response = requests.post(token_url, data=data)

        if response.status_code != 200:
            self.logger.error(f"❌ Failed to refresh token: {response.status_code} - {response.text}")
            response.raise_for_status()

        token_data = response.json()
        self.access_token = token_data['access_token']
        self.token_expiry = time.time() + (4 * 60 * 60 ) - 10  #this ius token expirary time that is 4 hours
        self.dbx = dropbox.Dropbox(self.access_token)
        self.logger.info("✅ Access token refreshed.")

    def refresh_if_needed(self):
        if time.time() > self.token_expiry:
            self.refresh_access_token()

    def ensure_dir(self, path):
        os.makedirs(path, exist_ok=True)

#this is used to bsend message to particular user if task has found eror
    def send_email_alert(self,subject,body,to_email="aum.ocius07@gmail.com"):
        msg=EmailMessage()
        msg['Subject'] =subject
        msg['From'] = "2101030400144@silveroakuni.ac.in"
        msg['To']=to_email
        msg.set_content(body)

        try:
            with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
                smtp.starttls()
                smtp.login('2101030400144@silveroakuni.ac.in','xhixuampdytffuyi')
                smtp.send_message(msg)
                self.logger.info(f"📧 Alert email sent to {to_email}")


        except Exception as e:
             self.logger.error(f"❌ Failed to send email: {e}")




    def list_file_paths(self, remote_path=''):
        self.refresh_if_needed()
        file_paths = []

        try:
            result = self.dbx.files_list_folder(path=remote_path, shared_link=SharedLink(url=self.shared_link_url))
        except Exception as e:
            self.logger.error(f"❌ Error listing folder {remote_path}: {e}")
            return file_paths

        for entry in result.entries:
            entry_path = "/" + os.path.join(remote_path, entry.name).replace("\\", "/").lstrip("/")

            if isinstance(entry, FileMetadata):
                file_paths.append({
                    'path': entry_path,
                    'client_modified': entry.client_modified.astimezone(self.ist)
                })
            elif isinstance(entry, FolderMetadata):
                file_paths += self.list_file_paths(entry_path)

        return sorted(file_paths, key=lambda x: x['path'])

    def download_file(self, dropbox_path, local_path):
        self.refresh_if_needed()
        self.ensure_dir(os.path.dirname(local_path))
        try:
            _, response = self.dbx.sharing_get_shared_link_file(url=self.shared_link_url, path=dropbox_path)
            with open(local_path, 'wb') as f:
                f.write(response.content)
            self.logger.info(f"✅ Downloaded: {dropbox_path}")
        except Exception as e:
            self.logger.error(f"❌ Error downloading {dropbox_path}: {e}")

    def zip_folder(self, source_dir, zip_path):
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(source_dir):
                for file in files:
                    filepath = os.path.join(root, file)
                    arcname = os.path.relpath(filepath, source_dir)
                    zipf.write(filepath, arcname)
        self.logger.info(f"📦 Zipped to {zip_path}")


    def wait_for_deletion(self, filepath):
        self.logger.info(f"⏳ Waiting for deletion of: {filepath}")
        max_wait_second= 1*60  #t set to 5min
        start_time=time.time()

        while os.path.exists(filepath):
            if time.time()- start_time> max_wait_second:
                self.logger.warning(f"⏰ File not deleted after 5 minutes: {filepath}")

                self.send_email_alert(
                subject="🚨 File Not Deleted",
                body=f"The file {filepath} was not deleted after 5 minutes."    
                )
                sys.exit(1) 
            time.sleep(5) 
        self.logger.info(f"🗑️ File deleted: {filepath}")

    def copy_files_one_by_one(self, source_dir):
        files = sorted(os.listdir(source_dir))
        self.logger.info(f"📋 Preparing to copy {len(files)} files one-by-one...")

        for filename in files:
            src_file = os.path.join(source_dir, filename)
            dest_file = os.path.join(self.target_dir, filename)

            if os.path.isfile(src_file):
                self.logger.info(f"📤 Copying: {filename}")
                shutil.copy2(src_file, dest_file)
                self.logger.info(f"📂 Waiting for deletion of copied file: {filename}")
                self.wait_for_deletion(dest_file)
                
    def monitor(self):
        """Main monitoring loop for downloading and processing files."""

        self.ensure_dir(self.target_dir)
        self.logger.info("📂 Scanning for today's files...")
        all_files = self.list_file_paths()
        today = datetime.now(self.ist).date()

        # self.logger.info(f"📋 Found {len(all_files)} file(s) in total:")
        # for f in all_files:
        #     is_today = (f['client_modified'].date() == today)
        #     flag = "[TODAY]" if is_today else ""
        #     self.logger.info(f"📝 {f['path']} (modified: {f['client_modified']}) {flag}")
        today_files = [f for f in all_files if f['client_modified'].date() == today]

        self.logger.info(f"📋 Found {len(today_files)} file(s) modified today:")
        for f in today_files:
            self.logger.info(f"📝 {f['path']} (modified: {f['client_modified']}) [TODAY]")

        self.logger.info(" Start monitoring...")

        while datetime.now(self.ist) < self.end_time:
            current_files = self.list_file_paths()
            # Filter files modified today
            today_files = [f for f in current_files if f['client_modified'].date() == today]
            total_today_files = len(today_files)

            self.logger.info(f"⏳ Currently found {total_today_files} file(s) modified today.")


            if total_today_files == 3:
               
                new_today_files = [f for f in today_files if f['path'] not in self.downloaded_paths]

                if new_today_files:
                    self.logger.info("📥 Exactly 3 files detected for today. Starting download and processing...")

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    local_folder = f"{'downloaded_dropbox'}_{timestamp}"
                    self.ensure_dir(local_folder)

                    for file_entry in new_today_files:
                        dropbox_path = file_entry['path']
                        local_path = os.path.join(local_folder, dropbox_path.lstrip("/"))
                        self.download_file(dropbox_path, local_path)
                        self.downloaded_paths.add(dropbox_path)

                    zip_path = f"{local_folder}.zip"
                    self.zip_folder(local_folder, zip_path)
                    self.copy_files_one_by_one(local_folder)

                    self.logger.info("✅ 3 files processed. Monitoring ends.")
                    break
                else:
                    self.logger.info("⏳ All 3 files have already been downloaded. Monitoring ends.")
                    break
            else:
                self.logger.info(f"⏳ Waiting for total 3 files modified today. Checking again in {self.check_interval} minute")
                time.sleep(self.check_interval*60)

                #debug
                now = datetime.now(self.ist)
                self.logger.info(f"⏰ Current Time: {now}, End Time: {self.end_time}")

                if now >= self.end_time:
                    self.send_email_alert(
                        subject="❌ File Requirement Not Met",
                        body="In the last 3 hours, 3 new Dropbox files were not detected. Please check if the required files were uploaded."
                    )
                    break




if __name__ == '__main__':
    monitor = DropboxMonitor(
        app_key='l8exkn0byj25u27',
        app_secret='zg6jezgg42cwuez',
        refresh_token='5jqd6S1W1D8AAAAAAAAAAU5bMngNi3WjRZqyU2d1Dr4J8B6uui6UC-ulQHWwr2s_',
        shared_link_url='https://www.dropbox.com/scl/fo/pabt32xxzlddnt2zv5ubb/AIqGQDnm7GnF7e-WCEb_rPo?rlkey=nxebp23z122xd7bmmc4qgpqqs&st=tf5tz4dg&dl=0',
        target_dir=os.path.join(os.path.expanduser("~"), "Documents"),
        duration_minutes=2,
        check_interval=1
    )
    monitor.monitor()
