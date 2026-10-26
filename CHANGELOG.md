# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] 2026-10-26

### Fixed

* `fabrication.inspect` counted the face resting on the build plate as overhang, so a
  part printed flat read as up to half overhang. The plate contact is now left out.

* `processes.pitting` read `resistance` backwards. It now pits where
  `resistance < -threshold`, as in `differential`: 1 never pits. Default
  results change where pits fall, not how many.
* `Piece.export_stl` left every piece open at its cut faces; it now samples
  past the box and its pins.
* `meshing.iso_surface` made zero-area triangles where a surface lay on a grid
  plane, which STL readers weld into non-manifold edges.
* Neovius read `3 cos x + cos y + cos z` instead of `3 (cos x + cos y + cos z)`,
  and Lidinoid had two index typos (both from upstream). Their meshes change.
* Grasshopper components with a geometry or list input failed in Rhino 8 with
  "Error getting GH_ScriptInstance instance"; every component now imports
  `Rhino` and `System`.
* The Shell component centres the wall on the surface, as its tooltip said.

### Added

Processes
* `compas_vol.processes`: one operator, `evolve`, and the weathering
  (`abrasion`, `differential`, `pitting`, `strata`, `runoff`, `jointing`),
  growth (`fingering`, `accretion`, `branching`, `diffusion_limited`) and
  generator (`spinodal`, `reaction_diffusion`) presets built on it; `fbm` and
  `value_noise` in world coordinates; results carry their history. Needs the
  new `processes` extra.
* `Field.constrain(keep=..., within=..., margin=...)`: material no process may
  remove and an envelope growth may not leave; `Field.violation()` measures it.
* `Field.from_object(..., voxel=...)` and `processes.lattice`: sampling on a
  world lattice. `Field.cropped()`.
* `docs/processes.rst`: the method, its invariants, accuracy and cost.

Modelling
* `microstructures.TPMSSolid`: a TPMS in model units (`cell_size`,
  `thickness`, `mode`), with graded `thickness` and `offset`. TPMS type
  `"IWP"`.
* `modifications.Remap` (a field as a parameter driver), `Offset` (grow by a
  distance that may be a field) and `Conform` (a lattice that follows a skin).
* `primitives.VolGrid`, a sampled field, and `VolGrid.from_mesh`, signed
  distance to any closed mesh.

Fabrication and meshing
* `compas_vol.fabrication`: `inspect` (pieces, sealed cavities, overhang,
  mid-air starts, wall thickness) and the repairs `keep_largest`,
  `drain_voids`, `make_self_supporting`. `Report.__str__`.
* `meshing.write_stl` and `export_stl`, about 45x faster than a COMPAS mesh's
  `to_stl`; `meshing.iso_surface` for an already-sampled grid;
  `meshing.is_watertight`.

Assembly
* `compas_vol.assembly`: `segment` cuts a model into pieces, by grid or by
  `cells` (any boxes); `Pins` adds clearance and pin/socket joints on every
  shared face; `Assembly.check` inspects every piece; `place_cuts` and
  `section_cost` move cuts off features.
* `Assembly.build` processes pieces one at a time with a halo; `Seams` checks
  that neighbours meet; `Assembly.cost` compares the whole model with the
  largest piece.

Grasshopper and contexts
* `compas_vol.ghpython`: 21 components under `COMPAS Vol` -- primitives, TPMS,
  boolean, shell, mesh, inspect, info, and twelve processes with a `run`
  toggle -- and the conversions they use.
* `compas_vol.nodes`: the components without Grasshopper, one function each.
* `compas_vol.runtime`: the context and the optional dependencies present;
  `require` names the extra a missing import needs.
* `scripts/ghuser`: build and verify the components. `scripts/ghuser dev`
  links the build into Grasshopper, checks requirements in Rhino's Python and
  reloads a running Rhino. `scripts/check_headless.py` and a release workflow
  run in CI.

Examples
* `examples/`: 26 scripts numbered in reading order and indexed by topic;
  `tests/test_examples.py` keeps them importing.

