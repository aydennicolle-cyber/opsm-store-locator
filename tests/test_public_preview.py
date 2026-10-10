"""The public preview must not expose the old private overlay or filesystem escapes."""
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import serve_local


class PublicPreviewTests(unittest.TestCase):
    def test_private_paths_and_symlink_escapes_are_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'public'
            root.mkdir()
            outside = Path(temp) / 'private.json'
            outside.write_text('private')
            (root / 'leak.json').symlink_to(outside)
            for name in ('output/data.json', '.git/config', 'scripts/source.py',
                         'tests/fixture.json', '__local__/coverage', 'leak.json'):
                self.assertFalse(serve_local.public_path_allowed(root / name, root), name)
            for name in ('index.html', 'assets/app.js', 'data/retail_places.json'):
                self.assertTrue(serve_local.public_path_allowed(root / name, root), name)

    def test_old_overlay_endpoint_returns_404(self):
        handler = object.__new__(serve_local.Handler)
        handler.headers = {'Host': '127.0.0.1:8001'}
        handler.path = '/__local__/coverage'
        handler.directory = str(serve_local.ROOT)
        with patch.object(handler, 'send_error') as error, patch.object(
                serve_local.SimpleHTTPRequestHandler, 'do_GET') as public_get:
            handler.do_GET()
            error.assert_called_once_with(404)
            public_get.assert_not_called()

    def test_no_directory_listing(self):
        handler = object.__new__(serve_local.Handler)
        with patch.object(handler, 'send_error') as error:
            self.assertIsNone(handler.list_directory(str(serve_local.ROOT)))
            error.assert_called_once_with(404)


if __name__ == '__main__':
    unittest.main()
