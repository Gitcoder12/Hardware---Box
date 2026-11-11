import json
import unittest
from pathlib import Path
from tools.validators.validate_device import validate

ROOT = Path(__file__).resolve().parents[1]

class DeviceValidationTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((ROOT / 'database/devices/example-controller.json').read_text())

    def test_example_valid(self):
        self.assertEqual(validate(self.record), [])

    def test_missing_name(self):
        del self.record['name']
        self.assertTrue(validate(self.record))

    def test_invalid_quantity(self):
        self.record['components'][0]['quantity'] = 0
        self.assertTrue(any('quantity' in e for e in validate(self.record)))

    def test_invalid_provenance(self):
        self.record['provenance']['verification'] = 'certified'
        self.assertTrue(validate(self.record))

if __name__ == '__main__':
    unittest.main()
