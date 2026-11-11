# Mechanical sample assets

`tetrahedron.stl` and `tetrahedron.3mf` are simple closed tetrahedron meshes with coordinates authored in millimeters. They are software test fixtures, not manufacturing designs. Run:

```bash
hardware-box analyze-mesh examples/mechanical/tetrahedron.stl --units mm
hardware-box analyze-mesh examples/mechanical/tetrahedron.3mf --units mm
```
