# Examples

These files are intentionally illustrative. The manufacturer names, MPNs, datasheet URLs, electrical values and KiCad exports are synthetic and must not be used to select or manufacture real parts.

- `device-electrical.json`: version 1 device record with a sample electrical load budget.
- `components/example-mcu.json`: synthetic local component catalog record.
- `kicad/bom.csv`: example BOM export with reference designators, MPN and manufacturer columns.
- `kicad/netlist.xml`: example KiCad XML netlist.
- `kicad-native/controller.kicad_sch`: small native schematic parser fixture.
- `kicad-native/controller.kicad_pcb`: small native PCB parser fixture.

Try from the repository root:

```bash
hardware-box validate examples/device-electrical.json
hardware-box check-electrical examples/device-electrical.json
hardware-box catalog-add examples/components/example-mcu.json
hardware-box catalog-search EX-MCU
hardware-box kicad-bom examples/kicad/bom.csv
hardware-box inspect-netlist examples/kicad/netlist.xml
hardware-box inspect-kicad examples/kicad-native/controller.kicad_sch
hardware-box inspect-kicad examples/kicad-native/controller.kicad_pcb
hardware-box audit-kicad examples/kicad/bom.csv examples/kicad/netlist.xml \\
  --schematic examples/kicad-native/controller.kicad_sch \\
  --pcb examples/kicad-native/controller.kicad_pcb
```

The native schematic and board are deliberately compact fixtures, not a complete manufacturable design. They have not been run through KiCad ERC or DRC.
