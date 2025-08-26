import os
import msal
import requests
import logging
import json
from html import unescape

PHOTO_FILE_EXTENSIONS = (".jpg", ".jpeg",)
FILE_SYNCED_METADATA_KEY = 'sync_status'
DOWNLOAD_DIR = 'downloads'

# TODO: convert this functions file into an importable class 

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
        next_link = self.config["onedrive_endpoint"]

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
        elif sync_status == "synced":
            return "synced"    


    def get_photos_to_sync_list(self, files):
        logging.info('Getting photos to sync list')

        files_to_sync = {}
        for filename, file_data in files.items():
            try:
                sync_status = self.check_metadata_for_sync_status(file_data['id'])
                if sync_status == "key does not exist":
                    files_to_sync[filename] = file_data
            except Exception as e:
                logging.error(f"Error checking metadata for {filename}: {e}")

        return files_to_sync

    #def download_file(self, filename: str):
    
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
    def download_file(download_url: str, filename: str) -> None:
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        logging.info(f'Downloading file from {download_url}')
        # Always stream large downloads
        response = requests.get(download_url, stream=True)

        if response.status_code == 200:
            with open(f"{DOWNLOAD_DIR}/{filename}", "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # skip keep-alive chunks
                        f.write(chunk)
            logging.info(f"{filename} download completed.")
        else:
            print("Failed to download:", response.status_code, response.text)