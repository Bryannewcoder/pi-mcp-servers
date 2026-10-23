#!/usr/bin/env python3
import json, urllib.request, urllib.parse, os
from mcp.server.fastmcp import FastMCP

TOKEN_FILE = os.path.expanduser("~/.config/google-docs-mcp/token.json")
def _load_google_pair():
    _env = {}
    for _line in open(os.path.expanduser("~/services/secrets/google.env")):
        if "=" in _line:
            _k, _v = _line.strip().split("=", 1)
            _env[_k] = _v
    return _env["GOOGLE_CLIENT_ID"], _env["GOOGLE_CLIENT_SECRET"]
CLIENT_ID, CLIENT_SECRET = _load_google_pair()


def get_access_token():
    t = json.load(open(TOKEN_FILE))
    data = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": t["refresh_token"],
        "grant_type": "refresh_token"
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
    resp = json.loads(urllib.request.urlopen(req).read())
    return resp["access_token"]

def gmail_api(method, path, body=None, params=None):
    token = get_access_token()
    url = f"https://gmail.googleapis.com/gmail/v1/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method=method
    )
    resp = urllib.request.urlopen(req).read()
    return json.loads(resp) if resp else {}

mcp = FastMCP("gmail-filters")

@mcp.tool()
def list_filters() -> str:
    """List all Gmail filters currently configured on the account"""
    result = gmail_api("GET", "users/me/settings/filters")
    filters = result.get("filter", [])
    if not filters:
        return "No filters found."
    lines = []
    for f in filters:
        crit = f.get("criteria", {})
        action = f.get("action", {})
        lines.append(f"id={f.get('id')} criteria={crit} action={action}")
    return "\n".join(lines)

@mcp.tool()
def create_filter(
    from_addr: str = "",
    to_addr: str = "",
    subject: str = "",
    query: str = "",
    has_attachment: bool = False,
    add_label_ids: str = "",
    remove_label_ids: str = "",
) -> str:
    """Create a Gmail filter.

    Matching criteria (leave unused ones blank/false):
    - from_addr: sender email/domain to match
    - to_addr: recipient email to match
    - subject: subject line substring to match
    - query: raw Gmail search syntax (combines with other criteria)
    - has_attachment: only match messages with attachments

    Actions (comma-separated label IDs, e.g. "Label_123,TRASH"):
    - add_label_ids: labels to apply (use "TRASH" to auto-delete, "UNREAD" removed = mark read via remove_label_ids)
    - remove_label_ids: labels to strip (e.g. "INBOX" to archive, "UNREAD" to mark read)

    Use list_labels (in google-workspace) first to find custom label IDs.
    """
    criteria = {}
    if from_addr:
        criteria["from"] = from_addr
    if to_addr:
        criteria["to"] = to_addr
    if subject:
        criteria["subject"] = subject
    if query:
        criteria["query"] = query
    if has_attachment:
        criteria["hasAttachment"] = True

    if not criteria:
        return "Error: at least one matching criterion is required (from_addr, to_addr, subject, query, or has_attachment)."

    action = {}
    if add_label_ids:
        action["addLabelIds"] = [x.strip() for x in add_label_ids.split(",") if x.strip()]
    if remove_label_ids:
        action["removeLabelIds"] = [x.strip() for x in remove_label_ids.split(",") if x.strip()]

    if not action:
        return "Error: at least one action is required (add_label_ids and/or remove_label_ids)."

    body = {"criteria": criteria, "action": action}
    result = gmail_api("POST", "users/me/settings/filters", body=body)
    return f"Filter created: id={result.get('id')} criteria={criteria} action={action}"

@mcp.tool()
def delete_filter(filter_id: str) -> str:
    """Delete a Gmail filter by its ID (get IDs from list_filters)"""
    gmail_api("DELETE", f"users/me/settings/filters/{filter_id}")
    return f"Filter deleted: {filter_id}"

if __name__ == "__main__":
    mcp.run()
