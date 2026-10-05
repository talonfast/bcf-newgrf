"""Build, package, install and publish releases.

    python tools/release.py [set ...] [--install] [--upload] [--notes "text"] [--repo owner/name]

1. builds the GRFs (python build.py),
2. packages releases/<release>-v<VERSION>.tar per set (GRF, readme, changelog, license),
3. --install: copies the tars into OpenTTD's newgrf folder ($OPENTTD_NEWGRF, or
   ~/Documents/OpenTTD/newgrf),
4. --upload: creates (or updates) the GitHub release <release>-v<VERSION> per set on the repository of
   the "origin" remote (or --repo) and uploads the tar. Re-running with the same VERSION replaces that
   release's tar. Authentication uses the GitHub credentials stored for git (git credential fill).
   Upload refuses to run from a working tree with uncommitted changes, from a commit that isn't
   pushed to origin, or when the release already exists at a different commit (bump VERSION).

Releases are made locally, not by GitHub Actions. Bump the set's VERSION in its src/build_<set>.py and
add a line to its CHANGELOG.txt first.
"""

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import build  # noqa: E402

RELEASES = os.path.join(ROOT, "releases")


def package(name):
    folder, _, grf, rel, _ = build.SETS[name]
    stem = f"{rel}-v{build.version(name)}"
    os.makedirs(RELEASES, exist_ok=True)
    path = os.path.join(RELEASES, stem + ".tar")
    files = [(build.grf_path(name), grf), (os.path.join(ROOT, "README.md"), "readme.txt"),
             (os.path.join(ROOT, folder, "CHANGELOG.txt"), "changelog.txt"),
             (os.path.join(ROOT, "LICENSE.txt"), "license.txt")]
    with tarfile.open(path, "w", format=tarfile.USTAR_FORMAT) as tar:
        for src, arcname in files:
            info = tar.gettarinfo(src, f"{stem}/{arcname}")
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mode = 0o644
            with open(src, "rb") as f:
                tar.addfile(info, f)
    print(f"packaged {os.path.relpath(path, ROOT)} ({os.path.getsize(path) / 1e6:.1f} MB)")
    return path


def install(paths, target):
    os.makedirs(target, exist_ok=True)
    for path in paths:
        shutil.copy2(path, os.path.join(target, os.path.basename(path)))
        print(f"installed {os.path.join(target, os.path.basename(path))}")
        rel = os.path.basename(path).rsplit("-v", 1)[0]
        older = [p for p in glob.glob(os.path.join(target, rel + "-v*.tar")) if os.path.basename(p) != os.path.basename(path)]
        if older:
            print(f"  note: older version(s) still installed: {', '.join(os.path.basename(p) for p in older)}")


def github_token() -> str:
    out = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
                         capture_output=True, text=True, check=True, cwd=ROOT).stdout
    fields = dict(line.split("=", 1) for line in out.splitlines() if "=" in line)
    if not fields.get("password"):
        raise SystemExit("no GitHub credentials stored for git (git credential fill); "
                         "log in with gh auth login")
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
        if e.code == 404 and method == "GET":
            return None
        raise RuntimeError(f"{method} {url}: {e.code} {e.read().decode(errors='replace')}") from e


def origin_repo():
    url = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True, check=True,
                         cwd=ROOT).stdout.strip()
    m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
    if not m:
        raise SystemExit(f"origin ({url}) is not a GitHub repository; use --repo owner/name")
    return m.group(1)


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True, cwd=ROOT).stdout.strip()


def remote_tag_commit(tag):
    """Commit the tag points to on origin, or None."""
    out = git("ls-remote", "--tags", "origin", f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}")
    refs = dict(reversed(line.split("\t")) for line in out.splitlines())
    return refs.get(f"refs/tags/{tag}^{{}}") or refs.get(f"refs/tags/{tag}")


def check_upload(names):
    """Fail before building if the releases wouldn't match a pushed commit. Returns HEAD."""
    if git("status", "--porcelain"):
        raise SystemExit("--upload: the working tree has uncommitted changes; commit (and push) them first")
    head = git("rev-parse", "HEAD")
    git("fetch", "--quiet", "origin")
    if not git("branch", "-r", "--contains", head):
        raise SystemExit("--upload: HEAD is not on any branch of origin; push it first")
    for name in names:
        tag = f"{build.SETS[name][3]}-v{build.version(name)}"
        at = remote_tag_commit(tag)
        if at and at != head:
            raise SystemExit(f"--upload: {tag} already exists at {at[:7]}, not HEAD {head[:7]}; "
                             f"bump VERSION in {build.SETS[name][0]}/{build.SETS[name][4]}")
    return head


def upload(name, path, repo, notes, token, head):
    rel_name = build.SETS[name][3]
    tag = f"{rel_name}-v{build.version(name)}"
    base = f"https://api.github.com/repos/{repo}"
    rel = api("GET", f"{base}/releases/tags/{tag}", token)
    if rel is None:
        rel = api("POST", f"{base}/releases", token, {
            "tag_name": tag, "target_commitish": head, "name": tag,
            "body": notes or f"{tag}. Drop the tar, as-is, into your OpenTTD newgrf folder.",
        })
        print(f"created release {tag}")
    elif notes:
        api("PATCH", f"{base}/releases/{rel['id']}", token, {"body": notes})
    asset_name = os.path.basename(path)
    for asset in rel.get("assets", []):
        if asset["name"] == asset_name:
            api("DELETE", f"{base}/releases/assets/{asset['id']}", token)
    with open(path, "rb") as f:
        api("POST", rel["upload_url"].split("{")[0] + f"?name={asset_name}", token, f.read(),
            content_type="application/x-tar")
    print(f"uploaded {asset_name} to {rel['html_url']}")


def main():
    ap = argparse.ArgumentParser(description="Build, package, install and publish releases.")
    ap.add_argument("sets", nargs="*", metavar="set",
                    help=f"sets to release (default: all): {', '.join(build.SETS)}")
    ap.add_argument("--install", action="store_true", help="copy the tars into OpenTTD's newgrf folder")
    ap.add_argument("--install-dir",
                    help="newgrf folder (default: $OPENTTD_NEWGRF or ~/Documents/OpenTTD/newgrf)")
    ap.add_argument("--upload", action="store_true", help="create or update the GitHub releases")
    ap.add_argument("--notes", default="", help="release notes")
    ap.add_argument("--repo", help="owner/name (default: the origin remote)")
    args = ap.parse_args()
    names = args.sets or list(build.SETS)
    unknown = [n for n in names if n not in build.SETS]
    if unknown:
        ap.error(f"unknown set(s) {', '.join(unknown)}; sets: {', '.join(build.SETS)}")
    target = args.install_dir or os.environ.get("OPENTTD_NEWGRF") or os.path.join(
        os.path.expanduser("~"), "Documents", "OpenTTD", "newgrf")

    head = check_upload(names) if args.upload else None
    build.build(names)
    paths = {name: package(name) for name in names}
    if args.install:
        install(paths.values(), target)
    if args.upload:
        token = github_token()
        repo = args.repo or origin_repo()
        for name in names:
            upload(name, paths[name], repo, args.notes, token, head)


if __name__ == "__main__":
    main()
