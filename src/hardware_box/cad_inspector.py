"""Read-only metadata inspection for STL, 3MF and STEP files (best-effort)."""
from pathlib import Path
import struct, zipfile, xml.etree.ElementTree as ET

def inspect_model(path):
    p=Path(path); ext=p.suffix.lower()
    if not p.is_file(): raise FileNotFoundError(p)
    result={'file':p.name,'format':ext.lstrip('.').upper(),'size_bytes':p.stat().st_size}
    if ext=='.stl': result.update(_inspect_stl(p))
    elif ext=='.3mf': result.update(_inspect_3mf(p))
    elif ext in {'.step','.stp'}: result.update(_inspect_step(p))
    else: raise ValueError('Supported formats: .stl, .3mf, .step, .stp')
    return result

def _inspect_stl(p):
    raw=p.read_bytes()
    if len(raw)>=84:
        count=struct.unpack_from('<I',raw,80)[0]
        if 84+count*50==len(raw):
            mins=[float('inf')]*3; maxs=[float('-inf')]*3
            for i in range(count):
                off=84+i*50+12
                for j in range(3):
                    xyz=struct.unpack_from('<3f',raw,off+j*12)
                    for k,v in enumerate(xyz): mins[k]=min(mins[k],v); maxs[k]=max(maxs[k],v)
            return {'encoding':'binary','triangle_count':count,'bounds_mm_assumed':_bounds(mins,maxs)}
    text=raw.decode('utf-8',errors='ignore')
    verts=[]
    for line in text.splitlines():
        parts=line.strip().split()
        if len(parts)==4 and parts[0].lower()=='vertex':
            try: verts.append(tuple(float(x) for x in parts[1:]))
            except ValueError: pass
    if not verts: raise ValueError('File does not look like a readable ASCII or binary STL')
    mins=[min(v[i] for v in verts) for i in range(3)]; maxs=[max(v[i] for v in verts) for i in range(3)]
    return {'encoding':'ascii','triangle_count':len(verts)//3,'bounds_mm_assumed':_bounds(mins,maxs)}

def _bounds(a,b): return {axis:{'min':round(a[i],4),'max':round(b[i],4),'size':round(b[i]-a[i],4)} for i,axis in enumerate(('x','y','z'))}
def _inspect_3mf(p):
    with zipfile.ZipFile(p) as z:
        names=z.namelist()
        model=next((n for n in names if n.lower().endswith('.model')),None)
        if not model: raise ValueError('3MF archive contains no .model file')
        root=ET.fromstring(z.read(model))
        vertices=root.findall('.//{*}mesh/{*}vertices/{*}vertex')
        triangles=root.findall('.//{*}mesh/{*}triangles/{*}triangle')
        coords=[(float(v.attrib['x']),float(v.attrib['y']),float(v.attrib['z'])) for v in vertices]
        bounds=None
        if coords: bounds=_bounds([min(v[i] for v in coords) for i in range(3)],[max(v[i] for v in coords) for i in range(3)])
        return {'model_entry':model,'vertex_count':len(vertices),'triangle_count':len(triangles),'bounds_model_units':bounds}
def _inspect_step(p):
    text=p.read_text(encoding='latin-1',errors='ignore')
    entities={}
    for token in ('MANIFOLD_SOLID_BREP','ADVANCED_FACE','CLOSED_SHELL','CARTESIAN_POINT','CIRCLE','CYLINDRICAL_SURFACE'):
        entities[token]=text.count(token)
    header=next((line.strip() for line in text.splitlines() if 'FILE_NAME' in line),None)
    return {'header_file_name_record':header,'entity_counts':entities,'note':'STEP geometry parsing is not performed; use a CAD kernel for exact geometry and topology.'}
