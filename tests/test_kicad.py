import tempfile, unittest
from pathlib import Path
from hardware_box.kicad import parse_kicad_bom_csv, inspect_kicad_netlist

class KiCadTests(unittest.TestCase):
    def test_bom_csv_grouped_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'bom.csv'
            p.write_text('References,Qty,Value,Footprint,MPN,Manufacturer\n"R1, R2",2,10k,Resistor_SMD:R_0603,RC0603FR-0710KL,Yageo\n')
            result = parse_kicad_bom_csv(p)
            self.assertEqual(result['components'][0]['quantity'], 2)
            self.assertEqual(result['components'][0]['references'], ['R1', 'R2'])
    def test_bom_rejects_unknown_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'bad.csv'; p.write_text('Ref,Value\nR1,10k\n')
            self.assertEqual(parse_kicad_bom_csv(p)['line_item_count'], 1)
    def test_xml_netlist(self):
        xml = '''<export><components><comp ref="R1"><value>10k</value><footprint>R_0603</footprint></comp></components><nets><net code="1" name="GND"><node ref="R1" pin="1"/></net></nets></export>'''
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'board.net'; p.write_text(xml)
            result = inspect_kicad_netlist(p)
            self.assertEqual(result['component_count'], 1)
            self.assertEqual(result['net_count'], 1)
            self.assertEqual(result['connection_count'], 1)
    def test_invalid_xml_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'bad.net'; p.write_text('<broken>')
            with self.assertRaises(ValueError): inspect_kicad_netlist(p)
