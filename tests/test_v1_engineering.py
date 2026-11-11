import json
import tempfile
import unittest
from pathlib import Path

from hardware_box.compatibility import compare_devices
from hardware_box.electrical import analyze_electrical
from hardware_box.schema_migrations import migrate_record
from hardware_box.units import convert, normalize_measurement
from hardware_box.validation import validate_device

ROOT = Path(__file__).resolve().parents[1]

class VersionAndUnitsTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((ROOT / 'database/devices/example-controller.json').read_text())

    def test_legacy_migration_is_copy_and_sets_version(self):
        migrated = migrate_record(self.record)
        self.assertNotIn('schema_version', self.record)
        self.assertEqual(migrated['schema_version'], 1)
        self.assertEqual(validate_device(migrated), [])

    def test_future_version_rejected(self):
        with self.assertRaises(ValueError): migrate_record({**self.record, 'schema_version': 9})

    def test_voltage_conversion(self):
        self.assertAlmostEqual(convert(3300, 'mV', 'V', 'voltage'), 3.3)

    def test_measurement_requires_unit(self):
        self.assertAlmostEqual(normalize_measurement({'value': 2, 'unit': 'A'}, 'current', 'mA'), 2000)
        with self.assertRaises(ValueError): normalize_measurement(2, 'current', 'mA')

class ElectricalTests(unittest.TestCase):
    def test_power_and_current_budget(self):
        rec = {'electrical': {'supply': {'voltage_v': 5, 'current_limit_a': 1},
            'loads': [{'name': 'logic', 'quantity': 2, 'current_a': .2, 'voltage_min_v': 3.0, 'voltage_max_v': 5.5},
                      {'name': 'sensor', 'current_a': .1, 'voltage_min_v': 5.0, 'voltage_max_v': 5.5}]}}
        result = analyze_electrical(rec)
        self.assertTrue(result['valid'])
        self.assertEqual(result['totals']['estimated_current_a'], .5)
        self.assertEqual(result['totals']['estimated_power_w'], 2.5)
        self.assertEqual({x['status'] for x in result['checks']}, {'pass'})

    def test_overcurrent_is_reported(self):
        rec = {'electrical': {'supply': {'voltage_v': 5, 'current_limit_a': .2},
            'loads': [{'name': 'motor', 'current_a': .4, 'voltage_min_v': 4, 'voltage_max_v': 6}]}}
        result = analyze_electrical(rec)
        self.assertIn('fail', [x['status'] for x in result['checks']])

    def test_voltage_mismatch_is_reported(self):
        rec = {'electrical': {'supply': {'voltage_v': 12},
            'loads': [{'name': 'logic', 'voltage_min_v': 3, 'voltage_max_v': 3.6}]}}
        result = analyze_electrical(rec)
        self.assertIn('fail', [x['status'] for x in result['checks']])

    def test_missing_current_is_unknown_not_pass(self):
        rec = {'electrical': {'supply': {'voltage_v': 5, 'current_limit_a': 1}, 'loads': [{'name': 'unknown'}]}}
        result = analyze_electrical(rec)
        self.assertIn('unknown', [x['status'] for x in result['checks']])

    def test_missing_supply_current_limit_is_unknown(self):
        rec = {'electrical': {'supply': {'voltage_v': 5}, 'loads': [{'name': 'load', 'current_a': .1}]}}
        result = analyze_electrical(rec)
        self.assertIn('unknown', [x['status'] for x in result['checks']])

    def test_invalid_electrical_profile_fails_validation(self):
        base = json.loads((ROOT / 'database/devices/example-controller.json').read_text())
        base['electrical'] = {'supply': {'voltage_v': -5}, 'loads': []}
        self.assertTrue(validate_device(base))

class CompatibilityTests(unittest.TestCase):
    def test_structured_voltage_conflict(self):
        a = {'interfaces': [{'name': 'I2C', 'protocol': 'I2C', 'voltage_min_v': 3.0, 'voltage_max_v': 3.6}]}
        b = {'interfaces': [{'name': 'i2c', 'protocol': 'I2C', 'voltage_min_v': 5.0, 'voltage_max_v': 5.5}]}
        result = compare_devices(a, b)
        self.assertEqual(result['assessment'], 'declared_conflict')
        self.assertEqual(result['interface_details'][0]['status'], 'incompatible')

    def test_label_only_remains_cautious(self):
        result = compare_devices({'interfaces': ['USB']}, {'interfaces': ['USB']})
        self.assertEqual(result['assessment'], 'potential_overlap')

    def test_structured_valid_interface(self):
        rec = json.loads((ROOT / 'database/devices/example-controller.json').read_text())
        rec['interfaces'] = [{'name': 'UART', 'protocol': 'UART', 'direction': 'bidirectional', 'pin_count': 2}]
        self.assertEqual(validate_device(rec), [])

class MalformedInputTests(unittest.TestCase):
    def test_invalid_voltage_string_returns_errors_without_crashing(self):
        result = analyze_electrical({'electrical': {'supply': {'voltage_v': 'five', 'current_limit_a': 1},
            'loads': [{'name': 'x', 'current_a': .1, 'voltage_min_v': 1, 'voltage_max_v': 2}]}})
        self.assertFalse(result['valid'])
        self.assertIsNone(result['totals']['estimated_power_w'])

    def test_invalid_current_limit_string_returns_errors_without_crashing(self):
        result = analyze_electrical({'electrical': {'supply': {'voltage_v': 5, 'current_limit_a': 'many'},
            'loads': [{'name': 'x', 'current_a': .1, 'voltage_min_v': 4, 'voltage_max_v': 6}]}})
        self.assertFalse(result['valid'])

    def test_unhashable_interface_direction_is_validation_error(self):
        record = json.loads((ROOT / 'database/devices/example-controller.json').read_text())
        record['interfaces'] = [{'name': 'X', 'direction': []}]
        self.assertTrue(validate_device(record))
