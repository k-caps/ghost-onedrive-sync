
import os
import logging
import datetime
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

def init_settings():
    """
    Initialize settings
    """
    # Sets a rotating file handler for logging, up to 100 MB in 3 files
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[
            RotatingFileHandler('ghost-onedrive-sync.log', maxBytes=100000000, backupCount=3)
        ],
        force=True
    )

    load_dotenv()
    onedrive_baseurl = 'https://graph.microsoft.com/v1.0/me'
    onedrive_base_path = 'drive/root:'
    onedrive_camera_path = f"Pictures/Samsung Gallery/DCIM/Camera"
    onedrive_web_path = f"Pictures/Web Optimized"
    this_month_folder_name: str = datetime.datetime.now().strftime("%Y/%m")
    config = {}
    config["client_id"]	= os.getenv('CLIENT_ID')
    config["authority"]	= 'https://login.microsoftonline.com/consumers'
    config["token_cache_path"] = 'token_cache.json'
    config["scopes"] = ["Files.ReadWrite.All"]
    config["onedrive_camera_endpoint"] = f"{onedrive_baseurl}/{onedrive_base_path}/{onedrive_camera_path}:/children"
    config["onedrive_web_endpoint"] = f"{onedrive_baseurl}/{onedrive_base_path}/{onedrive_web_path}/{this_month_folder_name}:/children"
    config["onedrive_upload_endpoint"] = f"{onedrive_baseurl}/{onedrive_base_path}/{onedrive_web_path}/{this_month_folder_name}"  # /"{{filename}}:/content"  <- MUST APPEND WHEN WE GET FILENAME
    config["onedrive_baseurl"] = onedrive_baseurl
    config["onedrive_camera_path"] = onedrive_camera_path
    config["onedrive_web_path"] = onedrive_web_path
    config["download_dir"] = 'downloads'
    config["output_dir"] = os.getenv('OUTPUT_DIR', 'optimized')

    return config