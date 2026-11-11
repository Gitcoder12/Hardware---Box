import tempfile, unittest
from pathlib import Path
from hardware_box.catalog import add_component, get_component, search_components

class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.db = Path(self.tmp.name) / 'catalog.sqlite3'
    def tearDown(self): self.tmp.cleanup()
    def item(self):
        return {'mpn': 'STM32F401CCU6', 'manufacturer': 'STMicroelectronics', 'name': 'MCU',
                'category': 'microcontroller', 'package': 'UFQFPN-48', 'lifecycle_status': 'active',
                'datasheet_url': 'https://example.test/ds.pdf', 'specifications': {'core': 'ARM Cortex-M4'},
                'provenance': {'source': 'manufacturer datasheet', 'license': 'reference only'}}
    def test_add_get_search(self):
        add_component(self.db, self.item())
        item = get_component(self.db, 'STM32F401CCU6')
        self.assertEqual(item['specifications']['core'], 'ARM Cortex-M4')
        self.assertEqual(len(search_components(self.db, 'stm32')), 1)
    def test_duplicate_mpn_rejected(self):
        add_component(self.db, self.item())
        with self.assertRaises(Exception): add_component(self.db, self.item())
    def test_required_fields(self):
        with self.assertRaises(ValueError): add_component(self.db, {'mpn': 'X'})
    def test_search_limit_guard(self):
        with self.assertRaises(ValueError): search_components(self.db, limit=0)
