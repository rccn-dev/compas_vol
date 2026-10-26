# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`compas_vol`: volumetric modelling with signed distance functions (SDFs) for **COMPAS 2**. It's a fork of `dbt-ethz/compas_vol` (which targets COMPAS 1), ported to COMPAS ≥2.15 and NumPy 2. Issues and PRs go to `rccn-dev/compas_vol`, branching off `main` (there is no `master`). `docs/porting.rst` lists every way this fork behaves differently from upstream.

## Commands

The project uses `uv`, which also manages the Python version.

```bash
uv sync --extra meshing --group dev          # dev setup (scikit-image/scipy, pytest, ruff)
uv sync --extra all                          # + compas_viewer (PySide6) and matplotlib, for examples
uv run ruff check .                          # lint (CI runs this)
uv run --extra meshing python -m pytest      # full suite, including doctests in src/
uv run --extra meshing python -m pytest tests/test_geometry.py::test_name
uv run --extra meshing python -m pytest tests/test_distance.py -k VolSphere   # one class across the shared checks
uv sync --group docs && uv run sphinx-build -b html -W docs docs/_build/html  # -W = warnings are errors, as in CI
uv run --extra examples python examples/02_booleans.py
uv run -p 3.9 --extra meshing --extra processes python -m pytest   # the Rhino 8 floor
uv run -p 3.9 --no-default-groups python scripts/check_headless.py # core-only contract
scripts/ghuser dev                            # build, verify, link into Grasshopper, check deps, reload a running Rhino
scripts/ghuser dev status                     # read-only: link, stale copies, deps, imports
scripts/ghuser                                # same in the ghuser-builder Docker image, with icons
uv run python scripts/make_icons.py           # redraw the component icons
```

pytest is configured with `--doctest-modules --pyargs` and `testpaths = ["tests", "compas_vol"]`, so doctests run against the *installed* package. `src/compas_vol/conftest.py` skips `scene/volobject.py` and `meshing/marching.py` when their optional dependencies aren't installed, and single doctests listed in `OPTIONAL_DOCTESTS` (the process nodes in `nodes.py`). CI does not install the viewer extra.

**Python 3.9 is a hard floor, not a leftover.** It is the CPython Rhino 8 embeds, and holding it is the only reason the package works in Grasshopper. Ruff's `target-version = "py39"` rejects newer syntax, CI runs the suite on 3.9 and 3.13, and `tests/test_ghpython.py` parses the component sources with `feature_version=(3, 9)`. Don't raise it, and don't add a dependency pin that drops 3.9 wheels.

Ruff enables only `E`, `W`, `F` and `NPY`, with a line length of 120. `UP` and `I` are left off on purpose, so don't turn `.format()` calls into f-strings or reorder imports as part of unrelated changes.

## Architecture

**`VolObject` (`src/compas_vol/base.py`)** is the root class. It subclasses `compas.data.Data`, which gives it JSON serialization, `copy()` and a guid. Each subclass implements:
- `get_distance(point)`: a single point, returns a float (negative inside).
- `get_distance_numpy(x, y, z)`: takes `np.ogrid` arrays shaped `(nx,1,1)`, `(1,ny,1)`, `(1,1,nz)`. It must be truly vectorized, because meshing and viewing use this path.
- `__data__` / `__from_data__`: children such as `self.objs` can be put straight into `__data__`, and COMPAS JSON serializes nested `Data` recursively.
- `__repr__`, using `format_number` for floats.

`VolObject` also defines `|`, `&` and `-` as Union, Intersection and Subtraction.

Shared helpers in `base.py`, which new code should use:
- `transform_numpy(matrix, x, y, z)`: applies a 4x4 transform to grids. It skips zero coefficients, so outputs are broadcast only over the axes they depend on -- callers needing a common shape use `np.broadcast_shapes` (all current ones do). This is what makes plan shapes (extrusions) cost one evaluation per plan point. Never build `np.array([x, y, z, 1], dtype=object)`. That was the COMPAS 1 approach, and it breaks on NumPy 2.
- `inverse_matrix_from_frame(frame)`: maps world coordinates into a frame's local space. Frame-based primitives use it.
- `broadcast_distances(...)`: call this before reducing several children's distance arrays. A child can return a smaller shape, e.g. `VolPlane` returns `(nx,1,1)`.
- `VolObject._as_point(point)`: copies the query point. Use it before transforming a point in `get_distance`, so the caller's point isn't mutated (upstream had this bug).

