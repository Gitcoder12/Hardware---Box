# Engineering Deep Dive: Mesh, Tolerance and EDA Validation

This document explains the implemented algorithms and the boundaries of their claims. It is not a CAD-kernel or manufacturing certification.

## Triangle-mesh analysis (STL / 3MF)

For each triangle with vertices a, b and c:

- Surface area is one half the magnitude of the cross product (b − a) × (c − a).
- The signed tetrahedral contribution to volume is a dot (b × c), divided by six. A closed, consistently oriented shell's signed contributions are summed; the absolute value is reported.
- Triangle vertices are quantized using a configurable weld tolerance before edge-incidence analysis.
- An edge used by one face is a boundary edge; more than two uses is non-manifold by edge incidence; two uses in the same direction indicate inconsistent orientation.
- Degenerate and duplicate faces are separately counted.

Volume is reported only for a single closed, consistently oriented, non-degenerate, duplicate-free edge-connected shell. Open meshes, multiple shells or ambiguous topology return volume: null rather than a misleading scalar.

**Limits:** STL does not reliably carry units. 3MF model units are read, but object/build transforms are not applied. Edge-incidence checks cannot certify self-intersection freedom, all vertex-manifold conditions, B-rep geometry or printability.

## Worst-case tolerance stack

For an algebraic one-dimensional stack:

Y = sum(c_i * X_i)

where each c_i is a signed direction coefficient. Nominal stack is Y_nom = sum(c_i * X_i_nom). Worst-case upper/lower contributions swap when a coefficient is negative; their magnitudes are summed to produce conservative limits.

## RSS tolerance stack

Under independent contributor assumptions:

T_RSS,+ = sqrt(sum(T_i,+ squared))
T_RSS,- = sqrt(sum(T_i,- squared))

This is a statistical combination, not a worst-case guarantee. Independence and distribution assumptions must be justified using process data.

## Shaft / hole fit

Limit sizes:

D_h,min = D_h,nom − T_h,-
D_h,max = D_h,nom + T_h,+
D_s,min = D_s,nom − T_s,-
D_s,max = D_s,nom + T_s,+

Clearance limits:

C_min = D_h,min − D_s,max
C_max = D_h,max − D_s,min

The result is classified as clearance, interference or transition based on these interval endpoints.

For the optional statistical model, each dimension is approximated as a normal process whose asymmetric tolerance limits span ±k sigma:

mu = D_nom + (T_plus − T_minus)/2
sigma = (T_plus + T_minus)/(2k)

Assuming independent hole and shaft processes:

mu_C = mu_h − mu_s
sigma_C = sqrt(sigma_h squared + sigma_s squared)
P(interference) = Phi(−mu_C / sigma_C)

The reported configured-k-sigma clearance interval uses the selected sigma multiplier, rather than implying that every result is a three-sigma interval. The zero-variance case is handled deterministically. This model does not constitute full GD&T: datum reference frames, geometric form/position/orientation, material-condition modifiers, thermal effects, surface finish and manufacturing process capability are outside scope.

## BOM / KiCad cross-check

The BOM audit compares reference-designator inventories between BOM CSV and exported XML netlists, reports references missing on either side, and checks duplicate references, unknown net-node references, repeated pin-to-net assignments and optional native schematic/PCB comparisons.

A structural pass does not imply electrical correctness. Use KiCad ERC/DRC, electrical simulation and design review for those claims.
