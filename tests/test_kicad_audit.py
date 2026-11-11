import tempfile
import unittest
from pathlib import Path

from hardware_box.kicad import parse_kicad_bom_csv
from hardware_box.kicad_audit import audit_kicad_exports


class KiCadAuditTests(unittest.TestCase):
    def _write(self, root, name, text):
        path = Path(root) / name
        path.write_text(text, encoding='utf-8')
        return path

    def test_reports_bom_netlist_mismatches_and_single_node_nets(self):
        with tempfile.TemporaryDirectory() as tmp:
            bom = self._write(tmp, 'bom.csv',
                'References,Value,Footprint,MPN\n"R1, R2",10k,R_0603,RES-10K\nC1,100nF,C_0603,CAP-100N\nU1,MCU,QFN-32,MCU-1\n')
            netlist = self._write(tmp, 'board.net', '''<export><components>
              <comp ref="R1"><value>10k</value></comp><comp ref="U1"><value>MCU</value></comp>
              </components><nets><net code="1" name="GND"><node ref="R1" pin="1"/><node ref="U1" pin="3"/></net>
              <net code="2" name="TEST"><node ref="U1" pin="8"/></net></nets></export>''')
            result = audit_kicad_exports(bom, netlist)
        self.assertEqual(result['status'], 'review')
        codes = {item['code'] for item in result['findings']}
        self.assertIn('bom_reference_missing_from_netlist', codes)
        self.assertIn('single_node_net', codes)
        self.assertEqual(result['severity_counts']['high'], 0)

    def test_flags_duplicate_pin_on_multiple_nets(self):
        with tempfile.TemporaryDirectory() as tmp:
            bom = self._write(tmp, 'bom.csv', 'References,Value\nU1,MCU\n')
            netlist = self._write(tmp, 'board.net', '''<export><components><comp ref="U1"><value>MCU</value></comp></components>
              <nets><net code="1" name="A"><node ref="U1" pin="1"/></net>
              <net code="2" name="B"><node ref="U1" pin="1"/></net></nets></export>''')
            result = audit_kicad_exports(bom, netlist)
        self.assertEqual(result['status'], 'fail')
        self.assertIn('pin_assigned_to_multiple_nets', {item['code'] for item in result['findings']})

    def test_bom_duplicate_reference_in_single_row_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, 'bad.csv', 'References,Value\n"R1, R1",10k\n')
            with self.assertRaisesRegex(ValueError, 'Duplicate reference'):
                parse_kicad_bom_csv(path)

    def test_duplicate_references_across_bom_rows_are_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            bom = self._write(tmp, 'bom.csv', 'References,Value\nR1,10k\nR1,22k\n')
            netlist = self._write(tmp, 'board.net', '''<export><components><comp ref="R1"><value>10k</value></comp></components>
              <nets><net code="1" name="GND"><node ref="R1" pin="1"/></net></nets></export>''')
            result = audit_kicad_exports(bom, netlist)
        self.assertEqual(result['status'], 'fail')
        self.assertIn('duplicate_bom_reference', {item['code'] for item in result['findings']})
    def test_flags_native_pcb_pad_net_mismatch_against_xml_netlist(self):
        with tempfile.TemporaryDirectory() as tmp:
            bom = self._write(tmp, 'bom.csv', 'References,Value\nU1,MCU\n')
            netlist = self._write(tmp, 'netlist.xml', '''<export><components><comp ref="U1"><value>MCU</value></comp></components>
              <nets><net code="1" name="GND"><node ref="U1" pin="1"/></net>
              <net code="2" name="3V3"><node ref="U1" pin="2"/></net></nets></export>''')
            pcb = self._write(tmp, 'board.kicad_pcb', '''(kicad_pcb (version 20241229) (generator "pcbnew")
              (layers (0 "F.Cu" signal)) (net 0 "") (net 1 "GND") (net 2 "3V3")
              (footprint "QFN" (property "Reference" "U1")
                (pad "1" smd rect (net 1 "GND"))
                (pad "2" smd rect (net 1 "GND"))))''')
            result = audit_kicad_exports(bom, netlist, pcb_path=pcb)
        self.assertEqual(result['status'], 'review')
        self.assertIn('pcb_pad_net_mismatch', {item['code'] for item in result['findings']})
        self.assertEqual(result['pcb_pad_net_comparisons'], 2)



if __name__ == '__main__':
    unittest.main()