**Subpackages** (each `__init__.py` has an `autosummary` list, which is what generates the API docs, so add new public classes there):
- `primitives/`: leaf SDFs, mostly wrapping `compas.geometry` shapes (`VolSphere(Sphere)`, `VolBox(Box, radius)`, …). `VolGrid.from_mesh` is the general way arbitrary geometry becomes a field — `VolPolyhedron` only covers convex solids. Its magnitude is the distance to a dense surface sampling (samples placed under half a voxel apart, so the error is below the grid's own resolution) and its **sign is exact**, from counting triangle crossings along +Z. The two ray nudges in `_mesh_field.py` are deliberately unequal: an equal nudge keeps the ray on the `x = y` diagonal, which is exactly where a fanned quad puts its shared edge, and every axis-aligned box then reads inside-out.
- `combinations/`: CSG and field arithmetic over child objects (Union, SmoothUnion, Morph, Blend, Addition, …).
- `modifications/`: wrap one object and change its field (Shell, Twist, VolTransformation, Blur, …). `Conform` is the domain-warp worth knowing: it substitutes a *guide's signed distance* for one coordinate, so a periodic field repeats in shells parallel to the guide rather than in flat world layers — the way to run a lattice along a curved skin instead of slicing it. Only the substituted axis follows the guide; the other two stay world coordinates, so cells stretch where the surface turns across them. A lattice that conforms in all three directions needs a global parametrization of the solid, which is a hex-meshing problem and not a field operation. `Remap` maps a field's value into a parameter range, which turns any object into a driver for graded parameters.
- `microstructures/`: infinite periodic or stochastic fields (TPMS, Lattice, Voronoi, polar and attractor-graded variants). `TPMSSolid` is the designer-facing TPMS: `cell_size` is the true period, and `thickness`/`offset` are in model units (the field is converted to an approximate distance with complex-step derivatives) and accept a VolObject as a driver field. The raw `TPMS` class has period `2 * wavelength` and is not metric. `TPMSTYPES` indices are append-only; unknown names raise, and `"SchwartzP"` is kept as an alias of `"SchwarzP"`.
- `analysis/`: `Gradient` and `Curvature`, computed by finite differences over any object.
- `meshing/`: `iso_surface` holds samples at least 1e-3 voxel off the level (on their own side): a face on a grid plane otherwise gives zero-area triangles that weld into non-manifold STL edges. `sample` (SDF → grid, threaded in slabs by default; `workers=1` to opt out), `iso_surface` (grid → vertices/faces, which `generate_vertices_and_faces` uses for its second half), `generate_mesh` (→ compas `Mesh`), `write_stl`/`export_stl` (arrays → binary STL, ~45x faster than building a `Mesh` and calling `to_stl`, which dominated runtime), `normalize_bounds`, and an adaptive `Octree`.
- `processes/`: geometry by process. `evolve` is the only loop (`phi += speed * |grad phi|`, then redistance); `terms.py` holds the composable speed terms; `weathering.py`, `growth.py` and `generators.py` are presets built from them; `field.py` holds `Field` (values + origin + spacing + history) and `redistance`. Needs the `processes` extra (scikit-fmm).
  - **Constraints live in `Field.redistanced()`.** `constrain(keep, within, margin)` stores sampled arrays on the field; `copy()` and `cropped()` carry them; `redistanced()` imposes `min(phi, keep)` / `max(phi, within)` before and after fast marching, and `evolve`/`displaced` scale speeds through `falloff()`. That single hook is why no preset takes a constraint parameter -- keep it that way, and make any new process end in `redistanced()`. `opened`/`closed` clip to their input because a kept part would otherwise be dilated.
  - `pitting(resistance=...)` means resistance, as in `differential`: 1 never pits (this was inverted until the roof example caught it).
- `fabrication/`: printability checks (`inspect` → `Report`) and repairs (`keep_largest`, `drain_voids`, `make_self_supporting`). Analysis is pure scipy; repairs redistance, so they need the `processes` extra. Two conventions worth keeping: the model's lowest occupied layer is the build plate (so it is never an "island", and support sweeps stop there), and wall thickness is read from the field (`-phi` at the ridge), not from a distance transform of the voxel mask, which inflates thin walls by about a voxel.
- `assembly/`: the orchestration layer above everything else. `segment` cuts a model into `Piece`s, each the model intersected with its own box; `Pins` adds clearance and pin/socket registration across shared faces, placing pins only where the field has material on both sides; `Assembly.check` inspects every piece. Two facts drive the design: a piece's `bounds` is small, so **memory is bounded by the piece and not the building** (a 6 m canopy at 1 mm voxels is ~1 TB whole and 512 MB per 400 mm piece); and **a piece cut from a lattice is usually not one part**, because struts held by material outside the box are cut loose — expect `keep_largest` to drop slivers, and treat a large share as a sign the cut is in the wrong place.
  - Everything goes through *cells*: a grid (`segment(piece=...)`) is one way to make them, `segment(cells=...)` takes any non-overlapping boxes with names and roles. `_interfaces` finds every shared face (T-junctions included); clearance and `Pins.apply` work from `Assembly.interfaces`, never from grid indices.
  - Joints are recorded as `Piece.features` (`Piece.add`/`remove`, with `reach` for how far a pin stands proud) so `Piece.bake` can re-apply them after a process -- a pin is machined, not weathered. `Piece.process_field` samples `piece.model` (the uncut design) over the box plus a halo on a world lattice (`voxel=`); `bake` crops, re-joints and pads by `reach` + two voxels so the mesh closes.
  - `layout.py`: `place_cuts` (dynamic programming over candidate positions) scored by `section_cost`, the void area of the cut plane. Score against the drawn design, not one with foam in it, whose noise swamps the features. Cuts are axis-aligned boxes. `Assembly.build` yields `(piece, finished, processed)` one piece at a time; `Seams` compares neighbours' processed fields on shared faces and keeps only face samples.
- `scene/`: viewer integration (see below).
- `utilities/`: `dumps_tree` / `loads_tree` (JSON; this replaces the upstream `eval(repr)` transport).

**Viewer integration** follows the COMPAS 2 plugin pattern. `compas_vol/__init__.py` declares `__all_plugins__ = ["compas_vol.scene"]`. `scene/__init__.py` registers `VolObjectSceneObject` against the `VolObject` base for the `"Viewer"` context, and registration resolves through the MRO. Users call `viewer.scene.add(obj, bounds=..., resolution=...)`, and `bounds` is required because SDFs have no inherent extent. The scene object imports `compas_viewer` lazily, so the core package doesn't depend on it. There is intentionally no `view()` convenience wrapper.

Optional-dependency imports are kept local so that `import compas_vol` works on a core-only install. **Route every one of them through `compas_vol.runtime.require`** (`ndimage = require("scipy.ndimage")`), never a bare `from scipy import ...`: `require` turns `No module named 'skimage'` into a message naming the extra to install, and `_PROVIDERS` in `runtime.py` is the one table that knows which extra provides what. `scripts/check_headless.py` runs in CI on an install with nothing but compas and numpy and checks both halves of that contract. Note that scipy is *not* really optional -- compas depends on it -- so the `meshing` extra effectively only adds scikit-image.

**Three contexts.** `compas_vol.runtime.context()` returns `headless`, `viewer` or `rhino`. Nothing in the package draws or converts geometry itself: the viewer is a COMPAS plugin (`scene/`), and Rhino conversion happens only in `ghpython/`. Keep it that way -- it is what lets one source run in all three.

- `nodes.py` is the components without Grasshopper: one function per component (`Cv_Box` -> `nodes.box`), same input names and order, COMPAS/NumPy types in and out, `None` for an unwired input. Component logic goes here, so it is tested and can run headless.
- `ghpython/__init__.py` holds the Rhino conversions (`point_to_compas`, `plane_to_frame`, `box_to_bounds`, `mesh_to_rhino`). They are duck-typed, so tests use stand-ins instead of Rhino.
- `ghpython/components/Cv_*/` holds the component bundles (`code.py`, `metadata.json`, 24x24 `icon.png`). These are **data, not modules** -- they import `ghpythonlib` and reference `ghenv`, so pytest is told to skip them in `addopts` and `tests/test_ghpython.py` validates them by parsing instead. A component is a signature, input conversions, one `nodes.<name>(...)` call and an output conversion; `tests/test_ghpython.py` enforces the call and the signature match.
- Icons come from 12x12 text sketches in `scripts/make_icons.py`; edit the sketch, rerun it, commit both.
- `scripts/ghuser` builds the `.ghuser` files with ghuser-builder: the sibling checkout `../ghuser-builder` first, then `../../ghuser-builder`, or `GHUSER_BUILDER`; it prints which, because a second, stale clone at `~/Developer/ghuser-builder` was silently used for a while. `dev` is `ghuser_dev.py deploy`: it builds with the installed Rhino 8, adds `# env: <checkout>/src` (library edits need no rebuild), links `build/ghuser-dev` into Grasshopper's User Object folder as `compas_vol-dev` (older copies with the same instanceGuids are moved to `~/.cache/ghuser-builder/backups`), checks `# r:` requirements and `import compas_vol` in Rhino's Python, and purges `compas_vol` from a running Rhino's `sys.modules` via `rhinocode`. Never tell anyone to copy or symlink the build folder by hand. The default runs the Docker image. Both read every file back through `GH_IO.dll` and compare it to its source.
- Process components (`subcategory: Processes`) all return `(VolGrid, history)`. A `VolGrid` with `bounds` unwired runs on its own grid (`nodes._field`), which is how processes chain without resampling; `nodes.mesh`/`nodes.inspect` read the domain off a grid the same way. Their nodes pass only wired inputs through (`nodes._options`), so the defaults live once, in `processes/`. `tests/test_ghpython.py::PROCESS_CASES` needs an entry per process component.
- Every `code.py` imports `System` and `Rhino` at module level, unused: Rhino 8 rewrites `RunScript` with annotations from the input types and evaluates them at class definition, so without them any component with a geometry- or list-typed input fails with "Error getting GH_ScriptInstance instance". Process components end with a `run` input; the component holds its last result on `self.held` when it is `False`, while the node just returns `(None, None)`. Rhino caches imported modules, so after changing a node's signature restart Rhino (dev builds read `src/` but don't reload it).
- Adding a component needs a fresh `instanceGuid`; a duplicate makes Grasshopper treat two components as one. `tests/test_ghpython.py` checks that, and that input names agree between `metadata.json`, `RunScript` and the docstring tooltip.

