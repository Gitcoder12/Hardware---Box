import json
import tempfile
import unittest
from pathlib import Path
from hardware_box.assets import write_manifest, verify_manifest
from hardware_box.audit import audit_project

class AssetManifestTests(unittest.TestCase):
    def test_manifest_round_trip_and_change_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'designs').mkdir()
            asset = root / 'designs' / 'part.stl'
            asset.write_bytes(b'original model')
            manifest = write_manifest(root)
            self.assertTrue(verify_manifest(root)['valid'])
            asset.write_bytes(b'changed model')
            result = verify_manifest(root)
            self.assertFalse(result['valid'])
            self.assertEqual(result['modified'], ['designs/part.stl'])

    def test_untracked_file_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'a.txt').write_text('a')
            write_manifest(root)
            (root / 'b.txt').write_text('b')
            result = verify_manifest(root)
            self.assertFalse(result['valid'])
            self.assertEqual(result['untracked'], ['b.txt'])

    def test_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'manifest.json').write_text(json.dumps({'manifest_version': 1, 'algorithm': 'sha256', 'assets': [{'path': '../outside', 'size_bytes': 0, 'sha256': 'x'}]}))
            with self.assertRaises(ValueError):
                verify_manifest(root, 'manifest.json')


    def test_missing_asset_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'part.step').write_text('solid')
            write_manifest(root)
            (root / 'part.step').unlink()
            result = verify_manifest(root)
            self.assertFalse(result['valid'])
            self.assertEqual(result['missing'], ['part.step'])

    def test_duplicate_manifest_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            item = {'path': 'a.txt', 'size_bytes': 1, 'sha256': '0' * 64}
            (root / 'hardware-box-manifest.json').write_text(json.dumps({'manifest_version': 1, 'algorithm': 'sha256', 'assets': [item, item]}))
            with self.assertRaisesRegex(ValueError, 'Duplicate manifest path'):
                verify_manifest(root)

    def test_symlink_asset_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root.parent / (root.name + '-outside.txt')
            outside.write_text('outside')
            try:
                (root / 'link.txt').symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks are unavailable on this platform')
            try:
                with self.assertRaisesRegex(ValueError, 'Symlinks are not allowed'):
                    write_manifest(root)
            finally:
                outside.unlink(missing_ok=True)

if __name__ == '__main__':
    unittest.main()
