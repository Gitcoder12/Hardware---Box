import json,tempfile,unittest
from pathlib import Path
from hardware_box.registry import add_device,get_device,list_devices,update_device,delete_device
from hardware_box.compatibility import compare_devices
from hardware_box.validation import validate_device
ROOT=Path(__file__).resolve().parents[1]
class RegistryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.db=str(Path(self.tmp.name)/'db.sqlite3')
  self.record=json.loads((ROOT/'database/devices/example-controller.json').read_text())
 def tearDown(self): self.tmp.cleanup()
 def test_add_get_list_delete(self):
  add_device(self.db,self.record); self.assertEqual(get_device(self.db,self.record['id']),self.record); self.assertEqual(len(list_devices(self.db)),1); self.assertTrue(delete_device(self.db,self.record['id'])); self.assertIsNone(get_device(self.db,self.record['id']))
 def test_duplicate_rejected(self):
  add_device(self.db,self.record)
  with self.assertRaises(Exception): add_device(self.db,self.record)
 def test_update(self):
  add_device(self.db,self.record); changed=dict(self.record); changed['name']='Updated Controller'; update_device(self.db,changed); self.assertEqual(get_device(self.db,changed['id'])['name'],'Updated Controller')
 def test_validation(self): self.assertEqual(validate_device(self.record),[])
 def test_interface_comparison_is_cautious(self):
  other=dict(self.record,interfaces=['USB','I2C']); result=compare_devices(self.record,other); self.assertEqual(result['shared_interfaces'],['usb']); self.assertEqual(result['assessment'],'potential_overlap')
if __name__=='__main__': unittest.main()
