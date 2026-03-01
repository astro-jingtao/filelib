import os
import requests


def download_response(url, filename, force=False, verbose=False, timeout=None):

    if not force:
        if os.path.exists(filename):
            if verbose:
                print(f"File {filename} already exists. Skipping download.")
            return

    response = requests.get(url, stream=True, timeout=timeout)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        if verbose:
            print(f"Download completed successfully for {filename}!")
    else:
        if verbose:
            print(f"Failed to download {filename}: {response.status_code}")

    return response.status_code
