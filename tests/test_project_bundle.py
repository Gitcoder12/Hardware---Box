import tempfile, unittest, zipfile, json
from pathlib import Path
from hardware_box.project_bundle import create_bundle, verify_bundle, extract_bundle, BUNDLE_NAME

class BundleTests(unittest.TestCase):
    def test_bundle_roundtrip_and_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'; root.mkdir(); (root / 'README.md').write_text('hello')
            (root / 'src').mkdir(); (root / 'src' / 'a.py').write_text('print(1)')
            bundle = Path(tmp) / 'project.zip'
            create_bundle(root, bundle)
            self.assertTrue(verify_bundle(bundle)['valid'])
            target = Path(tmp) / 'out'; result = extract_bundle(bundle, target)
            self.assertEqual(result['files_extracted'], 2)
            self.assertEqual((target / 'src' / 'a.py').read_text(), 'print(1)')
    def test_modified_bundle_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'p'; root.mkdir(); (root / 'x').write_text('a')
            bundle = Path(tmp) / 'p.zip'; create_bundle(root, bundle)
            with zipfile.ZipFile(bundle, 'r') as original:
                manifest = original.read(BUNDLE_NAME)
            with zipfile.ZipFile(bundle, 'w') as changed:
                changed.writestr(BUNDLE_NAME, manifest)
                changed.writestr('x', 'tampered')
            self.assertFalse(verify_bundle(bundle)['valid'])
            self.assertEqual(verify_bundle(bundle)['modified'], ['x'])
    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / 'evil.zip'
            manifest = {'bundle_version': 1, 'tool': 'Hardware-Box', 'file_count': 1,
                        'assets': [{'path': '../escape.txt', 'size_bytes': 1, 'sha256': '0'*64}]}
            with zipfile.ZipFile(bundle, 'w') as z:
                z.writestr(BUNDLE_NAME, json.dumps(manifest)); z.writestr('../escape.txt', 'x')
            with self.assertRaises(ValueError): verify_bundle(bundle)
    def test_existing_files_not_overwritten_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'p'; root.mkdir(); (root / 'x').write_text('new')
            bundle = Path(tmp) / 'p.zip'; create_bundle(root, bundle)
            target = Path(tmp) / 'out'; target.mkdir(); (target / 'x').write_text('old')
            with self.assertRaises(FileExistsError): extract_bundle(bundle, target)
