# Contributing

Contributions are welcome. This document describes how to set up a working
environment, what is expected of a change, and how to get it merged.

`compas_vol` is a fork of [dbt-ethz/compas_vol](https://github.com/dbt-ethz/compas_vol).
Issues and pull requests belong on **this** repository,
[rccn-dev/compas_vol](https://github.com/rccn-dev/compas_vol) — the upstream
project targets COMPAS 1 and is maintained separately. If a bug also affects
upstream, it is worth reporting there too.

## Getting set up

This project uses [uv](https://docs.astral.sh/uv/). It manages the Python
version as well as the dependencies, so no separate virtualenv or conda step is
needed.

```bash
git clone https://github.com/<your-username>/compas_vol
cd compas_vol
uv sync --extra meshing --group dev
```

That gives you the package, the iso-surfacing dependencies, `pytest` and
`ruff`. Two further groups exist:

```bash
uv sync --extra all      # adds the viewer (PySide6) and matplotlib
uv sync --group docs     # adds Sphinx, for building the documentation
```

Verify the setup before changing anything:

```bash
uv run --extra meshing python -m pytest
```

## Making a change

1. **Fork** this repository and clone your fork.
2. **Branch off `main`.** There is no `master` branch. Name the branch for what
   it does, e.g. `fix-twist-angle` or `add-voronoi-seeding`.
3. Make your change, with tests (see below).
4. Run the checks:

   ```bash
   uv run ruff check .
   uv run --extra meshing python -m pytest
   ```

5. **Add a `CHANGELOG.md` entry** under `## Unreleased`, in the appropriate
   subsection. This is not optional — CI fails a pull request that does not
   touch the changelog. Describe the change from a user's point of view.
6. **Add yourself** to the *Contributors* section of `AUTHORS.md`.
7. Commit, push to your fork, and open a
   [pull request](https://help.github.com/articles/about-pull-requests/)
   against `main`.

## What a change needs

### Tests

The suite is parametrized over one instance of every volumetric class. Each
instance is checked to ensure that:

* `get_distance` and `get_distance_numpy` agree on a grid to machine precision,
* querying does not mutate the point it was passed,
* the object survives a `json_dumps` / `json_loads` round trip.

**A new volumetric class needs one line, not a new test file.** Add an instance
to the `build_objects()` dictionary in `tests/conftest.py`, keyed by a readable
id, and every check above starts running against it. Construct it with the
shared `SKEW_FRAME` where the class takes a frame — it is deliberately neither
axis-aligned nor origin-centred, so a mismatch between the single-point and
vectorized transforms shows up.

Also add an analytic test pinning the geometry itself — a known distance to a
known point — in `tests/test_geometry.py`. The shared checks prove the two code
paths agree with each other; only an analytic case proves they are both right.

**A bug fix needs a regression test** in `tests/test_regressions.py`, written so
that it fails before your fix and passes after. This is how every defect
inherited from upstream is pinned, and it is the convention that keeps them
from coming back.

### Both distance methods

Anything implementing a field implements both `get_distance(point)` and
`get_distance_numpy(x, y, z)`. The two must agree — the suite checks this — and
the vectorized form must not fall back to looping over points, since that is the
path meshing and viewing actually use.

Vectorized code must work under **NumPy 2**. In particular, do not build
coordinate arrays with `dtype=object`; use `compas_vol.base.transform_numpy`
for transformations.

### Style

`ruff` enforces the parts of style that are worth enforcing:

```bash
uv run ruff check .          # report
uv run ruff check --fix .    # fix what is mechanically fixable
```

The configuration lives in `pyproject.toml` and is deliberately narrow —
pycodestyle, pyflakes and NumPy-2 correctness. It does not impose a formatter.
Beyond it, match the surrounding code: one import per line, NumPy-style
docstrings, and a `__repr__` on every public class.

Docstrings are the API documentation — they are rendered directly by Sphinx —
so a new public class or function should carry a NumPy-style docstring with an
`Examples` section. Doctests in `src/` are collected by the test run, so those
examples are verified rather than decorative.

### Documentation

If you add a public class or function, add it to the `autosummary` list in the
containing package's `__init__.py`. That is all the API reference needs; the
pages are generated.

For prose changes, build the docs and read the result:

```bash
uv sync --group docs
uv run sphinx-build -b html -W docs docs/_build/html
```

`-W` turns warnings into errors, which is how CI builds them. A broken cross
reference will fail the build.

## Reporting a bug

Open an issue at https://github.com/rccn-dev/compas_vol/issues including:

* Operating system, Python version, and the output of `uv pip list | grep -i compas`.
* A minimal script that reproduces the problem.
* What you expected to happen, and what happened instead.

For a wrong-geometry bug, the most useful thing you can include is the query
point and the distance value you got, since that pins the failure without
requiring anyone to reproduce a mesh.

## Requesting a feature

Open an issue describing:

* How it would work, in enough detail to be implementable.
* What you would use it for.
* Whether it belongs here or in COMPAS core.

Keep the scope as narrow as possible. A focused proposal is far more likely to
be implemented than a broad one.

## Licensing of contributions

This project is MIT licensed and carries the original copyright of Digital
Building Technologies, ETH Zurich alongside that of this fork's contributors
(see `LICENSE` and `AUTHORS.md`). By contributing, you agree that your
contribution is released under the same terms. There is no CLA.

If you are porting code from another project, say so in the pull request and
make sure its license permits it.
