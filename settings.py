
import os
import logging
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
        ]
    )

    load_dotenv()
    onedrive_baseurl = 'https://graph.microsoft.com/v1.0/me'
    onedrive_path = '/drive/items/root:/Pictures/Samsung Gallery/DCIM/Camera'

    config = {}
    config["client_id"]	= os.getenv('CLIENT_ID')
    config["authority"]	= 'https://login.microsoftonline.com/consumers'
    config["token_cache_path"] = 'token_cache.json'
    config["scopes"] = ["Files.ReadWrite.All"]
    config["onedrive_endpoint"] = onedrive_baseurl + onedrive_path + ':/children'
    config["onedrive_baseurl"] = onedrive_baseurl
    config["onedrive_path"] = onedrive_path

    return config