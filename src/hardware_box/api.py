"""Optional local-development REST API. Install with: pip install -e '.[api]'"""
from __future__ import annotations
import os
from fastapi import FastAPI, HTTPException, Query
from . import __version__
from .registry import add_device, update_device, get_device, list_devices, delete_device
from .validation import validate_device
from .compatibility import compare_devices
from .electrical import analyze_electrical
from .catalog import add_component, get_component, search_components

app = FastAPI(
    title="Hardware-Box API",
    version=__version__,
    description="Local hardware documentation and engineering analysis API",
)
DB = os.environ.get("HARDWARE_BOX_DB", ".hardware-box/registry.sqlite3")
CATALOG_DB = os.environ.get("HARDWARE_BOX_CATALOG_DB", ".hardware-box/catalog.sqlite3")


@app.get("/health")
def health():
    return {"status": "ok", "service": "hardware-box", "version": __version__}


@app.get("/devices")
def devices(category: str | None = None, q: str | None = Query(default=None, max_length=100)):
    return list_devices(DB, category, q)


@app.post("/devices", status_code=201)
def create_device(record: dict):
    errors = validate_device(record)
    if errors:
        raise HTTPException(422, detail=errors)
    try:
        add_device(DB, record)
    except Exception as exc:
        raise HTTPException(409, detail=str(exc)) from exc
    return record


@app.get("/devices/{device_id}")
def device(device_id: str):
    item = get_device(DB, device_id)
    if item is None:
        raise HTTPException(404, "Device not found")
    return item


@app.put("/devices/{device_id}")
def replace_device(device_id: str, record: dict):
    if record.get("id") != device_id:
        raise HTTPException(400, "Path id and record id must match")
    errors = validate_device(record)
    if errors:
        raise HTTPException(422, detail=errors)
    try:
        update_device(DB, record)
    except KeyError as exc:
        raise HTTPException(404, "Device not found") from exc
    return record


@app.delete("/devices/{device_id}", status_code=204)
def remove_device(device_id: str):
    if not delete_device(DB, device_id):
        raise HTTPException(404, "Device not found")


@app.post("/compare")
def compare(payload: dict):
    left, right = payload.get("left"), payload.get("right")
    if not isinstance(left, dict) or not isinstance(right, dict):
        raise HTTPException(422, "Provide left and right device records")
    return compare_devices(left, right)


@app.post("/electrical-check")
def electrical_check(record: dict):
    result = analyze_electrical(record)
    if not result.get("valid", False):
        raise HTTPException(422, detail=result.get("errors", []))
    return result


@app.get("/components")
def components(q: str = Query(default="", max_length=100), category: str | None = None,
              limit: int = Query(default=100, ge=1, le=1000)):
    return search_components(CATALOG_DB, q, category, limit)


@app.post("/components", status_code=201)
def create_component(item: dict):
    try:
        add_component(CATALOG_DB, item)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(409, detail=str(exc)) from exc
    return get_component(CATALOG_DB, item["mpn"])


@app.get("/components/{mpn}")
def component(mpn: str):
    item = get_component(CATALOG_DB, mpn)
    if item is None:
        raise HTTPException(404, "Component not found")
    return item
