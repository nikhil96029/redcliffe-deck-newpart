import subprocess, os, sys, time, json, base64, tempfile
from pathlib import Path
from PIL import Image
import io

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
HTML_FILE = Path(__file__).parent / "deck_v6_direct.html"
OUTPUT_PDF = Path(__file__).parent / "redcliffe_deck.pdf"
SLIDE_COUNT = 8
WIDTH, HEIGHT = 1920, 1080

# We drive Chrome via the DevTools remote debugging protocol
import urllib.request, urllib.error

def chrome_cmd(ws_url, method, params=None):
    import json, socket
    # Use a simple HTTP GET to the JSON endpoint then WebSocket for commands
    pass

def take_screenshot_via_cdp(port, slide_index):
    """Navigate to slide and capture screenshot via CDP."""
    import json, urllib.request, websocket  # websocket-client may not be available
    pass

# Simpler approach: generate per-slide HTML files and screenshot each
def make_slide_html(slide_index):
    """Create a standalone HTML that shows exactly one slide, fully resolved."""
    src = HTML_FILE.read_text(encoding="utf-8")

    # Extract the slide template IDs in order from the JS array
    import re
    slide_match = re.search(r'const slides\s*=\s*\[(.*?)\];', src, re.DOTALL)
    template_ids = re.findall(r"templateId:\s*'([^']+)'", slide_match.group(1))
    tid = template_ids[slide_index]

    # Extract that template's inner HTML
    tmpl_match = re.search(
        r'<template id="' + re.escape(tid) + r'">(.*?)</template>',
        src, re.DOTALL
    )
    inner_html = tmpl_match.group(1)

    # Rewrite relative src/href to absolute file:// URIs so Chrome finds assets from temp dir
    base = HTML_FILE.parent.as_uri() + "/"
    inner_html = re.sub(r'src="(?!https?://|data:)([^"]+)"', lambda m: f'src="{base}{m.group(1)}"', inner_html)
    inner_html = re.sub(r"src='(?!https?://|data:)([^']+)'", lambda m: f"src='{base}{m.group(1)}'", inner_html)

    # Build a self-contained page (preserving Google Fonts link from head)
    fonts_match = re.search(r'(<link[^>]+fonts\.googleapis[^>]+>)', src)
    fonts_tag = fonts_match.group(1) if fonts_match else ""

    page = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"/>
{fonts_tag}
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html, body {{ width:1920px; height:1080px; overflow:hidden; }}
</style>
</head>
<body>
{inner_html}
</body>
</html>"""
    return page

def screenshot_slide(slide_index, tmp_dir):
    html_content = make_slide_html(slide_index)
    html_path = Path(tmp_dir) / f"slide_{slide_index}.html"
    html_path.write_text(html_content, encoding="utf-8")
    png_path = Path(tmp_dir) / f"slide_{slide_index}.png"

    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--hide-scrollbars",
        f"--window-size={WIDTH},{HEIGHT}",
        f"--screenshot={png_path}",
        html_path.as_uri(),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    if not png_path.exists():
        print(f"  ERROR on slide {slide_index}: {result.stderr.decode()[:300]}")
        return None
    return str(png_path)

def main():
    print(f"Generating PDF for {SLIDE_COUNT} slides...")
    images = []
    with tempfile.TemporaryDirectory() as tmp_dir:
        for i in range(SLIDE_COUNT):
            print(f"  Capturing slide {i+1}/{SLIDE_COUNT}...", end=" ", flush=True)
            png = screenshot_slide(i, tmp_dir)
            if png:
                img = Image.open(png).convert("RGB")
                images.append(img)
                print("OK")
            else:
                print("FAILED")

    if not images:
        print("No slides captured. Exiting.")
        sys.exit(1)

    first, rest = images[0], images[1:]
    first.save(
        str(OUTPUT_PDF),
        save_all=True,
        append_images=rest,
        resolution=150,
    )
    print(f"\nDone! PDF saved to: {OUTPUT_PDF}")

if __name__ == "__main__":
    main()
