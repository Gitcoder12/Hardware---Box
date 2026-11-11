import struct,tempfile,unittest
from pathlib import Path
from hardware_box.cad_inspector import inspect_model
class CADTests(unittest.TestCase):
 def test_binary_stl(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'tiny.stl'; header=b'HardwareBox'.ljust(80,b' '); tri=struct.pack('<12fH',0,0,1,0,0,0,1,0,0,0,1,0,0); p.write_bytes(header+struct.pack('<I',1)+tri)
   result=inspect_model(p); self.assertEqual(result['triangle_count'],1); self.assertEqual(result['bounds_mm_assumed']['x']['size'],1.0)
if __name__=='__main__': unittest.main()
