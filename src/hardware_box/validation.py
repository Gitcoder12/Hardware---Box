"""Strict validation for versioned Hardware-Box device records."""
from __future__ import annotations
import re
from .electrical import analyze_electrical

CATEGORIES = {"mobile", "computing", "entertainment", "electronics", "mechanical", "appliances", "other"}
LEVELS = {"unverified", "documented", "verified"}
REQUIRED = {"id", "name", "category", "manufacturer", "revision", "components", "interfaces", "provenance"}
OPTIONAL = {"schema_version", "electrical", "tags", "documents"}
TOP_LEVEL = REQUIRED | OPTIONAL
COMPONENT_FIELDS = {"name", "quantity", "part_number", "manufacturer", "specifications"}
INTERFACE_FIELDS = {"name", "protocol", "connector", "pin_count", "direction", "voltage_min_v", "voltage_max_v", "current_max_a", "notes"}


def validate_device(data: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict): return ["root: expected object"]
    for key in sorted(REQUIRED - data.keys()): errors.append(f"{key}: missing required field")
    for key in sorted(data.keys() - TOP_LEVEL): errors.append(f"{key}: unknown field")

    version = data.get("schema_version")
    if version is not None and (type(version) is not int or version != 1):
        errors.append("schema_version: expected integer 1; migrate legacy records before validation")
    for key in ("name", "manufacturer", "revision"):
        if key in data and (not isinstance(data[key], str) or not data[key].strip()):
            errors.append(f"{key}: expected nonempty string")
    if "id" in data and (not isinstance(data["id"], str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", data["id"])):
        errors.append("id: expected lowercase slug (letters, numbers, hyphens)")
    if "category" in data and (not isinstance(data["category"], str) or data["category"] not in CATEGORIES):
        errors.append(f"category: expected one of {', '.join(sorted(CATEGORIES))}")

    components = data.get("components")
    if "components" in data and not isinstance(components, list): errors.append("components: expected array")
    if isinstance(components, list):
        seen: set[str] = set()
        for i, item in enumerate(components):
            prefix = f"components[{i}]"
            if not isinstance(item, dict): errors.append(f"{prefix}: expected object"); continue
            for key in sorted(item.keys() - COMPONENT_FIELDS): errors.append(f"{prefix}.{key}: unknown field")
            name = item.get("name")
            if not isinstance(name, str) or not name.strip(): errors.append(f"{prefix}.name: expected nonempty string")
            elif name.casefold() in seen: errors.append(f"{prefix}.name: duplicate component name")
            else: seen.add(name.casefold())
            quantity = item.get("quantity")
            if type(quantity) is not int or quantity < 1: errors.append(f"{prefix}.quantity: expected positive integer")
            for key in ("part_number", "manufacturer"):
                if key in item and (not isinstance(item[key], str) or not item[key].strip()):
                    errors.append(f"{prefix}.{key}: expected nonempty string")
            if "specifications" in item and (not isinstance(item["specifications"], dict) or not all(isinstance(k, str) for k in item["specifications"])):
                errors.append(f"{prefix}.specifications: expected object with string keys")

    interfaces = data.get("interfaces")
    if "interfaces" in data and not isinstance(interfaces, list): errors.append("interfaces: expected array")
    if isinstance(interfaces, list):
        seen_interfaces: set[str] = set()
        for i, value in enumerate(interfaces):
            prefix = f"interfaces[{i}]"
            if isinstance(value, str): name = value
            elif isinstance(value, dict):
                name = value.get("name")
                for key in sorted(value.keys() - INTERFACE_FIELDS): errors.append(f"{prefix}.{key}: unknown field")
                for field in ("pin_count",):
                    if field in value and (type(value[field]) is not int or value[field] < 1): errors.append(f"{prefix}.{field}: expected positive integer")
                for field in ("voltage_min_v", "voltage_max_v", "current_max_a"):
                    if field in value and (isinstance(value[field], bool) or not isinstance(value[field], (int, float)) or value[field] < 0):
                        errors.append(f"{prefix}.{field}: expected non-negative number")
                if all(k in value for k in ("voltage_min_v", "voltage_max_v")) and value["voltage_min_v"] > value["voltage_max_v"]:
                    errors.append(f"{prefix}: voltage_min_v exceeds voltage_max_v")
                if "direction" in value and (not isinstance(value["direction"], str) or value["direction"] not in {"input", "output", "bidirectional", "passive", "power_in", "power_out", "unknown"}):
                    errors.append(f"{prefix}.direction: unsupported direction")
            else:
                errors.append(f"{prefix}: expected string or interface object"); continue
            if not isinstance(name, str) or not name.strip(): errors.append(f"{prefix}.name: expected nonempty string")
            elif name.casefold() in seen_interfaces: errors.append(f"{prefix}: duplicate interface")
            else: seen_interfaces.add(name.casefold())

    if "provenance" in data:
        provenance = data["provenance"]
        if not isinstance(provenance, dict): errors.append("provenance: expected object")
        else:
            for key in ("source", "license"):
                if not isinstance(provenance.get(key), str) or not provenance[key].strip():
                    errors.append(f"provenance.{key}: expected nonempty string")
            if provenance.get("verification") not in LEVELS:
                errors.append(f"provenance.verification: expected one of {', '.join(sorted(LEVELS))}")
            for key in sorted(provenance.keys() - {"source", "license", "verification"}): errors.append(f"provenance.{key}: unknown field")

    if "electrical" in data:
        analysis = analyze_electrical({"electrical": data["electrical"]})
        errors.extend(analysis.get("errors", []))
    if "tags" in data and (not isinstance(data["tags"], list) or not all(isinstance(x, str) and x.strip() for x in data["tags"])):
        errors.append("tags: expected array of nonempty strings")
    if "documents" in data:
        docs = data["documents"]
        if not isinstance(docs, list): errors.append("documents: expected array")
        else:
            for i, doc in enumerate(docs):
                if not isinstance(doc, dict) or not isinstance(doc.get("path"), str) or not doc["path"].strip():
                    errors.append(f"documents[{i}]: expected object with nonempty path")
    return errors
