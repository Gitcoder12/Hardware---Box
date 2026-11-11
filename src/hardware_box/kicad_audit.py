"""Cross-check a KiCad BOM CSV against an exported XML netlist."""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
from typing import Any
from .kicad import inspect_kicad_netlist, parse_kicad_bom_csv
from .kicad_native import inspect_kicad_native


def audit_kicad_exports(bom_path: str | Path, netlist_path: str | Path,
                        schematic_path: str | Path | None = None,
                        pcb_path: str | Path | None = None) -> dict[str, Any]:
    bom = parse_kicad_bom_csv(bom_path)
    netlist = inspect_kicad_netlist(netlist_path)
    findings: list[dict[str, str]] = []

    def add(severity: str, code: str, message: str, subject: str = '') -> None:
        findings.append({'severity': severity, 'code': code, 'subject': subject, 'message': message})

    bom_refs: list[str] = []
    for item in bom['components']:
        bom_refs.extend(item['references'])
    net_refs = [item['reference'] for item in netlist['components'] if item['reference']]
    schematic = inspect_kicad_native(schematic_path) if schematic_path else None
    pcb = inspect_kicad_native(pcb_path) if pcb_path else None
    if schematic is not None and schematic['format'] != 'kicad_sch':
        raise ValueError('schematic_path must refer to a .kicad_sch file')
    if pcb is not None and pcb['format'] != 'kicad_pcb':
        raise ValueError('pcb_path must refer to a .kicad_pcb file')

    bom_counts: dict[str, int] = defaultdict(int)
    net_counts: dict[str, int] = defaultdict(int)
    for ref in bom_refs:
        bom_counts[ref] += 1
    for ref in net_refs:
        net_counts[ref] += 1

    for ref, count in sorted(bom_counts.items()):
        if count > 1:
            add('high', 'duplicate_bom_reference', f'Reference appears {count} times in BOM.', ref)
    for ref, count in sorted(net_counts.items()):
        if count > 1:
            add('high', 'duplicate_netlist_reference', f'Reference appears {count} times in netlist.', ref)

    bom_set, net_set = set(bom_counts), set(net_counts)
    for ref in sorted(bom_set - net_set):
        add('medium', 'bom_reference_missing_from_netlist', 'BOM reference is absent from the exported netlist.', ref)
    for ref in sorted(net_set - bom_set):
        add('medium', 'netlist_reference_missing_from_bom', 'Netlist reference is absent from the BOM.', ref)

    node_locations: dict[tuple[str, str], set[str]] = defaultdict(set)
    connected_refs: set[str] = set()
    for net in netlist['nets']:
        name = net['name'] or f"net:{net['code']}"
        nodes = net['nodes']
        if len(nodes) == 0:
            add('medium', 'empty_net', 'Net contains no connection nodes.', name)
        elif len(nodes) == 1:
            add('low', 'single_node_net', 'Net has one node; review intentional test points and dangling connections.', name)
        for node in nodes:
            ref, pin = node['reference'], node['pin']
            connected_refs.add(ref)
            if ref not in net_set:
                add('high', 'unknown_netlist_reference', 'Net node references a component absent from the netlist component table.', ref)
            key = (ref, pin)
            node_locations[key].add(name)
    for (ref, pin), net_names in sorted(node_locations.items()):
        if len(net_names) > 1:
            add('high', 'pin_assigned_to_multiple_nets', f'Pin {pin} appears on multiple nets: {", ".join(sorted(net_names))}.', ref)
    for ref in sorted(net_set - connected_refs):
        add('low', 'component_without_net_nodes', 'Component is present in netlist component table but has no net nodes.', ref)

    # Compare designator inventories across all supplied project representations.
    source_refs: dict[str, set[str]] = {'BOM': bom_set, 'netlist': net_set}
    if schematic is not None:
        source_refs['schematic'] = set(schematic['references'])
        for ref in schematic['duplicate_references']:
            add('high', 'duplicate_schematic_reference', 'Reference appears more than once in the native schematic.', ref)
    pcb_pad_comparisons = 0
    if pcb is not None:
        pcb_refs = {item['reference'] for item in pcb['footprints'] if item['reference']}
        source_refs['PCB'] = pcb_refs
        for ref in pcb['duplicate_references']:
            add('high', 'duplicate_pcb_reference', 'Reference appears more than once in native PCB footprints.', ref)

        # Compare schematic XML net nodes with native board pad-to-net assignments
        # for references actually placed on the PCB. This is structural only.
        board_pad_nets = {
            (item['reference'], item['pad']): item['net']
            for item in pcb['pad_net_assignments']
            if item['reference'] and item['pad']
        }
        schematic_pad_nets: dict[tuple[str, str], str] = {}
        for net in netlist['nets']:
            net_name = net['name'] or f"net:{net['code']}"
            for node in net['nodes']:
                key = (node['reference'], node['pin'])
                if node['reference'] in pcb_refs and node['pin']:
                    schematic_pad_nets.setdefault(key, net_name)

        for key, expected_net in sorted(schematic_pad_nets.items()):
            if key not in board_pad_nets:
                add('medium', 'netlist_pad_missing_from_pcb',
                    f'Netlist connection {key[0]}.{key[1]} has no matching pad in the native PCB.',
                    f'{key[0]}.{key[1]}')
            elif board_pad_nets[key] != expected_net:
                add('medium', 'pcb_pad_net_mismatch',
                    f'Netlist assigns {key[0]}.{key[1]} to {expected_net!r}, but PCB assigns it to {board_pad_nets[key]!r}.',
                    f'{key[0]}.{key[1]}')
            pcb_pad_comparisons += 1

        for key, actual_net in sorted(board_pad_nets.items()):
            if key[0] in net_set and actual_net and key not in schematic_pad_nets:
                add('medium', 'pcb_pad_missing_from_netlist',
                    f'PCB assigns {key[0]}.{key[1]} to {actual_net!r}, but the XML netlist has no corresponding pad connection.',
                    f'{key[0]}.{key[1]}')
    source_names = list(source_refs)
    for index, left_name in enumerate(source_names):
        for right_name in source_names[index + 1:]:
            if left_name == 'BOM' and right_name == 'netlist':
                continue  # Already reported with more specific mismatch codes above.
            left_set, right_set = source_refs[left_name], source_refs[right_name]
            for ref in sorted(left_set - right_set):
                add('medium', 'project_reference_mismatch',
                    f'Reference exists in {left_name} but is absent from {right_name}.', ref)
            for ref in sorted(right_set - left_set):
                add('medium', 'project_reference_mismatch',
                    f'Reference exists in {right_name} but is absent from {left_name}.', ref)

    severity_order = {'high': 0, 'medium': 1, 'low': 2, 'info': 3}
    findings.sort(key=lambda item: (severity_order[item['severity']], item['code'], item['subject']))
    counts = {level: sum(1 for item in findings if item['severity'] == level)
              for level in ('high', 'medium', 'low', 'info')}
    status = 'fail' if counts['high'] else ('review' if counts['medium'] or counts['low'] else 'pass')
    return {
        'status': status,
        'bom_file': Path(bom_path).name,
        'netlist_file': Path(netlist_path).name,
        'bom_component_lines': bom['line_item_count'],
        'bom_reference_count': len(bom_refs),
        'netlist_component_count': netlist['component_count'],
        'net_count': netlist['net_count'],
        'connection_count': netlist['connection_count'],
        'source_reference_counts': {name: len(refs) for name, refs in source_refs.items()},
        'native_schematic_inspected': schematic is not None,
        'native_pcb_inspected': pcb is not None,
        'pcb_pad_net_comparisons': pcb_pad_comparisons,
        'severity_counts': counts,
        'findings': findings,
        'limitations': [
            'This cross-check compares BOM, XML netlist and optional native schematic/PCB reference inventories plus XML net-node structure.',
            'It does not perform KiCad ERC or PCB DRC and does not prove electrical correctness.',
            'Native PCB pad-to-net comparisons are structural and apply only to matching placed component references.',
            'Single-node nets may be intentional; inspect each finding in the source design.',
            'Reference differences may be intentional due to BOM exclusions, DNP settings, or project hierarchy; resolve them manually.',
        ],
    }
