"""
Build, verify, install and publish a release of PNW Aviation.

    python release.py [--notes "text"]

1. builds build/pnw_aviation.grf and checks it with verify.py,
2. copies it into the local OpenTTD newgrf folder,
3. creates (or updates) the GitHub release v<VERSION> on teagangosling/pnw-aviation and uploads the .grf.

Releases are made on this machine, not by GitHub Actions. Bump VERSION in build.py for every new release;
re-running with the same VERSION replaces that release's .grf. Authentication uses the GitHub credentials
stored for git (git credential fill).
"""

import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import build
import verify

REPO = "teagangosling/pnw-aviation"
ROOT = Path(__file__).resolve().parent.parent
GRF = ROOT / "build" / "pnw_aviation.grf"
OPENTTD_NEWGRF = Path(r"G:\Google Drive\Documents\OpenTTD\newgrf")


def github_token() -> str:
    out = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
                         capture_output=True, text=True, check=True, cwd=ROOT).stdout
    fields = dict(line.split("=", 1) for line in out.splitlines() if "=" in line)
    return fields["password"]


def api(method, url, token, data=None, content_type="application/json"):
    body = data if isinstance(data, (bytes, type(None))) else json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method=method, headers={
        "Authorization": f"token {token}", "Accept": "application/vnd.github+json", "Content-Type": content_type})
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise RuntimeError(f"{method} {url}: {e.code} {e.read().decode(errors='replace')}") from e


def main():
    notes = sys.argv[sys.argv.index("--notes") + 1] if "--notes" in sys.argv else ""
    build.build(GRF)
    verify.main(str(GRF))
    try:
        shutil.copy2(GRF, OPENTTD_NEWGRF / GRF.name)
        print(f"installed {OPENTTD_NEWGRF / GRF.name}")
    except OSError as e:
        print(f"warning: could not install into {OPENTTD_NEWGRF}: {e}")

    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    if dirty:
        print("warning: working tree has uncommitted changes; the release is tagged at the last commit")

    tag = f"v{build.VERSION}"
    token = github_token()
    base = f"https://api.github.com/repos/{REPO}"
    rel = api("GET", f"{base}/releases/tags/{tag}", token)
    if rel is None:
        rel = api("POST", f"{base}/releases", token, {
            "tag_name": tag, "target_commitish": head, "name": f"PNW Aviation {tag}",
            "body": notes or f"PNW Aviation {tag}. Copy pnw_aviation.grf into your OpenTTD newgrf folder.",
        })
        print(f"created release {tag}")
    elif notes:
        api("PATCH", f"{base}/releases/{rel['id']}", token, {"body": notes})
    for asset in rel.get("assets", []):
        if asset["name"] == GRF.name:
            api("DELETE", f"{base}/releases/assets/{asset['id']}", token)
    upload = rel["upload_url"].split("{")[0] + f"?name={GRF.name}"
    api("POST", upload, token, GRF.read_bytes(), content_type="application/octet-stream")
    print(f"uploaded {GRF.name} to {rel['html_url']}")


if __name__ == "__main__":
    main()
