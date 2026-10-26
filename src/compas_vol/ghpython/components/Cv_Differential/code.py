# r: scikit-fmm>=2025.1.29
"""
Weathering by hardness: soft rock retreats, hard rock stands proud.

Hardness is a noise field in world coordinates, so the same design
weathers the same way at any resolution. One pass and no iteration: the
cheapest of the weathering components.

    Args:
        vol: The starting solid. A process result runs on its own grid when
            bounds is unwired.
        bounds: The box to sample vol over. Leave unwired to run on a process
            result's own grid.
        resolution: Samples per axis. Defaults to 64. Sets the finest feature:
            below two voxels, nothing survives.
        depth: Millimetres removed where the rock is softest. Defaults to 7.
        cell: Size of the hard and soft patches, in mm. Defaults to 25.
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


class CompasVolDifferential(component):
    def RunScript(self, vol, bounds, resolution: int, depth: float, cell: float, seed: int, run: bool):
        from compas_vol import nodes
        from compas_vol.ghpython import box_to_bounds

        # The script instance survives between solutions, so it can hold a result.
        if run is not False:
            self.held = nodes.differential(vol, box_to_bounds(bounds), resolution, depth, cell, seed, run)
        return getattr(self, "held", (None, None))
