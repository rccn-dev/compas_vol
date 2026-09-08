# compas_vol

Volumetric modelling with signed distance functions, for **COMPAS 2**.

A fork of [`dbt-ethz/compas_vol`](https://github.com/dbt-ethz/compas_vol), originally
by Mathias Bernhard at Digital Building Technologies, ETH Zurich. The original targets
COMPAS 1 and no longer imports, let alone runs, against the current stack. This fork
updates it to COMPAS 2.15, NumPy 2 and Python 3.13, and fixes a number of defects that
were present independently of the COMPAS version.

The architecture and the API shape are the original's. See the
[porting guide](https://rccn-dev.github.io/compas_vol/porting.html) for every
behavioural difference, and [AUTHORS.md](AUTHORS.md) for credits.

## Install

```bash
uv sync                        # core: compas + numpy
uv sync --extra meshing        # + scikit-image, scipy   (iso-surfacing, Blur)
uv sync --extra viewer         # + compas_viewer         (standalone 3D viewer)
uv sync --extra all            # everything
```

The core install has no heavy dependencies. The `viewer` extra pulls in PySide6, which
is large, so it is kept optional.

## Quick start

```python
from compas.geometry import Box, Point, Sphere
from compas_viewer import Viewer
from compas_vol.primitives import VolBox, VolSphere
from compas_vol.combinations import Subtraction

shape = Subtraction(
    VolBox(Box(20, 15, 10), radius=2.5),
    VolSphere(Sphere(9, point=Point(5, 6, 0))),
)

print(shape.get_distance((0, 0, 0)))   # signed distance at one point

viewer = Viewer()
viewer.scene.add(shape, bounds=20.0, resolution=100)
viewer.show()
```

Every object exposes two distance methods:

- `get_distance(point)` — one point, returns a float.
- `get_distance_numpy(x, y, z)` — a whole grid at once, given `np.ogrid` arrays.

The two are tested to agree to machine precision for every class in the package.

## Meshing

```python
from compas_vol.meshing import generate_mesh, sample, Octree

mesh = generate_mesh(shape, bounds=20.0, resolution=100)   # -> compas Mesh
dm, origin, spacing = sample(shape, bounds=20.0, resolution=64)

tree = Octree(shape, world_size=40.0, max_level=4)          # adaptive refinement
tree.build()
boxes = tree.to_boxes()
```

`bounds` accepts a `compas.geometry.Box`, a scalar `s` for the cube `[-s, s]`, a
6-sequence `(xmin, ymin, zmin, xmax, ymax, zmax)`, or three `(min, max)` pairs.

## Serialization

Every volumetric object is a `compas.data.Data` subclass, so whole CSG trees round-trip
through COMPAS JSON, children included:

```python
from compas.data import json_dumps, json_loads
restored = json_loads(json_dumps(shape))
```

COMPAS 1 shipped objects between processes by `eval`-ing their `repr` string. That path
is gone; `compas_vol.utilities.dumps_tree` / `loads_tree` use JSON instead.

## Viewing

Volumetric objects are **registered scene objects**, following the COMPAS 2 pattern: the
classes themselves know nothing about drawing, and `compas_vol.scene` declares separately
how to draw them. So they go straight into a scene, next to anything else:

```python
from compas_viewer import Viewer

viewer = Viewer()
viewer.scene.add(shape, bounds=20.0, resolution=100, opacity=0.5)
viewer.scene.add(some_box, show_faces=False)     # composes with ordinary geometry
viewer.show()
```

An SDF is an implicit function, so it has to be sampled before it can be drawn. That is
the same situation a `compas.geometry.Sphere` is in — it has to be tessellated — and it
is handled the same way: the sampling parameters ride along on the `scene.add` call,
exactly as `u`/`v` do for `ShapeObject`.

Unlike `u`/`v`, **`bounds` has no sensible default** and is required. A `TPMS` or
`Lattice` is infinite and an `Intersection` cannot report an extent, so the caller has to
say where to look. Omitting it raises with an explanatory message.

Registration is discovered automatically: COMPAS scans installed top-level packages whose
name starts with `compas` and reads their `__all_plugins__`. Since this package is named
`compas_vol`, nothing needs wiring up. Only the `Viewer` context is implemented; Rhino,
Blender and Grasshopper could be added in `compas_vol/scene/` the same way.

There is deliberately no `view()` convenience wrapper. `scene.add` is the one way to
draw a volumetric object — it is the same call used for every other COMPAS type, it
composes, and it does not hide the fact that `compas_viewer.Viewer` is a singleton
sharing one scene.

## What changed from the COMPAS 1 version

Briefly:

- **Ported to COMPAS 2**, which reorganized geometry constructors
  (`Box(x, y, z, frame=...)`, `Sphere(r, point=...)`) and replaced `to_data`/`from_data`
  with the `__data__`/`__from_data__` protocol.
- **NumPy 2.** The `np.array([x, y, z, 1], dtype=object)` transformation trick was
  replaced throughout; the variants written without `dtype=object` raise outright on
  NumPy 2.
- **Fifteen correctness fixes**, each with a regression test — among them query points
  being mutated in place, `Voronoi` not actually computing a Voronoi field, `Twist`
  ignoring its angle, `Octree` being entirely non-functional, and `Sine` raising
  `NameError` on construction.
- **Stubs filled in.** `GDF` and `Curvature` were unimplemented; `TPMSAttractor` had its
  attractor logic commented out as Rhino-specific code.
- **Drawing moved to scene objects**, replacing the `ipyvolume` / `meshplot` notebook
  path, neither of which works on current Python.

The [porting guide](docs/porting.rst) has the itemized list, and
[CHANGELOG.md](CHANGELOG.md) records it per release.

## Examples

`examples/` holds short, runnable ports of the original scripts — one CSG idea each:

```bash
uv run --extra all python examples/example_tpms.py
```

`examples/vol_mesh_examples/` holds fuller modelling studies, each of which opens the
viewer and then an interactive slice through the distance field. Six cover ordinary
constructive modelling; six cover graded and non-linear structures — cell size driven by
an attractor, cell *type* morphing across a part, a lattice twisted into a helix,
radially graded wall density, aperiodic Voronoi with a seed gradient, and scalar-field
arithmetic. See the [README there](examples/vol_mesh_examples/README.md).

```bash
uv sync --extra examples
uv run python examples/vol_mesh_examples/8_morphing_microstructure.py
```

## Tests

```bash
uv run --extra meshing python -m pytest
```

The suite parametrizes every volumetric class over shared checks: the two distance
methods must agree on a grid, queries must not mutate their input, and every object must
survive a JSON round trip. Analytic cases pin the geometry itself (a radius-5 sphere has
mean curvature 0.2, a unit box corner is `sqrt(3)` away, and so on).

## Documentation

```bash
uv sync --group docs
uv run sphinx-build -b html docs docs/_build/html
```

## License

MIT, as the original. The upstream copyright notice is retained; see
[LICENSE](LICENSE).
