import json
import argparse

from tap_sharepoint.file_stream import FilesStream


def load_json(path):
    with open(path) as f:
        return json.load(f)

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("-c", "--config", help="Config file", required=True)

    parser.add_argument("-s", "--state", help="State file", required=False)

    args = parser.parse_args()
    
    if not args.config:
        raise ValueError("Config file is required")

    setattr(args, "config_path", args.config)
    args.config = load_json(args.config)

    if args.state:
        setattr(args, "state_path", args.state)
        args.state = load_json(args.state)
    else:
        setattr(args, "state_path", args.config_path.replace("config.json", "state.json"))

    return args


def main():

    args = parse_args()

    # Sync Files
    if not args.state:
        args.state = {
            "bookmarks": {}
        }
    if not args.state_path:
        args.state_path = None

    files_stream = FilesStream(args.config, args.state, args.config_path, args.state_path)
    files_stream.sync()


if __name__ == "__main__":
    main()
