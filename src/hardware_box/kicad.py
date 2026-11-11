"""Import helpers for KiCad-generated BOM CSV files and XML netlists.

This reads exported interchange files; it does not open or modify KiCad projects.
"""
from __future__ import annotations
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

_ALIASES = {
    "references": ("references", "reference", "ref", "designator", "designators"),
    "quantity": ("qty", "quantity", "count"),
    "value": ("value", "component", "name", "part"),
    "footprint": ("footprint", "package"),
    "datasheet": ("datasheet", "datasheeturl", "url"),
    "mpn": ("mpn", "manufacturerpartnumber", "partnumber", "partno"),
    "manufacturer": ("manufacturer", "mfr", "vendor"),
}


def _norm(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


def parse_kicad_bom_csv(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    with source.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")
        header_map = {_norm(name): name for name in reader.fieldnames if name}
        mapping = {key: next((header_map[a] for a in aliases if a in header_map), None)
                   for key, aliases in _ALIASES.items()}
        if not mapping["value"] and not mapping["mpn"]:
            raise ValueError("Could not identify a Value/Component or MPN column")
        grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        for line_no, row in enumerate(reader, start=2):
            def get(key: str) -> str:
                col = mapping.get(key)
                return (row.get(col) or "").strip() if col else ""
            value, mpn, footprint = get("value"), get("mpn"), get("footprint")
            if not value and not mpn:
                continue
            refs_raw = get("references")
            refs = [r.strip() for r in refs_raw.replace(";", ",").split(",") if r.strip()]
            if len(refs) != len(set(refs)):
                raise ValueError(f"Duplicate reference designator on CSV line {line_no}")
            quantity_raw = get("quantity")
            try:
                quantity = int(quantity_raw) if quantity_raw else (len(refs) if refs else 1)
            except ValueError as exc:
                raise ValueError(f"Invalid quantity on CSV line {line_no}: {quantity_raw!r}") from exc
            if quantity < 1:
                raise ValueError(f"Quantity must be positive on CSV line {line_no}")
            key = (value, mpn, footprint, get("manufacturer"))
            item = grouped.setdefault(key, {"value": value, "mpn": mpn, "footprint": footprint,
                                             "manufacturer": get("manufacturer"), "datasheet": get("datasheet"),
                                             "quantity": 0, "references": []})
            item["quantity"] += quantity
            item["references"].extend(refs)
    components = sorted(grouped.values(), key=lambda x: (x["value"].casefold(), x["mpn"].casefold()))
    for item in components:
        item["references"] = sorted(item["references"])
    return {"source": source.name, "line_item_count": len(components),
            "reference_count": sum(len(item["references"]) for item in components), "components": components}


def inspect_kicad_netlist(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        root = ET.parse(source).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"Invalid KiCad XML netlist: {exc}") from exc
    if root.tag != "export":
        raise ValueError("Expected a KiCad XML netlist with <export> root")
    components = []
    for comp in root.findall("./components/comp"):
        components.append({"reference": comp.get("ref", ""),
                           "value": comp.findtext("value", default=""),
                           "footprint": comp.findtext("footprint", default="")})
    nets = []
    for net in root.findall("./nets/net"):
        nodes = [{"reference": node.get("ref", ""), "pin": node.get("pin", ""),
                  "pinfunction": node.get("pinfunction", "")}
                 for node in net.findall("node")]
        nets.append({"name": net.get("name", ""), "code": net.get("code", ""), "nodes": nodes})
    return {"file": source.name, "component_count": len(components), "net_count": len(nets),
            "connection_count": sum(len(net["nodes"]) for net in nets),
            "components": components, "nets": nets,
            "note": "Connectivity extracted from the exported XML netlist; ERC/DRC and electrical-rule validation are not performed."}
