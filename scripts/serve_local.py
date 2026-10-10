#!/usr/bin/env python3
"""Loopback-only preview of public assets. Private analysis stays offline."""
import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT=Path(__file__).resolve().parents[1]


def public_path_allowed(resolved, root=ROOT):
    """Reject private outputs, hidden paths and symlink escapes after resolution."""
    resolved = Path(resolved).resolve()
    root = Path(root).resolve()
    return resolved.is_relative_to(root) and not any(
        part.startswith('.') or part in {'output', 'scripts', 'tests', '__local__'}
        for part in resolved.relative_to(root).parts
    )


class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)

    def do_GET(self):
        host=self.headers.get('Host','').split(':')[0]
        if host not in {'127.0.0.1','localhost'}:
            self.send_error(403);return
        path=unquote(urlsplit(self.path).path)
        resolved=Path(self.translate_path(self.path)).resolve()
        if not public_path_allowed(resolved):
            self.send_error(404);return
        super().do_GET()

    def do_HEAD(self):
        # No HEAD bypass for private filesystem paths.
        self.send_error(405)

    def list_directory(self, path):
        # Directory listings can reveal private filenames even when reads are blocked.
        self.send_error(404)
        return None

    def end_headers(self):
        self.send_header('Cache-Control','no-store');super().end_headers()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=8001);args=parser.parse_args()
    print(f'Local hub: http://127.0.0.1:{args.port}/',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
