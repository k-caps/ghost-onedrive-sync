#!python3
import os
import logging
import datetime
import settings
from ghost import Ghost
from onedrive import Onedrive



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
    onedrive = Onedrive(config)
    all_onedrive_photos_info = onedrive.get_photos_information()

    # Don't always assume that every previous run synced every file sucessfully.
    # We need to maintain a list of photos that have been targeted to be synced previously, then check if any of those failed.
    # aside from failed atttempts, also go through this month's photos and check if they have been synced.
    # maintain a file with all photos marked for sync and also those failed?
    # basically ensure that we know the state of any given photo? Oof.

    this_months_photos = get_this_months_photos(all_onedrive_photos_info)
    # for photo in this_months_photos:
    #     logging.info(f"Photo name: {photo}")
    #     logging.info(f"Photo ID: {this_months_photos[photo]['id']}")
    #     logging.info(f"Photo download URL: {this_months_photos[photo]['download_url']}")

    
    this_months_unsynced_photos = onedrive.get_photos_to_sync_list(this_months_photos)

    # We only init this class here so as not to put more memory pressure on the system while it is busy with onedrive tasks.
    ghost = Ghost(os.environ['GHOST_ADMIN_URL'],  os.environ['GHOST_ADMIN_API_KEY'])

    all_uploaded_image_urls = []
    for photo_name, photo_file_data in this_months_unsynced_photos.items():
        logging.info(f"Photo to sync: {photo_name}")
        photo_local_file_name: str = onedrive.download_file(photo_file_data['download_url'], photo_name) # add check for if filename already exists on local disk
        # compress_images(photo)
        # resize_images(photo)
        uploaded_photo_url = ghost.upload_image(photo_local_file_name)
        logging.info(f"Uploaded photo URL: {uploaded_photo_url}")
        all_uploaded_image_urls.append(uploaded_photo_url)
        os.remove(photo_local_file_name)
        # mark photo as synced in onedrive metadata

    draft_post_html = ghost.prepare_draft_post_html(all_uploaded_image_urls)
    logging.info("-------------------------------------------------------------------------------- Prepared draft post HTML content:\n" + draft_post_html + '\n--------------------------------------------------------------------------------\n')
    this_month = datetime.datetime.now().strftime("%m-%Y")
    new_post = ghost.create_draft_post(this_month, draft_post_html)
    logging.info(f"Created new draft post: {new_post['url']}")
   

if __name__  == '__main__':
    main()

