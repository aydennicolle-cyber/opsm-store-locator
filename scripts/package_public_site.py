#!/usr/bin/env python3
"""Prepare a reviewed, explicitly enumerated static site; never deploy it."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import shutil

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path(__file__).with_name("public_site_files.json")


def approved_files():
    files = json.loads(MANIFEST.read_text())
    if not isinstance(files, list) or len(files) != len(set(files)):
        raise ValueError("Invalid public site manifest")
    for name in files:
        path = PurePosixPath(name)
        if (path.is_absolute() or ".." in path.parts or str(path) != name
                or name == "deployment.json" or any(p.startswith(".") and p != ".nojekyll" for p in path.parts)):
            raise ValueError("Unsafe public site manifest path")
    return set(files)


def validate_bundle(destination):
    destination = Path(destination)
    if not destination.is_dir():
        raise ValueError("Missing public website bundle")
    paths = list(destination.rglob("*"))
    if destination.is_symlink() or any(p.is_symlink() for p in paths):
        raise ValueError("Symlinks are not public website artifacts")
    actual = {p.relative_to(destination).as_posix() for p in paths if p.is_file()}
    expected = approved_files() | {"deployment.json"}
    if actual != expected:
        raise ValueError(f"Website file manifest mismatch: extra={sorted(actual-expected)}, missing={sorted(expected-actual)}")


def package(root, destination, revision="local-review"):
    try:
        from .scan_public_privacy import scan_structured, scan_browser_requests
    except ImportError:
        from scan_public_privacy import scan_structured, scan_browser_requests
    root, destination = Path(root).resolve(), Path(destination)
    # Validate the inputs, including source captures that may not be used on the map.
    scan_structured(root)
    scan_browser_requests(root)
    files = approved_files()
    for name in sorted(files):
        source = root / name
        if not source.is_file() or source.is_symlink() or any(p.is_symlink() for p in source.parents if p != root) or not source.resolve().is_relative_to(root):
            raise ValueError(f"Missing or unsafe public website source: {name}")
    # Refuse reuse so a stale unlisted file can never hitchhike into an upload.
    destination.mkdir(parents=True, exist_ok=False)
    for name in sorted(files):
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, target)
    (destination / "deployment.json").write_text(json.dumps({"revision": revision}) + "\n")
    validate_bundle(destination)
    scan_structured(destination, packaged=True)
    scan_browser_requests(destination)
    return len(files) + 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    total = package(ROOT, args.output, os.environ.get("SITE_REVISION", "local-review"))
    print(f"Prepared and scanned {total} public website files in {args.output}")


if __name__ == "__main__":
    main()
