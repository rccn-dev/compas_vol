# r: scikit-fmm>=2025.1.29
"""
Enforce a minimum feature size: remove what is too thin, or fill what is too narrow.

The clean-up after a process. open removes every wall, strut and
fragment thinner than twice the radius; close fills every gap narrower
than that and rejoins pieces that nearly touch. Everything larger keeps
its size, to within about half a voxel.

    Args:
        vol: The starting solid. A process result runs on its own grid when
            bounds is unwired.
        bounds: The box to sample vol over. Leave unwired to run on a process
            result's own grid.
        resolution: Samples per axis. Defaults to 64. Sets the finest feature:
            below two voxels, nothing survives.
        operation: open or close. Defaults to open.
        radius: Half the thinnest feature to keep, or the widest gap to fill,
            in mm. Defaults to 1.
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


class CompasVolMorphology(component):
    def RunScript(self, vol, bounds, resolution: int, operation: str, radius: float, run: bool):
        from compas_vol import nodes
        from compas_vol.ghpython import box_to_bounds

        # The script instance survives between solutions, so it can hold a result.
        if run is not False:
            self.held = nodes.morphology(vol, box_to_bounds(bounds), resolution, operation, radius, run)
        return getattr(self, "held", (None, None))
