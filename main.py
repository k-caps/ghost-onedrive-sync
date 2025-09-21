#!python3
import os
import logging
import datetime
import settings
from ghost import Ghost
from onedrive import Onedrive
from image_editor import ImageEditor


def get_this_months_photos(all_onedrive_photos_info):
    this_month = datetime.datetime.now().strftime("%Y%m")
    this_months_photos = {}

    for photo_name, photo_full_data in all_onedrive_photos_info.items():
        if photo_name.startswith(this_month):
            this_months_photos[photo_name] = photo_full_data

    return this_months_photos


def sync_failed_photos():
    pass


def main():
    # Change prints() to logging
    config = settings.init_settings()
    onedrive = Onedrive(config)
    all_onedrive_photos_info = onedrive.get_photos_information()

    this_months_photos = get_this_months_photos(all_onedrive_photos_info)

    # for photo in this_months_photos:
    #     logging.info(f"Photo name: {photo}")
    #     logging.info(f"Photo ID: {this_months_photos[photo]['id']}")
    #     logging.info(f"Photo download URL: {this_months_photos[photo]['download_url']}")

    
    # # Reset all photos to unsynced for testing purpose
    # for filename, photo in this_months_photos.items():
    #     print(f"Resetting {filename}")
    #     onedrive.set_kv_metadata_file_description(photo['id'], 'sync_status', 'unsynced')
    
    this_months_unsynced_photos = onedrive.get_photos_to_sync_list(this_months_photos)

    # We only init these classes here so as not to put more memory pressure on the system while it is busy with onedrive tasks.
    ghost = Ghost(os.environ['GHOST_ADMIN_URL'],  os.environ['GHOST_ADMIN_API_KEY'])
    image_editor = ImageEditor(out_dir=config["output_dir"], max_long_edge=1600, target_kb=300)

    all_uploaded_image_urls = []
    for photo_name, photo_file_data in this_months_unsynced_photos.items():
        logging.info(f"Photo to sync: {photo_name}")
        photo_local_file_name: str = onedrive.download_file(photo_file_data['download_url'], photo_name, config["download_dir"]) # add check for if filename already exists on local disk
        photo_webp_file_name: str = f"{config['output_dir']}/{photo_local_file_name.rsplit('.', 1)[0]}.webp"


        image_editor.prepare_for_upload(f"{config["download_dir"]}/{photo_local_file_name}")
        uploaded_photo_url = ghost.upload_image(photo_webp_file_name)
        if uploaded_photo_url == "upload failed":
            logging.error(f"Failed to upload photo {photo_name} to Ghost. Skipping marking as synced.")
        else:
            logging.info(f"Uploaded photo URL: {uploaded_photo_url}")
            all_uploaded_image_urls.append(uploaded_photo_url)

            os.remove(f"{config["download_dir"]}/{photo_local_file_name}") # TODO: always delete, even on failed uploads. Currently leaving this here so that we can debug failed uploads if any occur.
            os.remove(f"{config["output_dir"]}/{photo_local_file_name}")
            os.remove(photo_webp_file_name)
            onedrive.set_kv_metadata_file_description(photo_file_data['id'], 'sync_status', 'synced')

    draft_post_html = ghost.prepare_draft_post_html(all_uploaded_image_urls)
    logging.info("-------------------------------------------------------------------------------- Prepared draft post HTML content:\n" + draft_post_html + '\n--------------------------------------------------------------------------------\n')
    this_month = datetime.datetime.now().strftime("%m-%Y")
    new_post = ghost.create_draft_post(this_month, draft_post_html)
    logging.info(f"Created new draft post: {new_post['url']}")
   

if __name__  == '__main__':
    main()

