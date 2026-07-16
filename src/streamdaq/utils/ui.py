import os
import urllib.request


def _is_ui_up() -> bool:
    ui_url = os.getenv("STREAMDAQ_UI_URL")
    urls = [ui_url] if ui_url else ["http://127.0.0.1:5173"]
    for url in urls:
        try:
            with urllib.request.urlopen(url, timeout=0.5):
                return True
        except Exception:
            continue
    return False
