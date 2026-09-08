# Volumetric modelling examples

Run any of these with:

```bash
uv sync --extra examples
uv run python examples/vol_mesh_examples/6_tpms.py
```

Each script opens the COMPAS viewer with the meshed result. Close it and an
interactive slice through the signed distance field opens: drag the slider to
move the cutting plane, blue is inside, red is outside, and the black contour
is the surface that gets meshed.

## The scripts

| | | |
|---|---|---|
| `template.py` | the full pipeline written out step by step, no helpers | reference |
| `1_extrusion.py` | a star polygon extruded along a tilted frame | primitives |
| `2_intersection.py` | sphere ∩ filleted box | CSG |
| `3_union.py` | sphere ∪ box, with the hard seam a union leaves | CSG |
| `4_smooth_union.py` | the same pair blended | CSG |
| `5_lattice.py` | a periodic strut lattice trimmed to a cube | microstructure |
| `6_tpms.py` | a TPMS shell with thickness graded by a plane | microstructure |
| `7_graded_tpms.py` | **cell size** driven by distance to an attractor | graded |
| `8_morphing_microstructure.py` | **cell type** morphing gyroid → Schwartz-P across the part | graded |
| `9_twisted_lattice.py` | a lattice sheared into a helix by warping the domain | non-linear |
| `10_graded_shell.py` | wall density graded radially, ~25% at the core to ~12% at the rim | graded |
| `11_graded_voronoi.py` | aperiodic cells with a seed-density gradient | stochastic |
| `12_field_math.py` | arithmetic on fields, producing surfaces CSG cannot | non-linear |

The first six are ordinary constructive modelling. The last six are the ones
worth reading if you already know CSG: nothing in them is a boolean of two
finished shapes, and each varies a property continuously through space rather
than tiling one unit cell.

## Notes

`_common.py` holds the sampling, viewing and slice-inspection code that would
otherwise be copy-pasted into every script, so each example is just its CSG
tree. `template.py` deliberately does not use it.

Resolution defaults to 160³, which takes a few seconds per example. Drop
`RESOLUTION` in `_common.py`, or pass `resolution=` to `demo()`, while
iterating on a model.

STL export is off by default so that running an example does not drop a large
file in the repository. Pass `export=True` to `demo()` (or set `EXPORT = True`
in `template.py`) to write one; `*.stl` is gitignored.

`11_graded_voronoi.py` is the slowest, because a Voronoi field walks the whole
seed list twice per sample. It runs at a reduced resolution for that reason.
