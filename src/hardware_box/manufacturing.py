"""Conservative, explainable first-pass fabrication hints from file type and metadata."""
def suggest_processes(model_info):
    fmt=model_info.get('format','').upper()
    if fmt=='STL' or fmt=='3MF':
        return [{'process':'FDM/FFF','reason':'Common route for suitable thermoplastic parts; check geometry, material, strength and tolerances.'},
                {'process':'SLA/DLP','reason':'Potential option for small, detailed resin parts; check resin properties and post-processing.'},
                {'process':'SLS','reason':'Potential option for suitable powder-bed polymer parts; check service capability and design rules.'}]
    if fmt in {'STEP','STP'}:
        return [{'process':'CNC machining','reason':'Potential route for suitable machinable geometry and materials.'},
                {'process':'Sheet fabrication / laser cutting','reason':'Only where the design can be adapted to sheet-based parts.'},
                {'process':'3D printing','reason':'Possible after export to a suitable mesh and design-for-additive review.'}]
    return []
