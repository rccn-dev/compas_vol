"""Check that a core-only install is genuinely usable, and fails helpfully.

The package promises two things about a bare ``pip install compas-vol``: that
importing it and building a tree of objects needs nothing but compas and
numpy, and that asking for something heavier tells you which extra to install
rather than dying with ``No module named 'skimage'``.

Both are easy to break by adding one import at the top of a module, and no
ordinary test would catch it, because the test environment has everything
installed. So this runs in CI in an environment with nothing else present.

Run it the same way locally::

    uv run -p 3.9 --no-default-groups python scripts/check_headless.py
"""

import sys


def main():
    from compas.geometry import Sphere

    import compas_vol  # noqa: F401  -- the bare import is the thing being checked
    from compas_vol.combinations import Union
    from compas_vol.primitives import VolBox, VolSphere
    from compas_vol.runtime import capabilities, context, report

    print(report())
    print()

    caps = capabilities()
    # scipy is not checked: compas depends on it, so it is always present and
    # the meshing extra only really adds scikit-image.
    if caps["skimage"] or caps["skfmm"]:
        raise SystemExit("This check only means something with the extras absent; found {}.".format(caps))
    if context() != "headless":
        raise SystemExit('Expected the "headless" context, got "{}".'.format(context()))

    # Building and evaluating a tree must work on the core alone.
    from compas.geometry import Box

    tree = Union(VolSphere(Sphere(5.0)), VolBox(Box(8.0), 1.0))
    distance = tree.get_distance([0.0, 0.0, 0.0])
    if distance >= 0:
        raise SystemExit("The origin should be inside the union; got {}.".format(distance))
    if compas_vol.__version__ is None:
        raise SystemExit("No version.")
    print("core          : import, build and evaluate all work")

    # Serialization is core too: it is how a headless run hands work on.
    from compas_vol.utilities import dumps_tree, loads_tree

    if loads_tree(dumps_tree(tree)).get_distance([0.0, 0.0, 0.0]) != distance:
        raise SystemExit("A round-tripped tree measures differently.")
    print("serialization : JSON round-trip preserves the field")

    # And anything needing an extra must say so by name.
    from compas_vol.meshing import generate_mesh

    try:
        generate_mesh(tree, 8.0, 16)
    except ImportError as error:
        if "compas-vol[meshing]" not in str(error):
            raise SystemExit("The error does not name the extra to install: {}".format(error))
        print("missing extra : {}".format(error))
    else:
        raise SystemExit("Meshing succeeded without scikit-image, which cannot be right.")

    print("\nA core-only install behaves as documented.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
