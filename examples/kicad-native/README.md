# Native KiCad sample project

These compact `.kicad_sch` and `.kicad_pcb` files are deliberately small parser fixtures for Hardware-Box. They demonstrate the file structures inspected by `inspect-kicad`; they are not a complete manufacturable circuit design and have not been validated by KiCad ERC/DRC.

Run from the repository root:

```bash
hardware-box inspect-kicad examples/kicad-native/controller.kicad_sch
hardware-box inspect-kicad examples/kicad-native/controller.kicad_pcb
hardware-box audit-kicad examples/kicad/bom.csv examples/kicad/netlist.xml \\
  --schematic examples/kicad-native/controller.kicad_sch \\
  --pcb examples/kicad-native/controller.kicad_pcb
```

The audit uses reference-inventory consistency, not full netlist-to-PCB equivalence.
