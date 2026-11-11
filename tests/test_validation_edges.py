import json
import unittest
from pathlib import Path
from hardware_box.validation import validate_device

ROOT = Path(__file__).resolve().parents[1]

class ValidationEdgeTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((ROOT / 'database/devices/example-controller.json').read_text())

    def test_category_wrong_type_returns_errors_not_exception(self):
        self.record['category'] = []
        self.assertTrue(validate_device(self.record))

    def test_duplicate_component_names_rejected(self):
        self.record['components'].append(dict(self.record['components'][0]))
        self.assertTrue(any('duplicate component name' in e for e in validate_device(self.record)))

    def test_duplicate_interfaces_rejected_case_insensitively(self):
        self.record['interfaces'].append('usb')
        self.assertTrue(any('duplicate interface' in e for e in validate_device(self.record)))

if __name__ == '__main__':
    unittest.main()
