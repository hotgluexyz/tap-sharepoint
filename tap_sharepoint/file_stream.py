"""Stream type classes for tap-sharepointsites."""

import datetime
import os
import typing as t
from functools import cached_property
import logging

import requests
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from tap_sharepoint.auth import TapSharepointAuth


class FilesStream():
    """Define custom stream."""

    def __init__(self, config, state, config_file_path):
        self.config = config
        self.state = state
        self.logger = logging.getLogger(__name__)
        self.auth = TapSharepointAuth(config, config_file_path)

        if not config.get("site_name"):
            raise ValueError("site_name is required")
        if not config.get("tenant_name"):
            raise ValueError("tenant_name is required")
        
        self.site_id = self.get_site_id(config["site_name"])
        if not config.get("drive_name"):
            raise ValueError("drive_name is required")
        
        self.drive_id = self.get_drive_id(self.site_id, config["drive_name"])

        if not config.get("target_dir"):
            raise ValueError("target_dir is required")
        self.target_dir = config["target_dir"]

    def make_request(self, url, method="GET", params=None):
        self.auth.update_access_token()
        headers = {
            "Authorization": f"Bearer {self.auth.access_token}",
            "Content-Type": "application/json",
        }
        response = requests.request(method, url, headers=headers, params=params)
        return response
    
    def get_site_id(self):
        url = f"https://graph.microsoft.com/v1.0/sites/{self.config['tenant_name']}.sharepoint.com:/sites/{self.config['site_name']}"
        response = self.make_request(url)
        return response.json()["id"]

    def get_drive_id(self, site_id, drive_name):
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        response = self.make_request(url)
        drives = response.json()["value"]
        drive = next((drive for drive in drives if drive["name"] == drive_name), None)
        if not drive:
            raise ValueError(f"Drive {drive_name} not found")
        return drive["id"]
    
    def get_file_metadata(self, file_id):
        url = f"https://graph.microsoft.com/v1.0/drives/{self.drive_id}/items/{file_id}"
        response = self.make_request(url)
        return response.json()
    
    def download_file(self, file_id, file_name):
        url = f"https://graph.microsoft.com/v1.0/drives/{self.drive_id}/items/{file_id}/content"
        response = self.make_request(url, method="GET")
        with open(os.path.join(self.target_dir, file_name), "wb") as f:
            f.write(response.content)

    def sync(self):
        for file in self.config["files"]:
            file_metadata = self.get_file_metadata(file["id"])
            bookmark = self.get_bookmark(file["name"])

            if bookmark is None or file_metadata["lastModifiedDateTime"] > bookmark:
                self.download_file(file["id"], file["name"])
            else:
                self.logger.info(f"File {file['name']} is up to date")

    def get_bookmark(self, file_name):
        return self.config.get("start_date", None)
    
    