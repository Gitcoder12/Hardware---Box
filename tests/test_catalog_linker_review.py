import json, tempfile, unittest
from pathlib import Path
from hardware_box.catalog import add_component
from hardware_box.component_linker import link_bom_to_catalog
from hardware_box.design_review import review_design
from hardware_box.supply_chain import analyze_supply_chain, cost_summary

ROOT = Path(__file__).resolve().parents[1]

class LinkerAndReviewTests(unittest.TestCase):
    def test_exact_mpn_link_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / 'catalog.sqlite3')
            add_component(db, {'mpn': 'EX-1', 'manufacturer': 'Example', 'name': 'Part 1'})
            result = link_bom_to_catalog(db, {'components': [
                {'name': 'Exact', 'part_number': 'EX-1', 'quantity': 1},
                {'name': 'Near match', 'part_number': 'EX-1A', 'quantity': 1},
            ]})
            self.assertEqual(result['linked_count'], 1)
            self.assertEqual(result['unresolved_count'], 1)
    def test_sourcing_flags_obsolete_parts(self):
        record = {'id': 'x', 'components': [{'name': 'old', 'quantity': 1,
            'part_number': 'OLD-1', 'manufacturer': 'Example',
            'specifications': {'lifecycle_status': 'obsolete', 'unit_cost': 2, 'currency': 'USD',
                               'suppliers': ['one'], 'lead_time_days': 5}}]}
        report = analyze_supply_chain(record)
        self.assertEqual(report['severity_counts']['high'], 1)
        self.assertEqual(cost_summary(record)['totals_by_currency'], {'USD': 2.0})
    def test_review_has_explicit_disclaimer(self):
        record = json.loads((ROOT / 'database/devices/example-controller.json').read_text())
        result = review_design(record)
        self.assertEqual(result['total_checks'], 7)
        self.assertIn('not safety', result['disclaimer'])
