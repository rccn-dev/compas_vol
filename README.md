# compas_vol

Volumetric modelling with signed distance functions, for **COMPAS 2**.

A fork of [`dbt-ethz/compas_vol`](https://github.com/dbt-ethz/compas_vol) by Mathias
Bernhard (Digital Building Technologies, ETH Zurich), ported to COMPAS 2.15 and NumPy 2,
with its defects fixed and processes, fabrication checks, assembly and Grasshopper
components added. See [AUTHORS.md](AUTHORS.md) for credits.

## Install

```bash
git clone https://github.com/rccn-dev/compas_vol
cd compas_vol
uv sync                        # core: compas + numpy
uv sync --extra meshing        # + scikit-image: meshing and STL export
uv sync --extra processes      # + scikit-fmm: erosion, growth, phase separation
uv sync --extra all            # everything, including the viewer and the examples
```

Python 3.9 or newer: 3.9 is the interpreter Rhino 8 embeds, so the package also runs in
Grasshopper; see [grasshopper](docs/grasshopper.rst) to install it there.

## Quick start

```python
from compas.geometry import Box, Point, Sphere
from compas_vol.combinations import Subtraction
from compas_vol.meshing import export_stl
from compas_vol.primitives import VolBox, VolSphere

shape = Subtraction(
    VolBox(Box(20, 15, 10), radius=2.5),
    VolSphere(Sphere(9, point=Point(5, 6, 0))),
)
shape.get_distance((0, 0, 0))                              # signed distance at a point
export_stl(shape, "part.stl", bounds=20.0, resolution=200)
```

## Documentation

| Topic | Page |
|---|---|
| fields, and how the package is organised | [intro](docs/intro.rst) |
| installing, first steps, meshing, viewing, JSON | [getting started](docs/gettingstarted/firststeps.rst) |
| erosion, growth, phase separation, constraints | [processes](docs/processes.rst) |
| printability checks and repairs | [fabrication](docs/fabrication.rst) |
| models built in pieces | [assembly](docs/assembly.rst) |
| headless and viewer use | [contexts](docs/contexts.rst) |
| the Grasshopper components | [grasshopper](docs/grasshopper.rst) |
| building components, tests, docs | [development](docs/development.rst) |
| differences from the original | [porting](docs/porting.rst), [CHANGELOG](CHANGELOG.md) |

Build the HTML docs with `uv sync --group docs && uv run sphinx-build -b html docs docs/_build/html`.

## Examples

[`examples/`](examples) holds 26 scripts in reading order: modelling, microstructures,
grading, processes, assembly. See the [index](examples/README.md).

```bash
uv sync --extra examples
uv run python examples/02_booleans.py
```

## Related

- [grid-roof](https://github.com/rccn-dev/grid-roof): an 18 × 12 m roof designed and built
  in pieces with this package, as a notebook and as Grasshopper components.
- [designing-by-process](https://github.com/rccn-dev/designing-by-process): a five-day
  workshop on both.

## License

MIT, as the original; the upstream copyright notice is retained. See [LICENSE](LICENSE).
