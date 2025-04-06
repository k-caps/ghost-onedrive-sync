#!python3
import onedrive
import json
import datetime
import settings
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler


# VARIABLES

# FUNCTIONS





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




def main():
    # Change prints() to logging
    config = settings.init_settings()
    msal_app = onedrive.initialize_msal_app(config)
    access_token = onedrive.get_access_token(msal_app, config["scopes"], config["token_cache_path"])
    if not access_token:
        onedrive.interactive_login(msal_app, config["scopes"], config["token_cache_path"])
    all_onedrive_files_json = onedrive.list_onedrive_files(access_token, config['onedrive_endpoint'])
    print(json.dumps(all_onedrive_files_json))


    #onedrive_photos_list = onedrive.get_photos_list(access_token, config['onedrive_endpoint'])
    #this_month = datetime.datetime.now().strftime("%Y%m")
    #this_months_photos = []

    # seems that only files from 2023 are being returned. Maybe the API only returns chunks?
    #for photo in onedrive_photos_list:
    #    #print(photo["name"])
    #    if photo["name"].startswith(this_month):
    #        #print(photo["name"])
    #        pass
        
    #print(this_month)
    #for photo in this_months_photos:

    #print(json.dumps(onedrive_photos_list))


if __name__  == '__main__':
    main()

