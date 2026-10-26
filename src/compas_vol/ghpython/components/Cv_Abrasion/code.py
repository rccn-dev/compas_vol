# r: scikit-fmm>=2025.1.29
"""
Weathering that rounds: what sticks out wears first.

Convex parts of the surface meet the wind and the water; hollows are
sheltered. Run far enough, any massing turns into a boulder -- which is
also the limit: it only ever removes distinction. Pair it with Pitting
or Strata for something that reads as rock.

    Args:
        vol: The starting solid. A process result runs on its own grid when
            bounds is unwired.
        bounds: The box to sample vol over. Leave unwired to run on a process
            result's own grid.
        resolution: Samples per axis. Defaults to 64. Sets the finest feature:
            below two voxels, nothing survives.
        depth: Millimetres removed from a flat face. Edges lose more. Defaults
            to 4.
        length: Roughly the radius the sharpest edge ends up with, in mm.
            Defaults to 9.
        edge_bias: How much faster an edge wears than a face. 0 wears evenly.
            Defaults to 2.
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


class CompasVolAbrasion(component):
    def RunScript(self, vol, bounds, resolution: int, depth: float, length: float, edge_bias: float, run: bool):
        from compas_vol import nodes
        from compas_vol.ghpython import box_to_bounds

        # The script instance survives between solutions, so it can hold a result.
        if run is not False:
            self.held = nodes.abrasion(vol, box_to_bounds(bounds), resolution, depth, length, edge_bias, run)
        return getattr(self, "held", (None, None))