## Testing conventions

- `tests/conftest.py::build_objects()` holds one instance of every volumetric class. Any test with a `volobject` argument is parametrized over all of them, and the shared checks are: scalar and numpy distances agree, queries don't mutate their input, and JSON round-trips work. **A new class needs one entry there.** Where the class takes a frame, build it with `SKEW_FRAME`.
- A new class also needs an analytic test (a known distance at a known point) in `tests/test_geometry.py`.
- Bug fixes get a regression test in `tests/test_regressions.py` that fails before the fix.
- Public classes and functions carry NumPy-style docstrings with an `Examples` section. These are executed as doctests.

## PR requirements

- CI fails a PR that doesn't touch `CHANGELOG.md`. Add an entry under `## Unreleased`.
- Contributors add themselves to `AUTHORS.md`.
- The version is bumped with bumpversion (`.bumpversion.cfg`), which updates `pyproject.toml`, `docs/conf.py`, `src/compas_vol/__init__.py` and the CHANGELOG heading together.

## Docs

`README.md` is a front page: install, a quick start, and a table pointing into `docs/`. Topics live in one page each -- `intro`, `gettingstarted/`, `examples` (generated from `examples/README.md`), `processes`, `fabrication`, `assembly`, `contexts`, `grasshopper` (using the components), `development` (building components, tests), `porting` -- so add to the page that owns a topic; the README only links to it. Write plainly: say what a thing does and the one fact that matters; skip "X, not Y" contrasts and justifications the reader did not ask for.

