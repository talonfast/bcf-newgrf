"""Re-render a set's gfx/ only when the contents of its inputs changed.

    python tools/render_if_changed.py OUTPUT.json SCRIPT [INPUT ...]
    python tools/render_if_changed.py --stamp OUTPUT.json SCRIPT [INPUT ...]

make compares file times, and a git checkout gives every file a new one, so make alone would re-render
every set after a fresh clone or a pull. This keeps a hash of the script and the inputs in
OUTPUT.json.inputs (committed next to it): when the hash matches, the render is skipped and OUTPUT is
only touched; otherwise SCRIPT runs and the stamp is rewritten. --stamp writes the stamp without
rendering (for gfx/ that is known to match its inputs).
"""

import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def inputs_hash(files):
    h = hashlib.sha1()
    for path in sorted(set(files)):
        h.update(os.path.relpath(os.path.abspath(path), ROOT).encode() + b"\0")
        with open(path, "rb") as f:
            h.update(hashlib.sha1(f.read()).digest())
    return h.hexdigest()


def main():
    args = sys.argv[1:]
    stamp_only = "--stamp" in args
    if stamp_only:
        args.remove("--stamp")
    output, script, *inputs = args
    stamp = output + ".inputs"
    digest = inputs_hash([script] + inputs)
    if not stamp_only:
        if os.path.exists(output) and os.path.exists(stamp):
            with open(stamp) as f:
                if f.read().strip() == digest:
                    os.utime(output)
                    print(f"{os.path.relpath(output, ROOT)}: inputs unchanged, not re-rendering")
                    return
        subprocess.run([sys.executable, script], check=True)
    with open(stamp, "w") as f:
        f.write(digest + "\n")


if __name__ == "__main__":
    main()
