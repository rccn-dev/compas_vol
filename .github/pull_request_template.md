<!-- Thank you for your pull request! -->
<!-- Please start by describing your change in a few sentences. -->
<!-- You can erase any parts of this template not applicable to your Pull Request. -->

### What type of change is this?

- [ ] Bug fix in a **backwards-compatible** manner.
- [ ] New feature in a **backwards-compatible** manner.
- [ ] Breaking change: bug fix or new feature that involves incompatible API changes.
- [ ] Other (e.g. doc update, configuration, etc)

### Checklist

_Put an `x` in the boxes that apply. You can also fill these out after creating the PR. If you're unsure about any of them, don't hesitate to ask — this is a reminder of what we look for before merging, not a barrier._

- [ ] I added a line to `CHANGELOG.md` under `## Unreleased`, in the most fitting subsection (`Added`, `Changed`, `Fixed`, `Removed`). **CI fails without this.**
- [ ] Tests pass: `uv run --extra meshing python -m pytest`
- [ ] Lint passes: `uv run ruff check .`
- [ ] I added tests that prove my fix is effective or that my feature works.
      Bug fixes go in `tests/test_regressions.py`; a new volumetric class goes
      into `build_objects()` in `tests/conftest.py`.
- [ ] New classes/functions are available on a second-level import
      (e.g. `compas_vol.primitives.VolBox`) and are listed in the `autosummary`
      block of the containing `__init__.py`.
- [ ] Any new field implements **both** `get_distance` and `get_distance_numpy`,
      and the vectorized path is NumPy-2 safe (no `dtype=object`).
- [ ] I added the necessary documentation (if appropriate), and
      `uv run sphinx-build -b html -W docs docs/_build/html` succeeds.
- [ ] I added myself to `AUTHORS.md`.

<!-- See CONTRIBUTING.md for the full development workflow. -->
