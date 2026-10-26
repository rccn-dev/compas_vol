# r: scikit-fmm>=2025.1.29
"""
A branching network grown by space colonization, drawn as a solid.

Tips grow towards the points that claim them, and a tip pulled two ways
splits. Branches thicken with the number of tips they feed, so the
network tapers like a tree or a vascular system. It grows from nothing:
the box is required.

    Args:
        bounds: The box to fill. Required: there is no starting shape.
        resolution: Samples per axis. Defaults to 64.
        root: Where growth starts. Defaults to the middle of the floor of the
            box.
        attractors: Points competing to be reached; more is denser. Defaults to
            800.
        step: Length of one growth step, in mm. Defaults to 3.5.
        influence: How far a tip can be pulled from, in mm. Defaults to 22.
        thin: Radius of the finest twig, in mm. Defaults to 1.5.
        thick: Radius of the trunk, in mm. Defaults to 5.
        seed: Which variation. Change it for another result with the same
            character.
        run: False holds the last result while you change things upstream.
            Unwired, it runs.
    Returns:
        result: The result: a volumetric object to combine, run another process
            on, or mesh.
        history: How it was made, one operation per line.
"""
# Rhino 8 annotates RunScript with each input's type -- Rhino.Geometry.Box,
# System.Collections.Generic.List -- and evaluates the annotations when it
# defines the class, so both names must exist even though nothing here uses them.
import System  # noqa: F401
import Rhino  # noqa: F401
from ghpythonlib.componentbase import executingcomponent as component


class CompasVolBranching(component):
    def RunScript(
        self,
        bounds,
        resolution: int,
        root,
        attractors: int,
        step: float,
        influence: float,
        thin: float,
        thick: float,
        seed: int,
        run: bool,
    ):
        from compas_vol import nodes
        from compas_vol.ghpython import box_to_bounds, point_to_compas

        # The script instance survives between solutions, so it can hold a result.
        if run is not False:
            self.held = nodes.branching(
                box_to_bounds(bounds), resolution, point_to_compas(root), attractors, step, influence, thin, thick,
                seed, run
            )
        return getattr(self, "held", (None, None))
