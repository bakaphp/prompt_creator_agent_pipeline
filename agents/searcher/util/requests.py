import requests
import os
from dotenv import load_dotenv

load_dotenv()


class RequestsUtil(object):
    """
    Utility class for making HTTP requests.
    """

    @staticmethod
    def post(payload: dict, auth_token: str = None, withapp_key: bool = False) -> requests.Response:
        """
        Make a POST request.
        """
        headers = {
            "Content-Type": "application/json",
            "X-Kanvas-App": os.getenv("KANVAS_APP_ID"),
            # "X-Kanvas-Location": os.getenv("KANVAS_LOCATION"),
        }
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        if withapp_key:
            headers["X-Kanvas-Key"] = os.getenv("KANVAS_APP_KEY")

        return requests.post(os.getenv("KANVAS_API_URL"), json=payload, headers=headers)
