"""Offline supply-chain and procurement analysis for declared BOM data."""
from __future__ import annotations
import csv
from pathlib import Path
from typing import Any

STATUSES={"active","nrnd","obsolete","unknown"}

def analyze_supply_chain(record: dict[str,Any]) -> dict[str,Any]:
    findings=[]
    for i,item in enumerate(record.get("components",[]),1):
        name=str(item.get("name",f"Component {i}")); specs=item.get("specifications",{}) or {}
        status=str(specs.get("lifecycle_status","unknown")).lower(); suppliers=specs.get("suppliers",[])
        if not item.get("part_number"): findings.append({"severity":"medium","component":name,"issue":"Missing manufacturer part number; sourcing identity is ambiguous."})
        if not item.get("manufacturer"): findings.append({"severity":"medium","component":name,"issue":"Missing manufacturer; authenticity and substitution checks are harder."})
        if status not in STATUSES or status=="unknown": findings.append({"severity":"low","component":name,"issue":"Lifecycle status is unknown; verify it against the manufacturer."})
        elif status in {"nrnd","obsolete"}: findings.append({"severity":"high","component":name,"issue":f"Declared lifecycle status is {status.upper()}; qualify an alternative."})
        if not isinstance(suppliers,list) or not suppliers: findings.append({"severity":"low","component":name,"issue":"No supplier list is declared."})
        elif len(suppliers)==1: findings.append({"severity":"medium","component":name,"issue":"Only one supplier is declared; assess single-source exposure."})
        lead=specs.get("lead_time_days")
        if lead is None: findings.append({"severity":"low","component":name,"issue":"Lead time is not recorded."})
        elif isinstance(lead,bool) or not isinstance(lead,(int,float)) or lead<0: findings.append({"severity":"high","component":name,"issue":"Lead time must be a non-negative number of days."})
        cost=specs.get("unit_cost")
        if cost is None: findings.append({"severity":"low","component":name,"issue":"Unit cost is not recorded; BOM cost is incomplete."})
        elif isinstance(cost,bool) or not isinstance(cost,(int,float)) or cost<0: findings.append({"severity":"high","component":name,"issue":"Unit cost must be a non-negative number."})
    counts={s:sum(f["severity"]==s for f in findings) for s in ("high","medium","low")}
    return {"device_id":record.get("id"),"component_count":len(record.get("components",[])),"finding_count":len(findings),"severity_counts":counts,"findings":findings,"limitations":["Offline analysis only; no live inventory or pricing is queried.","Lifecycle and supplier data are user-provided and must be verified.","A low finding count does not certify authenticity or availability."]}

def procurement_rows(record:dict[str,Any])->list[dict[str,Any]]:
    rows=[]
    for item in record.get("components",[]):
        s=item.get("specifications",{}) or {}; qty=item.get("quantity",0); cost=s.get("unit_cost")
        valid_cost=isinstance(cost,(int,float)) and not isinstance(cost,bool) and cost>=0 and isinstance(qty,int) and not isinstance(qty,bool) and qty>0
        rows.append({"device_id":record.get("id",""),"component":item.get("name",""),"manufacturer":item.get("manufacturer",""),"part_number":item.get("part_number",""),"quantity":qty,"unit_cost":cost if valid_cost else "","currency":s.get("currency","USD") if valid_cost else "","extended_cost":round(qty*cost,4) if valid_cost else "","lifecycle_status":s.get("lifecycle_status","unknown"),"lead_time_days":s.get("lead_time_days",""),"suppliers":"; ".join(s.get("suppliers",[])) if isinstance(s.get("suppliers",[]),list) else ""})
    return rows

def export_procurement_csv(record:dict[str,Any],destination:str|Path)->Path:
    path=Path(destination); path.parent.mkdir(parents=True,exist_ok=True); rows=procurement_rows(record)
    cols=["device_id","component","manufacturer","part_number","quantity","unit_cost","currency","extended_cost","lifecycle_status","lead_time_days","suppliers"]
    with path.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(rows)
    return path

def cost_summary(record:dict[str,Any])->dict[str,Any]:
    totals={}; missing=0
    for item in record.get("components",[]):
        s=item.get("specifications",{}) or {}; c=s.get("unit_cost"); q=item.get("quantity",0)
        if isinstance(c,(int,float)) and not isinstance(c,bool) and c>=0 and isinstance(q,int) and not isinstance(q,bool) and q>0:
            currency=str(s.get("currency","USD")); totals[currency]=totals.get(currency,0.0)+c*q
        else: missing+=1
    return {"totals_by_currency":{k:round(v,4) for k,v in sorted(totals.items())},"components_without_cost":missing,"is_complete":missing==0}
