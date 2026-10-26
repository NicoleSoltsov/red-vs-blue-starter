"""
tools.py  --  the three "hands" the agent uses to interact with the world.

This file is COMPLETE. These are the only things the agent is allowed to do:

    list_files(root)             -> list every .py file under a folder
    read_file(root, path)        -> read a file's contents, with line numbers
    send_request(method, path, data) -> make an HTTP request to the LOCAL app

Each function has safety checks so the agent can only look inside the project
and can only talk to the practice app on localhost.
"""

import os

import requests

# The agent is ONLY ever allowed to talk to this exact host. Any attempt to
# reach anywhere else is refused. This keeps your experiments on your own
# machine.
TARGET_HOST = "http://127.0.0.1:5000"

# The repo root: the folder ABOVE this agent/ folder. This file lives at
# <repo>/agent/tools.py, so going up two levels from __file__ gives <repo>.
# The agent is only ever allowed to look at code inside here.
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Folders we never want to list -- virtual environments, caches, git internals,
# and installed packages. These aren't the project's own code, so skipping them
# keeps the agent focused and its output short.
SKIP_DIRS = {".venv", "venv", "__pycache__", ".git", "node_modules"}


def list_files(root="."):
    """
    Return a sorted list of all .py files under `root` (searched recursively).

    `root` is resolved RELATIVE TO the repo root (BASE), and the result must
    stay inside BASE. If it points outside the repo (e.g. "../.."), we refuse
    and return an error string instead of walking it.

    Paths are returned relative to the repo root so they are short and easy to
    read, e.g. "target_app/app.py".
    """
    target = os.path.abspath(os.path.join(BASE, root))

    # os.path.commonpath lets us confirm `target` really lives inside BASE.
    if os.path.commonpath([BASE, target]) != BASE:
        return "ERROR: that folder is outside the repo. Not allowed."

    # Debug: show exactly which absolute directory we are about to scan, so you
    # can see the agent is staying inside the project (and not wandering into
    # parent folders, .venv, or other repos).
    print("[list_files] walking: " + target)

    found = []
    for dirpath, dirnames, filenames in os.walk(target):
        # Prune unwanted folders in place so os.walk won't descend into them.
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(".py"):
                full = os.path.join(dirpath, name)
                found.append(os.path.relpath(full, BASE))
    return sorted(found)


def read_file(root, path):
    """
    Return the contents of a file, with a line number on each line.

    Safety: `path` is joined onto `root` and we then confirm the final location
    is still INSIDE `root`. This blocks tricks like "../../etc/passwd" that try
    to escape the project folder.
    """
    root = os.path.abspath(root)
    target = os.path.abspath(os.path.join(root, path))

    # os.path.commonpath lets us check that `target` really lives under `root`.
    if os.path.commonpath([root, target]) != root:
        return "ERROR: that path is outside the project folder. Not allowed."

    if not os.path.isfile(target):
        return "ERROR: no such file: " + path

    with open(target, "r", encoding="utf-8") as fh:
        lines = fh.readlines()

    # Number the lines starting at 1 so the agent can report an exact line.
    numbered = []
    for i, line in enumerate(lines, start=1):
        numbered.append(str(i).rjust(4) + ": " + line.rstrip("\n"))
    return "\n".join(numbered)


def send_request(method, path, data=None):
    """
    Make an HTTP request to the LOCAL practice app only.

    method -- "GET" or "POST"
    path   -- the route, e.g. "/login" or "/search?q=mug"
    data   -- a dict sent as JSON on POST requests (ignored for GET)

    Returns a small dict describing the response (status code + body text).
    Refuses anything that is not a GET/POST to TARGET_HOST.
    """
    method = method.upper()
    if method not in ("GET", "POST"):
        return {"error": "only GET and POST are allowed, got: " + method}

    # Make sure the path starts with a slash, then glue it onto our fixed host.
    if not path.startswith("/"):
        path = "/" + path
    url = TARGET_HOST + path

    # Belt-and-suspenders: confirm the final URL really points at our host.
    if not url.startswith(TARGET_HOST):
        return {"error": "refusing to contact anything other than " + TARGET_HOST}

    try:
        if method == "GET":
            resp = requests.get(url, timeout=10)
        else:
            resp = requests.post(url, json=(data or {}), timeout=10)
    except requests.RequestException as exc:
        return {"error": "request failed: " + str(exc)}

    return {"status": resp.status_code, "body": resp.text}
