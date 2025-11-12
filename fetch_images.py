"""
Script to fetch images from Brown University Library API.
"""

import argparse
import json
import sys, os
import pathlib
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

from tqdm import tqdm


def fetch_parent_data(pid: str) -> dict:
    """
    Fetch item data from Brown University Library API.
    
    Args:
        pid: The persistent identifier for the item
        
    Returns:
        dict: JSON response from the API
        
    Raises:
        HTTPError: If the API request fails
        URLError: If there's a network issue
        json.JSONDecodeError: If the response is not valid JSON
    """
    url = f"https://repository.library.brown.edu/api/items/{pid}/"
    
    try:
        with urlopen(url) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data
    except HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}", file=sys.stderr)
        raise
    except URLError as e:
        print(f"URL Error: {e.reason}", file=sys.stderr)
        raise
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}", file=sys.stderr)
        raise

def get_child_pids(parent_data: dict) -> list[tuple]:
    """
    Extract child PIDs from parent data returned by the API.

    Args:
        parent_data: The JSON data of the parent item

    Returns:
        list: A list of tuples containing child PIDs and their page numbers
    """
    relations = parent_data.get('relations')
    if not relations:
        raise ValueError("No relations found in parent data.")
    children = relations.get('hasPart')
    if not children:
        raise ValueError("No child items found in parent data.")
    child_pids_and_pages = [ (child.get('pid'), child.get('order')) for child in children if child.get('pid') and child.get('order') is not None]
    if not child_pids_and_pages or len(child_pids_and_pages) == 0:
        raise ValueError("No valid child PIDs found.")
    print(f"Found {len(child_pids_and_pages)} child PIDs.")
    return child_pids_and_pages

def download_image(image_url: str, output_path: str):
    """
    Download an image from a given URL and save it to the specified path.

    Args:
        image_url: The URL of the image to download
        output_path: The file path to save the downloaded image
    """
    # Skip existing files
    if os.path.exists(output_path):
        print(f"Image already exists at {output_path}, skipping download.")
        return

    try:
        with urlopen(image_url) as response:
            with open(output_path, 'wb') as out_file:
                out_file.write(response.read())
        # print(f"Image downloaded to {output_path}")
    except Exception as e:
        print(f"Failed to download image from {image_url}: {e}", file=sys.stderr)
        raise

def download_images_for_children(child_pids: list, output_dir: str):
    """
    Download images for each child PID.

    Args:
        child_pids: List of child PIDs
        output_dir: Directory to save downloaded images
    """

    for pid, page in tqdm(child_pids):
        # pad the page number to 4 digits
        page = str(page).zfill(4)
        try:
            image_url = f'https://repository.library.brown.edu/iiif/image/{pid}/full/!800,800/0/default.jpg'
            output_path = f"{output_dir}/{page}.jpg"
            download_image(image_url, output_path)
        except Exception as e:
            print(f"Error processing PID {pid}: {e}", file=sys.stderr)
            raise

def main():
    """Main function to handle command line arguments and fetch data."""
    parser = argparse.ArgumentParser(
        description="Fetch item data from Brown University Library API"
    )
    parser.add_argument(
        "pid",
        help="Persistent identifier for the item to fetch"
    )
    parser.add_argument(
        "output",
        help="Output directory to save downloaded images"
    )
    
    args = parser.parse_args()

    if not args.pid.strip():
        print("Error: PID cannot be empty.", file=sys.stderr)
        sys.exit(1)

    output_dir = pathlib.Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Fetch the data
        data = fetch_parent_data(args.pid)
        
        # Get child PIDs
        child_pids = get_child_pids(data)

        # Download images for child PIDs
        download_images_for_children(child_pids, str(output_dir))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()