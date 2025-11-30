import jwt 
import json
import time
import html
import logging
import calendar
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

# Removed in favor of onedrive as storage backend:
    # def upload_image(self, image_path: str) -> str:
    #     """
    #     Uploads an image file to Ghost Admin API.
    #     Returns the absolute URL of the uploaded image.
    #     """
    #     url = f"{self.admin_api_url}/images/upload/"

    #     with open(image_path, "rb") as f:
    #         files = {
    #             "file": (image_path, f, "image/jpeg")  # change MIME if needed
    #         }

    #         resp = requests.Response()            

    #         try:
    #             resp = requests.post(url, headers=self._get_ghost_api_auth_header(self.admin_api_key), files=files, timeout=30, verify=False)
    #             resp.raise_for_status()
    #         except requests.exceptions.HTTPError as ex:
    #             logging.error(f"HTTP error during image upload: {ex}")
    #             logging.error(resp.text)
    #             logging.error(f"Failed to upload image {image_path} to Ghost.")
    #             return "upload failed"
    #         except Exception as ex: # TODO: cleanup error handling with something actually useful
    #             logging.error(f"HTTP error during image upload: {ex}")
    #             logging.error(f"Failed to upload image {image_path} to Ghost.")
    #             return "upload failed"
    #     if resp.status_code in (200, 201):    
    #         data = resp.json()
    #          # Typical response shape: {"images":[{"url":"https://.../content/images/..." }]}
    #         return data["images"][0]["url"]
    #     else:
    #         logging.error(f"Unexpected response status {resp.status_code} during image upload.")
    #         logging.error(f"Failed to upload image {image_path} to Ghost.")
    #         return "upload failed"


    def find_post_by_slug(self, slug: str):
        url = f"{self.admin_api_url}/posts/?filter=slug:{json.dumps(slug)}"
        headers = self._get_ghost_api_auth_header(self.admin_api_key)

        resp = requests.get(url, headers=headers, timeout=20, verify=False)
        if resp.status_code != 200:
            logging.warning("Failed to search for post: %s %s", resp.status_code, resp.text[:200])
            return None

        posts = resp.json().get("posts", [])
        return posts[0] if posts else None


    def create_draft_post(self, slug: str, html: str) -> dict | None:
        title = self._humanize_title(slug)

        url = f"{self.admin_api_url}/posts/?source=html"
        headers = {
            **self._get_ghost_api_auth_header(self.admin_api_key),
            "Content-Type": "application/json",
        }

        body = {
            "posts": [{
                "slug": slug,           # <--- NEW
                "title": title,         # <--- HUMANIZED
                "html": html,
                "status": "draft"
            }]
        }

        for attempt in range(1, 4):
            try:
                resp = requests.post(url, headers=headers, json=body, timeout=30, verify=False)

                if resp.status_code == 503:
                    logging.warning("Ghost returned 503 (attempt %d). Retrying...", attempt)
                    time.sleep(2)
                    continue

                if 200 <= resp.status_code < 300:
                    return resp.json()["posts"][0]

                logging.error(f"Ghost returned error {resp.status_code}: {resp.text[:300]}")
                return None

            except requests.exceptions.RequestException as e:
                logging.warning("Network error (attempt %d): %s", attempt, e)
                time.sleep(2)

        logging.error("Failed to create draft post after 3 attempts.")
        return None



    def update_existing_post(self, post_id: str, slug: str, html: str):
        title = self._humanize_title(slug)

        url = f"{self.admin_api_url}/posts/{post_id}/?source=html"
        headers = {
            **self._get_ghost_api_auth_header(self.admin_api_key),
            "Content-Type": "application/json",
        }

        body = {
            "posts": [{
                "id": post_id,
                "slug": slug, 
                "title": title, 
                "html": html,
                "status": "draft"
            }]
        }

        resp = requests.put(url, headers=headers, json=body, timeout=30, verify=False)

        if 200 <= resp.status_code < 300:
            return resp.json()["posts"][0]

        logging.error("Failed to update post %s: %s %s", post_id, resp.status_code, resp.text[:300])
        return None



    def upsert_post(self, slug: str, html: str):
        existing = self.find_post_by_slug(slug)

        if existing:
            logging.info("Post '%s' exists (id=%s). Updating.", slug, existing["id"])
            return self.update_existing_post(existing["id"], slug, html)

        logging.info("Post '%s' does not exist. Creating new draft.", slug)
        return self.create_draft_post(slug, html)



    @staticmethod
    def prepare_draft_post_html(all_file_urls: list[str]) -> str:
        """
        Accepts either:
          - Old style: list of image URLs (str)
          - New style: list of dicts with keys:
              - "url"         (required)
              - "caption"     (optional)
              - "description" (optional, used if caption missing)
        """
        html_content: str = ''

        for item in all_file_urls:
            # Backwards compatible: if it's a plain string, behave like before
            if isinstance(item, str):
                url = item
                caption = None
            else:
                # New shape: dict coming from OneDrive helper:
                # {"id", "filename", "url", "description", "caption"}
                url = item.get("url")
                caption = item.get("caption") or item.get("description")

            if not url:
                # Skip anything malformed
                continue

            if caption:
                esc_caption = html.escape(str(caption), quote=True)
                html_content += (
                    f'<figure>'
                    f'<img src="{url}" alt="{esc_caption}">'
                    f'<figcaption>{esc_caption}</figcaption>'
                    f'</figure>\n'
                )
            else:
                html_content += f"""<p><img src="{url}"></p>\n"""

        return html_content


    @staticmethod
    def _humanize_title(date_slug: str) -> str:
        """
        Converts a slug like '11-2025' → 'November 2025'
        """
        month, year = date_slug.split("-")
        month_name = calendar.month_name[int(month)]
        return f"{month_name} {year}"
    
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