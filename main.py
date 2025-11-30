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


def main():
    # Change prints() to logging
    config = settings.init_settings()
    onedrive = Onedrive(config)
    all_onedrive_photos_info = onedrive.get_photos_information()

    this_months_photos = get_this_months_photos(all_onedrive_photos_info)
    
    # Reset all photos to unsynced for testing purpose
    #onedrive.reset_photos_for_month(this_months_photos)
    #exit()
    
    this_months_unsynced_photos = onedrive.get_photos_to_sync_list(this_months_photos)

    logging.info(f"Ensuring monthly folder exists in OneDrive")
    if not onedrive.ensure_monthly_folder_exists():
        logging.error(f"Failed to ensure monthly folder {config['onedrive_upload_endpoint']} exists in OneDrive.")
        raise Exception("Failed to ensure folder exists in OneDrive.")
    
    # We only init these classes here so as not to put more memory pressure on the system while it is busy with onedrive tasks.
    ghost = Ghost(os.environ['GHOST_ADMIN_URL'],  os.environ['GHOST_ADMIN_API_KEY'])
    image_editor = ImageEditor(out_dir=config["output_dir"], max_long_edge=1600, target_kb=300)

    for photo_name, photo_file_data in this_months_unsynced_photos.items():
        logging.info(f"Photo to sync: {photo_name}")
        photo_local_file_name: str = onedrive.download_file(photo_file_data['download_url'], photo_name, config["download_dir"])
        photo_webp_file_name: str = f"{config['output_dir']}/{photo_local_file_name.rsplit('.', 1)[0]}.webp"


        image_editor.prepare_for_upload(f"{config["download_dir"]}/{photo_local_file_name}")
        #uploaded_photo_url = ghost.upload_image(photo_webp_file_name)

        upload_status = onedrive.upload_file(photo_webp_file_name, config["onedrive_upload_endpoint"])
        if upload_status != "upload ok":
            logging.error(f"Failed to upload photo {photo_name} to OneDrive. Skipping marking as synced.")
        else:
            onedrive.set_kv_metadata_file_description(photo_file_data['id'], 'sync_status', 'synced')
            
        # if uploaded_photo_url == "upload failed":
        #     logging.error(f"Failed to upload photo {photo_name} to Ghost. Skipping marking as synced.")
        # else:
        #     logging.info(f"Uploaded photo URL: {uploaded_photo_url}")
        #     all_uploaded_image_urls.append(uploaded_photo_url)

        os.remove(f"{config["output_dir"]}/{photo_local_file_name.rsplit('.', 1)[0]}.jpg")
        os.remove(f"{config["download_dir"]}/{photo_local_file_name}")
        os.remove(photo_webp_file_name)
    
    all_uploaded_image_urls_and_captions = onedrive.get_public_urls_and_captions_for_photos_in_folder(config["onedrive_upload_endpoint"])

    draft_post_html = ghost.prepare_draft_post_html(all_uploaded_image_urls_and_captions)
    logging.info("-------------------------------------------------------------------------------- Prepared draft post HTML content:\n" + draft_post_html + '\n--------------------------------------------------------------------------------\n')
    this_month = datetime.datetime.now().strftime("%m-%Y")
    post = ghost.upsert_post(this_month, draft_post_html)
    logging.info(f"Created new draft post: {post['url']}")
   

if __name__  == '__main__':
    main()

