#!python3

import os
import msal
import json
import datetime
import logging
import requests
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler


# VARIABLES

# FUNCTIONS


def connect_to_onedrive():  
    pass


def get_photos_from_onedrive():
    pass

def login_to_onedrive():
    pass


def compress_images():
    pass


def resize_images():
    pass


def upload_images_to_ghost_post():
    pass


def create_ghost_post():
    pass


def check_if_post_exists():
    pass


def get_date_from_photo():
    pass


def initialize_msal_app(config: dict) -> msal.ConfidentialClientApplication:
    """
    Initialize MSAL app instance
    """
    app = msal.PublicClientApplication(
        client_id=config["client_id"],
        authority=config["authority"],
        token_cache=msal.SerializableTokenCache()
    )
    return app


def interactive_login(app: msal.PublicClientApplication, scopes_list: list, cache_path: str) -> str:
    """
    Interactive login to get access token
    """
    # One-time interactive login (run this once)
    flow = app.initiate_device_flow(scopes=scopes_list)
    print(f"Visit: {flow['verification_uri']}\nEnter code: {flow['user_code']}")
    result = app.acquire_token_by_device_flow(flow)

    # Save refresh token to file
    with open(cache_path, "w") as f:
        f.write(app.token_cache.serialize())
    

    return result


def get_access_token(app: msal.PublicClientApplication, scopes_list: list, cache_path: str) -> str:
    # Load cached tokens
    app.token_cache.deserialize(open(cache_path).read())
    
    accounts = app.get_accounts()
    if accounts:
        # Silent token acquisition using refresh token
        result = app.acquire_token_silent(
            scopes=scopes_list, 
            account=accounts[0]
        )
        return result["access_token"]
    raise Exception("No valid token cached. Re-run interactive login.")


def list_onedrive_files(access_token: str, onedrive_endpoint: str) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(
            onedrive_endpoint,
            headers=headers
        )
        return response.json()
    except Exception as ex:
        # TODO: when this happens, we should also try to send a notification of failure. 
        # It should either be here, or have a function constantly scan the log and notifiy if any errors found.
        logging.error(f"Error: {ex}")
                

def init_settings():
    """
    Initialize settings
    """
    # Sets a rotating file handler for logging, up to 100 MB in 3 files, using Elastics ECS log format:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[
            RotatingFileHandler('app.log', maxBytes=100000000, backupCount=3)
        ]
    )

    load_dotenv()
    MICROSOFT_CLIENT_ID = os.getenv('CLIENT_ID')
    MICROSOFT_CLIENT_SECRET = os.getenv('CLIENT_SECRET')
    onedrive_baseurl = 'https://graph.microsoft.com/v1.0/me'
    onedrive_path = '/drive/items/root:/Pictures/Samsung Gallery/DCIM/Camera'
    onedrive_endpoint = onedrive_baseurl + onedrive_path + ':/children'
    config = {}
    config["secret"] =  MICROSOFT_CLIENT_SECRET	
    config["client_id"]	= MICROSOFT_CLIENT_ID 
    config["authority"]	= 'https://login.microsoftonline.com/consumers' 
    config["endpoint"] = "https://graph.microsoft.com/v1.0/users"
    config["token_cache_path"] = 'token_cache.json'
    config["scopes"] = ["Files.ReadWrite.All"]
    config["onedrive_endpoint"] = onedrive_endpoint

    return config


def main():
    # Change prints() to logging
    config = init_settings()

    msal_app = initialize_msal_app(config)
    access_token = get_access_token(msal_app, config["scopes"], config["token_cache_path"])
    if not access_token:
        interactive_login(msal_app, config["scopes"], config["token_cache_path"])
    onedrive_files_list = list_onedrive_files(access_token, config['onedrive_endpoint'])
    print(json.dumps(onedrive_files_list))


if __name__  == '__main__':
    main()

