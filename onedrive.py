import msal
import requests
import logging
import json

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


def get_photos_list(access_token: str, onedrive_endpoint: str):
    """
    Get photos from OneDrive.
    Photos are determined by the file extension.
    """
    all_onedrive_files_json = list_onedrive_files(access_token, onedrive_endpoint)
    photos_list = []
    print(json.dumps(all_onedrive_files_json))
    # Iterate through the files and filter photos based on file extension
    for item in all_onedrive_files_json.get("value", []):
        if "name" in item and item["name"].lower().endswith((".jpg", ".jpeg", ".png")):
            #photos_list.append(item["name"])
            photos_list.append(item)

    return photos_list
