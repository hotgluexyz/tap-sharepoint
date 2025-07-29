"""Stream type classes for tap-sharepointsites."""

import json
import os
import logging
from datetime import datetime

import requests
from tap_sharepoint.auth import TapSharepointAuth


class FilesStream():
    """Define custom stream."""

    def __init__(self, config, state, config_file_path, state_file_path):
        self.config = config
        self.state = state
        self.state_file_path = state_file_path
        self.logger = logging.getLogger("tap-sharepoint")
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self.auth = TapSharepointAuth(config, config_file_path)

        if not config.get("site_name"):
            raise ValueError("site_name is required")
        if not config.get("tenant_name"):
            raise ValueError("tenant_name is required")
        
        self.site_id = self.get_site_id()
        if not config.get("drive_name"):
            raise ValueError("drive_name is required")
        
        self.drive_id = self.get_drive_id(self.site_id, config["drive_name"])

        if not config.get("target_dir"):
            raise ValueError("target_dir is required")
        self.target_dir = config["target_dir"]

    def make_request(self, url, method="GET", params=None):
        self.logger.info(f"Making request to {url}")
        headers = {
            "Authorization": f"Bearer {self.auth.get_access_token()}",
            "Content-Type": "application/json",
        }
        response = requests.request(method, url, headers=headers, params=params)
        return response
    
    def list_files(self, folder_id):
        if folder_id:
            url = f"https://graph.microsoft.com/v1.0/drives/{self.drive_id}/items/{folder_id}/children"
        else:
            url = f"https://graph.microsoft.com/v1.0/drives/{self.drive_id}/root/children"
        response = self.make_request(url)
        return response.json()["value"]
    
    def raise_for_status(self, response):
        if response.status_code == 404:
            raise ValueError(response.json().get("message", f"Something went wrong with the request: {response.text}"))
        
        if response.status_code == 400:
            raise ValueError(response.json().get("message", f"Something went wrong with the request: {response.text}"))
    
    def get_site_id(self):
        url = f"https://graph.microsoft.com/v1.0/sites/{self.config['tenant_name']}.sharepoint.com:/sites/{self.config['site_name']}"
        response = self.make_request(url)
        self.raise_for_status(response)
        return response.json()["id"]

    def get_drive_id(self, site_id, drive_name):
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        response = self.make_request(url)
        self.raise_for_status(response)
        drives = response.json()["value"]
        drive = next((drive for drive in drives if drive["name"] == drive_name), None)
        if not drive:
            raise ValueError(f"Drive {drive_name} not found")
        return drive["id"]
    
    def get_file_metadata(self, file_id):
        url = f"https://graph.microsoft.com/v1.0/drives/{self.drive_id}/items/{file_id}"
        response = self.make_request(url)
        self.raise_for_status(response)
        return response.json()
    
    def download_file(self, file_id, file_name):
        url = f"https://graph.microsoft.com/v1.0/drives/{self.drive_id}/items/{file_id}/content"
        response = self.make_request(url, method="GET")
        self.raise_for_status(response)
        with open(os.path.join(self.target_dir, file_name), "wb") as f:
            f.write(response.content)

    def sync(self):
        files_to_sync = self.config["files"]
        for file in files_to_sync:
            file_metadata = self.get_file_metadata(file["id"])
            bookmark = self.get_bookmark(file["id"])

            is_folder = file_metadata.get("folder")

            if self.file_has_been_modified(file_metadata, bookmark):
                if is_folder:
                    files_to_sync.extend(self.list_files(file["id"]))
                    self.logger.info(f"Folder {file['name']} is modified - fetching new version")
                    continue
                
                self.logger.info(f"File {file['name']} is modified - fetching new version")
                self.download_file(file["id"], file["name"])
                self.update_bookmark(file["id"], {
                    "replication_key_value": file_metadata["lastModifiedDateTime"],
                    "replication_key": "lastModifiedDateTime"
                })
            else:
                self.logger.info(f"File {file['name']} is up to date")

    def get_bookmark(self, file_id):
        start_date = self.config.get("start_date", None)
        return self.state.get("bookmarks", {}).get(file_id, {}).get("replication_key_value", None) or start_date
        
    def update_bookmark(self, file_id, bookmark):
        if self.state_file_path:
            self.state["bookmarks"][file_id] = bookmark
            with open(self.state_file_path, "w") as f:
                json.dump(self.state, f)
    
    def file_has_been_modified(self, file_metadata, bookmark):
        if not bookmark:
            return True
        
        # Handle datetime parsing with flexible format
        last_modified_str = file_metadata["lastModifiedDateTime"]
        
        # Parse datetime without microseconds since SharePoint returns format like '2025-07-14T20:49:42Z'
        parsed_last_modified_date = datetime.strptime(last_modified_str, "%Y-%m-%dT%H:%M:%SZ")

        parsed_bookmark = datetime.strptime(bookmark, "%Y-%m-%dT%H:%M:%SZ")
        
        return parsed_last_modified_date > parsed_bookmark
    
    