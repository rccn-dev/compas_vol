# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

### Changed

### Removed

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

* The `ipyvolume` and `meshplot` notebook display paths, neither of which works
  on current Python. Drawing goes through `compas_vol.scene` instead.
* The Jupyter notebooks under `examples/notebooks/` and `examples/ita21/`,
  superseded by the scripts in `examples/`.
* `setup.py`, `setup.cfg`, `requirements.txt`, `requirements-dev.txt`, `pytest.ini`
  and `tasks.py`, all replaced by `pyproject.toml`.
