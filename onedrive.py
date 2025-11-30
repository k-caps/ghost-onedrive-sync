import os
import msal
import requests
import logging
import json
from html import unescape
from urllib.parse import urlparse, parse_qs, urlencode


# TODO: move these to settings.py
PHOTO_FILE_EXTENSIONS = (".jpg", ".jpeg", ".webp",)
FILE_SYNCED_METADATA_KEY = 'sync_status' # should contain 'synced', 'unsynced', or not exist. Uploads as url encoded.
PHOTO_CAPTION_METADTA_KEY = 'caption' # should contain the caption for the photo, or not exist. NOT url encoded.

class Onedrive:
    """
    Class to handle OneDrive operations
    """

    def __init__(self, config: dict):
        logging.info('Starting OneDrive class init')
        self.config = config
        self.msal_app = self._initialize_msal_app(config)

        self.access_token = None
        self.access_token = self._get_access_token(self.msal_app, self.config["scopes"], self.config["token_cache_path"])
        if not self.access_token:
            self._interactive_login(self.msal_app, self.config["scopes"], self.config["token_cache_path"])

    def _initialize_msal_app(self, config: dict) -> msal.ConfidentialClientApplication:
        logging.info('Initializing MSAL app instance')
        """
        Initialize MSAL app instance
        """
        msal_app = msal.PublicClientApplication(
            client_id=config["client_id"],
            authority=config["authority"],
            token_cache=msal.SerializableTokenCache()
        )
        return msal_app
    
    def _interactive_login(self, app: msal.PublicClientApplication, scopes_list: list, cache_path: str) -> str:
        """
        Interactive login to get access token
        """
        # One-time interactive login (run this once)
        flow = app.initiate_device_flow(scopes=scopes_list)
        logging.info(f"Visit: {flow['verification_uri']}\nEnter code: {flow['user_code']}")
        result = app.acquire_token_by_device_flow(flow)

        # Save refresh token to file
        with open(cache_path, "w") as f:
            f.write(app.token_cache.serialize())
        
        return result
    
    def _get_access_token(self, app: msal.PublicClientApplication, scopes_list: list, cache_path: str) -> str:
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


    ############################# End of init and helper functions #############################


    def get_all_files(self) -> dict:
        logging.info('Getting all files from OneDrive')
        headers = {"Authorization": f"Bearer {self.access_token}"}
        all_files = []
        # Graph API only returns 200 items at a time, so we need to loop through the pages, using a field called "@odata.nextLink" to get the next page of results.  
        next_link = self.config["onedrive_camera_endpoint"]

        while next_link:
            try:
                response = requests.get(next_link, headers=headers)
                
                if response.status_code != 200:
                    logging.error(f"Error: {response.status_code}, {response.text}")
                response.raise_for_status()

                data = response.json()
                all_files.extend(data.get("value", []))  # Add the current page of files
                next_link = data.get("@odata.nextLink") # Get the next page link if it exists            

            except Exception as ex:
                # TODO: when this happens, we should also try to send a notification of failure. 
                # It should either be here, or have a function constantly scan the log and notifiy if any errors found.
                logging.error(f"Error: {ex}")
        
        # Once there are no more pages, return the list of all files    
        return {"value": all_files}


    def get_photos_information(self):
        """
        Get photos from OneDrive.
        Photos are determined by the file extension.
        """
        all_onedrive_files_json = self.get_all_files()
            
        photos_info_dict_of_dicts = {}
        
        # Iterate through the file objects and filter photos based on file extension
        for item in all_onedrive_files_json.get("value", []):
            if "name" in item and item["name"].lower().endswith(PHOTO_FILE_EXTENSIONS):
                photos_info_dict_of_dicts[item["name"].lower()] = {
                    "filename": item["name"],
                    "id": item["id"],
                    "download_url": item.get("@microsoft.graph.downloadUrl", ""),
                }

        
        return photos_info_dict_of_dicts


    def check_metadata_for_sync_status(self, file_id: str) -> str:
        sync_status = self.get_kv_metadata_file_description(file_id, FILE_SYNCED_METADATA_KEY) or None
        if sync_status is None:
            return "key does not exist"
        elif sync_status == "unsynced":
            return "unsynced"
        elif sync_status == "synced":
            return "synced"    


    def check_metadata_for_photo_caption(self, file_id: str) -> str:
        photo_caption = self.get_kv_metadata_file_description(file_id, PHOTO_CAPTION_METADTA_KEY) or None
        return  photo_caption


    def get_photos_to_sync_list(self, files):
        logging.info('Getting photos to sync list')

        files_to_sync = {}
        for filename, file_data in files.items():
            try:
                sync_status = self.check_metadata_for_sync_status(file_data['id'])
                logging.info(f"File: {filename}, Sync status: {sync_status}")
                if sync_status != "synced":
                    files_to_sync[filename] = file_data
            except Exception as e:
                logging.error(f"Error checking metadata for {filename}: {e}")

        return files_to_sync

    
    def set_kv_metadata_file_description(self, file_id: str, data_key: str, data_value: str) -> None:
        """
        Add a key-value metadata to the file description.
        """
        logging.info(f'Adding metadata {data_key}: {data_value} to file {file_id}')
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        metadata_endpoint = f"{self.config['onedrive_baseurl']}/drive/items/{file_id}"
        
        metadata_payload = {
            "description": json.dumps({data_key: data_value})
        }
        
        response = requests.patch(metadata_endpoint, headers=headers, json=metadata_payload)
        
        if response.status_code != 200:
            raise Exception(f"Failed to add metadata to file. Error: {response.status_code}, {response.text}")
        

    def get_kv_metadata_file_description(self, file_id: str, data_key: str) -> str:
        """
        Get a key-value metadata from the file description.
        """
        logging.info(f'Getting metadata {data_key} from file {file_id}')
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        metadata_endpoint = f"{self.config['onedrive_baseurl']}/drive/items/{file_id}"
        
        response = requests.get(metadata_endpoint, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"Failed to get metadata from file. Error: {response.status_code}, {response.text}")
        
        metadata = response.json()
        description = metadata.get("description", "{}")
        
        try:
            description_dict = json.loads(unescape(description))
            return description_dict.get(data_key, "")
        

        except json.JSONDecodeError:
            return ""
        

    @staticmethod
    def download_file(download_url: str, filename: str, download_dir: str) -> str:
        os.makedirs(download_dir, exist_ok=True)
        logging.info(f'Downloading file from {download_url}')
        # Always stream large downloads
        response = requests.get(download_url, stream=True)

        if response.status_code == 200:
            with open(f"{download_dir}/{filename}", "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # skip keep-alive chunks
                        f.write(chunk)
            logging.info(f"{filename} download completed.")
        else:
            print("Failed to download:", response.status_code, response.text)
        
        return filename
    
    
    def upload_file(self, local_image_path: str, upload_url_base: str) -> str:
        """
        Uploads an image file to designated folder in OneDrive using personal Graph API.
        Returns 'upload ok' on success; otherwise logs the filename and API error and returns 'upload failed'.
        NOTE: destination_folder (string) is ignored in favor of the pre-existing config['onedrive_web_path'].
        """
        headers = {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/octet-stream"}
        filename = os.path.basename(local_image_path)

        upload_url = f"{upload_url_base}/{filename}:/content"

        try:

            with open(local_image_path, "rb") as fh:
                resp = requests.put(upload_url, headers=headers, data=fh)

            if resp.status_code in (200, 201):
                logging.info(f"Uploaded {filename} successfully.")
                return "upload ok"

            logging.error(f"Upload failed for {filename}: {resp.status_code} {resp.text}")
            return "upload failed"

        except Exception as ex:
            logging.error(f"Upload failed for {filename}: {ex}")
            return "upload failed"


    def ensure_monthly_folder_exists(self) -> bool:
        """
        Creates the monthly folder chain if it does not exist,
        by uploading an empty .keep file to that path.
        """
        url = f"{self.config['onedrive_upload_endpoint']}/.keep:/content"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        resp = requests.put(url, headers=headers, data=b"")
        if resp.status_code not in (200, 201):
            logging.error(f"Failed to ensure monthly folder exists: {resp.status_code} {resp.text}")
            return False
        return True



    # ChatGPT Generated
    def get_public_urls_and_captions_for_photos_in_folder(self, upload_url_base: str) -> list:
        """
        Returns a list of dicts, one per photo file in the folder.

        Each dict has:
        {
            "id":          <file id>,
            "filename":    <file name>,
            "url":         <public URL suitable for <img src="">>,
            "description": <OneDrive description field or "">,
            "caption":     <caption from metadata or None>,
        }

        The 'url' is built from a OneDrive sharing link and should stay valid
        until you revoke or change sharing on the item (unlike
        @microsoft.graph.downloadUrl which expires in ~1 hour).
        """
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        image_infos: list[dict] = []

        try:
            # Normalize base '.../drive/root:/Folder'
            base = upload_url_base
            for tail in (":/content", ":/children"):
                if base.endswith(tail):
                    base = base[: -len(tail)]
            base = base.rstrip(":")

            # Resolve folder metadata
            folder_url = f"{base}"
            folder_resp = requests.get(folder_url, headers=headers)
            if folder_resp.status_code != 200:
                logging.error(
                    f"Failed to resolve folder {folder_url}: "
                    f"{folder_resp.status_code} {folder_resp.text}"
                )
                return image_infos

            folder_id = folder_resp.json()["id"]

            # List files in folder
            next_link = f"{self.config['onedrive_baseurl']}/drive/items/{folder_id}/children"
            items: list[dict] = []
            while next_link:
                page = requests.get(next_link, headers=headers)
                if page.status_code != 200:
                    logging.error(
                        f"Failed to list children for {folder_id}: "
                        f"{page.status_code} {page.text}"
                    )
                    return image_infos

                data = page.json()
                items.extend(data.get("value", []))
                next_link = data.get("@odata.nextLink")

            # For each photo file: fetch description, create share link, get caption
            for it in items:
                name = it.get("name", "")
                if not name.lower().endswith(PHOTO_FILE_EXTENSIONS):
                    continue

                item_id = it["id"]

                # Get item metadata (for description; we no longer use @microsoft.graph.downloadUrl)
                meta_url = f"{self.config['onedrive_baseurl']}/drive/items/{item_id}"
                meta_resp = requests.get(meta_url, headers=headers)

                if meta_resp.status_code != 200:
                    logging.error(
                        f"Failed to fetch metadata for {name}: "
                        f"{meta_resp.status_code} {meta_resp.text}"
                    )
                    continue

                meta_json = meta_resp.json()
                description = meta_json.get("description") or ""

                # Create (or re-use) an anonymous view sharing link
                create_link_url = f"{self.config['onedrive_baseurl']}/drive/items/{item_id}/createLink"
                link_body = {
                    "type": "view",
                    "scope": "anonymous",
                }
                link_resp = requests.post(create_link_url, headers=headers, json=link_body)

                if link_resp.status_code not in (200, 201):
                    logging.error(
                        f"Failed to create share link for {name}: "
                        f"{link_resp.status_code} {link_resp.text}"
                    )
                    continue

                link_json = link_resp.json()
                share_url = (link_json.get("link") or {}).get("webUrl")
                if not share_url:
                    logging.error(f"No share link webUrl found for {name}")
                    continue

                # Turn the share link into a direct-download-ish URL for <img src="">
                public_url = self._make_public_image_url_from_share(share_url)

                # Use your helper to get the caption from metadata
                raw_caption = self.check_metadata_for_photo_caption(item_id)
                # Normalize to None if the helper uses a sentinel string
                if raw_caption and raw_caption != "caption key does not exist":
                    caption = raw_caption
                else:
                    caption = None

                image_infos.append(
                    {
                        "id": item_id,
                        "filename": name,
                        "url": public_url,
                        "description": description,
                        "caption": caption,
                    }
                )

        except Exception as ex:
            logging.error(f"Error while getting public URLs: {ex}")

        return image_infos




    def reset_photos_for_month(self, photos_for_month):
        for filename, photo in photos_for_month.items():
            logging.info(f"Resetting {filename}")
            self.set_kv_metadata_file_description(photo['id'], 'sync_status', 'unsynced')


    def _make_public_image_url_from_share(self, share_url: str) -> str:
        """
        Convert a OneDrive share link (webUrl) into a URL suitable for <img src="">.

        For personal OneDrive, this follows the documented pattern:
          https://onedrive.live.com/?cid=...&id=FILE_ID&authkey=...
        -> https://onedrive.live.com/download?cid=...&resid=FILE_ID&authkey=...

        For SharePoint / OneDrive for Business URLs, we fall back to adding
        ?download=1 or &download=1, which often forces a direct file response.

        NOTE: These patterns are based on public guidance and may change in the
        future, since Microsoft doesn't officially guarantee a permanent
        "direct image URL" API. If you need something 100% stable, a small
        proxy service in front of Graph is the robust solution.
        """
        try:
            parsed = urlparse(share_url)

            # Personal OneDrive: onedrive.live.com with cid / id / resid / authkey
            if "onedrive.live.com" in parsed.netloc:
                qs = parse_qs(parsed.query)

                cid = qs.get("cid", [None])[0]
                # Some links use 'id', others 'resid'; prefer resid if present
                resid = qs.get("resid", [None])[0] or qs.get("id", [None])[0]
                authkey = qs.get("authkey", [None])[0]

                params = {}
                if cid:
                    params["cid"] = cid
                if resid:
                    params["resid"] = resid
                if authkey:
                    params["authkey"] = authkey

                if params:
                    # Direct download form
                    return f"https://onedrive.live.com/download?{urlencode(params)}"

            # Fallback (SharePoint / ODB / 1drv.ms etc.): append download=1
            if "download=1" not in parsed.query:
                sep = "&" if parsed.query else "?"
                return share_url + f"{sep}download=1"

        except Exception as ex:
            logging.warning(f"Failed to turn share URL into download URL: {ex}")

        # If anything goes wrong, just return the original share URL
        return share_url
