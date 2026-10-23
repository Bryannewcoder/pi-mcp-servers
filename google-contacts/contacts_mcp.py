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

def people_api(path, params=None):
    token = get_access_token()
    url = f"https://people.googleapis.com/v1/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    return json.loads(urllib.request.urlopen(req).read())

mcp = FastMCP("google-contacts")

@mcp.tool()
def search_contacts(query: str) -> str:
    """Search Google Contacts by name or email"""
    result = people_api("people:searchContacts", {
        "query": query,
        "readMask": "names,emailAddresses,phoneNumbers"
    })
    results = result.get("results", [])
    if not results:
        return "No contacts found."
    out = []
    for r in results:
        p = r.get("person", {})
        resource = p.get("resourceName", "unknown")
        name = p.get("names", [{}])[0].get("displayName", "Unknown")
        emails = [e["value"] for e in p.get("emailAddresses", [])]
        phones = [ph["value"] for ph in p.get("phoneNumbers", [])]
        out.append(f"{resource} | {name} | {', '.join(emails)} | {', '.join(phones)}")
    return "\n".join(out)

@mcp.tool()
def list_contacts(page_size: int = 20) -> str:
    """List Google Contacts"""
    result = people_api("people/me/connections", {
        "personFields": "names,emailAddresses,phoneNumbers",
        "pageSize": page_size
    })
    connections = result.get("connections", [])
    if not connections:
        return "No contacts found."
    out = []
    for p in connections:
        resource = p.get("resourceName", "unknown")
        name = p.get("names", [{}])[0].get("displayName", "Unknown")
        emails = [e["value"] for e in p.get("emailAddresses", [])]
        phones = [ph["value"] for ph in p.get("phoneNumbers", [])]
        out.append(f"{resource} | {name} | {', '.join(emails)} | {', '.join(phones)}")
    return "\n".join(out)


@mcp.tool()
def create_contact(name: str, phone: str = "", email: str = "") -> str:
    """Create a new Google Contact"""
    token = get_access_token()
    body = {"names": [{"givenName": name}]}
    if phone:
        body["phoneNumbers"] = [{"value": phone}]
    if email:
        body["emailAddresses"] = [{"value": email}]
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        "https://people.googleapis.com/v1/people:createContact",
        data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    created_name = resp.get("names", [{}])[0].get("displayName", name)
    return f"Contact created: {created_name}"

@mcp.tool()
def update_contact(resource_name: str, name: str = "", phone: str = "", email: str = "") -> str:
    """Update an existing Google Contact by resource name (e.g. people/c12345)"""
    token = get_access_token()
    # First get current etag
    url = f"https://people.googleapis.com/v1/{resource_name}?personFields=names,phoneNumbers,emailAddresses"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    current = json.loads(urllib.request.urlopen(req).read())
    etag = current.get("etag", "")
    body = {"etag": etag, "names": [{"givenName": name}] if name else current.get("names", [])}
    if phone:
        body["phoneNumbers"] = [{"value": phone}]
    if email:
        body["emailAddresses"] = [{"value": email}]
    update_fields = ",".join(["names"] + (["phoneNumbers"] if phone else []) + (["emailAddresses"] if email else []))
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"https://people.googleapis.com/v1/{resource_name}:updateContact?updatePersonFields={update_fields}",
        data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="PATCH"
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    updated_name = resp.get("names", [{}])[0].get("displayName", resource_name)
    return f"Contact updated: {updated_name}"

@mcp.tool()
def delete_contact(resource_name: str) -> str:
    """Delete a Google Contact by resource name (e.g. people/c12345)"""
    token = get_access_token()
    req = urllib.request.Request(
        f"https://people.googleapis.com/v1/{resource_name}:deleteContact",
        data=b"",
        headers={"Authorization": f"Bearer {token}"},
        method="DELETE"
    )
    urllib.request.urlopen(req)
    return f"Contact deleted: {resource_name}"
if __name__ == "__main__":
    mcp.run()
