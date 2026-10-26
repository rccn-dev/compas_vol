# r: scikit-fmm>=2025.1.29
"""
Gray-Scott reaction-diffusion, set solid: spots, worms and labyrinths.

The least predictable process here. The pattern scales with the
resolution, not the box, and neighbouring feed and kill values give
patterns that look nothing alike -- or nothing at all, which shows as an
error. For labyrinths try feed 0.02 to 0.04 and kill 0.05 to 0.065.

    Args:
        bounds: The box to fill. Required: there is no starting shape.
        resolution: Samples per axis. Defaults to 64.
        feed: Feed rate. Defaults to 0.037.
        kill: Kill rate. Defaults to 0.06.
        steps: Defaults to 1500.
        level: Concentration taken as the surface. Defaults to 0.25.
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


class CompasVolReactionDiffusion(component):
    def RunScript(
        self,
        bounds,
        resolution: int,
        feed: float,
        kill: float,
        steps: int,
        level: float,
        seed: int,
        run: bool,
    ):
        from compas_vol import nodes
        from compas_vol.ghpython import box_to_bounds

        # The script instance survives between solutions, so it can hold a result.
        if run is not False:
            self.held = nodes.reactiondiffusion(box_to_bounds(bounds), resolution, feed, kill, steps, level, seed, run)
        return getattr(self, "held", (None, None))
