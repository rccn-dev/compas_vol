# r: scikit-fmm>=2025.1.29
"""
Growth that fills hollows: deposition settling where it is sheltered.

The opposite bias to Pitting. Material lands where flow is slow, which
is in the hollows, so the surface smooths and fills -- useful for
softening a model that weathering has left too jagged to build.

    Args:
        vol: The starting solid. A process result runs on its own grid when
            bounds is unwired.
        bounds: The box to sample vol over. Leave unwired to run on a process
            result's own grid.
        resolution: Samples per axis. Defaults to 64. Sets the finest feature:
            below two voxels, nothing survives.
        height: Millimetres deposited in the most sheltered places. Defaults to
            4.
        reach: How far around each point shelter is measured, in mm. Defaults
            to 8.
        shelter: How strongly deposition prefers hollows. 0 coats evenly.
            Defaults to 1.6.
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


class CompasVolAccretion(component):
    def RunScript(self, vol, bounds, resolution: int, height: float, reach: float, shelter: float, run: bool):
        from compas_vol import nodes
        from compas_vol.ghpython import box_to_bounds

        # The script instance survives between solutions, so it can hold a result.
        if run is not False:
            self.held = nodes.accretion(vol, box_to_bounds(bounds), resolution, height, reach, shelter, run)
        return getattr(self, "held", (None, None))
