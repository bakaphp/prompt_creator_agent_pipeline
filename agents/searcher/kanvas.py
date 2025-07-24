from asyncio import constants
from util.requests import RequestsUtil
import os
import json
from datetime import datetime
from typing import Optional


class KanvasClient(object):
    """
    KanvasClient is a utility class for interacting with the Kanvas API.
    It provides methods for logging in, posting messages, and fetching creator profiles.
    It uses GraphQL mutations to perform these actions.
    It requires the KANVAS_USER_EMAIL and KANVAS_USER_PASSWORD environment variables to be set for authentication.
    The KANVAS_API_URL and KANVAS_APP_ID environment variables are also required for making API requests.
    The class uses the RequestsUtil class to handle HTTP requests.
    It returns JSON responses for the various operations.
    The class is designed to be used in a server-side application where the Kanvas API is accessible.
    It is not intended for use in a client-side application or in a browser environment.
    It is also not intended for use in a command-line interface or in a script.
    The class is designed to be used in a Python application where the Kanvas API is accessible.
    """

    SOCIAL_CREATOR_AGENTS_KEY='social-creator-agents'

    def login(self, email: str = None, password: str = None) -> str:
        graphql_query = """
        mutation login($data: LoginInput!) {
          login(data: $data) {
            token
          }
        }
        """
        if not email:
            email = os.getenv("KANVAS_USER_EMAIL")
        if not password:
            password = os.getenv("KANVAS_USER_PASSWORD")

        payload = {
            "query": graphql_query,
            "variables": {
                "data": {
                    "email": email,
                    "password": password,
                }
            },
        }

        response = RequestsUtil.post(payload=payload)
        data = response.json()
        return json.dumps(data)

    def post_kanvas_message(self, email: str, password: str, title: str, prompt: str) -> str:
        """
        Post a message to the Kanvas API.
        """
        kanvas_auth = self.login(email=email, password=password)
        if not kanvas_auth:
            return json.dumps({"success": False, "error": "Authentication failed"})
        auth_token = (
            json.loads(kanvas_auth).get("data", {}).get("login", {}).get("token")
        )
        if not auth_token:
            return json.dumps(
                {"success": False, "error": "Authentication token not found", "kanvas_auth": kanvas_auth}
            )
        graphql_query = """
        mutation createMessage($input: MessageInput!) {
          createMessage(input: $input) {
            id
            uuid
            message
            created_at
          }
        }
        """

        payload = {
            "query": graphql_query,
            "variables": {
                "input": {
                    "message_verb": "prompt",
                    "message": {
                        "ai_model": {
                            "key": "gemini",
                            "value": "gemini-2.5-flash",
                            "name": "Gemini 2.5 Flash",
                            "payment": {
                                "price": 0,
                                "is_locked": False,
                                "free_regeneration": False
                            },
                            "icon": "https://cdn.promptmine.ai/Gemini.png",
                            "isDefault": True,
                            "isNew": True
                        },
                        "prompt": prompt,
                        "title": title,
                        "type": "text-format"
                    },
                    "is_public": 0,
                },
            },
        }

        response = RequestsUtil.post(payload=payload, auth_token=auth_token)
        if response.status_code == 200:
            data = response.json()
            return json.dumps({"success": True, "data": data})
        else:
            return json.dumps(
                {
                    "success": False,
                    "status_code": response.status_code,
                    "error": response.text,
                }
            )
        
    def post_kanvas_nugget_message(self, email: str, password: str, title: str, nugget: str, parent_id: str) -> str:
        """
        Post a message to the Kanvas API.
        """
        kanvas_auth = self.login(email=email, password=password)
        if not kanvas_auth:
            return json.dumps({"success": False, "error": "Authentication failed"})
        auth_token = (
            json.loads(kanvas_auth).get("data", {}).get("login", {}).get("token")
        )
        if not auth_token:
            return json.dumps(
                {"success": False, "error": "Authentication token not found", "kanvas_auth": kanvas_auth}
            )
        graphql_query = """
        mutation createMessage($input: MessageInput!) {
          createMessage(input: $input) {
            id
            uuid
            message
            created_at
          }
        }
        """

        payload = {
            "query": graphql_query,
            "variables": {
                "input": {
                    "message_verb": "memo",
                    "message": {
                        "ai_model": {
                            "key": "gemini",
                            "value": "gemini-2.5-flash",
                            "name": "Gemini 2.5 Flash",
                            "payment": {
                                "price": 0,
                                "is_locked": False,
                                "free_regeneration": False
                            },
                            "icon": "https://cdn.promptmine.ai/Gemini.png",
                            "isDefault": True,
                            "isNew": True
                        },
                        "nugget": nugget,
                        "title": title,
                        "type": "text-format"
                    },
                    "is_public": 0,
                },
                "parent_id": parent_id,
            },
        }

        response = RequestsUtil.post(payload=payload, auth_token=auth_token)
        if response.status_code == 200:
            data = response.json()
            return json.dumps({"success": True, "data": data})
        else:
            return json.dumps(
                {
                    "success": False,
                    "status_code": response.status_code,
                    "error": response.text,
                }
            )

    def fetch_creator_profile(self, key: str) -> object:
        """
        Fetch a random creator profile from the Kanvas API.

        Returns:
          object: Profiles of users
        """
        kanvas_auth = self.login()
        if not kanvas_auth:
            return json.dumps({"success": False, "error": "Authentication failed"})
        auth_token = (
            json.loads(kanvas_auth).get("data", {}).get("login", {}).get("token")
        )
        if not auth_token:
            return json.dumps(
                {"success": False, "error": "Authentication token not found"}
            )

        # Create an endpoint in Kanvas API to fetch a random creator profile
        graphql_query = """
        query adminAppSetting($key: String!) {
          adminAppSetting(key: $key)
        }
        """

        payload = {
            "query": graphql_query,
            "variables": {
                "key": key
            }
        }

        response = RequestsUtil.post(payload=payload, auth_token=auth_token, withapp_key=True)
        data = response.json()
        return json.dumps(data)
    
    def fetch_random_profile(self) -> dict:
      """_summary_
        Get a random profile bio from the social-creator-agents apps_settings for Promptmine
      Returns:
          str: bio of the profile
      """
      profiles = self.fetch_creator_profile(self.SOCIAL_CREATOR_AGENTS_KEY)
      profile_object = json.loads(profiles).get('data',{}).get('adminAppSetting')

      # Get the current hour
      current_hour = datetime.now().hour
      for profile in profile_object:
          if profile['activeHour'] == current_hour:
              return {"bio": profile['bio'], "email": profile['email'], "password": profile['password']}

      return {"bio": "No profile for this hour"}


