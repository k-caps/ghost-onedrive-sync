#!python3

import os
import msal
import datetime
from dotenv import load_dotenv
from office365.graph_client import GraphClient
from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.authentication_context import AuthenticationContext


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

#def connect_to_onedrive(tenant_url: str, client_id: str, client_secret: str) -> ClientContext:
#    context = AuthenticationContext(tenant_url)
#    context.acquire_token_for_app(client_id, client_secret)
#    return context


def acquire_token(tenant_id: str, client_id: str, client_secret: str):
    """
    Acquire token via MSAL
    """
    authority_url = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(
        authority=authority_url,
        client_id=f"{client_id}",
        client_credential=f"{client_secret}"
    )
    token = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    return token




# MAIN
def main():
    # Change prints() to logging
    load_dotenv()
    MICROSOFT_TENANT_ID = os.getenv('tenant_id')
    MICROSOFT_CLIENT_ID = os.getenv('client_id')
    MICROSOFT_CLIENT_SECRET = os.getenv('client_secret')

    def token_callback():
        return acquire_token(MICROSOFT_TENANT_ID, MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET)

    #api_token = acquire_token(MICROSOFT_TENANT_ID, MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET)
    client = GraphClient(token_callback)
    drives = client.drives.get().execute_query()
    for drive in drives:
        print(f"Drive url: {drive.web_url}")

# https://learn.microsoft.com/en-us/onedrive/developer/rest-api/concepts/direct-endpoint-differences?view=odsp-graph-online
# office365.runtime.client_request_exception.ClientRequestException: ('BadRequest', 'Tenant does not have a SPO license.', '400 Client Error: Bad Request for url: https://graph.microsoft.com/v1.0/drives')


    #onedrive_context = connect_to_onedrive(MICROSOFT_TENANT_URL, MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET)
    #print(f"Began program execution at {datetime.datetime.now()}")
    #get_photos_from_onedrive(onedrive_context)


if __name__  == '__main__':
    main()

