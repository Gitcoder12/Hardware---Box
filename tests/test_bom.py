import csv
import json
import tempfile
import unittest
from pathlib import Path
from hardware_box.bom import bom_rows, export_bom_csv

ROOT = Path(__file__).resolve().parents[1]

class BOMTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((ROOT / 'database/devices/example-controller.json').read_text())

    def test_bom_rows(self):
        rows = bom_rows(self.record)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['quantity'], 1)
        self.assertEqual(rows[0]['reference'], 'ITEM-001')

    def test_csv_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = export_bom_csv(self.record, Path(tmp) / 'bom.csv')
            with path.open(encoding='utf-8-sig', newline='') as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[1]['component'], 'USB connector')

if __name__ == '__main__':
    unittest.main()
