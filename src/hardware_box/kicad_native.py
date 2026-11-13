"""Read-only inspection of native KiCad S-expression files.

This module extracts structural metadata from .kicad_sch and .kicad_pcb files.
It deliberately does not attempt to replace KiCad ERC, PCB DRC, simulation,
or manufacturing sign-off.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Iterator

_MAX_FILE_BYTES = 100 * 1024 * 1024
_MAX_TOKENS = 5_000_000
_MAX_DEPTH = 256


class _Quoted(str):
    """Distinguish quoted atom values from structural parentheses."""


def _tokens(text: str) -> Iterator[str]:
    """Tokenize a KiCad S-expression stream, including quoted strings/comments."""
    i, n, count = 0, len(text), 0
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch == ';':
            newline = text.find('\n', i)
            i = n if newline < 0 else newline + 1
            continue
        if ch in '()':
            token = ch
            i += 1
        elif ch == '"':
            i += 1
            chars: list[str] = []
            while i < n:
                ch = text[i]
                if ch == '"':
                    i += 1
                    break
                if ch == '\\':
                    i += 1
                    if i >= n:
                        raise ValueError('Unterminated escape in quoted KiCad string')
                    escaped = text[i]
                    chars.append({'n': '\n', 'r': '\r', 't': '\t'}.get(escaped, escaped))
                    i += 1
                else:
                    chars.append(ch)
                    i += 1
            else:
                raise ValueError('Unterminated quoted KiCad string')
            token = _Quoted(''.join(chars))
        else:
            start = i
            while i < n and not text[i].isspace() and text[i] not in '();':
                i += 1
            token = text[start:i]
        count += 1
        if count > _MAX_TOKENS:
            raise ValueError(f'KiCad file exceeds token limit ({_MAX_TOKENS:,})')
        yield token


def parse_sexpr(text: str) -> list[Any]:
    """Parse one S-expression root into nested Python lists and strings."""
    stack: list[list[Any]] = []
    roots: list[Any] = []
    for token in _tokens(text):
        if isinstance(token, _Quoted):
            if not stack:
                raise ValueError('Text found outside KiCad root expression')
            stack[-1].append(str(token))
        elif token == '(':
            if len(stack) >= _MAX_DEPTH:
                raise ValueError(f'KiCad expression exceeds nesting limit ({_MAX_DEPTH})')
            node: list[Any] = []
            if stack:
                stack[-1].append(node)
            else:
                roots.append(node)
            stack.append(node)
        elif token == ')':
            if not stack:
                raise ValueError('Unexpected closing parenthesis in KiCad file')
            stack.pop()
        else:
            if not stack:
                raise ValueError('Text found outside KiCad root expression')
            stack[-1].append(token)
    if stack:
        raise ValueError('Unclosed parenthesis in KiCad file')
    if len(roots) != 1 or not isinstance(roots[0], list):
        raise ValueError('Expected exactly one KiCad root expression')
    return roots[0]


def _head(node: Any) -> str | None:
    return node[0] if isinstance(node, list) and node and isinstance(node[0], str) else None


def _children(node: list[Any], tag: str) -> list[list[Any]]:
    return [item for item in node if isinstance(item, list) and _head(item) == tag]


def _first(node: list[Any], tag: str) -> list[Any] | None:
    return next(iter(_children(node, tag)), None)


def _all(node: list[Any], tag: str) -> Iterator[list[Any]]:
    """Yield matching descendants, including the node itself."""
    if _head(node) == tag:
        yield node
    for item in node:
        if isinstance(item, list):
            yield from _all(item, tag)


def _string_child(node: list[Any], tag: str, index: int = 1, default: str = '') -> str:
    child = _first(node, tag)
    if child is not None and len(child) > index and isinstance(child[index], str):
        return child[index]
    return default


def _number(value: Any) -> float | None:
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def _xy(node: list[Any] | None) -> tuple[float, float] | None:
    if node is None or len(node) < 3:
        return None
    x, y = _number(node[1]), _number(node[2])
    return (x, y) if x is not None and y is not None else None


def _arc_length(start: tuple[float, float] | None,
                mid: tuple[float, float] | None,
                end: tuple[float, float] | None) -> float | None:
    # Calculate circular arc length along the three supplied KiCad XY points.
    if start is None or mid is None or end is None:
        return None
    (x1, y1), (x2, y2), (x3, y3) = start, mid, end
    determinant = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if abs(determinant) < 1e-12:
        return None
    s1, s2, s3 = x1 * x1 + y1 * y1, x2 * x2 + y2 * y2, x3 * x3 + y3 * y3
    cx = (s1 * (y2 - y3) + s2 * (y3 - y1) + s3 * (y1 - y2)) / determinant
    cy = (s1 * (x3 - x2) + s2 * (x1 - x3) + s3 * (x2 - x1)) / determinant
    radius = math.hypot(x1 - cx, y1 - cy)
    a1 = math.atan2(y1 - cy, x1 - cx)
    am = math.atan2(y2 - cy, x2 - cx)
    a3 = math.atan2(y3 - cy, x3 - cx)
    ccw_sweep = (a3 - a1) % (2 * math.pi)
    mid_ccw = (am - a1) % (2 * math.pi)
    sweep = ccw_sweep if mid_ccw <= ccw_sweep + 1e-12 else (2 * math.pi - ccw_sweep)
    return radius * sweep


def _inspect_schematic(root: list[Any], source: Path) -> dict[str, Any]:
    placed_symbols = []
    for symbol in _all(root, 'symbol'):
        lib_id = _string_child(symbol, 'lib_id')
        if not lib_id:
            continue
        properties = {}
        for prop in _children(symbol, 'property'):
            if len(prop) >= 3 and isinstance(prop[1], str):
                properties[prop[1]] = prop[2]
        placed_symbols.append({
            'reference': properties.get('Reference', ''),
            'value': properties.get('Value', ''),
            'library_id': lib_id,
            'in_bom': _string_child(symbol, 'in_bom', default='unknown'),
            'on_board': _string_child(symbol, 'on_board', default='unknown'),
            'dnp': _string_child(symbol, 'dnp', default='unknown'),
        })

    references = [item['reference'] for item in placed_symbols if item['reference']]
    from collections import Counter
    duplicate_refs = sorted(ref for ref, count in Counter(references).items() if count > 1)
    return {
        'file': source.name,
        'format': 'kicad_sch',
        'version': _string_child(root, 'version'),
        'generator': _string_child(root, 'generator'),
        'generator_version': _string_child(root, 'generator_version'),
        'placed_symbol_count': len(placed_symbols),
        'references': sorted(references),
        'duplicate_references': duplicate_refs,
        'wire_count': sum(1 for _ in _all(root, 'wire')),
        'junction_count': sum(1 for _ in _all(root, 'junction')),
        'no_connect_count': sum(1 for _ in _all(root, 'no_connect')),
        'dnp_symbol_count': sum(1 for item in placed_symbols if item['dnp'].lower() == 'yes'),
        'excluded_from_bom_symbol_count': sum(1 for item in placed_symbols if item['in_bom'].lower() == 'no'),
        'not_on_board_symbol_count': sum(1 for item in placed_symbols if item['on_board'].lower() == 'no'),
        'local_label_count': sum(1 for _ in _all(root, 'label')),
        'global_label_count': sum(1 for _ in _all(root, 'global_label')),
        'hierarchical_label_count': sum(1 for _ in _all(root, 'hierarchical_label')),
        'sheet_count': sum(1 for _ in _all(root, 'sheet')),
        'symbols': placed_symbols,
        'limitations': [
            'Read-only structural extraction; no electrical-rule check (ERC) is performed.',
            'Connectivity, symbol pin semantics, simulation and design intent are not certified.',
        ],
    }


def _inspect_board(root: list[Any], source: Path) -> dict[str, Any]:
    # Older native PCB files commonly store only `(net 1)` on pads/tracks
    # while declaring `(net 1 "GND")` once at the root.
    net_declarations = _children(root, 'net')
    code_to_name: dict[str, str] = {}
    net_codes: dict[str, str] = {}
    for declaration in net_declarations:
        if len(declaration) >= 3:
            code, name = str(declaration[1]), str(declaration[2])
        elif len(declaration) >= 2:
            code, name = '', str(declaration[1])
        else:
            continue
        if name:
            net_codes.setdefault(name, code)
            if code:
                code_to_name[code] = name

    def resolve_net(node: list[Any] | None) -> str:
        if node is None or len(node) < 2:
            return ''
        if len(node) >= 3:
            return str(node[2])
        raw = str(node[1])
        return code_to_name.get(raw, raw)

    footprints = []
    pad_net_assignments: list[dict[str, str]] = []
    pad_count = 0
    assigned_pad_count = 0
    pad_nets: dict[str, int] = {}
    pad_types: dict[str, int] = {}
    for footprint in _children(root, 'footprint'):
        properties = {}
        for prop in _children(footprint, 'property'):
            if len(prop) >= 3 and isinstance(prop[1], str):
                properties[prop[1]] = prop[2]
        pads = _children(footprint, 'pad')
        pad_count += len(pads)
        reference = properties.get('Reference', '')
        for pad in pads:
            if len(pad) > 2 and isinstance(pad[2], str):
                pad_types[pad[2]] = pad_types.get(pad[2], 0) + 1
            net = _first(pad, 'net')
            net_name = resolve_net(net)
            pad_number = str(pad[1]) if len(pad) > 1 and isinstance(pad[1], str) else ''
            if reference and pad_number:
                pad_net_assignments.append({'reference': reference, 'pad': pad_number, 'net': net_name})
            if net_name:
                pad_nets[net_name] = pad_nets.get(net_name, 0) + 1
                assigned_pad_count += 1
        footprints.append({
            'reference': reference,
            'value': properties.get('Value', ''),
            'library_id': footprint[1] if len(footprint) > 1 and isinstance(footprint[1], str) else '',
            'pad_count': len(pads),
            'model_count': len(_children(footprint, 'model')),
        })

    segments = _children(root, 'segment')
    arcs = _children(root, 'arc')
    vias = _children(root, 'via')
    via_nets: dict[str, int] = {}
    for via in vias:
        via_net = resolve_net(_first(via, 'net'))
        if via_net:
            via_nets[via_net] = via_nets.get(via_net, 0) + 1
    track_length = 0.0
    track_segments_by_net: dict[str, int] = {}
    track_arcs_by_net: dict[str, int] = {}
    track_segments_by_layer: dict[str, int] = {}
    track_primitives_by_layer: dict[str, int] = {}
    track_widths: list[float] = []
    for segment in segments:
        segment_net = resolve_net(_first(segment, 'net'))
        segment_layer = _string_child(segment, 'layer')
        if segment_net:
            track_segments_by_net[segment_net] = track_segments_by_net.get(segment_net, 0) + 1
        if segment_layer:
            track_segments_by_layer[segment_layer] = track_segments_by_layer.get(segment_layer, 0) + 1
            track_primitives_by_layer[segment_layer] = track_primitives_by_layer.get(segment_layer, 0) + 1
        width = _number(_string_child(segment, 'width'))
        if width is not None:
            track_widths.append(width)
        start, end = _first(segment, 'start'), _first(segment, 'end')
        if start and end and len(start) >= 3 and len(end) >= 3:
            x1, y1, x2, y2 = (_number(start[1]), _number(start[2]), _number(end[1]), _number(end[2]))
            if None not in (x1, y1, x2, y2):
                track_length += math.hypot(x2 - x1, y2 - y1)
    for arc in arcs:
        arc_net = resolve_net(_first(arc, 'net'))
        if arc_net:
            track_arcs_by_net[arc_net] = track_arcs_by_net.get(arc_net, 0) + 1
        arc_layer = _string_child(arc, 'layer')
        if arc_layer:
            track_primitives_by_layer[arc_layer] = track_primitives_by_layer.get(arc_layer, 0) + 1
        width = _number(_string_child(arc, 'width'))
        if width is not None:
            track_widths.append(width)
        length = _arc_length(_xy(_first(arc, 'start')),
                             _xy(_first(arc, 'mid')),
                             _xy(_first(arc, 'end')))
        if length is not None:
            track_length += length

    layer_node = _first(root, 'layers')
    layers = []
    if layer_node:
        for item in layer_node:
            if isinstance(item, list) and len(item) >= 2 and isinstance(item[1], str):
                layers.append(item[1])

    # KiCad versions have used both numeric net declarations and name-only net references.
    # Derive the net inventory from declarations plus pad, segment, via and zone assignments.
    setup = _first(root, 'setup')
    stackup_node = _first(setup, 'stackup') if setup is not None else None
    stackup_layers = []
    if stackup_node is not None:
        for item in _children(stackup_node, 'layer'):
            name = item[1] if len(item) > 1 and isinstance(item[1], str) else ''
            stackup_layers.append({
                'name': name,
                'type': _string_child(item, 'type'),
                'thickness_mm': _number(_string_child(item, 'thickness')),
                'material': _string_child(item, 'material'),
                'epsilon_r': _number(_string_child(item, 'epsilon_r')),
                'loss_tangent': _number(_string_child(item, 'loss_tangent')),
            })

    all_net_names = {name for node in _all(root, 'net') if (name := resolve_net(node))}
    nets = [{'code': net_codes.get(name, ''), 'name': name} for name in sorted(all_net_names)]

    from collections import Counter
    refs = [item['reference'] for item in footprints if item['reference']]
    thickness = None
    general = _first(root, 'general')
    if general is not None:
        thickness = _number(_string_child(general, 'thickness'))
    duplicate_refs = sorted(ref for ref, count in Counter(refs).items() if count > 1)
    return {
        'file': source.name,
        'format': 'kicad_pcb',
        'version': _string_child(root, 'version'),
        'generator': _string_child(root, 'generator'),
        'generator_version': _string_child(root, 'generator_version'),
        'thickness_mm': thickness,
        'footprint_count': len(footprints),
        'embedded_3d_model_count': sum(item['model_count'] for item in footprints),
        'pad_type_counts': dict(sorted(pad_types.items())),
        'pad_net_assignments': sorted(pad_net_assignments, key=lambda item: (item['reference'], item['pad'])),
        'duplicate_references': duplicate_refs,
        'pad_count': pad_count,
        'assigned_pad_count': assigned_pad_count,
        'unassigned_pad_count': pad_count - assigned_pad_count,
        'track_segment_count': len(segments),
        'track_arc_count': len(arcs),
        'track_primitive_count': len(segments) + len(arcs),
        'via_count': len(vias),
        'zone_count': len(_children(root, 'zone')),
        'net_count': len(nets),
        'nets': nets,
        'copper_layers': [layer for layer in layers if layer.endswith('.Cu')],
        'stackup_layers': stackup_layers,
        'pad_counts_by_net': dict(sorted(pad_nets.items())),
        'track_segments_by_net': dict(sorted(track_segments_by_net.items())),
        'track_arcs_by_net': dict(sorted(track_arcs_by_net.items())),
        'track_primitives_by_net': dict(sorted({name: track_segments_by_net.get(name, 0) + track_arcs_by_net.get(name, 0) for name in set(track_segments_by_net) | set(track_arcs_by_net)}.items())),
        'vias_by_net': dict(sorted(via_nets.items())),
        'track_segments_by_layer': dict(sorted(track_segments_by_layer.items())),
        'track_primitives_by_layer': dict(sorted(track_primitives_by_layer.items())),
        'track_width_mm': ({'minimum': min(track_widths), 'maximum': max(track_widths),
                            'mean': round(sum(track_widths) / len(track_widths), 6)} if track_widths else None),
        'track_length_total_mm': round(track_length, 6),
        'footprints': footprints,
        'limitations': [
            'Read-only structural extraction; no PCB design-rule check (DRC) is performed.',
            'Track length is a centerline estimate from straight segments and three-point circular arcs; invalid/degenerate arcs are omitted.',
            'Clearance, impedance, thermal, current capacity and fabrication rules are not assessed.',
        ],
    }


def inspect_kicad_native(path: str | Path) -> dict[str, Any]:
    """Inspect a native KiCad schematic or PCB file without modifying it."""
    source = Path(path)
    if source.suffix.lower() not in {'.kicad_sch', '.kicad_pcb'}:
        raise ValueError('Expected a .kicad_sch or .kicad_pcb file')
    size = source.stat().st_size
    if size > _MAX_FILE_BYTES:
        raise ValueError(f'KiCad file is too large ({size:,} bytes; limit {_MAX_FILE_BYTES:,})')
    try:
        text = source.read_text(encoding='utf-8')
    except UnicodeDecodeError as exc:
        raise ValueError(f'KiCad file is not valid UTF-8: {source.name}') from exc
    root = parse_sexpr(text)
    expected = 'kicad_sch' if source.suffix.lower() == '.kicad_sch' else 'kicad_pcb'
    if _head(root) != expected:
        raise ValueError(f'File extension expects root {expected!r}; found {_head(root)!r}')
    return _inspect_schematic(root, source) if expected == 'kicad_sch' else _inspect_board(root, source)
