"""Build, package, install and publish releases.

    python tools/release.py [set ...] [--install] [--upload] [--notes "text"] [--repo owner/name]

1. builds the GRFs (python build.py),
2. packages releases/<release>-v<VERSION>.tar per set (GRF, readme, changelog, license),
3. --install: copies the tars into OpenTTD's newgrf folder ($OPENTTD_NEWGRF, or
   ~/Documents/OpenTTD/newgrf),
4. --upload: creates (or updates) the GitHub release <release>-v<VERSION> per set on the repository of
   the "origin" remote (or --repo) and uploads the tar. Re-running with the same VERSION replaces that
   release's tar. Authentication uses the GitHub credentials stored for git (git credential fill).

Releases are made locally, not by GitHub Actions. Bump the set's VERSION in its src/build_<set>.py and
add a line to its CHANGELOG.txt first.
"""

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


def origin_repo():
    url = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True, check=True,
                         cwd=ROOT).stdout.strip()
    m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
    if not m:
        raise SystemExit(f"origin ({url}) is not a GitHub repository; use --repo owner/name")
    return m.group(1)


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
    args = sys.argv[1:]

    def option(flag):
        if flag in args:
            i = args.index(flag)
            value = args[i + 1]
            del args[i:i + 2]
            return value
        return None

    notes = option("--notes") or ""
    repo = option("--repo")
    target = option("--install-dir") or os.environ.get("OPENTTD_NEWGRF") or os.path.join(
        os.path.expanduser("~"), "Documents", "OpenTTD", "newgrf")
    do_install, do_upload = "--install" in args, "--upload" in args
    names = [a for a in args if not a.startswith("--")] or list(build.SETS)
    unknown = [n for n in names if n not in build.SETS]
    if unknown:
        sys.exit(f"unknown set(s) {', '.join(unknown)}; sets: {', '.join(build.SETS)}")

    build.build(names)
    paths = {name: package(name) for name in names}
    if do_install:
        install(paths.values(), target)
    if do_upload:
        head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
        if subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=ROOT).stdout.strip():
            print("warning: working tree has uncommitted changes; the releases are tagged at the last commit")
        token = github_token()
        repo = repo or origin_repo()
        for name in names:
            upload(name, paths[name], repo, notes, token, head)


if __name__ == "__main__":
    main()
