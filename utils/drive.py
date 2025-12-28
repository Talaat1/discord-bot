import re

def convert_drive_url(url: str) -> str:
    """
    Convert a Google Drive view/open URL to a direct download URL.
    Supports:
    - drive.google.com/file/d/ID/view... -> drive.google.com/uc?export=download&id=ID
    - drive.google.com/open?id=ID -> drive.google.com/uc?export=download&id=ID
    """
    if not url:
        return url

    # Regex for file/d/ID
    file_id_match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
    if file_id_match:
        file_id = file_id_match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"

    # Regex for open?id=ID
    id_param_match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
    if id_param_match:
        file_id = id_param_match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"

    return url