The grid roof, built alongside these features, lives in [grid-roof](https://github.com/rccn-dev/grid-roof) with what
it needed that is too specific for this package: drainage, a plan height
field, a world-coordinate foam and a beam-grid kit of parts.

### Changed

* Python floor 3.9 (Rhino 8's interpreter), with relaxed `scipy` and
  `scikit-image` bounds. CI runs 3.9 and 3.13.
* `meshing.sample` runs in parallel slabs, bit-identical to serial (about 5x on
  ten cores); `workers=1` opts out. It returns a writable array.
* `Voronoi` skips seeds that cannot affect a block, exactly: 4.6x faster at 340
  seeds, 8x at 800.
* `base.transform_numpy` broadcasts each coordinate only over the axes it
  depends on, so a plan shape is evaluated per plan point (7x faster sampling
  in the roof).
* `processes.opened` never adds material and `closed` never removes it, also
  on a constrained field.
* TPMS type `"SchwarzP"`; `"SchwartzP"`, `"Primitive"` and `"SchwarzD"` still
  work. An unknown type raises `ValueError` instead of falling back to the
  gyroid. `TPMS.wavelength` is documented as half the period.

### Removed

* `examples/example_*.py`, the upstream one-operation ports; each idea is in
  the curated examples.
* `compas_vol.HOME`, `DATA`, `DOCS`, `TEMP`, which pointed beside the source
  checkout.
* From `compas_vol.utilities`: `export_ipv_mesh`, `export_ski_mesh`,
  `export_layer`, `get_compas_mesh`, `get_random_vector_2D`,
  `get_random_vector_3D`, `bbox_edges`. `get_iso_vfs`, `get_iso_mesh`,
  `dumps_tree`, `loads_tree` and `get_vfs_from_tree` stay.

## [0.2.0] 2026-09-08

First release of the fork of [dbt-ethz/compas_vol](https://github.com/dbt-ethz/compas_vol).
Upstream's last release was 0.1.0, targeting COMPAS 1; this release targets
COMPAS 2. See [the porting guide](https://rccn-dev.github.io/compas_vol/porting.html)
for the full account.

### Added

* `compas_vol.base.VolObject`, a common base class for every volumetric object.
* `compas_vol.scene`, registering volumetric objects as COMPAS 2 scene objects,
  so they can be passed to `scene.add` like any other COMPAS geometry.
* `compas_vol.meshing.marching`, with `generate_mesh`, `generate_vertices_and_faces`,
  `sample` and `normalize_bounds`.
* Implementations for `GDF` and `Curvature`, which were stubs upstream.
* `TPMSAttractor` now grades wavelength by distance to any volumetric object;
  upstream left the attractor logic commented out as Rhino-specific code.
* A test suite parametrizing every volumetric class over shared checks, plus
  `tests/test_regressions.py` pinning each correctness fix below.
* `examples/vol_mesh_examples/`, twelve modelling studies covering constructive
  modelling and graded, non-linear and stochastic structures.

### Changed

* Ported to COMPAS 2.15, NumPy 2 and Python 3.13. Requires Python >= 3.13.
* Geometry constructors follow COMPAS 2 signatures (`Box(x, y, z, frame=...)`,
  `Sphere(r, point=...)`, and so on).
* Serialization uses the COMPAS 2 `__data__` / `__from_data__` protocol, so CSG
  trees round-trip through `json_dumps` / `json_loads`. `dumps_tree` / `loads_tree`
  use JSON instead of `eval`-ing a `repr` string.
* Transformations use an explicit matrix-vector expansion
  (`compas_vol.base.transform_numpy`) instead of `np.array([x, y, z, 1], dtype=object)`.
* Packaging moved from `setup.py` to `pyproject.toml` with the `uv_build` backend.
  Heavy dependencies are behind the `meshing`, `viewer` and `examples` extras.
* Documentation rebuilt for the current API, with a porting guide.

### Fixed

* Query points were mutated in place, so `get_distance(p)` returned a different
  answer on each call with the same point.
* `Sine` raised `NameError` on construction.
* `Division.__repr__` and `Multiplication.__repr__` referenced an undefined attribute.
* `Blend` returned `None` for any ramp type other than 0 or 1.
* `TPMSPolar` called the nonexistent `math.arctan2`, read an unassigned attribute
  in its `wavelength` property, and never applied its wavelength argument.
* `Voronoi` mixed in a term independent of the query point, so it was not a
  Voronoi field, and imported from `numpy.core`, so it failed to import at all.
* `Twist` ignored its `angle` argument in both code paths.
* `SmoothUnionList.get_distance_numpy` returned a transposed grid.
* `Gradient.get_gradient_numpy` normalized over a reduced axis without
  re-inserting it.
* `Octree` was non-functional: it never stored the object to sample, called
  `get_distance` with three loose coordinates, and read an attribute `OctNode`
  never defined.
* The dodecahedron's vectorized branch used `(1 + sqrt(5)/2)` where the scalar
  branch used `(1 + sqrt(5))/2`.
* `Heart.get_distance` ignored its frame while `get_distance_numpy` honoured it.
* Meshes came out translated: marching cubes returns grid-relative coordinates
  and the grid origin was never added back.
* `get_iso_mesh` and `get_iso_vfs` hard-coded a `VolBox` reconstruction, so they
  only ever worked for boxes.
* A missing comma in `combinations.__all__` concatenated `'SmoothUnionList'` and
  `'SmoothIntersection'` into one name.

### Removed

* `compas_vol.HOME`, `DATA`, `DOCS` and `TEMP`. They pointed at directories
  beside the *source* checkout, two of which never existed, and nothing used
  them; in an installed package they resolved into site-packages.
* From `compas_vol.utilities`: `export_ipv_mesh`, `export_ski_mesh`,
  `export_layer`, `get_compas_mesh`, `get_random_vector_2D`,
  `get_random_vector_3D` and `bbox_edges`. These served the ipyvolume and
  meshplot notebook workflow that this fork already replaced with scene
  objects, or wrapped a single COMPAS call. The COMPAS 1 compatibility that
  is still useful -- `get_iso_vfs`, `get_iso_mesh`, `dumps_tree`,
  `loads_tree`, `get_vfs_from_tree` -- stays.

* The `ipyvolume` and `meshplot` notebook display paths, neither of which works
  on current Python. Drawing goes through `compas_vol.scene` instead.
* The Jupyter notebooks under `examples/notebooks/` and `examples/ita21/`,
  superseded by the scripts in `examples/`.
* `setup.py`, `setup.cfg`, `requirements.txt`, `requirements-dev.txt`, `pytest.ini`
  and `tasks.py`, all replaced by `pyproject.toml`.