## Scope

This package is for field/SDF modelling only. Mesh-based methods (minimal-surface relaxation, tessellation, panels, fabrication outlines) live in the sibling package `../compas_tess`; don't add them here.

It is also general-purpose. A project built with it -- a brief, a drawing, its own checks, anything with a building type in its name -- lives beside it as an application, like `../roof` (the grid roof: drainage in plan, a plan height field, a world-coherent foam, a beam-grid kit of parts, its walkthrough notebook and batch build) and `../prints`. Add something to compas_vol only when it is general and more than one project would otherwise write it; `Assembly.build`, `Seams` and `meshing.is_watertight` came in that way. The roof's classes left this package on purpose; don't bring them back without that reason.

## Examples

`examples/` is one curated sequence, `NN_name.py`, numbered in reading order with no gaps and indexed by topic in `examples/README.md` (modelling, microstructures, grading, processes, assembly); `docs/examples.rst` mirrors that index. One idea per script: fold a new variant into the example it belongs to rather than adding a near-duplicate, and add a new example when a general feature has none. They share sampling, viewing and slice inspection in `examples/_common.py` (`demo(shape, name, bounds=..., resolution=...)`), and `template.py` shows the pipeline without it. `tests/test_examples.py` checks numbering, parsing, that every import still exists, and that every example is in the index; running them (viewer, simulations) is left to whoever edits them -- run their module-level code headless with `runpy.run_path(path, run_name="example")` from inside `examples/`.
