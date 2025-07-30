# tap-sharepoint

`tap-sharepoint` is a Singer tap for Microsoft Sharepoint, build to be used with the Hotglue widget.

`tap-sharepoint` can be run on [Hotglue](https://hotglue.com), an embedded integration platform for running ETL jobs.

The tap is capable of downloading files from a given Sharepoint drive using OAuth credentials.

## Configuration

In the `config.json`, the Tap expects the four oauth fields:
```
    "client_id": "abc123-fff-4aae-9936-aaaafg3423",
    "client_secret": "00000000-0000-0000-0000-000000000000",
    "refresh_token": "1.AWMB9P5nxw",
    "access_token": "eyJ0eXAiOiJHQTg",
```

3 fields configuring which Sharepoint files we should access:

```
    "tenant_name": "coldglue",
    "site_name": "mysite",
    "drive_name": "Documents",
```

The files that you want to download:
```json
    "files": [
        {
            "name": "data.txt",
            "id": "01OFQPGGPI5AFETI6CANFZWSZW37YRUIR6"
        }
    ],
```

And the directory to download the files to:
```json
"target_dir": "/Users/..../outputfiles"
```

You can optionally specify a `start_date` to fetch only files that have been modified since a given data:
```json
"start_date": "2005-01-01T00:00:00Z",
```

