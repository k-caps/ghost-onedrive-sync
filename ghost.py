import jwt 
import json
import time
import logging
import requests


class Ghost:
    """
    Class to handle Ghhost API operations
    """

    def __init__(self, admin_api_url: str, admin_api_key: str):
        logging.info('Starting Ghost class init')
        self.admin_api_url = admin_api_url.rstrip("/")
        self.admin_api_key = admin_api_key



    def _get_ghost_api_auth_header(self, admin_api_key: str) -> dict:
        """
        Authenticate to Ghost Admin API using JWT signed with Admin key secret
        """
        key_id, secret = admin_api_key.split(":")
        iat = int(time.time())
        payload = {
            "iat": iat,
            "exp": iat + 5 * 60,       # 5 minutes
            "aud": "/admin/"           # per Ghost Admin API docs
        }
        token = jwt.encode(
            payload,
            bytes.fromhex(secret),
            algorithm="HS256",
            headers={"kid": key_id}
        )
        # PyJWT returns str on recent versions; ensure we return a str
        auth_token: str = token if isinstance(token, str) else token.decode("utf-8")

        return {"Authorization": f"Ghost {auth_token}"}


    def upload_image(self, image_path: str) -> str:
        """
        Uploads an image file to Ghost Admin API.
        Returns the absolute URL of the uploaded image.
        """
        url = f"{self.admin_api_url}/images/upload/"

        with open(image_path, "rb") as f:
            files = {
                "file": (image_path, f, "image/jpeg")  # change MIME if needed
            }
            # Optional: you can add {"purpose": (None, "image")} if you need a specific purpose
            resp = requests.post(url, headers=self._get_ghost_api_auth_header(self.admin_api_key), files=files, timeout=30, verify=False)
            print( resp.text )
        resp.raise_for_status()

        data = resp.json()
        # Typical response shape: {"images":[{"url":"https://.../content/images/..." }]}
        return data["images"][0]["url"]


    def create_draft_post(self, title: str, html: str) -> dict:
        """
        Creates a draft post with given title + HTML.
        Returns the created post JSON.
        """
        # ?source=html lets you supply "html" directly
        url = f"{self.admin_api_url}/posts/?source=html"
        headers = {
            **self.ghost_auth_header,
            "Content-Type": "application/json"
        }
        body = {
            "posts": [{
                "title": title,
                "html": html,
                "status": "draft"
            }]
        }
        resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=30, verify=False)
        resp.raise_for_status()
        return resp.json()["posts"][0]
    

    @staticmethod
    def prepare_draft_post_html(all_file_urls: list[str]) -> str:
        html_content: str
        for url in all_file_urls:
            html_content += f"""<p><img src="{url}" alt="Uploaded image"></p>\n""".strip()

        return html_content


### Example of hardcoded HTML content:
'''
     html_content = f"""
<p>Hello from the API 👋 — this is a paragraph in a draft post.</p>

<p><img src="{img1_url}" alt="First uploaded image"></p>

<hr>

<figure>
  <img src="{img2_url}" alt="Second uploaded image">
  <figcaption>Second image — a friendly caption</figcaption>
</figure>
""".strip()"    
'''