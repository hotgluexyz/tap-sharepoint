"""TapSharepoint Authentication."""


import json
import requests
from datetime import datetime
import logging


class TapSharepointAuth():
    """Authenticator class for TapSharepoint."""

    auth_endpoint = "https://login.microsoftonline.com/common/oauth2/token"
    last_refreshed = None
    
    def __init__(
        self,
        config: dict,
        config_file_path: str
    ) -> None:
        self.config = config
        self.access_token = config.get("access_token", None)
        self.expires_in = config.get("expires_in", None)
        self.logger = logging.getLogger("tap-sharepoint")
        self.config_file_path = config_file_path

    @property
    def oauth_request_body(self) -> dict:
        """Define the OAuth request body for the TapSharepoint API."""
        # TODO: Define the request body needed for the API.
        return {
            # 'resource': 'https://login.microsoftonline.com/common/oauth2/token',
            "client_id": self.config["client_id"],
            "client_secret": self.config["client_secret"],
            "refresh_token": self.config["refresh_token"],
            "grant_type": "refresh_token",
        }

    def is_token_valid(self) -> bool:
        """Check if token is valid.

        Returns:
            True if the token is valid (fresh).
        """
        if self.expires_in is not None:
            self.expires_in = int(self.expires_in)
        if self.last_refreshed is None:
            return False
        if not self.expires_in:
            return True
        if self.expires_in > (datetime.now() - self.last_refreshed).total_seconds():
            return True
        return False



    # Authentication and refresh
    def update_access_token(self) -> None:
        """Update `access_token` along with: `last_refreshed` and `expires_in`.

        Raises:
            RuntimeError: When OAuth login fails.
        """
        request_time = datetime.now()
        auth_request_payload = self.oauth_request_body
        token_response = requests.post(self.auth_endpoint, data=auth_request_payload)
        try:
            token_response.raise_for_status()
            self.logger.info("OAuth authorization attempt was successful.")
        except Exception as ex:
            raise RuntimeError(
                f"Failed OAuth login, response was '{token_response.json()}'. {ex}"
            )
        token_json = token_response.json()
        self.access_token = token_json["access_token"]
        self.expires_in = token_json.get("expires_in", 10)
        if self.expires_in is None:
            self.logger.debug(
                "No expires_in receied in OAuth response and no "
                "default_expiration set. Token will be treated as if it never "
                "expires."
            )
        self.last_refreshed = request_time

        # store access_token in config file
        self.config["access_token"] = token_json["access_token"]
        self.config["refresh_token"] = token_json["refresh_token"]

        with open(self.config_file_path, "w") as outfile:
            json.dump(self.config, outfile, indent=4)

    def get_access_token(self):
        if not self.is_token_valid():
            self.update_access_token()
        return self.access_token