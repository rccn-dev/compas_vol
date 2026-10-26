# r: scikit-fmm>=2025.1.29
"""
A bicontinuous foam by phase separation: a TPMS without the unit cell.

A mixture separates into two phases that both stay connected -- how
porous glass and nanoporous metal form. You choose the feature size and
the solid fraction rather than drawing the structure; the fraction is
exact. The box is filled, and the result tiles across its faces.

    Args:
        bounds: The box to fill. Required: there is no starting shape.
        resolution: Samples per axis. Defaults to 64.
        feature: Wall and pore size, in mm. Defaults to 8.
        fraction: Solid fraction, 0 to 1. Below 0.3 the solid falls into
            islands. Defaults to 0.45.
        steps: Longer coarsens and smooths the structure. Defaults to 400.
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


class CompasVolSpinodal(component):
    def RunScript(self, bounds, resolution: int, feature: float, fraction: float, steps: int, seed: int, run: bool):
        from compas_vol import nodes
        from compas_vol.ghpython import box_to_bounds

        # The script instance survives between solutions, so it can hold a result.
        if run is not False:
            self.held = nodes.spinodal(box_to_bounds(bounds), resolution, feature, fraction, steps, seed, run)
        return getattr(self, "held", (None, None))
