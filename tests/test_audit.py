import json
import tempfile
import unittest
from pathlib import Path
from hardware_box.audit import audit_project

class ProjectAuditTests(unittest.TestCase):
    def test_audit_reports_valid_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / 'database' / 'devices'
            folder.mkdir(parents=True)
            sample = {
                'id':'demo-board','name':'Demo Board','category':'electronics','manufacturer':'Example','revision':'A',
                'components':[], 'interfaces':['USB'],
                'provenance':{'source':'test fixture','license':'CC0-1.0','verification':'unverified'}
            }
            (folder / 'demo-board.json').write_text(json.dumps(sample))
            result = audit_project(root)
            self.assertTrue(result['valid'])
            self.assertEqual(result['device_records_checked'], 1)

if __name__ == '__main__':
    unittest.main()
