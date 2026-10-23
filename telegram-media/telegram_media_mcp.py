#!/usr/bin/env python3
import json, urllib.request, urllib.parse, os, base64, time
from mcp.server.fastmcp import FastMCP

def _load_telegram_secrets():
    vals = {}
    with open(os.path.expanduser("~/services/secrets/telegram-trouble.env")) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip()
    return vals

_SECRETS = _load_telegram_secrets()
BOT_TOKEN = _SECRETS["TELEGRAM_BOT_TOKEN"]
CHAT_ID = _SECRETS["TELEGRAM_CHAT_ID"]
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

mcp = FastMCP("telegram-media")

def tg_request(endpoint, data):
    url = f"{API_BASE}/{endpoint}"
    data_encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=data_encoded)
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

def wait_for_file(filepath, timeout=5.0, interval=0.2):
    """Poll for filepath to appear, handling the case where a producer
    tool (e.g. ring__get_camera_snapshot) is still writing it when this
    tool is called in parallel rather than after the producer's result."""
    deadline = time.monotonic() + timeout
    while not os.path.exists(filepath):
        if time.monotonic() >= deadline:
            return False
        time.sleep(interval)
    return True

def tg_upload(endpoint, field, filename, filebytes, mimetype, extra={}):
    import http.client
    boundary = "----TelegramBoundary"
    body = b""
    for k, v in {**{"chat_id": CHAT_ID}, **extra}.items():
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{field}\"; filename=\"{filename}\"\r\nContent-Type: {mimetype}\r\n\r\n".encode()
    body += filebytes
    body += f"\r\n--{boundary}--\r\n".encode()
    conn = http.client.HTTPSConnection("api.telegram.org")
    conn.request("POST", f"/bot{BOT_TOKEN}/{endpoint}", body,
        {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    resp = conn.getresponse()
    return json.loads(resp.read())

@mcp.tool()
def send_message(text: str) -> str:
    """Send a text message to the configured chat via Telegram"""
    result = tg_request("sendMessage", {"chat_id": CHAT_ID, "text": text})
    return "Message sent." if result.get("ok") else f"Error: {result}"

@mcp.tool()
def send_photo_file(filepath: str, caption: str = "") -> str:
    """Send a photo from a local file path to the configured chat via Telegram"""
    if not wait_for_file(filepath):
        return f"File not found: {filepath}"
    with open(filepath, "rb") as f:
        filebytes = f.read()
    filename = os.path.basename(filepath)
    extra = {"caption": caption} if caption else {}
    result = tg_upload("sendPhoto", "photo", filename, filebytes, "image/jpeg", extra)
    return "Photo sent." if result.get("ok") else f"Error: {result}"

@mcp.tool()
def send_video_file(filepath: str, caption: str = "") -> str:
    """Send a video from a local file path to the configured chat via Telegram"""
    if not wait_for_file(filepath):
        return f"File not found: {filepath}"
    with open(filepath, "rb") as f:
        filebytes = f.read()
    filename = os.path.basename(filepath)
    extra = {"caption": caption} if caption else {}
    result = tg_upload("sendVideo", "video", filename, filebytes, "video/mp4", extra)
    return "Video sent." if result.get("ok") else f"Error: {result}"

@mcp.tool()
def send_photo_base64(b64data: str, caption: str = "") -> str:
    """Send a photo from base64-encoded data to the configured chat via Telegram"""
    try:
        filebytes = base64.b64decode(b64data)
    except Exception as e:
        return f"Base64 decode error: {e}"
    extra = {"caption": caption} if caption else {}
    result = tg_upload("sendPhoto", "photo", "snapshot.jpg", filebytes, "image/jpeg", extra)
    return "Photo sent." if result.get("ok") else f"Error: {result}"

if __name__ == "__main__":
    mcp.run()
