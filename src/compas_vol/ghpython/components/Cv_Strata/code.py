# r: scikit-fmm>=2025.1.29
"""
Bedding: hard and soft layers weathering into ledges and overhangs.

The layers run through the whole mass, tilted by the normal and bent by
noise, so the ledges follow the bedding rather than being a pattern on
the surface. The cheapest way to make a massing read as rock.

    Args:
        vol: The starting solid. A process result runs on its own grid when
            bounds is unwired.
        bounds: The box to sample vol over. Leave unwired to run on a process
            result's own grid.
        resolution: Samples per axis. Defaults to 64. Sets the finest feature:
            below two voxels, nothing survives.
        thickness: Bed thickness, in mm. Defaults to 10.
        normal: Perpendicular to the beds; tilt it to dip them. Defaults to
            slightly off vertical.
        depth: Millimetres removed from the softest beds. Defaults to 5.
        wobble: How far the beds wander, in mm. 0 keeps them flat. Defaults to
            3.
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


class CompasVolStrata(component):
    def RunScript(
        self,
        vol,
        bounds,
        resolution: int,
        thickness: float,
        normal,
        depth: float,
        wobble: float,
        seed: int,
        run: bool,
    ):
        from compas_vol import nodes
        from compas_vol.ghpython import box_to_bounds, vector_to_compas

        # The script instance survives between solutions, so it can hold a result.
        if run is not False:
            self.held = nodes.strata(
                vol, box_to_bounds(bounds), resolution, thickness, vector_to_compas(normal), depth, wobble, seed, run
            )
        return getattr(self, "held", (None, None))
