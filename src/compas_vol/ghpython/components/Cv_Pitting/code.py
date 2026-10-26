# r: scikit-fmm>=2025.1.29
"""
Weathering into hollows that deepen themselves: tafoni and honeycombing.

Pits start where the rock is weakest, then run away with it, because a
hollow shelters itself. Left long enough, neighbouring pits merge into
honeycombed walls. Most of the surface loses nothing at all, which is the
difference from general weathering.

    Args:
        vol: The starting solid. A process result runs on its own grid when
            bounds is unwired.
        bounds: The box to sample vol over. Leave unwired to run on a process
            result's own grid.
        resolution: Samples per axis. Defaults to 64. Sets the finest feature:
            below two voxels, nothing survives.
        depth: Millimetres removed at the weakest, deepest point. Defaults to
            9.
        length: Roughly the width of a pit, in mm. Defaults to 6.
        threshold: Hardness, -1 to 1, above which nothing pits. Raise for fewer
            pits. Defaults to 0.2.
        feedback: How much a hollow speeds its own deepening. Defaults to 1.7.
        cell: Size of the weak patches pits start in, in mm. Defaults to 25.
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


class CompasVolPitting(component):
    def RunScript(
        self,
        vol,
        bounds,
        resolution: int,
        depth: float,
        length: float,
        threshold: float,
        feedback: float,
        cell: float,
        seed: int,
        run: bool,
    ):
        from compas_vol import nodes
        from compas_vol.ghpython import box_to_bounds

        # The script instance survives between solutions, so it can hold a result.
        if run is not False:
            self.held = nodes.pitting(
                vol, box_to_bounds(bounds), resolution, depth, length, threshold, feedback, cell, seed, run
            )
        return getattr(self, "held", (None, None))
