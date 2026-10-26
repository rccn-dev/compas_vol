# r: scikit-fmm>=2025.1.29
"""
Rain: water gathers downhill over the top of the model and cuts gullies.

Flow accumulates over the topmost surface of each column, so only what a
raindrop can reach is cut. Undersides and the inside of overhangs are
left alone -- true of rain, and also this method's limit.

    Args:
        vol: The starting solid. A process result runs on its own grid when
            bounds is unwired.
        bounds: The box to sample vol over. Leave unwired to run on a process
            result's own grid.
        resolution: Samples per axis. Defaults to 64. Sets the finest feature:
            below two voxels, nothing survives.
        depth: Millimetres cut where the flow is heaviest. Defaults to 6.
        decay: How far the cut reaches below the surface, in mm. Defaults to
            10.
        smooth: Blur on the flow, in voxels. Higher gives fewer, broader
            channels. Defaults to 0.9.
        concentration: Lower spreads the cutting; higher gathers it into a few
            deep gullies. Defaults to 0.4.
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


class CompasVolRunoff(component):
    def RunScript(
        self,
        vol,
        bounds,
        resolution: int,
        depth: float,
        decay: float,
        smooth: float,
        concentration: float,
        run: bool,
    ):
        from compas_vol import nodes
        from compas_vol.ghpython import box_to_bounds

        # The script instance survives between solutions, so it can hold a result.
        if run is not False:
            self.held = nodes.runoff(vol, box_to_bounds(bounds), resolution, depth, decay, smooth, concentration, run)
        return getattr(self, "held", (None, None))
