# r: scikit-fmm>=2025.1.29
"""
Joints: the mass breaks into blocks, the seams opening from the outside in.

The joint set is a Voronoi diagram, and the seams taper closed reach
millimetres inside, which keeps the result one object. Set reach larger
than the model to cut it into loose blocks on purpose.

    Args:
        vol: The starting solid. A process result runs on its own grid when
            bounds is unwired.
        bounds: The box to sample vol over. Leave unwired to run on a process
            result's own grid.
        resolution: Samples per axis. Defaults to 64. Sets the finest feature:
            below two voxels, nothing survives.
        count: Number of blocks, when points is not wired. Defaults to 25.
        opening: Seam width at the surface, in mm. Defaults to 2.5.
        reach: How far in the seams stay open, in mm. Defaults to 12.
        seed: Which variation. Change it for another result with the same
            character.
        points: Block centres, to place the joints by hand.
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


class CompasVolJointing(component):
    def RunScript(
        self,
        vol,
        bounds,
        resolution: int,
        count: int,
        opening: float,
        reach: float,
        seed: int,
        points,
        run: bool,
    ):
        from compas_vol import nodes
        from compas_vol.ghpython import box_to_bounds, point_to_compas

        points = [point_to_compas(p) for p in points or []]
        # The script instance survives between solutions, so it can hold a result.
        if run is not False:
            self.held = nodes.jointing(vol, box_to_bounds(bounds), resolution, count, opening, reach, seed, points, run)
        return getattr(self, "held", (None, None))
