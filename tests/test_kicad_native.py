import tempfile
import unittest
from pathlib import Path

from hardware_box.kicad_native import inspect_kicad_native, parse_sexpr


class SExpressionParserTests(unittest.TestCase):
    def test_quoted_parentheses_and_escaped_quotes_are_values(self):
        parsed = parse_sexpr('(root (property "Reference" "U1") (label "net (debug) and \\"quoted\\" text"))')
        self.assertEqual(parsed[0], 'root')
        self.assertEqual(parsed[1][2], 'U1')
        self.assertIn('(debug)', parsed[2][1])
        self.assertIn('"quoted"', parsed[2][1])

    def test_comments_are_ignored(self):
        self.assertEqual(parse_sexpr('(root ; ignore this\n (child value))'), ['root', ['child', 'value']])

    def test_rejects_unbalanced_and_multiple_roots(self):
        for invalid in ('(root', 'root)', '(one)(two)', 'text (root)'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                parse_sexpr(invalid)

    def test_rejects_excessive_nesting(self):
        from hardware_box.kicad_native import _MAX_DEPTH
        expression = '(' * (_MAX_DEPTH + 1) + 'leaf' + ')' * (_MAX_DEPTH + 1)
        with self.assertRaisesRegex(ValueError, 'nesting limit'):
            parse_sexpr(expression)

    def test_rejects_token_count_overflow(self):
        from unittest.mock import patch
        with patch('hardware_box.kicad_native._MAX_TOKENS', 2):
            with self.assertRaisesRegex(ValueError, 'token limit'):
                parse_sexpr('(root value)')

    def test_rejects_wrong_file_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'wrong.kicad_sch'
            path.write_text('(kicad_pcb (version 1))', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'expects root'):
                inspect_kicad_native(path)


class NativeKiCadInspectionTests(unittest.TestCase):
    def test_schematic_extracts_symbols_and_connectivity_markers(self):
        content = '''(kicad_sch
          (version 20250114)
          (generator "eeschema")
          (lib_symbols (symbol "Device:R" (property "Reference" "R")))
          (symbol (lib_id "Device:R") (at 10 10 0)
            (property "Reference" "R1") (property "Value" "10k") (in_bom yes) (on_board yes) (dnp no))
          (symbol (lib_id "Device:C") (at 20 10 0)
            (property "Reference" "C1") (property "Value" "100nF"))
          (wire (pts (xy 10 10) (xy 20 10)))
          (junction (at 15 10))
          (no_connect (at 20 20))
          (label "SENSOR_OUT" (at 15 10 0))
          (global_label "GND" (shape input) (at 10 20 0)))'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'controller.kicad_sch'
            path.write_text(content, encoding='utf-8')
            result = inspect_kicad_native(path)
        self.assertEqual(result['format'], 'kicad_sch')
        self.assertEqual(result['placed_symbol_count'], 2)
        self.assertEqual(result['references'], ['C1', 'R1'])
        self.assertEqual(result['wire_count'], 1)
        self.assertEqual(result['junction_count'], 1)
        self.assertEqual(result['no_connect_count'], 1)
        self.assertEqual(result['local_label_count'], 1)
        self.assertEqual(result['global_label_count'], 1)
        self.assertEqual(result['dnp_symbol_count'], 0)

    def test_board_extracts_footprints_pads_nets_and_track_length(self):
        content = '''(kicad_pcb
          (version 20241229) (generator "pcbnew")
          (general (thickness 1.6))
          (setup (stackup (layer "F.Cu" (type "copper") (thickness 0.035)) (layer "dielectric 1" (type "core") (thickness 1.51) (material "FR4") (epsilon_r 4.5))))
          (layers (0 "F.Cu" signal) (31 "B.Cu" signal) (44 "Edge.Cuts" user))
          (net 0 "") (net 1 "GND")
          (footprint "Resistor_SMD:R_0603"
            (property "Reference" "R1") (property "Value" "10k")
            (pad "1" smd rect (at 0 0) (size 1 1) (layers "F.Cu") (net 1 "GND")))
          (segment (start 0 0) (end 3 4) (width 0.2) (layer "F.Cu") (net 1))
          (via (at 2 2) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu") (net 1))
          (zone (net 1) (layer "F.Cu")))'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'controller.kicad_pcb'
            path.write_text(content, encoding='utf-8')
            result = inspect_kicad_native(path)
        self.assertEqual(result['format'], 'kicad_pcb')
        self.assertEqual(result['footprint_count'], 1)
        self.assertEqual(result['pad_count'], 1)
        self.assertEqual(result['assigned_pad_count'], 1)
        self.assertEqual(result['track_segment_count'], 1)
        self.assertEqual(result['via_count'], 1)
        self.assertEqual(result['net_count'], 1)
        self.assertEqual(result['track_segments_by_net'], {'GND': 1})
        self.assertEqual(result['vias_by_net'], {'GND': 1})
        self.assertEqual(result['zone_count'], 1)
        self.assertAlmostEqual(result['track_length_total_mm'], 5.0)
        self.assertEqual(result['thickness_mm'], 1.6)
        self.assertEqual(result['copper_layers'], ['F.Cu', 'B.Cu'])
        self.assertEqual(result['stackup_layers'][1]['material'], 'FR4')
        self.assertEqual(result['stackup_layers'][1]['epsilon_r'], 4.5)

    def test_kicad_10_name_only_net_assignments(self):
        content = '''(kicad_pcb (version 20260206) (generator "pcbnew")
          (general (thickness 1.6))
          (layers (0 "F.Cu" signal) (2 "B.Cu" signal))
          (footprint "LED_SMD:LED_0805" (property "Reference" "D1") (property "Value" "RED")
            (pad "1" smd roundrect (net "GND"))
            (pad "2" smd roundrect (net "Net-(D1-A)")))
          (segment (start 0 0) (end 1 0) (width 0.25) (layer "F.Cu") (net "GND"))
          (via (at 2 2) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu") (net "GND"))
          (arc (start 1 0) (mid 0 1) (end -1 0) (width 0.2) (layer "F.Cu") (net "GND"))
          (zone (net "GND") (layer "F.Cu")))'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'modern.kicad_pcb'
            path.write_text(content, encoding='utf-8')
            result = inspect_kicad_native(path)
        self.assertEqual(result['net_count'], 2)
        self.assertEqual(result['assigned_pad_count'], 2)
        self.assertEqual(result['pad_counts_by_net'], {'GND': 1, 'Net-(D1-A)': 1})
        self.assertEqual(result['track_segments_by_net'], {'GND': 1})
        self.assertEqual(result['track_arc_count'], 1)
        self.assertEqual(result['track_primitive_count'], 2)
        self.assertEqual(result['via_count'], 1)
        self.assertEqual(result['vias_by_net'], {'GND': 1})
        self.assertAlmostEqual(result['track_length_total_mm'], 1 + 3.14159265, places=5)

    def test_rejects_unsupported_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'design.kicad_pro'
            path.write_text('(project)', encoding='utf-8')
            with self.assertRaises(ValueError):
                inspect_kicad_native(path)
    def test_enforces_file_size_limit_before_reading(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'large.kicad_sch'
            path.write_text('(kicad_sch (version 1))', encoding='utf-8')
            with patch('hardware_box.kicad_native._MAX_FILE_BYTES', 5):
                with self.assertRaisesRegex(ValueError, 'too large'):
                    inspect_kicad_native(path)

    def test_legacy_numeric_net_codes_resolve_to_declared_names(self):
        content = """(kicad_pcb (version 20241229) (generator \"pcbnew\")
          (layers (0 \"F.Cu\" signal)) (net 0 \"\") (net 1 \"GND\")
          (footprint \"R_0603\" (property \"Reference\" \"R1\")
            (pad \"1\" smd rect (net 1)))
          (segment (start 0 0) (end 2 0) (width 0.2) (layer \"F.Cu\") (net 1)))"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'legacy.kicad_pcb'
            path.write_text(content, encoding='utf-8')
            result = inspect_kicad_native(path)
        self.assertEqual(result['net_count'], 1)
        self.assertEqual(result['nets'], [{'code': '1', 'name': 'GND'}])
        self.assertEqual(result['pad_counts_by_net'], {'GND': 1})
        self.assertEqual(result['track_segments_by_net'], {'GND': 1})



if __name__ == '__main__':
    unittest.main()
