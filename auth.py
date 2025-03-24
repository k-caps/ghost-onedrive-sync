#!python3
import os
from dotenv import load_dotenv

from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.client_context import ClientContext

load_dotenv()

tenant_url = os.getenv('tenant_url')
client_id = os.getenv('client_id')
client_secret = os.getenv('client_secret')

context = AuthenticationContext(tenant_url)
if context.acquire_token_for_app(client_id, client_secret):
    print("Authentication successful")
else:
    print("Authentication failed")
