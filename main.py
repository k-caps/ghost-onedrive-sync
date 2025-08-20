#!python3
import onedrive
import json
import datetime
import settings
from dotenv import load_dotenv
from onedrive import Onedrive
from logging.handlers import RotatingFileHandler


def get_this_months_photos(all_onedrive_photos_info):
    this_month = datetime.datetime.now().strftime("%Y%m")
    this_months_photos = {}

    for photo_name, photo_full_data in all_onedrive_photos_info.items():
        if photo_name.startswith(this_month):
            this_months_photos[photo_name] = photo_full_data

    return this_months_photos


def check_previously_synced_photos():
    pass


def sync_failed_photos():
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




def main():
    # Change prints() to logging
    config = settings.init_settings()

    # msal_app = onedrive.initialize_msal_app(config)
    # access_token = onedrive.get_access_token(msal_app, config["scopes"], config["token_cache_path"])
    # if not access_token:
    #     onedrive.interactive_login(msal_app, config["scopes"], config["token_cache_path"])
   
    onedrive = Onedrive(config)
    all_onedrive_photos_info = onedrive.get_photos_information()

    # Don't always assume that every previous run synced every file sucessfully.
    # We need to maintain a list of photos that have been targeted to be synced previously, then check if any of those failed.
    # aside from failed atttempts, also go through this month's photos and check if they have been synced.
    # maintain a file with all photos marked for sync and also those failed?
    # basically ensure that we know the state of any given photo? Oof.

    this_months_photos = get_this_months_photos(all_onedrive_photos_info)
    # for photo in this_months_photos:
    #     print(f"Photo name: {photo}")
    #     print(f"Photo ID: {this_months_photos[photo]['id']}")
    #     print(f"Photo download URL: {this_months_photos[photo]['download_url']}")

    
    this_months_unsynced_photos = onedrive.get_photos_to_sync_list(this_months_photos)

    for photo in this_months_unsynced_photos:
        print(f"Photo to sync: {photo}")
        onedrive.download_file()
        # compress_images(photo)
        # resize_images(photo)
        # upload_images_to_ghost_post(photo)
        # create_ghost_post(photo)
        # check_if_post_exists(photo)
        # get_date_from_photo(photo)


            

if __name__  == '__main__':
    main()

